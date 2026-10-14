from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_module
from apps.api.main import app
from promoguard.experiments.hillstrom import HISTORY_SEGMENTS, TREATMENT_SEGMENTS


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


def valid_hillstrom_result(source_sha256: str) -> dict:
    comparisons = [
        {
            "treatment_arm": treatment,
            "control_arm": control,
            "contrast_type": contrast_type,
            "treatment_n": 4,
            "control_n": 4,
            "incremental_effect_per_person": 0.1,
        }
        for treatment, control, contrast_type in (
            ("Mens E-Mail", "No E-Mail", "treatment_vs_control"),
            ("Womens E-Mail", "No E-Mail", "treatment_vs_control"),
            ("Mens E-Mail", "Womens E-Mail", "treatment_vs_treatment"),
        )
    ]
    contrasts = [
        {
            "history_segment": history_segment,
            "treatment_arm": treatment,
            "control_arm": "No E-Mail",
            "treatment_n": 4,
            "control_n": 4,
            "interpretation_allowed": False,
        }
        for history_segment in HISTORY_SEGMENTS
        for treatment in TREATMENT_SEGMENTS
    ]
    heterogeneity_tests = [
        {
            "treatment_arm": treatment,
            "control_arm": "No E-Mail",
            "method": "inverse-variance Cochran Q with asymptotic chi-square reference",
            "strata_count": 7,
            "estimable_strata_count": 7,
            "degrees_of_freedom": 6,
            "minimum_cell_size": 4,
            "minimum_cell_size_for_interpretation": 1_000,
            "interpretation_allowed": False,
            "statistic": None,
            "p_value": None,
            "familywise_adjusted_p_value": None,
            "familywise_test_count": 2,
            "status": "insufficient_sample",
            "reason_code": "below_minimum_cell_size_for_interpretation",
        }
        for treatment in TREATMENT_SEGMENTS
    ]
    return {
        "benchmark": api_module.HILLSTROM_DATASET,
        "source": {"sha256": source_sha256},
        "comparisons": comparisons,
        "subgroup_analysis": {
            "contrasts": contrasts,
            "heterogeneity_tests": heterogeneity_tests,
        },
    }


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


def test_failed_experiment_retry_preserves_configuration_and_report_type(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "hillstrom.csv"
    source.write_text("test-only source", encoding="utf-8")
    monkeypatch.setattr(api_module, "HILLSTROM_DATASET_PATH", source)
    monkeypatch.setattr(api_module, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(api_module, "_run_hillstrom_report", lambda _id: None)
    configuration = {"primary_outcome": "spend", "minimum_effect_per_person": 0.5,
                     "financial_assumptions": {
                         "common_contribution_margin": 0.3, "margin_source": "test margin",
                         "mens_campaign_cost_per_1000": 0, "mens_cost_source": "test mens",
                         "womens_campaign_cost_per_1000": 60, "womens_cost_source": "test womens",
                         "currency": "USD",
                     }}
    previous = {"report_id": "rpt_failed_experiment", "dataset_id": "hillstrom-test",
                "analysis_type": "randomized_experiment", "status": "failed", "progress": 20,
                "configuration": {"analysis": configuration}, "result": None}
    api_module._save_report(previous)
    response = client.post("/v1/reports/rpt_failed_experiment/retry")
    assert response.status_code == 202
    record = response.json()
    assert record["report_id"] != previous["report_id"]
    assert record["analysis_type"] == "randomized_experiment"
    assert record["configuration"]["analysis"] == configuration
    assert api_module._store().get("report", previous["report_id"])["status"] == "failed"


@pytest.mark.parametrize("analysis", [None, {"primary_outcome": "unknown"}])
def test_failed_experiment_retry_rejects_unrecoverable_settings(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, analysis: object,
) -> None:
    monkeypatch.setattr(api_module, "RUNTIME_ROOT", tmp_path / "runtime")
    api_module._save_report({
        "report_id": "rpt_bad_config", "dataset_id": "hillstrom-test",
        "analysis_type": "randomized_experiment", "status": "failed", "progress": 20,
        "configuration": {"analysis": analysis}, "result": None,
    })
    assert client.post("/v1/reports/rpt_bad_config/retry").status_code == 422


def test_upload_padded_columns_reaches_selected_report_without_losing_ids(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_module, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(api_module, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(api_module, "REPORT_ROOT", tmp_path / "reports")
    frame = realistic_panel().assign(store_id="001", upc="00010")
    frame.columns = [f" {name} " for name in frame.columns]
    response = client.post("/v1/datasets", files={"file": ("test.csv", frame.to_csv(index=False).encode(), "text/csv")})
    assert response.status_code == 200
    dataset = response.json()
    assert dataset["status"] == "ready"
    events = client.get(f"/v1/datasets/{dataset['dataset_id']}/promotions").json()["events"]
    assert events[0]["store_id"] == "001" and events[0]["upc"] == "00010"
    event = {key: events[0][key] for key in ("store_id", "upc", "start_date")}
    created = client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"], **event})
    assert created.status_code == 202
    ready = client.get(f"/v1/reports/{created.json()['report_id']}").json()
    assert ready["status"] == "ready"
    assert ready["result"]["audit"]["upc"] == "00010"


def test_upload_bad_inventory_is_rejected_and_does_not_queue_analysis(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_module, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(api_module, "UPLOAD_ROOT", tmp_path / "uploads")
    frame = realistic_panel().assign(inventory_on_hand="invalid")
    response = client.post("/v1/datasets", files={"file": ("test.csv", frame.to_csv(index=False).encode(), "text/csv")})
    dataset = response.json()
    assert dataset["status"] == "rejected"
    assert dataset["quality"]["invalid_inventory_rows"] == len(frame)
    assert client.post("/v1/reports", json={"dataset_id": dataset["dataset_id"]}).status_code == 422


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
    assert (runtime / "reports" / f"{report_id}-experiment-v9.pdf").is_file()


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
    expected = valid_hillstrom_result(api_module.hillstrom_sha256_file(source))

    def evaluate(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return expected

    monkeypatch.setattr(api_module, "evaluate_hillstrom_csv", evaluate)
    configuration = {"primary_outcome": "spend", "minimum_effect_per_person": None}
    def create_report(report_id: str) -> None:
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

    create_report("rpt_first")
    cache_path = next((reports / "cache").glob("hillstrom-*.json"))
    damaged_cache = json.loads(cache_path.read_text(encoding="utf-8"))
    damaged_cache["subgroup_analysis"]["heterogeneity_tests"] = [None, None]
    cache_path.write_text(json.dumps(damaged_cache), encoding="utf-8")
    create_report("rpt_second")
    create_report("rpt_third")

    first = api_module._store().get("report", "rpt_first")
    second = api_module._store().get("report", "rpt_second")
    third = api_module._store().get("report", "rpt_third")
    assert first["status"] == second["status"] == third["status"] == "ready"
    assert first["cache_hit"] is False
    assert second["cache_hit"] is False
    assert third["cache_hit"] is True
    assert calls == 2
    assert second["result"] == expected
    assert (reports / "rpt_first.json").is_file()


def test_hillstrom_result_contract_rejects_malformed_nested_tests_and_non_finite_numbers() -> None:
    import copy

    result = valid_hillstrom_result("a" * 64)
    assert api_module._valid_hillstrom_result(result, "a" * 64)

    malformed = copy.deepcopy(result)
    malformed["subgroup_analysis"]["heterogeneity_tests"] = [None, None]
    assert not api_module._valid_hillstrom_result(malformed, "a" * 64)

    non_finite = copy.deepcopy(result)
    non_finite["comparisons"][0]["incremental_effect_per_person"] = float("nan")
    assert not api_module._valid_hillstrom_result(non_finite, "a" * 64)


def test_malformed_upload_is_reported_without_analysis(client: TestClient) -> None:
    response = client.post(
        "/v1/panels/validate-upload",
        files={"file": ("weekly_panel.csv", b"only,wrong\n1,2\n", "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "units" in response.json()["missing_required_columns"]


def manager_scenario_request_body() -> dict[str, object]:
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
    return {
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
                    "projected_demand_units": {"point": 100, "lower": 90, "upper": 120},
                    "evidence": [
                        {
                            "field_name": field,
                            "kind": "model_output" if field == "projected_demand_units" else "partner_export",
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
    }


def test_manager_scenario_comparison_api_returns_bounded_policy_result(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/optimization/comparisons", json=manager_scenario_request_body()
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


def test_manager_scenario_pdf_is_downloadable_and_preserves_limits(client: TestClient) -> None:
    from io import BytesIO

    from pypdf import PdfReader

    request_body = manager_scenario_request_body()
    request_body["optimization"]["scenarios"][0]["evidence"][0]["reference"] = "source <tag> & text"
    response = client.post(
        "/v1/optimization/comparisons/pdf", json=request_body
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert 'filename="promoguard-scenario-comparison.pdf"' in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content.startswith(b"%PDF")
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert reader.metadata.title == "PromoGuard | گزارش مقایسهٔ سناریوهای پروموشن"
    assert "api-review-1" in text
    assert "candidate_for_human_review" not in text
    assert "source <tag> & text" in text
    assert "2,400,000.00" in text
    assert "IRR" in text
    assert any("\ufb50" <= char <= "\ufdff" for char in text)


def test_manager_scenario_pdf_paginates_multiple_scenarios_and_keeps_each_id(
    client: TestClient,
) -> None:
    import copy
    from io import BytesIO

    from pypdf import PdfReader

    request_body = manager_scenario_request_body()
    template = request_body["optimization"]["scenarios"][0]
    scenarios = []
    for index in range(1, 9):
        scenario = copy.deepcopy(template)
        scenario["scenario_id"] = f"case-{index}"
        scenario["store_id"] = f"store-{index}"
        scenario["sku_id"] = f"sku-{index}"
        for evidence in scenario["evidence"]:
            evidence["reference"] = f"case-{index}:{evidence['field_name']}"
        scenarios.append(scenario)
    request_body["optimization"]["scenarios"] = scenarios

    response = client.post("/v1/optimization/comparisons/pdf", json=request_body)

    assert response.status_code == 200
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) > 2
    for index in range(1, 9):
        assert f"case-{index}" in text
        assert f"case-{index}:projected_demand_units" in text


def test_manager_scenario_pdf_rejects_currency_mismatch_without_returning_file(
    client: TestClient,
) -> None:
    request_body = manager_scenario_request_body()
    request_body["policy"]["currency"] = "USD"

    response = client.post(
        "/v1/optimization/comparisons/pdf", json=request_body
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "manager hurdle currency must match scenario currency"


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
