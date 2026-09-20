from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import apps.api.main as api_module
from apps.api.main import app


def test_dashboard_summary_returns_quality_audit_and_real_trend(
    tmp_path: Path, monkeypatch
) -> None:
    weeks = pd.date_range("2023-01-01", periods=70, freq="7D")
    panel = pd.DataFrame(
        {
            "week_end_date": weeks,
            "store_id": "1",
            "upc": "10",
            "units": [10.0] * 55 + [20.0, 20.0] + [10.0] * 13,
            "promotion_flag": [0] * 55 + [1, 1] + [0] * 13,
        }
    )
    path = tmp_path / "weekly_panel.csv"
    panel.to_csv(path, index=False)
    monkeypatch.setattr(api_module, "LOCAL_DATA_ROOT", tmp_path.resolve())

    response = TestClient(app).post("/v1/dashboard/summary", json={"input_path": str(path)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["quality"]["valid"] is True
    assert payload["audit"]["recommendation"] == "candidate_for_controlled_test"
    # Eight weeks before and after a two-week event gives 18 displayed weeks.
    assert len(payload["trend"]) == 18
    assert payload["trend"][0]["week_end_date"] == "2023-11-26"
