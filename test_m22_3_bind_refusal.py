"""M22.3 (Decisions 2 and 3): loopback-only default binding with an
explicit override, and the accepted, documented limitation that a raw
`uvicorn ... --host 0.0.0.0` invocation bypasses this launcher entirely.
See docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md sections 5.2/5.3/6.7.

Tests the pure decision function directly - no real socket is opened, no
real uvicorn process is started.
"""

import unittest

from scripts.run_uri_server import (
    DEFAULT_HOST,
    InsecureBindRefusedError,
    build_arg_parser,
    check_bind_is_safe,
    is_loopback_host,
)


class LoopbackHostDetectionTests(unittest.TestCase):

    def test_recognizes_127_0_0_1(self):
        self.assertTrue(is_loopback_host("127.0.0.1"))

    def test_recognizes_ipv6_loopback(self):
        self.assertTrue(is_loopback_host("::1"))

    def test_recognizes_localhost_by_name(self):
        self.assertTrue(is_loopback_host("localhost"))

    def test_lan_ip_is_not_loopback(self):
        self.assertFalse(is_loopback_host("192.168.1.20"))

    def test_all_interfaces_is_not_loopback(self):
        self.assertFalse(is_loopback_host("0.0.0.0"))


class DefaultHostTests(unittest.TestCase):

    def test_default_host_is_loopback(self):
        # Decision 2: loopback-only by default - the pre-M22.3 default
        # was 0.0.0.0.
        self.assertEqual(DEFAULT_HOST, "127.0.0.1")
        self.assertTrue(is_loopback_host(DEFAULT_HOST))

    def test_argparse_default_host_matches_the_module_constant(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        self.assertEqual(args.host, DEFAULT_HOST)

    def test_argparse_default_does_not_require_the_override_flag(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        self.assertFalse(args.allow_insecure_bind)


class CheckBindIsSafeTests(unittest.TestCase):

    def test_loopback_host_is_always_safe(self):
        # No TLS, no override, still fine - it's loopback.
        check_bind_is_safe("127.0.0.1", tls_configured=False, allow_insecure_bind=False)

    def test_non_loopback_with_no_tls_and_no_override_is_refused(self):
        with self.assertRaises(InsecureBindRefusedError):
            check_bind_is_safe(
                "0.0.0.0", tls_configured=False, allow_insecure_bind=False
            )

    def test_non_loopback_with_tls_configured_is_allowed(self):
        check_bind_is_safe("0.0.0.0", tls_configured=True, allow_insecure_bind=False)

    def test_non_loopback_with_explicit_override_is_allowed(self):
        check_bind_is_safe(
            "0.0.0.0", tls_configured=False, allow_insecure_bind=True
        )

    def test_lan_ip_with_no_tls_and_no_override_is_refused(self):
        with self.assertRaises(InsecureBindRefusedError):
            check_bind_is_safe(
                "192.168.1.20", tls_configured=False, allow_insecure_bind=False
            )

    def test_refusal_never_happens_silently(self):
        # The exception must carry an actionable message, not an empty
        # or generic one - this is what a human sees at startup.
        with self.assertRaises(InsecureBindRefusedError) as ctx:
            check_bind_is_safe(
                "0.0.0.0", tls_configured=False, allow_insecure_bind=False
            )
        self.assertIn("0.0.0.0", str(ctx.exception))
        self.assertIn("--allow-insecure-bind", str(ctx.exception))


class ArgParserOverrideWiringTests(unittest.TestCase):

    def test_cli_flag_sets_allow_insecure_bind(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--host", "0.0.0.0", "--allow-insecure-bind"])
        self.assertTrue(args.allow_insecure_bind)

    def test_ssl_args_are_accepted_and_optional(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.ssl_keyfile)
        self.assertIsNone(args.ssl_certfile)

        args_with_tls = parser.parse_args(
            [
                "--host",
                "0.0.0.0",
                "--ssl-keyfile",
                "key.pem",
                "--ssl-certfile",
                "cert.pem",
            ]
        )
        self.assertEqual(args_with_tls.ssl_keyfile, "key.pem")
        self.assertEqual(args_with_tls.ssl_certfile, "cert.pem")


if __name__ == "__main__":
    unittest.main()
