"""One-shot, isolated live-evidence harness for M30.7C.

Starts a loopback URI server, authenticates through /auth/login, captures the
actual /ask JSON and the matching canonical telemetry line, then always stops
the server.  It never changes production configuration or credentials.
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
LOG = ROOT / "uri_workspace" / "canonical_execution_log.jsonl"
SHADOW_LOG = ROOT / "uri_workspace" / "decision_engine_shadow_log.jsonl"
OUT = ROOT / "uri_workspace" / "evidence" / "m30_7c_live_capture.json"


def request(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.status, json.loads(response.read().decode())


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_ready(base):
    end = time.time() + 45
    while time.time() < end:
        try:
            if request(base + "/health")[1].get("status") == "ok":
                return
        except Exception:
            time.sleep(.4)
    raise RuntimeError("isolated server did not become healthy")


def matching_telemetry(session_id, before, path=LOG):
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()[before:]
    for line in reversed(lines):
        try:
            item = json.loads(line)
            if item.get("session_id") == session_id:
                return item
        except json.JSONDecodeError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=("2", "6", "7", "8", "12"))
    parser.add_argument("--text", default=None, help="Override the /ask user text for this run.")
    parser.add_argument("--tag", default=None, help="Extra session-id suffix to disambiguate repeated runs.")
    args = parser.parse_args()
    scenario = args.scenario
    port = free_port()
    env = os.environ.copy()
    env.update({
        "URI_ENABLE_DECISION_ENGINE_LIVE": "1",
        "URI_ENABLE_DECISION_ENGINE_SHADOW": "1",
        "URI_SERVER_PORT": str(port),
        "PYTHONUTF8": "1",
    })
    fixture = None
    if scenario == "2":
        fixture = Path(tempfile.mkdtemp(prefix="uri-m30-7c-disconnected-"))
        shutil.copy2(ROOT / "credentials.json", fixture / "credentials.json")
        (fixture / "token.json").write_text("{not-valid-json", encoding="utf-8")
        env["URI_GOOGLE_CREDENTIALS_DIR"] = str(fixture)
        text = "Using Gmail, how many unread emails do I have?"
    elif scenario == "8":
        text = "Using Gmail, prepare a draft reply but do not send it. To: test@example.com. Subject: M30.7C approval review. Body: This is a draft for approval only; do not send it."
    elif scenario == "7":
        text = "Search Gmail for an email with an attachment and tell me what the attachment is."
    elif scenario == "6":
        text = "Remember that my favorite color is blue."
    else:
        env["OLLAMA_BASE_URL"] = "http://127.0.0.1:19999"
        text = "What is the weather in Delhi today?"
    if args.text:
        text = args.text
    suffix = f"_{args.tag}" if args.tag else ""
    session_id = f"m30_7c_s{scenario}{suffix}_{int(time.time())}"
    stdout = ROOT / "uri_workspace" / "evidence" / f"m30_7c_s{scenario}_server_stdout.log"
    stderr = ROOT / "uri_workspace" / "evidence" / f"m30_7c_s{scenario}_server_stderr.log"
    stdout.parent.mkdir(parents=True, exist_ok=True)
    proc = None
    try:
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            proc = subprocess.Popen([str(PYTHON), "scripts/run_uri_server.py", "--port", str(port)], cwd=ROOT, env=env, stdout=out, stderr=err)
            base = f"http://127.0.0.1:{port}"
            wait_ready(base)
            _, login = request(base + "/auth/login", {"username": "URI_test2", "password": "URI_test2", "device_id": "m30_7c_capture"})
            before = len(LOG.read_text(encoding="utf-8").splitlines()) if LOG.exists() else 0
            shadow_before = len(SHADOW_LOG.read_text(encoding="utf-8").splitlines()) if SHADOW_LOG.exists() else 0
            status, response = request(base + "/ask", {"session_id": session_id, "text": text}, login["token"])
            capture = {
                "scenario": scenario, "session_id": session_id, "http_status": status, "text": text,
                "ask_response": response, "telemetry": matching_telemetry(session_id, before),
                "shadow_telemetry": matching_telemetry(session_id, shadow_before, path=SHADOW_LOG),
            }
            existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
            existing[session_id] = capture
            OUT.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
            print(json.dumps(capture, indent=2, ensure_ascii=False))
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=15)
        if fixture:
            shutil.rmtree(fixture, ignore_errors=True)


if __name__ == "__main__":
    main()
