"""M22.3 (Decision 7): CORS allowlisting - explicit origins in
production, loopback-only in local development, never a bare wildcard.
See docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md sections 5.7/6.6.

Two layers are tested:

1. server._resolve_cors_kwargs(), a pure function - both the
   explicit-allowlist and the loopback-regex branches, without touching
   the live app's already-configured middleware.
2. The actually-configured app's live CORS behaviour, which reflects
   whichever branch was active when this process imported
   uri_core.app.server - in this test environment that is the
   loopback-only dev default (URI_CORS_ALLOWED_ORIGINS unset), so these
   tests assert the dev-default behaviour end-to-end over real requests.
"""

import os
import unittest

from fastapi.testclient import TestClient

from uri_core.app import server


class ResolveCorsKwargsTests(unittest.TestCase):
    """Pure-function tests - no HTTP, no app construction."""

    def test_empty_env_yields_the_loopback_regex(self):
        kwargs = server._resolve_cors_kwargs("")

        self.assertEqual(
            kwargs, {"allow_origin_regex": server.LOOPBACK_CORS_ORIGIN_REGEX}
        )

    def test_whitespace_only_env_is_treated_as_empty(self):
        kwargs = server._resolve_cors_kwargs("   ")

        self.assertIn("allow_origin_regex", kwargs)
        self.assertNotIn("allow_origins", kwargs)

    def test_configured_env_yields_an_explicit_origin_list(self):
        kwargs = server._resolve_cors_kwargs(
            "https://app.example.com, https://admin.example.com"
        )

        self.assertEqual(
            kwargs,
            {
                "allow_origins": [
                    "https://app.example.com",
                    "https://admin.example.com",
                ]
            },
        )

    def test_configured_env_never_yields_a_wildcard(self):
        for raw in ("*", "https://a.example.com,*", "  *  "):
            with self.subTest(raw=raw):
                kwargs = server._resolve_cors_kwargs(raw)
                self.assertNotIn("*", kwargs.get("allow_origins", []))

    def test_no_configuration_path_ever_produces_a_bare_wildcard_string(self):
        for raw in ("", "https://app.example.com"):
            kwargs = server._resolve_cors_kwargs(raw)
            self.assertNotEqual(kwargs.get("allow_origins"), "*")


class LiveDevDefaultCorsTests(unittest.TestCase):
    """Exercises the actually-registered CORSMiddleware. Assumes this
    test process was started with URI_CORS_ALLOWED_ORIGINS unset (the
    normal local/CI test environment) - skips rather than giving a
    false result if that assumption doesn't hold here."""

    def setUp(self):
        if os.environ.get("URI_CORS_ALLOWED_ORIGINS", "").strip():
            self.skipTest(
                "URI_CORS_ALLOWED_ORIGINS is set in this environment; "
                "the live app is not using the loopback-regex default."
            )
        self.client = TestClient(server.app)

    def test_localhost_origin_is_allowed(self):
        response = self.client.get(
            "/health", headers={"Origin": "http://localhost:54213"}
        )
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:54213",
        )

    def test_127_0_0_1_origin_is_allowed(self):
        response = self.client.get(
            "/health", headers={"Origin": "http://127.0.0.1:9999"}
        )
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://127.0.0.1:9999",
        )

    def test_non_loopback_origin_is_rejected(self):
        response = self.client.get(
            "/health", headers={"Origin": "http://evil.example"}
        )
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    def test_suffix_abuse_is_rejected_by_the_anchored_regex(self):
        response = self.client.get(
            "/health", headers={"Origin": "http://localhost.evil.com"}
        )
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    def test_no_middleware_option_in_this_process_is_a_bare_wildcard(self):
        for middleware in server.app.user_middleware:
            options = getattr(middleware, "kwargs", {})
            self.assertNotEqual(options.get("allow_origins"), ["*"])
            self.assertNotEqual(options.get("allow_origins"), "*")


if __name__ == "__main__":
    unittest.main()
