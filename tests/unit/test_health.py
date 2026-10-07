import sqlite3
from importlib.metadata import version

from fastapi.testclient import TestClient

import apps.api.main as api_module
from apps.api.main import app
from promoguard import __version__


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == __version__
    assert version("promoguard-ai") == __version__


def test_readiness_endpoint_checks_durable_storage() -> None:
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "promoguard-api",
        "version": __version__,
        "storage": "ok",
        "deployment_scope": "controlled_environment",
    }


def test_readiness_endpoint_returns_dependency_failure_without_internal_details(
    monkeypatch,
) -> None:
    class BrokenStore:
        def connection(self):
            raise OSError("private filesystem path")

    monkeypatch.setattr(api_module, "_store", lambda: BrokenStore())
    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "ذخیره‌ساز متادیتای پایلوت آماده نیست؛ فضای runtime را بررسی کنید."
    }


def test_readiness_endpoint_maps_sqlite_failure_to_service_unavailable(monkeypatch) -> None:
    class LockedStore:
        def connection(self):
            raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(api_module, "_store", lambda: LockedStore())
    response = TestClient(app).get("/ready")

    assert response.status_code == 503

