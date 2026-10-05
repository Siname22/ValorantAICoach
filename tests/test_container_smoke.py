import json
import os
import shlex
import shutil
import socket
import struct
import subprocess
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread

import pytest
import yaml


def liveness_command(url):
    workflow = yaml.safe_load(
        (Path(__file__).parents[1] / ".github/workflows/ci.yml").read_text(
            encoding="utf-8"
        )
    )
    step = next(
        step
        for step in workflow["jobs"]["backend-image"]["steps"]
        if step.get("name") == "Check liveness without provider credentials"
    )
    statement = next(
        line.strip()
        for line in step["run"].splitlines()
        if line.strip().startswith("curl ")
    )
    command = shlex.split(statement)
    executable = shutil.which("curl")
    if not executable:
        pytest.skip("curl is required to exercise the container smoke command")
    command[0] = executable
    command[-1] = url
    return command


@contextmanager
def health_server(mode):
    requests = []
    release = Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            if mode == "reset-once" and len(requests) == 1:
                linger = struct.pack("hh" if os.name == "nt" else "ii", 1, 0)
                self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
                self.close_connection = True
                self.connection.close()
                return
            if mode == "stall":
                release.wait(timeout=10)
                return
            body = b'{"status":"ok","version":"0.4.0"}'
            self.send_response(400 if mode == "unhealthy" else 200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/health/live", requests
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def run_liveness(command, timeout=10):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"},
        check=False,
    )


def test_workflow_liveness_recovers_from_startup_connection_reset():
    with health_server("reset-once") as (url, requests):
        result = run_liveness(liveness_command(url))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "ok"
    assert requests == ["/health/live", "/health/live"]


def test_workflow_liveness_does_not_accept_persistent_http_failure():
    with health_server("unhealthy") as (url, requests):
        command = liveness_command(url)
        command[command.index("--retry") + 1] = "1"
        result = run_liveness(command)
    assert result.returncode == 22, result.stderr
    assert result.stdout == ""
    assert requests


def test_workflow_liveness_bounds_a_stalled_response():
    with health_server("stall") as (url, requests):
        command = liveness_command(url)
        command[command.index("--retry") + 1] = "0"
        try:
            result = run_liveness(command, timeout=6)
        except subprocess.TimeoutExpired:
            pytest.fail("The workflow must time out a stalled liveness response")
    assert result.returncode == 28, result.stderr
    assert requests == ["/health/live"]
