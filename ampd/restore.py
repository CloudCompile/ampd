"""Library restore — the missing half of /api/library/export.

The export is a complete restore reference (catalog ids for every song).
This module turns one back into a library:

* DRY-RUN BY DEFAULT — same design rule as the sweeps: a plan is returned,
  nothing is touched until `execute=1` (and the route is behind the writes
  gate on top of that; a schedule must never run this).
* Never silent: every track that can't be restored is listed with a reason.
* Two key spaces: the export rows carry CATALOG ids (that's what playlists
  accept — adding one auto-adds the song to the library). Rows without a
  catalog id (fresh/local-only rows) fall back to catalog search by
  name+artist, bounded; misses are reported, never guessed.
* Apple's mutations are 202-async: after executing, verification re-reads
  the playlists with bounded retries (the cache is already busted+graced by
  the mutation path itself).
"""
import logging
import time

log = logging.getLogger("ampd.restore")


def _norm(s):
    return (s or "").strip().lower()


def build_plan(export, existing_lookup, catalog_lookup, match_budget=2000):
    """Build the restore PLAN.

    export          — /api/library/export shape: {playlists: [{name, tracks}]}
    existing_lookup — fn(name) -> playlist_id | None   (case-insensitive)
    catalog_lookup  — fn(name, artist) -> catalog_id | None (bounded; injected
                      so tests can fake it and the route wires a real search)
    """
    plan = []
    totals = {"playlists": 0, "exists": 0, "create": 0,
              "tracks": 0, "catalog": 0, "name_match": 0, "unmatched": 0}
    searches = 0
    for pl in export.get("playlists", []):
        name = pl.get("name") or ""
        pid = existing_lookup(name)
        actions, unmatched = [], []
        for t in pl.get("tracks", []):
            totals["tracks"] += 1
            cid = t.get("catalog_id")
            row = {"name": t.get("name"), "artist": t.get("artist")}
            if cid:
                totals["catalog"] += 1
                actions.append({"kind": "catalog", "catalog_id": cid, **row})
                continue
            if searches < match_budget:
                searches += 1
                hit = catalog_lookup(t.get("name"), t.get("artist"))
            else:
                hit = None          # budget exhausted — honest report, not a hang
            if hit:
                totals["name_match"] += 1
                actions.append({"kind": "name-match", "catalog_id": hit, **row})
            else:
                totals["unmatched"] += 1
                unmatched.append({**row, "reason":
                                  "no catalog id in the export and no catalog "
                                  "search hit (local-only or not on Apple)"})
        mode = "exists" if pid else "create"
        totals["playlists"] += 1
        totals["exists" if pid else "create"] += 1
        plan.append({"name": name, "mode": mode, "playlist_id": pid,
                     "track_count": len(actions) + len(unmatched),
                     "actions": actions, "unmatched": unmatched})
    return {"totals": totals, "playlists": plan,
            "note": "dry-run plan — nothing was touched. POST with execute=1 "
                    "(and AMPD_ENABLE_WRITES=1) to apply."}


def execute_plan(plan, mk_mod, verify_retries=3, verify_delay=2.0):
    """Run a plan: create missing playlists, add tracks (catalog ids only —
    adding a catalog song auto-adds it to the library), then verify by
    re-reading each playlist with bounded retries (202-async)."""
    report = {"created": [], "verified": [], "mismatch": [], "errors": [],
              "unmatched_total": sum(len(p["unmatched"]) for p in plan["playlists"])}

    def verify(pid, name, want):
        for attempt in range(verify_retries):
            try:
                got = len(mk_mod.playlist_tracks(pid, fresh=True))
            except Exception as e:
                got = None
                log.debug("restore verify read failed: %s", e)
            if got == want:
                return True
            time.sleep(verify_delay * (attempt + 1))
        return False

    for p in plan["playlists"]:
        name = p["name"]
        try:
            pid = p["playlist_id"]
            if p["mode"] == "create" or not pid:
                pid = mk_mod.playlist_create(name)
                report["created"].append({"name": name, "playlist_id": pid})
            cids = [a["catalog_id"] for a in p["actions"]]
            for i in range(0, len(cids), 100):     # bounded batches
                batch = cids[i:i + 100]
                if batch:
                    mk_mod.playlist_add_tracks(pid, batch)
            if verify(pid, name, p["track_count"]):
                report["verified"].append(
                    {"name": name, "playlist_id": pid,
                     "tracks": p["track_count"]})
            else:
                report["mismatch"].append(
                    {"name": name, "playlist_id": pid,
                     "expected": p["track_count"],
                     "note": "track count did not match after retries — "
                             "Apple's async apply may still be settling, or "
                             "the playlist hit the 333-song/sync limits"})
        except Exception as e:
            report["errors"].append({"name": name, "error": str(e)[:200]})
    return report
