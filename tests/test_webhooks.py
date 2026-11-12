"""Webhook engine tests (v0.6 Automation) — hermetic.

The signature contract, the registry (persistence, secret redaction, stats),
the event -> transition mapping, and the retry/dead-letter rules. No network,
no threads started: the worker's `_attempt` is driven directly with an
injected sender and clock.
"""
import json
import heapq
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm import webhooks
from tonearm.webhooks import (DeliveryWorker, StreamWatcher, WebhookRegistry,
                              hook_accepts, make_event, sign)


def temp_registry():
    d = tempfile.mkdtemp(prefix="tonearm-webhooks-test-")
    return WebhookRegistry(path=os.path.join(d, "webhooks.json"))


def ev(seq, key, title="Song", artist="Artist", playing=True, ts=None):
    e = {"seq": seq, "id": key, "title": title, "artist": artist,
         "album": "Album", "isPlaying": playing, "ts": ts or time.time() * 1000,
         "durationMs": 200000, "artworkUrl": None}
    return e


class TestSignature(unittest.TestCase):
    def test_is_hmac_sha256_of_the_exact_body(self):
        import hashlib
        import hmac as hmac_mod
        body = b'{"type":"track.change"}'
        expect = hmac_mod.new(b"sekrit", body, hashlib.sha256).hexdigest()
        self.assertEqual(sign("sekrit", body), expect)
        self.assertEqual(sign("sekrit", body.decode()), expect,
                         "str and bytes bodies sign identically")
        self.assertNotEqual(sign("other", body), expect)

    def test_timestamped_signature_covers_ts_and_body(self):
        import hashlib
        import hmac as hmac_mod
        body = b'{"type":"track.change"}'
        expect = hmac_mod.new(b"sekrit", b"1700000000." + body,
                              hashlib.sha256).hexdigest()
        self.assertEqual(sign("sekrit", body, ts="1700000000"), expect)
        self.assertNotEqual(sign("sekrit", body), expect,
                            "the timestamped form differs from the bare form")

    def test_event_shape_is_stable(self):
        e = make_event("track.change", {"id": "i.1"})
        self.assertTrue(e["id"].startswith("evt_"))
        self.assertEqual(e["type"], "track.change")
        self.assertEqual(e["data"], {"id": "i.1"})
        self.assertIn("T", e["created_at"])           # ISO
        self.assertTrue(e["tonearm_version"])         # versioned payloads
        self.assertNotEqual(e["id"], make_event("track.change")["id"],
                            "ids are unique — consumers dedupe on them")


class TestMatchingAndValidation(unittest.TestCase):
    def test_empty_filter_receives_everything(self):
        self.assertTrue(hook_accepts({"url": "http://x", "events": []},
                                     "track.change"))

    def test_filtered_hook_only_matches_listed_events(self):
        h = {"url": "http://x", "events": ["track.change"], "enabled": True}
        self.assertTrue(hook_accepts(h, "track.change"))
        self.assertFalse(hook_accepts(h, "playlist.created"))

    def test_disabled_hook_never_matches(self):
        self.assertFalse(hook_accepts({"url": "http://x", "events": [],
                                       "enabled": False}, "track.change"))

    def test_star_filter_normalizes_to_all(self):
        self.assertEqual(webhooks._normalize_events(["*"]), [])

    def test_unknown_event_rejected(self):
        with self.assertRaises(ValueError):
            webhooks._normalize_events(["track.change", "not.a.thing"])

    def test_url_must_be_absolute_http(self):
        for bad in ("", None, "ftp://x", "not a url", "http://"):
            with self.assertRaises(ValueError):
                webhooks._validate_url(bad)
        self.assertEqual(webhooks._validate_url(" http://ok/hook "),
                         "http://ok/hook")


class TestRegistry(unittest.TestCase):
    def test_add_update_remove_roundtrip(self):
        r = temp_registry()
        hook = r.add("http://example.test/hook", events=["track.change"],
                     secret="s3cret")
        self.assertEqual(r.count(), 1)
        self.assertEqual(hook["events"], ["track.change"])
        self.assertTrue(hook["has_secret"])
        self.assertNotIn("secret", hook,
                         "secrets are stored, never echoed back")
        self.assertEqual(json.loads(json.dumps(hook))["has_secret"], True)

        updated = r.update(hook["id"], events=[], enabled=False)
        self.assertEqual(updated["events"], [])
        self.assertFalse(updated["enabled"])
        self.assertTrue(updated["has_secret"], "update without a secret keeps it")
        self.assertTrue(r.remove(hook["id"]))
        self.assertEqual(r.count(), 0)
        self.assertFalse(r.remove(hook["id"]), "removing twice is a no-op")

    def test_same_url_updates_instead_of_duplicating(self):
        r = temp_registry()
        first = r.add("http://example.test/hook")
        second = r.add("http://example.test/hook", events=["rating.changed"])
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(r.count(), 1)
        self.assertEqual(r.get(first["id"])["events"], ["rating.changed"])

    def test_secret_can_be_cleared_with_empty_string(self):
        r = temp_registry()
        h = r.add("http://example.test/hook", secret="s")
        self.assertTrue(r.update(h["id"], secret="")["has_secret"] is False)

    def test_persists_across_reload_and_is_0600(self):
        path = os.path.join(tempfile.mkdtemp(prefix="tonearm-wh-"),
                            "webhooks.json")
        r = WebhookRegistry(path=path)
        r.add("http://example.test/hook", events=["track.change"],
              secret="s3cret")
        mode = os.stat(path).st_mode & 0o777
        self.assertEqual(mode, 0o600, "the config holds a signing secret")

        r2 = WebhookRegistry(path=path).load()
        self.assertEqual(r2.count(), 1)
        self.assertTrue(r2.public_hooks()[0]["has_secret"])

    def test_corrupt_file_starts_empty(self):
        path = os.path.join(tempfile.mkdtemp(prefix="tonearm-wh-"),
                            "webhooks.json")
        with open(path, "w") as f:
            f.write("{not json")
        self.assertEqual(WebhookRegistry(path=path).load().count(), 0)

    def test_stats_note_accumulates(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        r.note(h["id"], True, status=200)
        r.note(h["id"], False, status=500, error="boom")
        stats = r.public_hooks()[0]["stats"]
        self.assertEqual(stats["delivered"], 1)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["last_status"], 500)
        self.assertEqual(stats["last_error"], "boom")

    def test_dead_letter_cap_parks_the_url(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        with mock.patch.object(webhooks.config, "webhook_park_after", 2), \
                mock.patch.object(webhooks.config, "webhook_park_s", 60):
            r.note(h["id"], False, status=500, error="x", dead_letter=True)
            self.assertFalse(r.public_hooks()[0]["stats"]["parked"])
            r.note(h["id"], False, status=500, error="x", dead_letter=True)
        stats = r.public_hooks()[0]["stats"]
        self.assertTrue(stats["parked"], "the dead-letter cap parks the URL")
        self.assertEqual(r.matching("track.change"), [],
                         "a parked hook receives no events")

    def test_success_resets_dead_letters_and_unparks(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        with mock.patch.object(webhooks.config, "webhook_park_after", 1), \
                mock.patch.object(webhooks.config, "webhook_park_s", 60):
            r.note(h["id"], False, status=400, error="x", dead_letter=True)
            self.assertTrue(r.public_hooks()[0]["stats"]["parked"])
            r.note(h["id"], True, status=200)
        stats = r.public_hooks()[0]["stats"]
        self.assertFalse(stats["parked"], "a real success unparks")
        self.assertEqual(stats["dead_letters"], 0, "streak resets")
        self.assertTrue(r.matching("track.change"))

    def test_intermediate_retries_are_not_dead_letters(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        with mock.patch.object(webhooks.config, "webhook_park_after", 1), \
                mock.patch.object(webhooks.config, "webhook_park_s", 60):
            r.note(h["id"], False, status=503, error="x")   # will retry
        self.assertFalse(r.public_hooks()[0]["stats"]["parked"],
                         "only the FINAL failure (dead letter) parks")


def static_worker(registry, results, clock=time.time):
    """A worker whose HTTP never leaves the process: `results` is a list of
    (status, error) tuples consumed per attempt."""
    it = iter(results)

    def send(hook, event, attempt, timeout):
        return next(it)

    return DeliveryWorker(registry, send_fn=send, clock=clock)


class TestDeliveryWorker(unittest.TestCase):
    def test_submit_fans_out_to_matching_hooks_only(self):
        r = temp_registry()
        a = r.add("http://example.test/a")                       # everything
        r.add("http://example.test/b", events=["playlist.created"])
        w = static_worker(r, [])
        queued = w.submit(make_event("track.change", {}))
        self.assertEqual(queued, 1, "one event, one matching hook")
        with w._cv:
            jobs = [job for _, _, job in w._heap]
        self.assertEqual([j["hook"]["id"] for j in jobs], [a["id"]])

    def test_success_records_and_does_not_retry(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        w = static_worker(r, [(200, None)])
        result = w._attempt({"event": make_event("track.change"), "hook": r.get(h["id"]),
                             "attempt": 1, "delivery_id": "evt_x"})
        self.assertTrue(result["ok"])
        self.assertFalse(result["retry_scheduled"])
        self.assertEqual(w.pending(), 0)
        self.assertEqual(r.public_hooks()[0]["stats"]["delivered"], 1)

    def test_5xx_retries_with_backoff_then_dead_letters(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        w = DeliveryWorker(r, max_attempts=2, backoff=(7, 30),
                           send_fn=lambda *a: (503, "HTTP 503"))
        job = {"event": make_event("track.change"), "hook": r.get(h["id"]),
               "attempt": 1, "delivery_id": "evt_x"}
        result = w._attempt(job)
        self.assertFalse(result["ok"])
        self.assertTrue(result["retry_scheduled"])
        with w._cv:
            due, _, retried = heapq.heappop(w._heap)   # run() pops due jobs
        self.assertEqual(retried["attempt"], 2)
        self.assertGreaterEqual(due, time.time() + 6,
                                "backoff schedules the retry in the future")
        result = w._attempt(retried)
        self.assertFalse(result["retry_scheduled"], "max attempts reached")
        stats = r.public_hooks()[0]["stats"]
        self.assertEqual(stats["failed"], 2)
        self.assertEqual(w.pending(), 0)

    def test_client_error_is_a_dead_letter_not_a_retry(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        w = static_worker(r, [(400, "HTTP 400")])
        result = w._attempt({"event": make_event("track.change"),
                             "hook": r.get(h["id"]), "attempt": 1,
                             "delivery_id": "evt_x"})
        self.assertFalse(result["retry_scheduled"],
                         "a 400 will never succeed by being sent again")

    def test_network_error_retries(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        w = static_worker(r, [(None, "connection refused")])
        result = w._attempt({"event": make_event("track.change"),
                             "hook": r.get(h["id"]), "attempt": 1,
                             "delivery_id": "evt_x"})
        self.assertTrue(result["retry_scheduled"])

    def test_deliver_now_never_retries(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        w = static_worker(r, [(500, "HTTP 500")])
        result = w.deliver_now(r.get(h["id"]), make_event("webhook.test"))
        self.assertFalse(result["retry_scheduled"],
                         "the test endpoint wants an answer, not a retry")
        self.assertEqual(w.pending(), 0)

    def test_queue_full_drops_the_oldest_not_the_newest(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        w = DeliveryWorker(r, send_fn=lambda *a: (200, None), queue_max=2)
        old = make_event("track.change", {"n": 1})
        mid = make_event("track.change", {"n": 2})
        w.submit(old)
        w.submit(mid)
        self.assertEqual(w.pending(), 2)
        new = make_event("track.change", {"n": 3})
        self.assertEqual(w.submit(new), 1, "the queue never turns events away")
        with w._cv:
            jobs = [j for _, _, j in w._heap]
        ids = [j["event"]["data"]["n"] for j in jobs]
        self.assertEqual(sorted(ids), [2, 3], "oldest (n=1) was dropped")
        self.assertEqual(w._dropped, 1)

    def test_final_dead_letter_parks_the_hook(self):
        r = temp_registry()
        h = r.add("http://example.test/hook")
        with mock.patch.object(webhooks.config, "webhook_park_after", 1), \
                mock.patch.object(webhooks.config, "webhook_park_s", 60):
            w = static_worker(r, [(400, "HTTP 400")])
            w._attempt({"event": make_event("track.change"),
                        "hook": r.get(h["id"]), "attempt": 1,
                        "delivery_id": "evt_x"})
            self.assertTrue(r.public_hooks()[0]["stats"]["parked"])
            self.assertEqual(w.submit(make_event("track.change")), 0,
                             "parked hooks are skipped at fan-out")


def fake_mk(entries):
    """A musickit surface good for exactly one drain."""
    class FakeMk:
        def install_stream_hook(self):
            return True

        def drain_stream(self, after_seq=0):
            out = [e for e in entries if e["seq"] > after_seq]
            entries = []
            return out
    return FakeMk()


class FakeOkBrowser:
    def health(self):
        return {"running": True, "last_ok": True, "consecutive_failures": 0}


class TestStreamWatcher(unittest.TestCase):
    def setUp(self):
        self.emitted = []
        self.w = StreamWatcher(lambda t, d: self.emitted.append((t, d)),
                               FakeOkBrowser(), None)

    def test_track_change_once_then_progress_is_silent(self):
        T = 1_700_000_000_000
        out = self.w.process_events([
            ev(1, "a", ts=T),
            ev(2, "a", ts=T + 1000),          # progress tick
            ev(3, "a", ts=T + 2000),
        ])
        self.assertEqual([t for t, _ in out], ["track.change"])
        self.assertEqual(out[0][1]["id"], "a")
        self.assertEqual(out[0][1]["started_at"], T / 1000)
        self.assertEqual(len(self.emitted), 1)

    def test_pause_and_resume_emit_transitions(self):
        out = self.w.process_events([
            ev(1, "a", playing=True),
            ev(2, "a", playing=False),
            ev(3, "a", playing=False),        # repeated pause — no event
            ev(4, "a", playing=True),
        ])
        self.assertEqual([t for t, _ in out],
                         ["track.change", "playback.paused",
                          "playback.resumed"])

    def test_next_track_after_pause_is_a_change_not_a_resume(self):
        out = self.w.process_events([
            ev(1, "a", playing=True),
            ev(2, "a", playing=False),
            ev(3, "b", playing=True),
        ])
        self.assertEqual([t for t, _ in out],
                         ["track.change", "playback.paused", "track.change"])

    def test_seq_advances_past_silent_events(self):
        self.w.process_events([ev(1, "a"), ev(2, "a"), ev(3, "a", playing=False)])
        self.assertEqual(self.w._seq, 3)

    def test_first_sight_of_a_track_emits_even_mid_song(self):
        out = self.w.process_events([ev(9, "a")])
        self.assertEqual([t for t, _ in out], ["track.change"],
                         "a receiver wants current state on connect")


class TestEmitNoOp(unittest.TestCase):
    def test_emit_before_start_is_a_no_op(self):
        webhooks._worker = None
        webhooks.emit("track.change", {"id": "x"})      # must not raise


class TestSnapshot(unittest.TestCase):
    def test_disabled_raises(self):
        with mock.patch.object(webhooks.config, "webhooks_enabled", False):
            with self.assertRaises(webhooks.WebhooksDisabled):
                webhooks.snapshot()


class TestRoutes(unittest.TestCase):
    """The management surface is plain functions — driven directly, with the
    module registry injected (no HTTP, no server)."""

    def setUp(self):
        self._saved = (webhooks._registry, webhooks._worker)
        webhooks._worker = None

    def tearDown(self):
        webhooks._registry, webhooks._worker = self._saved

    def test_disabled_answers_501_with_code(self):
        from tonearm.errors import ApiError
        from tonearm.routes import webhooks as wr
        with mock.patch.object(webhooks.config, "webhooks_enabled", False):
            with self.assertRaises(ApiError) as ctx:
                wr.list_hooks()
        self.assertEqual((ctx.exception.status, ctx.exception.code),
                         (501, "webhooks_disabled"))

    def test_create_update_delete_lifecycle(self):
        from tonearm.errors import ApiError
        from tonearm.routes import webhooks as wr
        from tonearm.models import WebhookCreate, WebhookUpdate
        with mock.patch.object(webhooks.config, "webhooks_enabled", True):
            hook = wr.create_hook(WebhookCreate(
                url="http://example.test/hook", events=["track.change"],
                secret="s3cret"))
            self.assertTrue(hook["has_secret"])
            self.assertNotIn("secret", hook)

            # same URL again updates, never duplicates
            again = wr.create_hook(WebhookCreate(url="http://example.test/hook"))
            self.assertEqual(again["id"], hook["id"])

            patched = wr.update_hook(hook["id"], WebhookUpdate(enabled=False))
            self.assertFalse(patched["enabled"])

            self.assertTrue(wr.delete_hook(hook["id"])["ok"])
            with self.assertRaises(ApiError) as ctx:
                wr.delete_hook("wh_nope")
            self.assertEqual((ctx.exception.status, ctx.exception.code),
                             (404, "not_found"))

    def test_create_rejects_bad_url_and_events(self):
        from tonearm.errors import ApiError
        from tonearm.routes import webhooks as wr
        from tonearm.models import WebhookCreate
        with mock.patch.object(webhooks.config, "webhooks_enabled", True):
            with self.assertRaises(ApiError) as ctx:
                wr.create_hook(WebhookCreate(url="ftp://nope"))
            self.assertEqual((ctx.exception.status, ctx.exception.code),
                             (400, "bad_request"))
            with self.assertRaises(ApiError):
                wr.create_hook(WebhookCreate(url="http://ok",
                                             events=["nope.nope"]))

    def test_test_endpoint_404s_on_unknown_hook(self):
        from tonearm.errors import ApiError
        from tonearm.routes import webhooks as wr
        with mock.patch.object(webhooks.config, "webhooks_enabled", True):
            with self.assertRaises(ApiError) as ctx:
                wr.test_hook("wh_nope")
            self.assertEqual(ctx.exception.status, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
