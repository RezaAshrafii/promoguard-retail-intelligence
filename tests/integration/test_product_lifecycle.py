from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import apps.api.main as api_module
from apps.api.main import app


def test_upload_dataset_report_and_pdf_lifecycle(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.setattr(api_module, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(api_module, "UPLOAD_ROOT", tmp_path / "runtime" / "datasets")
    monkeypatch.setattr(api_module, "REPORT_ROOT", tmp_path / "runtime" / "reports")
    api_module.DATASETS.clear()
    api_module.REPORTS.clear()

    content = panel.to_csv(index=False).encode("utf-8")
    client = TestClient(app)
    upload = client.post("/v1/datasets", files={"file": ("sales.csv", content, "text/csv")})
    assert upload.status_code == 200
    dataset = upload.json()
    assert dataset["status"] == "ready"
    assert len(dataset["dataset_id"]) == 24
    assert dataset["quality"]["valid"] is True

    created = client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"]})
    assert created.status_code == 202
    report_id = created.json()["report_id"]
    report = client.get(f"/v1/reports/{report_id}")
    assert report.status_code == 200
    assert report.json()["status"] == "ready"
    assert report.json()["result"]["audit"]["recommendation"] == "candidate_for_controlled_test"

    pdf = client.get(f"/v1/reports/{report_id}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")
