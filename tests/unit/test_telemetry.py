"""Tracing exports real OTLP/HTTP spans when an endpoint is configured, and stays off otherwise."""

import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from apps.api import telemetry

CHILD = """
from fastapi.testclient import TestClient
from opentelemetry import trace
from apps.api.main import app
assert TestClient(app).get("/api/v1/batteries").status_code == 200
TestClient(app).get("/health")
trace.get_tracer_provider().force_flush()
"""


def test_disabled_without_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert telemetry.configure(app=None, engine=None) is False


def test_request_spans_are_exported_over_otlp_http():
    received: list[tuple[str, bytes]] = []

    class Collector(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - http.server API
            received.append((self.path, self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Collector)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = {**os.environ, "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": f"http://127.0.0.1:{server.server_port}/v1/traces"}
    result = subprocess.run([sys.executable, "-c", CHILD], env=env, capture_output=True, text=True, timeout=120)
    server.shutdown()
    assert result.returncode == 0, result.stderr[-2000:]
    payload = b"".join(body for path, body in received if path == "/v1/traces")
    assert b"/api/v1/batteries" in payload  # the request span was exported
    assert b"batterymind-api" in payload  # service.name resource attribute
    assert b"/health" not in payload  # health checks are excluded
