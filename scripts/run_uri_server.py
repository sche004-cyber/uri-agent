"""Starts the real URI backend (uri_core.app.server:app) via uvicorn.

This is pure process plumbing - it contains no Brain reasoning, no
orchestration logic, and no business logic of its own. It only ever
imports and serves the existing, unmodified `app` object from
uri_core.app.server; every request it receives is still handled
exactly as UriOrchestrator.process_user_input() and the rest of
server.py already define. This is the single entry point used both
for a manual foreground run and for the persistent Task Scheduler
launcher (see scripts/uri_server_ctl.ps1), so both start the server
identically.

M22.3 (docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md section 6.7,
Decision 2): host defaults to 127.0.0.1 (loopback-only), not 0.0.0.0.
Binding a non-loopback host is refused unless TLS is configured
(--ssl-keyfile/--ssl-certfile) or the caller explicitly accepts the risk
via --allow-insecure-bind (or URI_ALLOW_INSECURE_BIND=1). This is a
deliberate default change from the pre-M22.3 behaviour, which bound
0.0.0.0 unconditionally - see the plan's section 19.1 for the exact
operational consequence to scripts/uri_server_ctl.ps1's persistent
Task Scheduler launcher, which invokes this script with no --host flag
at all and will now bind loopback-only unless updated to pass
--allow-insecure-bind or TLS arguments explicitly.

M22.3 also documents, rather than attempts to close, a real limitation:
a raw `uvicorn uri_core.app.server:app --host 0.0.0.0` invocation
bypasses this file entirely, because uvicorn's own CLI loader never
gives this script a chance to see or reject the host it was bound to.
This script protects the SANCTIONED launcher path only (Decision 3) -
see server.py's own module docstring, which points here rather than at
the raw uvicorn CLI form.
"""

import argparse
import os
import socket
import sys

# Running this file directly (`python scripts/run_uri_server.py`) puts
# this script's OWN directory on sys.path, not the repo root - so
# `uri_core` would not be importable by uvicorn's "module:app" string
# loader without this. Inserted before importing uvicorn so it applies
# regardless of the invoking working directory (Task Scheduler's
# included -WorkingDirectory is a separate, redundant safeguard for
# the same reason).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

# Loopback hostnames/addresses that never require TLS or an override -
# matches how a browser/OS treats "this machine only". Anything else is
# treated as potentially network-reachable.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


class InsecureBindRefusedError(Exception):
    """Raised by check_bind_is_safe() when a non-loopback bind is
    requested with no TLS and no explicit override. A pure, importable
    exception so scripts/../test_m22_3_bind_refusal.py can assert on it
    without spawning a real process or opening a real socket."""


def is_loopback_host(host: str) -> bool:
    return host in LOOPBACK_HOSTS


def check_bind_is_safe(
    host: str, tls_configured: bool, allow_insecure_bind: bool
) -> None:
    """The one decision this file makes about binding. Returns None
    (safe to proceed) or raises InsecureBindRefusedError - it never
    silently downgrades a non-loopback request to loopback, and it
    never silently allows a non-loopback bind without one of the two
    explicit conditions below."""

    if is_loopback_host(host):
        return

    if tls_configured:
        return

    if allow_insecure_bind:
        print(
            f"WARNING: binding to non-loopback host {host!r} with no TLS "
            "configured. --allow-insecure-bind (or "
            "URI_ALLOW_INSECURE_BIND=1) was explicitly set, so this is "
            "proceeding anyway. This exposes the API in cleartext, "
            "including login credentials, to anything that can reach "
            f"{host}. This is a deliberately accepted risk, not a "
            "default.",
            file=sys.stderr,
        )
        return

    raise InsecureBindRefusedError(
        f"Refusing to bind non-loopback host {host!r} with no TLS "
        "configured and no override. Configure --ssl-keyfile/"
        "--ssl-certfile for TLS, or pass --allow-insecure-bind (or set "
        "URI_ALLOW_INSECURE_BIND=1) to proceed anyway and accept the "
        "risk. See docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md "
        "section 6.7."
    )


def _env_flag_set(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def _lan_ip_guess() -> str:
    """Best-effort local LAN IP for the startup banner only - never
    used for binding or any decision, purely a convenience hint so
    whoever started the server can see what to type into the phone's
    Settings screen without opening a separate terminal for
    `ipconfig`. Falls back to a placeholder if it can't be determined
    (e.g. no network at all) rather than raising."""

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
        finally:
            probe.close()
    except OSError:
        return "<this PC's LAN IP - see `ipconfig`>"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the URI API server (uri_core.app.server:app)."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("URI_SERVER_HOST", DEFAULT_HOST),
        help=f"Bind address (default: {DEFAULT_HOST}, loopback-only).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("URI_SERVER_PORT", str(DEFAULT_PORT))),
        help=f"Bind port (default: {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn's auto-reload (interactive development only - "
        "never used by the persistent launcher).",
    )
    parser.add_argument(
        "--allow-insecure-bind",
        action="store_true",
        default=_env_flag_set("URI_ALLOW_INSECURE_BIND"),
        help="Explicitly accept a non-loopback bind with no TLS. Logged "
        "loudly at startup. Not for production use.",
    )
    parser.add_argument(
        "--ssl-keyfile",
        default=os.environ.get("URI_SSL_KEYFILE") or None,
        help="Path to a TLS private key, if terminating TLS in this "
        "process rather than via a reverse proxy.",
    )
    parser.add_argument(
        "--ssl-certfile",
        default=os.environ.get("URI_SSL_CERTFILE") or None,
        help="Path to a TLS certificate, if terminating TLS in this "
        "process rather than via a reverse proxy.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    tls_configured = bool(args.ssl_keyfile and args.ssl_certfile)

    try:
        check_bind_is_safe(args.host, tls_configured, args.allow_insecure_bind)
    except InsecureBindRefusedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("URI API server")
    print(f"Local:  http://127.0.0.1:{args.port}")
    if not is_loopback_host(args.host):
        scheme = "https" if tls_configured else "http"
        print(f"LAN:    {scheme}://{_lan_ip_guess()}:{args.port}")
    print("Health: GET /health")
    print("=" * 60, flush=True)

    uvicorn.run(
        "uri_core.app.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile,
    )


if __name__ == "__main__":
    main()
