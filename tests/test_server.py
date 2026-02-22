"""Tests for the WebSocket server REST endpoints."""

import pytest

try:
    from fastapi.testclient import TestClient
    _HAS_TESTCLIENT = True
except ImportError:
    _HAS_TESTCLIENT = False

try:
    from gesture_engine.server import app, state
    _HAS_SERVER = True
except ImportError:
    _HAS_SERVER = False


pytestmark = pytest.mark.skipif(
    not (_HAS_TESTCLIENT and _HAS_SERVER),
    reason="fastapi not installed"
)


@pytest.fixture
def client():
    # Prevent capture_loop from starting
    state.running = False
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    state.running = False


class TestRESTEndpoints:
    def test_api_status(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "running" in data
        assert "fps" in data
        assert "clients" in data

    def test_api_gestures(self, client):
        resp = client.get("/api/gestures")
        assert resp.status_code == 200
        data = resp.json()
        assert "gestures" in data

    def test_api_heatmap(self, client):
        resp = client.get("/api/heatmap")
        assert resp.status_code == 200
        assert "heatmap" in resp.json()

    def test_api_trajectories(self, client):
        resp = client.get("/api/trajectories")
        assert resp.status_code == 200

    def test_api_plugins(self, client):
        resp = client.get("/api/plugins")
        assert resp.status_code == 200

    def test_metrics_endpoint(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "gesture_engine" in resp.text


class TestWebSocket:
    def test_ws_connect(self, client):
        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"
            assert "gestures" in msg
