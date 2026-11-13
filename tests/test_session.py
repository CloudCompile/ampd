"""Session-expiry UX tests (#189): Apple's 403/40300 means the session
died — /health says so and the error envelope says 'run login'."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm import musickit as mk
from tonearm.errors import wrap_http_exception


class FakeHTTPException(Exception):
    def __init__(self, status, detail):
        self.status_code = status
        self.detail = detail


class TestSessionState(unittest.TestCase):
    def setUp(self):
        mk.session_state.update(state="unknown", since=0.0)

    def test_a_200_marks_the_session_ok(self):
        mk._note_session(200, '{"data": []}')
        self.assertEqual(mk.session_state["state"], "ok")

    def test_403_40300_marks_expired(self):
        mk._note_session(403, '{"errors":[{"title":"Forbidden",'
                              '"code":"40300"}]}')
        self.assertEqual(mk.session_state["state"], "expired")
        self.assertGreater(mk.session_state["since"], 0)

    def test_other_403s_are_not_expiry(self):
        mk._note_session(403, '{"errors":[{"code":"40401"}]}')
        self.assertEqual(mk.session_state["state"], "unknown",
                         "a 403 without 40300 is not a dead session")

    def test_recovery_marks_ok_again(self):
        mk._note_session(403, '{"code":"40300"}')
        mk._note_session(200, "{}")
        self.assertEqual(mk.session_state["state"], "ok",
                         "a 200 after re-login heals the state")


class TestEnvelope(unittest.TestCase):
    def test_invalid_auth_502_says_run_login(self):
        content = wrap_http_exception(FakeHTTPException(
            502, "apple api: HTTP 403 — {\"code\":\"40300\", "
                 "\"detail\":\"Invalid authentication\"}"))
        status, body = content
        self.assertEqual(status, 502)
        self.assertEqual(body["error"]["code"], "session_expired")
        self.assertIn("login", body["error"]["hint"])

    def test_other_502s_stay_renderer_unavailable(self):
        status, body = wrap_http_exception(FakeHTTPException(
            502, "apple api: HTTP 500 — oops"))
        self.assertEqual(body["error"]["code"], "renderer_unavailable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
