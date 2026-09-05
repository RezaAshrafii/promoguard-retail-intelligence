import json
import math
from pathlib import Path

REPORT = Path("reports/phase-06/criteo-uplift-model-ranking.json")
QUALITY_REPORT = Path("reports/phase-06/release-0.6.4-quality-report.json")


def test_phase_06_report_is_locked_and_conservative() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    test_rows = report["split"]["row_counts"]["test"]

    assert report["artifact_schema_version"] == "1.1.0"
    assert report["source"]["raw_data_committed_to_git"] is False
    assert report["source"]["sha256"] == (
        "2716e1bf0fd157a93b5bf86924d9088419dfbac2022c6cd90030220634f616dc"
    )
    assert report["source"]["dataset_page"].startswith("https://ailab.criteo.com/")
    assert report["source"]["license"] == "CC BY-NC-SA 4.0"
    assert report["features"] == [f"f{i}" for i in range(12)]
    assert all("exposure" not in feature for feature in report["features"])
    assert report["selection"]["selected_learner"] in {
        "s_learner",
        "t_learner",
        "s_learner_hist_gb",
    }
    assert report["coverage"]["test"]["rows"] == test_rows
    assert report["coverage"]["test"]["both_treatment_arms_present"] is True
    assert report["coverage"]["test"]["both_outcome_classes_present"] is True
    assert report["gate"]["test_rows_match_split"] is True
    assert report["gate"]["all_logistic_models_converged"] is True
    assert report["gate"]["nonlinear_training_completed"] is True
    assert report["gate"]["selected_model_ci_above_zero"] is True
    assert report["gate"]["covariate_balance_acceptable"] is True
    assert report["gate"]["randomization_auc_acceptable"] is True
    assert report["gate"]["common_support_acceptable"] is True
    assert report["gate"]["promotion_allowed"] is False
    audit = report["post_freeze_audit_subset"]
    assert audit["rows"] > 0
    assert audit["selected_learner"] == report["selection"]["selected_learner"]
    assert audit["publication_status"].startswith("not a pristine")
    assert "final_audit_holdout" not in report


def test_phase_06_report_gate_matches_selected_model_comparison() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    baseline = report["random_ranking_baseline"]["qini_coefficient"]
    selected = report["selection"]["selected_learner"]
    selected_qini = report["learners"][selected]["test"]["qini_coefficient"]

    expected = selected_qini > baseline

    assert report["gate"]["selected_model_beats_random_baseline_mean"] is expected
    assert report["gate"]["promotion_allowed"] is False


def test_phase_06_selection_uses_validation_only() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = max(
        report["learners"],
        key=lambda learner: report["learners"][learner]["validation"]["qini_coefficient"],
    )

    assert report["selection"]["selected_learner"] == expected
    assert "test is not used for selection" in report["selection"]["criterion"]


def test_phase_06_policy_rates_have_unambiguous_mathematical_identity() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    selected = report["selection"]["selected_learner"]
    model_curves = [
        report["learners"][selected]["test"],
        report["post_freeze_audit_subset"]["curve"],
    ]

    for curve in model_curves:
        for point in curve["qini_at"]:
            assert math.isclose(
                point["qini_per_ranked_row"],
                point["qini"] / point["prefix_rows"],
                rel_tol=1e-12,
            )
            assert math.isclose(
                point["difference_in_means_incremental_rate"],
                point["qini"] / point["treated_rows"],
                rel_tol=1e-12,
            )
            assert math.isfinite(point["ipw_incremental_rate"])

    for point in report["random_ranking_baseline"]["qini_at"]:
        assert math.isfinite(point["difference_in_means_incremental_rate"])
        assert math.isfinite(point["ipw_incremental_rate"])

    assert report["metric"]["qini_per_ranked_row"].endswith("not an ATE")
    assert report["random_ranking_baseline"]["role"].endswith(
        "not an inferential interval"
    )


def test_release_quality_report_is_derived_from_the_locked_artifact() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    quality = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))
    selected = report["selection"]["selected_learner"]
    point = report["learners"][selected]["test"]["qini_at"][1]

    assert quality["release"] == "0.6.4"
    assert quality["artifact_schema_version"] == report["artifact_schema_version"]
    assert quality["source_sha256"] == report["source"]["sha256"]
    assert quality["selected_learner"] == selected
    assert quality["selected_test_qini_coefficient"] == report["learners"][selected]["test"][
        "qini_coefficient"
    ]
    assert quality["selected_test_policy_at_20_percent"]["cumulative_qini"] == point["qini"]
    assert quality["promotion_allowed"] is False
