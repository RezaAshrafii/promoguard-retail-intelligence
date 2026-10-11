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


@pytest.fixture(autouse=True)
def isolate_local_data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_module, "LOCAL_DATA_ROOT", tmp_path.resolve())


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


def test_oversized_local_panel_is_rejected_before_loading(
    client: TestClient,
    panel_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_module, "MAX_UPLOAD_BYTES", 1)

    response = client.post("/v1/panels/validate", json={"input_path": str(panel_path)})

    assert response.status_code == 400
    assert "limit is 1 bytes" in response.json()["detail"]


def test_local_path_outside_configured_data_root_is_forbidden(
    client: TestClient, tmp_path: Path
) -> None:
    outside_path = tmp_path.parent / "outside-root-panel.csv"
    realistic_panel().to_csv(outside_path, index=False)

    response = client.post("/v1/panels/validate", json={"input_path": str(outside_path)})

    assert response.status_code == 403
    assert "configured data root" in response.json()["detail"]


def test_api_blocks_blank_canonical_grain_identifier(
    client: TestClient, tmp_path: Path
) -> None:
    panel = realistic_panel()
    panel.loc[0, "store_id"] = "   "
    invalid_path = tmp_path / "invalid-grain.csv"
    panel.to_csv(invalid_path, index=False)

    response = client.post("/v1/panels/validate", json={"input_path": str(invalid_path)})

    assert response.status_code == 422
    assert response.json()["detail"]["missing_store_id_rows"] == 1


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


def test_upload_rejects_non_finite_units_without_serialization_failure(
    client: TestClient,
) -> None:
    panel = realistic_panel()
    panel.loc[0, "units"] = float("inf")
    content = panel.to_csv(index=False).encode("utf-8")

    response = client.post(
        "/v1/panels/validate-upload",
        files={"file": ("weekly_panel.csv", content, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["non_finite_units_rows"] == 1


def test_upload_rejects_columns_that_collide_after_trimming(client: TestClient) -> None:
    content = b"week_end_date,store_id,upc,units, units ,promotion_flag\n2024-01-01,1,2,3,4,0\n"

    response = client.post(
        "/v1/panels/validate-upload",
        files={"file": ("weekly_panel.csv", content, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["duplicate_column_names"] == ["units"]


def test_auto_audit_without_an_eligible_event_returns_422(
    client: TestClient, tmp_path: Path
) -> None:
    panel = realistic_panel()
    panel["promotion_flag"] = 0
    path = tmp_path / "no-events.csv"
    panel.to_csv(path, index=False)

    response = client.post("/v1/audits", json={"input_path": str(path)})

    assert response.status_code == 422
    assert "No promotion episode" in response.json()["detail"]


def test_hillstrom_report_uses_async_report_contract_and_persists_result(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "hillstrom.csv"
    source.write_text("public benchmark test source", encoding="utf-8")
    runtime = tmp_path / "runtime"
    reports = runtime / "reports"
    monkeypatch.setattr(api_module, "RUNTIME_ROOT", runtime)
    monkeypatch.setattr(api_module, "REPORT_ROOT", reports)
    monkeypatch.setattr(api_module, "HILLSTROM_DATASET_PATH", source)
    monkeypatch.setattr(api_module, "_run_hillstrom_report", lambda _report_id: None)

    response = client.post(
        "/v1/experiments/hillstrom/reports",
        json={
            "primary_outcome": "spend",
            "financial_assumptions": {
                "common_contribution_margin": 0.3,
                "margin_source": "test-only stated assumption",
                "mens_campaign_cost_per_1000": 90,
                "mens_cost_source": "test-only mens cost assumption",
                "womens_campaign_cost_per_1000": 60,
                "womens_cost_source": "test-only womens cost assumption",
                "currency": "USD",
            },
        },
    )

    assert response.status_code == 202
    created = response.json()
    assert created["analysis_type"] == "randomized_experiment"
    assert created["status"] == "queued"
    assert created["configuration"]["analysis"]["primary_outcome"] == "spend"
    assert created["configuration"]["analysis"]["financial_assumptions"]["mens_campaign_cost_per_1000"] == 90
    stored = api_module._store().get("report", created["report_id"])
    assert stored["dataset_id"].startswith("hillstrom-")


def test_hillstrom_report_rejects_margin_without_a_source(client: TestClient) -> None:
    response = client.post(
        "/v1/experiments/hillstrom/reports",
        json={
            "financial_assumptions": {
                "common_contribution_margin": 0.3,
                "margin_source": " ",
                "mens_campaign_cost_per_1000": 90,
                "mens_cost_source": "test-only",
                "womens_campaign_cost_per_1000": 60,
                "womens_cost_source": "test-only",
            }
        },
    )
    assert response.status_code == 422


def test_hillstrom_report_rejects_financial_inputs_for_non_revenue_outcome(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/experiments/hillstrom/reports",
        json={
            "primary_outcome": "conversion",
            "financial_assumptions": {
                "common_contribution_margin": 0.3,
                "margin_source": "test only",
                "mens_campaign_cost_per_1000": 1,
                "mens_cost_source": "test only",
                "womens_campaign_cost_per_1000": 1,
                "womens_cost_source": "test only",
            },
        },
    )
    assert response.status_code == 422


def test_hillstrom_ready_report_downloads_dedicated_pdf(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_id = "rpt_hillstrom_pdf"
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(api_module, "RUNTIME_ROOT", runtime)
    monkeypatch.setattr(api_module, "REPORT_ROOT", runtime / "reports")
    record = {
        "report_id": report_id,
        "dataset_id": "hillstrom-test",
        "analysis_type": "randomized_experiment",
        "configuration": {"analysis": {"financial_assumptions": None}},
        "status": "ready",
        "progress": 100,
        "result": {
            "benchmark": "hillstrom-email-analytics-2008",
            "source": {"sha256": "a" * 64, "license_status": "No explicit license stated", "dataset_page": "https://example.org"},
            "design": {"sample_rows": 0, "outcome_window": "two weeks", "arm_counts": {}},
            "primary_outcome": {"name": "spend", "unit": "USD gross revenue per assigned customer"},
            "uncertainty": {"method": "Welch interval", "contrast_count": 3},
            "comparisons": [],
            "interpretation": ["Gross spend is not profit."],
        },
    }
    api_module._save_report(record)

    response = client.get(f"/v1/reports/{report_id}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"].endswith(f'filename="{report_id}.pdf"')
    assert response.content.startswith(b"%PDF")
    assert (runtime / "reports" / f"{report_id}-experiment-v2.pdf").is_file()


def test_hillstrom_pdf_is_not_available_before_report_is_ready(
    client: TestClient,
) -> None:
    api_module._save_report({
        "report_id": "rpt_hillstrom_queued_pdf",
        "dataset_id": "hillstrom-test",
        "analysis_type": "randomized_experiment",
        "status": "queued",
        "progress": 30,
        "result": None,
    })

    response = client.get("/v1/reports/rpt_hillstrom_queued_pdf/pdf")

    assert response.status_code == 409


def test_hillstrom_worker_caches_valid_result_by_source_and_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "hillstrom.csv"
    source.write_text("public benchmark test source", encoding="utf-8")
    runtime = tmp_path / "runtime"
    reports = runtime / "reports"
    monkeypatch.setattr(api_module, "RUNTIME_ROOT", runtime)
    monkeypatch.setattr(api_module, "REPORT_ROOT", reports)
    monkeypatch.setattr(api_module, "HILLSTROM_DATASET_PATH", source)
    calls = 0
    expected = {
        "benchmark": "hillstrom-email-analytics-2008",
        "source": {"sha256": api_module.hillstrom_sha256_file(source)},
        "comparisons": [{"arm": "a"}, {"arm": "b"}, {"arm": "c"}],
    }

    def evaluate(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return expected

    monkeypatch.setattr(api_module, "evaluate_hillstrom_csv", evaluate)
    configuration = {"primary_outcome": "spend", "minimum_effect_per_person": None}
    for report_id in ("rpt_first", "rpt_second"):
        api_module._save_report(
            {
                "report_id": report_id,
                "dataset_id": "hillstrom-test",
                "analysis_type": "randomized_experiment",
                "configuration": {
                    "benchmark": "hillstrom-email-analytics-2008",
                    "source_sha256": api_module.hillstrom_sha256_file(source),
                    "analysis": configuration,
                },
                "status": "queued",
                "progress": 0,
            }
        )
        api_module._run_hillstrom_report(report_id)

    first = api_module._store().get("report", "rpt_first")
    second = api_module._store().get("report", "rpt_second")
    assert first["status"] == second["status"] == "ready"
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert calls == 1
    assert second["result"] == expected
    assert (reports / "rpt_first.json").is_file()


def test_malformed_upload_is_reported_without_analysis(client: TestClient) -> None:
    response = client.post(
        "/v1/panels/validate-upload",
        files={"file": ("weekly_panel.csv", b"only,wrong\n1,2\n", "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "units" in response.json()["missing_required_columns"]


def test_manager_scenario_comparison_api_returns_bounded_policy_result(
    client: TestClient,
) -> None:
    economics_fields = [
        "regular_unit_price",
        "promotion_unit_price",
        "unit_cost",
        "supplier_funding_per_unit",
        "fixed_trade_spend",
        "variable_trade_spend_per_unit",
        "available_inventory_units",
        "baseline_demand_units",
        "projected_demand_units",
    ]
    response = client.post(
        "/v1/optimization/comparisons",
        json={
            "optimization": {
                "request_id": "api-review-1",
                "currency": "IRR",
                "total_trade_spend_budget": "250000",
                "minimum_unit_contribution": "20000",
                "maximum_discount_rate": "0.20",
                "inventory_reserve_units": 20,
                "scenarios": [
                    {
                        "scenario_id": "case-1",
                        "store_id": "store-1",
                        "sku_id": "sku-1",
                        "start_date": "2026-10-01",
                        "end_date": "2026-10-07",
                        "currency": "IRR",
                        "regular_unit_price": "100000",
                        "promotion_unit_price": "90000",
                        "unit_cost": "70000",
                        "supplier_funding_per_unit": "5000",
                        "fixed_trade_spend": "100000",
                        "variable_trade_spend_per_unit": "1000",
                        "available_inventory_units": 200,
                        "baseline_demand_units": 80,
                        "projected_demand_units": {
                            "point": 100,
                            "lower": 90,
                            "upper": 120,
                        },
                        "evidence": [
                            {
                                "field_name": field,
                                "kind": "model_output"
                                if field == "projected_demand_units"
                                else "partner_export",
                                "reference": f"approved-export:{field}",
                                "as_of_date": "2026-10-11",
                                "approved_by": "sales-manager",
                            }
                            for field in economics_fields
                        ],
                    }
                ],
                "human_approval_required": True,
                "automatic_execution_allowed": False,
            },
            "policy": {
                "minimum_incremental_profit": "0",
                "currency": "IRR",
                "reference": "manager-approved-zero-hurdle",
                "approved_by": "sales-manager",
                "as_of_date": "2026-10-11",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == "api-review-1"
    assert payload["assessments"][0]["decision"] == "hurdle_not_resolved"
    assert payload["selection_status"] == "manual_review_required"
    assert payload["selected_scenario_id"] is None
    assert payload["budget_scope"] == "per_scenario_screen_only"
    assert payload["assessments"][0]["blocking_reasons"] == []
    assessment = payload["assessments"][0]
    assert assessment["conditional_economics"]["baseline_profit"] == "2400000.0"
    assert assessment["conditional_economics"]["promoted_profit"]["point"] == "2300000.0"
    assert assessment["economic_sensitivity"]["cases"][1]["incremental_profit"] == "-100000.0"
    assert assessment["discount_rate"] == "0.1"
    assert assessment["projected_unit_contribution"] == "24000"
    assert assessment["projected_trade_spend"] == "220000.0"
    assert assessment["sellable_inventory_units"] == 180
    assert "میان سبد تقسیم نشده است" in payload["limitation"]
    assert "هویت او احراز نمی‌شود" in payload["limitation"]
    assert "نه بازهٔ اطمینان" in payload["limitation"]


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
