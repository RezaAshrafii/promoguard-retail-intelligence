import json
from pathlib import Path

REPORT = Path("reports/phase-06/criteo-uplift-model-ranking.json")


def test_phase_06_report_is_locked_and_conservative() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    test_rows = report["split"]["row_counts"]["test"]

    assert report["source"]["raw_data_committed_to_git"] is False
    assert report["features"] == [f"f{i}" for i in range(12)]
    assert all("exposure" not in feature for feature in report["features"])
    assert report["selection"]["selected_learner"] in {"s_learner", "t_learner"}
    assert report["coverage"]["test"]["rows"] == test_rows
    assert report["coverage"]["test"]["both_treatment_arms_present"] is True
    assert report["coverage"]["test"]["both_outcome_classes_present"] is True
    assert report["gate"]["test_rows_match_split"] is True
    assert report["gate"]["promotion_allowed"] is False


def test_phase_06_report_preserves_negative_gate_result() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    baseline = report["random_ranking_baseline"]["auuc"]
    model_auucs = [result["test"]["auuc"] for result in report["learners"].values()]

    assert report["gate"]["beats_random_baseline"] is False
    assert all(auuc < baseline for auuc in model_auucs)
