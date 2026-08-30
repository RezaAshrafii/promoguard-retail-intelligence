from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_module
from apps.api.main import app


def realistic_panel() -> pd.DataFrame:
    weeks = pd.date_range("2023-01-01", periods=70, freq="7D")
    units = [10.0] * len(weeks)
    promotions = [0] * len(weeks)
    units[55:57] = [20.0, 20.0]
    promotions[55:57] = [1, 1]
    return pd.DataFrame(
        {
            "week_end_date": weeks,
            "store_id": "1",
            "upc": "10",
            "units": units,
            "promotion_flag": promotions,
            "inventory_on_hand": 100,
        }
    )


@pytest.fixture
def panel_path(tmp_path: Path) -> Path:
    path = tmp_path / "weekly_panel.csv"
    realistic_panel().to_csv(path, index=False)
    return path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_validate_list_and_audit_realistic_panel(client: TestClient, panel_path: Path) -> None:
    validation = client.post("/v1/panels/validate", json={"input_path": str(panel_path)})
    assert validation.status_code == 200
    assert validation.json()["valid"] is True

    promotions = client.post(
        "/v1/promotions", json={"input_path": str(panel_path), "limit": 10}
    )
    assert promotions.status_code == 200
    assert promotions.json()["count"] == 1

    audit = client.post("/v1/audits", json={"input_path": str(panel_path)})
    assert audit.status_code == 200
    payload = audit.json()
    assert payload["recommendation"] == "candidate_for_controlled_test"
    assert any(warning["code"] == "OBSERVATIONAL_ONLY" for warning in payload["warnings"])
    assert "causal treatment effect" in payload["claim_language"]


def test_contribution_sensitivity_is_typed_and_never_drives_recommendation(
    client: TestClient, panel_path: Path
) -> None:
    response = client.post(
        "/v1/audits",
        json={
            "input_path": str(panel_path),
            "contribution_assumption": {
                "amount_per_incremental_unit": -100,
                "currency": "irr",
                "source": "approved test assumption",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["contribution_sensitivity"]["status"] == "sensitivity_only"
    assert payload["contribution_sensitivity"]["assumption"]["currency"] == "IRR"
    assert payload["recommendation"] == "candidate_for_controlled_test"


def test_missing_local_panel_returns_not_found(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/v1/panels/validate", json={"input_path": str(tmp_path / "missing.csv")}
    )
    assert response.status_code == 404


def test_partial_event_key_is_rejected_by_contract(client: TestClient, panel_path: Path) -> None:
    response = client.post(
        "/v1/audits",
        json={"input_path": str(panel_path), "store_id": "1"},
    )
    assert response.status_code == 422


def test_csv_upload_returns_quality_report(client: TestClient) -> None:
    content = realistic_panel().to_csv(index=False).encode("utf-8")
    response = client.post(
        "/v1/panels/validate-upload",
        files={"file": ("weekly_panel.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_malformed_upload_is_reported_without_analysis(client: TestClient) -> None:
    response = client.post(
        "/v1/panels/validate-upload",
        files={"file": ("weekly_panel.csv", b"only,wrong\n1,2\n", "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "units" in response.json()["missing_required_columns"]


def test_empty_and_oversized_uploads_are_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = client.post(
        "/v1/panels/validate-upload",
        files={"file": ("weekly_panel.csv", b"", "text/csv")},
    )
    assert empty.status_code == 400

    monkeypatch.setattr(api_module, "MAX_UPLOAD_BYTES", 10)
    oversized = client.post(
        "/v1/panels/validate-upload",
        files={"file": ("weekly_panel.csv", b"a" * 11, "text/csv")},
    )
    assert oversized.status_code == 413
