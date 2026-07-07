import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch):
    monkeypatch.setenv("APP_API_TOKEN", "test-token")
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def auth_headers():
    return {"Authorization": "Bearer test-token"}


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "investment-data-api"
    assert data["version"] == "1.0.0"
    assert "time" in data


def test_v1_requires_bearer_token(client):
    response = client.get("/v1/equity/snapshot?market=US&symbol=AAPL")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_correct_bearer_token_reaches_provider_logic(client):
    response = client.get("/v1/equity/snapshot?market=US&symbol=AAPL", headers=auth_headers())
    assert response.status_code == 424
    assert response.json()["error"]["code"] == "MISSING_PROVIDER_KEY"


def test_missing_fmp_key_returns_clear_error(client):
    response = client.get("/v1/equity/snapshot?market=US&symbol=AAPL", headers=auth_headers())
    body = response.json()
    assert response.status_code == 424
    assert body["error"]["code"] == "MISSING_PROVIDER_KEY"
    assert "FMP_API_KEY" in body["error"]["user_action"]


def test_missing_tushare_token_returns_clear_error(client):
    response = client.get("/v1/equity/snapshot?market=CN&symbol=600519.SH", headers=auth_headers())
    body = response.json()
    assert response.status_code == 424
    assert body["error"]["code"] == "MISSING_PROVIDER_KEY"
    assert "TUSHARE_TOKEN" in body["error"]["user_action"]


def test_research_pack_with_missing_data_cannot_analyze(client):
    response = client.get("/v1/equity/research-pack?market=US&symbol=AAPL", headers=auth_headers())
    assert response.status_code == 200
    report = response.json()["data_quality_report"]
    assert report["can_analyze"] is False
    assert "snapshot" in report["missing_sections"]
    assert report["blocking_issues"]
    assert report["required_user_action"]
