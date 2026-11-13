"""The freeze machinery (#50, #126, #127, #128): deprecation headers,
surface pinning, and the OpenAPI diff gate."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from tonearm import deprecate               # noqa: E402
from tonearm.config import config           # noqa: E402

# NOTE: no mock-install at module import — unittest discover imports every
# test module up front, and an import-time mock install leaks into the
# shared musickit module (it broke test_backoff under discover). Mocking
# happens in SurfaceOnLiveApp.setUpClass only.


class DeprecateTest(unittest.TestCase):
    def test_sunset_headers(self):
        deprecate.DEPRECATED["/api/library/export"] = {
            "sunset": "2030-01-01", "replacement": "/api/library/snapshot",
            "note": "use snapshot"}
        try:
            h = deprecate.sunset_headers("/api/library/export")
            self.assertEqual(h["Deprecation"], "true")
            self.assertIn("GMT", h["Sunset"])
            self.assertIn("successor-version", h["Link"])
            self.assertEqual(h["Deprecation-Note"], "use snapshot")
            self.assertEqual(deprecate.sunset_headers("/api/nope"), {})
        finally:
            deprecate.DEPRECATED.clear()

    def test_surface(self):
        # no global mutation: other tests read the real app's SURFACE
        old = deprecate.SURFACE_VERSION
        try:
            self.assertEqual(deprecate.init_surface("0.8.0"), "0.8")
            self.assertEqual(deprecate.init_surface("1.0.0-rc1"), "1.0")
        finally:
            deprecate.init_surface(old)


class SurfaceOnLiveApp(unittest.TestCase):
    """The real app in mock mode — headers and /health.surface."""

    @classmethod
    def setUpClass(cls):
        config.mock_enabled = True
        # isolate the key registry: the dev box has real keys; a keyless
        # test server is the old behavior (auth passes through)
        import tempfile
        import tonearm.keys as keys_mod
        import tonearm.musickit as mk
        from tonearm.mock import install as mock_install
        mock_install(mk)
        cls._registry = keys_mod.registry
        keys_mod.registry = keys_mod.KeysRegistry(
            os.path.join(tempfile.mkdtemp(), "keys.json"))
        from tonearm.main import app
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        import tonearm.keys as keys_mod
        keys_mod.registry = cls._registry

    def test_health_carries_surface(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("surface"), deprecate.SURFACE_VERSION)
        self.assertEqual(r.headers.get("X-Tonearm-Surface"),
                         deprecate.SURFACE_VERSION)

    def test_api_carries_surface_header(self):
        r = self.client.get("/api/library/songs?limit=1")
        self.assertEqual(r.headers.get("X-Tonearm-Surface"),
                         deprecate.SURFACE_VERSION)

    def test_deprecated_route_stamped(self):
        deprecate.DEPRECATED["/api/library/songs"] = {
            "sunset": "2030-01-01"}
        try:
            r = self.client.get("/api/library/songs?limit=1")
            self.assertEqual(r.headers.get("Deprecation"), "true")
            self.assertIn("GMT", r.headers.get("Sunset", ""))
        finally:
            deprecate.DEPRECATED.clear()


class OpenApiDiffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snap = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "api", "openapi.json")
        # the snapshot is the app's own schema in mock mode — generate it
        # here rather than trusting a stale file
        from tonearm.main import app
        cls.current = app.openapi()

    def test_snapshot_matches_app(self):
        if os.path.exists(self.snap):
            with open(self.snap) as f:
                snap = json.load(f)
            # a plain assertEqual on two ~100KB dicts is unreadable —
            # report the FIRST differing path instead
            def first_diff(a, b, path=""):
                if type(a) is not type(b):
                    return f"{path}: type {type(a).__name__} vs " \
                        f"{type(b).__name__}"
                if isinstance(a, dict):
                    for k in sorted(set(a) | set(b)):
                        if k not in a:
                            return f"{path}/{k}: only in the fresh schema"
                        if k not in b:
                            return f"{path}/{k}: only in the snapshot"
                        d = first_diff(a[k], b[k], f"{path}/{k}")
                        if d:
                            return d
                    return None
                if isinstance(a, list):
                    if len(a) != len(b):
                        return f"{path}: list len {len(a)} vs {len(b)}"
                    for i, (x, y) in enumerate(zip(a, b)):
                        d = first_diff(x, y, f"{path}[{i}]")
                        if d:
                            return d
                    return None
                return None if a == b else \
                    f"{path}: {str(a)[:60]!s} != {str(b)[:60]!s}"
            diff = first_diff(snap, self.current)
            self.assertIsNone(diff, "api/openapi.json is stale — regen "
                             "with scripts/openapi_dump.py; first diff: "
                             + str(diff))

    def test_path_removal_is_breaking(self):
        from scripts.openapi_diff import breaking
        # the FRESH schema lost a path the contract still has — that is
        # the break (mutate a copy of the current schema, not the contract)
        grown = json.loads(json.dumps(self.current))
        victim = next(iter(grown["paths"]))
        del grown["paths"][victim]
        self.assertIn(f"path removed: {victim}", breaking(self.current, grown))

    def test_additions_are_not_breaking(self):
        from scripts.openapi_diff import breaking
        grown = json.loads(json.dumps(self.current))
        grown["paths"]["/api/future/thing"] = {
            "get": {"responses": {"200": {"description": "ok"}}}}
        self.assertEqual(breaking(self.current, grown), [])

    def test_response_field_removal_is_breaking(self):
        from scripts.openapi_diff import breaking
        grown = json.loads(json.dumps(self.current))
        # responses point at component schemas via $ref — drop a field
        # from one the fresh schema still references
        comps = grown.get("components", {}).get("schemas", {})
        victim_model, victim_field = next(
            (name, next(iter(s.get("properties", {}))))
            for name, s in sorted(comps.items())
            if s.get("properties"))
        del comps[victim_model]["properties"][victim_field]
        findings = breaking(self.current, grown)
        self.assertTrue(any(victim_field in f for f in findings),
                        f"component field removal not caught: {findings[:3]}")


if __name__ == "__main__":
    unittest.main()
