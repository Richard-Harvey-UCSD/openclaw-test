"""Tests for REST endpoints using httpx async client."""
import pytest
import httpx
from castgesture.server.app import app


@pytest.fixture
def client():
    from starlette.testclient import TestClient
    return TestClient(app)


class TestStatusEndpoint:
    def test_status(self, client):
        r = client.get("/api/status")
        assert r.status_code == 200
        data = r.json()
        assert data["server"] == "running"
        assert "clients" in data

    def test_root_returns_html(self, client):
        r = client.get("/")
        assert r.status_code == 200


class TestEffectsEndpoint:
    def test_get_effects(self, client):
        r = client.get("/api/effects")
        assert r.status_code == 200
        data = r.json()
        assert "confetti" in data
        assert "fire" in data

    def test_test_effect(self, client):
        r = client.post("/api/test/confetti")
        assert r.status_code == 200
        assert r.json()["status"] == "triggered"

    def test_test_unknown_effect(self, client):
        r = client.post("/api/test/nonexistent")
        assert r.status_code == 200


class TestMappingsEndpoint:
    def test_get_mappings(self, client):
        r = client.get("/api/mappings")
        assert r.status_code == 200
        data = r.json()
        assert "mappings" in data

    def test_update_mapping(self, client):
        r = client.post("/api/mappings", json={
            "gesture": "test_gesture",
            "effect": "confetti",
            "params": {"intensity": 1.5},
        })
        assert r.status_code == 200

    def test_delete_mapping(self, client):
        # Add then delete
        client.post("/api/mappings", json={
            "gesture": "to_delete", "effect": "flash",
        })
        r = client.delete("/api/mappings/to_delete")
        assert r.status_code == 200


class TestConfigEndpoint:
    def test_get_config(self, client):
        r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        assert "host" in data
        assert "port" in data

    def test_update_config(self, client):
        r = client.post("/api/config", json={"debug": True})
        assert r.status_code == 200


class TestSoundsEndpoint:
    def test_get_sounds(self, client):
        r = client.get("/api/sounds")
        assert r.status_code == 200
        data = r.json()
        assert "pop" in data
