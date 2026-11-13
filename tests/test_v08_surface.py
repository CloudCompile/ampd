"""The v0.8 surface additions: the batch endpoint (#183) and the
storefront param (#184)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import tonearm.musickit as mk               # noqa: E402
from tonearm.mock import install as mock_install  # noqa: E402
from tonearm import keys as keys_mod        # noqa: E402
from tonearm.config import config           # noqa: E402


class BatchTest(unittest.TestCase):
    """POST /api/batch — N reads, one round trip (#183)."""

    @classmethod
    def setUpClass(cls):
        config.mock_enabled = True
        mock_install(mk)
        import tempfile
        cls._registry = keys_mod.registry
        cls._api_key = config.api_key
        config.api_key = ""          # earlier test modules may have keyed
        keys_mod.registry = keys_mod.KeysRegistry(
            os.path.join(tempfile.mkdtemp(), "keys.json"))
        from tonearm.main import app
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        keys_mod.registry = cls._registry
        config.api_key = cls._api_key

    def test_batch_answers_each_entry(self):
        r = self.client.post("/api/batch", json={"requests": [
            {"path": "/api/library/songs", "params": {"limit": "2"}},
            {"path": "/api/catalog/search",
             "params": {"term": "natori", "types": "songs", "limit": "2"}},
        ]})
        self.assertEqual(r.status_code, 200)
        out = r.json()
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["status"], 200)
        self.assertIsInstance(out[0]["body"], (dict, list))
        self.assertEqual(out[1]["status"], 200)

    def test_one_bad_entry_does_not_sink_the_batch(self):
        r = self.client.post("/api/batch", json={"requests": [
            {"path": "/api/library/songs", "params": {"limit": "1"}},
            {"path": "/api/catalog/nope-resource", "params": {"ids": "x"}},
        ]})
        self.assertEqual(r.status_code, 200)
        out = r.json()
        self.assertEqual(out[0]["status"], 200)
        self.assertGreaterEqual(out[1]["status"], 400)   # its own envelope

    def test_mutations_have_no_way_in(self):
        # there is no method field — a POST-only route hit as a GET is a
        # 405 in its own envelope
        r = self.client.post("/api/batch", json={"requests": [
            {"path": "/api/playback/play-song/1234"},
        ]})
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.json()[0]["status"], 400)

    def test_batch_itself_cannot_batch(self):
        r = self.client.post("/api/batch", json={"requests": [
            {"path": "/api/batch"},
        ]})
        self.assertEqual(r.status_code, 400)

    def test_streams_cannot_batch(self):
        for denied in ("/api/stream", "/api/audio/stream.mp3", "/metrics"):
            r = self.client.post("/api/batch", json={"requests": [
                {"path": denied}]})
            self.assertEqual(r.status_code, 400, denied)

    def test_non_api_paths_rejected(self):
        r = self.client.post("/api/batch", json={"requests": [
            {"path": "/etc/passwd"}]})
        self.assertEqual(r.status_code, 400)

    def test_over_the_cap_rejected(self):
        r = self.client.post("/api/batch", json={"requests": [
            {"path": "/api/library/songs"}] * 11})
        self.assertEqual(r.status_code, 400)
        self.assertIn("max 10", r.text)


class StorefrontTest(unittest.TestCase):
    """?storefront= on catalog routes (#184): validated, default us."""

    @classmethod
    def setUpClass(cls):
        config.mock_enabled = True
        mock_install(mk)
        import tempfile
        cls._registry = keys_mod.registry
        cls._api_key = config.api_key
        config.api_key = ""          # earlier test modules may have keyed
        keys_mod.registry = keys_mod.KeysRegistry(
            os.path.join(tempfile.mkdtemp(), "keys.json"))
        from tonearm.main import app
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        keys_mod.registry = cls._registry
        config.api_key = cls._api_key

    def test_bad_storefront_is_a_typed_400(self):
        r = self.client.get("/api/catalog/search",
                            params={"term": "x", "storefront": "usa"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("ISO", r.json()["error"]["hint"])

    def test_injection_shape_is_rejected(self):
        r = self.client.get("/api/catalog/search",
                            params={"term": "x", "storefront": "us/search"})
        self.assertEqual(r.status_code, 400)

    def test_valid_storefront_passes_through(self):
        # capture the amp-api path the route builds
        calls = []
        real = mk.api_music

        def spy(path, *a, **kw):
            calls.append(path)
            return real(path, *a, **kw)

        mk.api_music = spy
        try:
            # the mock has no gb fixture (502) — the capture is the assert;
            # what matters is the storefront reached the amp-api path
            self.client.get("/api/catalog/search",
                            params={"term": "x", "storefront": "gb"})
        finally:
            mk.api_music = real
        self.assertTrue(any("/v1/catalog/gb/search" in c for c in calls),
                        calls[:2])


if __name__ == "__main__":
    unittest.main()
