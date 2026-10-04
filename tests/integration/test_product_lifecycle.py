from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

import apps.api.main as api_module
from apps.api.main import app


@pytest.fixture(autouse=True)
def isolate_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(api_module, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(api_module, "UPLOAD_ROOT", tmp_path / "runtime" / "datasets")
    monkeypatch.setattr(api_module, "REPORT_ROOT", tmp_path / "runtime" / "reports")
    api_module.DATASETS.clear()
    api_module.REPORTS.clear()


def upload_fixture(client, *, personal=False):
    panel = pd.DataFrame({
        "week_end_date": pd.date_range("2023-01-01", periods=70, freq="7D"),
        "store_id": "001", "upc": "00010", "units": [10.] * 55 + [20., 20.] + [10.] * 13,
        "promotion_flag": [0] * 55 + [1, 1] + [0] * 13,
    })
    if personal:
        panel["customer_phone"] = "09120000000"
    return client.post("/v1/datasets", files={"file": ("sales.csv", panel.to_csv(index=False).encode(), "text/csv")})


def test_restart_preserves_dataset_report_history_and_pdf():
    client = TestClient(app)
    dataset = upload_fixture(client).json()
    created = client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"]}).json()
    before = client.get(f"/v1/reports/{created['report_id']}").json()
    api_module.DATASETS.clear()
    api_module.REPORTS.clear()
    with TestClient(app) as restarted:
        after = restarted.get(f"/v1/reports/{created['report_id']}").json()
        assert after == before
        assert restarted.get(f"/v1/datasets/{dataset['dataset_id']}").status_code == 200
        assert restarted.get(f"/v1/reports/{created['report_id']}/pdf").content.startswith(b"%PDF")
        assert restarted.get("/v1/reports").json()["reports"][0]["report_id"] == created["report_id"]
        assert before["result"]["audit"]["store_id"] == "001"
        assert before["result"]["audit"]["upc"] == "00010"


def test_interrupted_job_recovers_to_failed_and_can_retry():
    client = TestClient(app)
    dataset = upload_fixture(client).json()
    api_module._store().put("report", "rpt_interrupted", {
        "report_id": "rpt_interrupted", "dataset_id": dataset["dataset_id"],
        "status": "running", "progress": 20, "result": None, "error": None,
    })
    with TestClient(app) as restarted:
        old = restarted.get("/v1/reports/rpt_interrupted").json()
        assert old["status"] == "failed"
        retried = restarted.post("/v1/reports/rpt_interrupted/retry").json()
        assert retried["report_id"] != "rpt_interrupted"
        assert restarted.get(f"/v1/reports/{retried['report_id']}").json()["status"] == "ready"


def test_invalid_campaign_returns_persisted_failure_without_stack_trace():
    client = TestClient(app)
    dataset = upload_fixture(client).json()
    created = client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"],
        "store_id": "001", "upc": "00010", "start_date": "2020-01-01"}).json()
    report = client.get(f"/v1/reports/{created['report_id']}").json()
    assert report["status"] == "failed"
    assert report["result"] is None
    assert "C:" not in report["error"]


def test_changed_source_cannot_use_cached_result():
    client = TestClient(app)
    dataset = upload_fixture(client).json()
    client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"]})
    source = Path(api_module._dataset_record(dataset["dataset_id"])["path"])
    source.write_bytes(source.read_bytes() + b"\n")
    created = client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"]}).json()
    report = client.get(f"/v1/reports/{created['report_id']}").json()
    assert report["status"] == "failed"
    assert report["result"] is None


def test_personal_columns_rejected_before_storage():
    response = upload_fixture(TestClient(app), personal=True)
    assert response.status_code == 422
    assert not api_module.UPLOAD_ROOT.exists()


def test_unexpected_worker_error_is_persisted_without_internal_details(monkeypatch):
    def broken_analysis(*args):
        raise RuntimeError("private internal debug message")

    client = TestClient(app)
    dataset = upload_fixture(client).json()
    monkeypatch.setattr(api_module, "_dashboard_summary_for_path", broken_analysis)
    created = client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"]}).json()
    report = client.get(f"/v1/reports/{created['report_id']}").json()
    assert report["status"] == "failed"
    assert report["result"] is None
    assert "private internal" not in report["error"]


def test_corrupt_cache_is_recomputed_without_changing_result():
    client = TestClient(app)
    dataset = upload_fixture(client).json()
    created = client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"]}).json()
    before = client.get(f"/v1/reports/{created['report_id']}").json()
    cache = next((api_module.REPORT_ROOT / "cache").glob("*.json"))
    cache.write_text('{"quality": {}, "audit": {}, "decision_support": {}, "trend": []}', encoding="utf-8")
    created = client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"]}).json()
    after = client.get(f"/v1/reports/{created['report_id']}").json()
    assert after["status"] == "ready"
    assert after["cache_hit"] is False
    assert after["result"] == before["result"]


def test_report_cache_key_separates_source_and_selected_event() -> None:
    first = {"store_id": "1", "upc": "10", "start_date": "2024-01-01"}
    other_event = {"store_id": "1", "upc": "10", "start_date": "2024-02-01"}

    assert api_module._report_cache_key("a" * 64, first) == api_module._report_cache_key(
        "a" * 64, {**first}
    )
    assert api_module._report_cache_key("a" * 64, first) != api_module._report_cache_key(
        "a" * 64, other_event
    )
    assert api_module._report_cache_key("a" * 64, first) != api_module._report_cache_key(
        "b" * 64, first
    )


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

    promotions = client.get(f"/v1/datasets/{dataset['dataset_id']}/promotions")
    assert promotions.status_code == 200
    assert promotions.json()["count"] == 1
    selected = promotions.json()["events"][0]

    created = client.post(
        "/v1/reports",
        json={
            "dataset_id": dataset["dataset_id"],
            "store_id": selected["store_id"],
            "upc": selected["upc"],
            "start_date": selected["start_date"],
        },
    )
    assert created.status_code == 202
    report_id = created.json()["report_id"]
    report = client.get(f"/v1/reports/{report_id}")
    assert report.status_code == 200
    assert report.json()["status"] == "ready"
    assert report.json()["selected_event"]["start_date"] == selected["start_date"]
    assert report.json()["result"]["audit"]["start_date"] == selected["start_date"]
    assert report.json()["result"]["audit"]["recommendation"] == "candidate_for_controlled_test"
    assert report.json()["result"]["decision_support"]["recommended_action"] == "more_testing"
    assert report.json()["result"]["dataset_name"] == "sales.csv"
    assert "dataset_path" not in report.json()["result"]
    assert report.json()["cache_hit"] is False

    repeated = client.post(
        "/v1/reports",
        json={
            "dataset_id": dataset["dataset_id"],
            "store_id": selected["store_id"],
            "upc": selected["upc"],
            "start_date": selected["start_date"],
        },
    )
    cached_report = client.get(f"/v1/reports/{repeated.json()['report_id']}").json()
    assert cached_report["status"] == "ready"
    assert cached_report["cache_hit"] is True
    assert cached_report["result"] == report.json()["result"]

    pdf = client.get(f"/v1/reports/{report_id}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")
    reader = PdfReader(BytesIO(pdf.content))
    assert len(reader.pages) == 1
    assert "گزارش ممیزی پروموشن" in (reader.metadata.title or "")
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert report_id in extracted


def test_controlled_path_import_uses_the_same_dataset_contract(tmp_path: Path, monkeypatch) -> None:
    panel = pd.DataFrame(
        {
            "week_end_date": pd.date_range("2023-01-01", periods=70, freq="7D"),
            "store_id": "1",
            "upc": "10",
            "units": [10.0] * 55 + [20.0, 20.0] + [10.0] * 13,
            "promotion_flag": [0] * 55 + [1, 1] + [0] * 13,
        }
    )
    dataset_root = tmp_path / "data"
    dataset_root.mkdir()
    path = dataset_root / "weekly_panel.csv"
    panel.to_csv(path, index=False)
    monkeypatch.setattr(api_module, "LOCAL_DATA_ROOT", dataset_root.resolve())
    api_module.DATASETS.clear()

    response = TestClient(app).post("/v1/datasets/import-path", json={"input_path": str(path)})

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["filename"] == "weekly_panel.csv"


def test_report_rejects_partial_selected_event_key() -> None:
    response = TestClient(app).post(
        "/v1/reports", json={"dataset_id": "dataset-123", "store_id": "1"}
    )

    assert response.status_code == 422
