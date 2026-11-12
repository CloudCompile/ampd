"""Unit tests for the error envelope (v0.4 #32) — hermetic, no TestClient.

Run:  python3 -m unittest discover -s tests
The envelope is built by pure functions (ampd/errors.py); the FastAPI
handlers are thin wrappers over them.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ampd.errors import (ApiError, STATUS_CODES, envelope_content,
                         wrap_http_exception, wrap_validation_error)
from starlette.exceptions import HTTPException as StarletteHTTPException


class FakeValidation:
    """Duck-typed RequestValidationError (importing the real one needs the
    fastapi exceptions wiring; only .errors() is consumed)."""

    def __init__(self, errors):
        self._errors = errors

    def errors(self):
        return self._errors


class TestEnvelopeShape(unittest.TestCase):
    def test_shape_is_always_error_code_hint(self):
        for status in (400, 401, 404, 429, 501, 502):
            s, body = envelope_content(status)
            self.assertEqual(s, status)
            self.assertEqual(set(body.keys()), {"error"})
            self.assertEqual(set(body["error"].keys()), {"code", "hint"})
            self.assertTrue(body["error"]["code"])
            self.assertTrue(body["error"]["hint"],
                            f"{status} must have a default hint")

    def test_status_codes_map(self):
        self.assertEqual(STATUS_CODES[502], "renderer_unavailable")
        self.assertEqual(STATUS_CODES[501], "disabled")
        self.assertEqual(STATUS_CODES[429], "rate_limited")
        self.assertEqual(STATUS_CODES[400], "bad_request")
        self.assertEqual(STATUS_CODES[401], "unauthorized")
        self.assertEqual(STATUS_CODES[404], "not_found")

    def test_detail_wins_as_hint(self):
        s, body = envelope_content(400, detail="term is required")
        self.assertEqual(body["error"]["hint"], "term is required")
        s, body = envelope_content(400)               # no detail -> default
        self.assertTrue(body["error"]["hint"])

    def test_non_string_detail_ignored(self):
        s, body = envelope_content(404, detail={"weird": 1})
        self.assertNotIn("weird", body["error"]["hint"])

    def test_wrap_http_exception(self):
        s, body = wrap_http_exception(StarletteHTTPException(404, "nope"))
        self.assertEqual(s, 404)
        self.assertEqual(body, {"error": {"code": "not_found", "hint": "nope"}})

    def test_wrap_validation_error(self):
        exc = FakeValidation([{"loc": ("query", "term"), "msg": "field required"}])
        s, body = wrap_validation_error(exc)
        self.assertEqual(s, 400)
        self.assertEqual(body["error"]["code"], "bad_request")
        self.assertEqual(body["error"]["hint"], "term: field required")


class TestApiError(unittest.TestCase):
    def test_explicit_codes_beat_status_defaults(self):
        e = ApiError(501, "writes_disabled", "set AMPD_ENABLE_WRITES=1")
        s, body = envelope_content(e.status, e.code, e.hint)
        self.assertEqual(body["error"]["code"], "writes_disabled",
                         "both 501 flavors share a status, not a code")
        e2 = ApiError(501, "store_disabled", "set AMPD_STORE=1")
        self.assertNotEqual(e.code, e2.code)

    def test_default_hint_applied(self):
        e = ApiError(502, "renderer_unavailable")
        self.assertTrue(e.hint, "502 gets the recovers-on-its-own hint")


if __name__ == "__main__":
    unittest.main(verbosity=2)
