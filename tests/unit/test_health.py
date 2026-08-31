from fastapi.testclient import TestClient

from apps.api.main import app
from promoguard import __version__


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == __version__ == "0.5.2"

