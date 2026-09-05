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

Host/port default to 0.0.0.0:8000 - LAN-reachable, matching
server.py's own documented "reachable from another device on the same
LAN" instructions - and are overridable via the URI_SERVER_HOST /
URI_SERVER_PORT environment variables or --host / --port. This is a
local/LAN development convenience, not a public deployment: no TLS, no
reverse proxy, no authentication beyond server.py's own login
endpoints.
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the URI API server (uri_core.app.server:app)."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("URI_SERVER_HOST", "0.0.0.0"),
        help="Bind address (default: 0.0.0.0, all interfaces - LAN-reachable).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("URI_SERVER_PORT", "8000")),
        help="Bind port (default: 8000).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn's auto-reload (interactive development only - "
        "never used by the persistent launcher).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("URI API server")
    print(f"Local:  http://127.0.0.1:{args.port}")
    print(f"LAN:    http://{_lan_ip_guess()}:{args.port}")
    print("Health: GET /health")
    print("=" * 60, flush=True)

    uvicorn.run(
        "uri_core.app.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
