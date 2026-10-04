from __future__ import annotations

import pandas as pd
import pytest

from promoguard.experiments.hillstrom import (
    HillstromAnalysisConfig,
    evaluate_hillstrom_frame,
    validate_hillstrom_frame,
)


def hillstrom_fixture() -> pd.DataFrame:
    """Small test-only assignment fixture; it is not benchmark or business evidence."""
    rows = []
    outcomes = {
        "Mens E-Mail": [(1, 10.0), (1, 12.0), (0, 0.0), (0, 0.0)],
        "Womens E-Mail": [(1, 5.0), (0, 0.0), (0, 0.0), (0, 0.0)],
        "No E-Mail": [(1, 2.0), (0, 0.0), (0, 0.0), (0, 0.0)],
    }
    for segment, values in outcomes.items():
        for index, (conversion, spend) in enumerate(values):
            rows.append(
                {
                    "recency": 1 + index,
                    "history_segment": "1) $0 - $100",
                    "history": float(index),
                    "mens": index % 2,
                    "womens": (index + 1) % 2,
                    "zip_code": "Rural",
                    "newbie": index % 2,
                    "channel": "Web",
                    "segment": segment,
                    "visit": conversion,
                    "conversion": conversion,
                    "spend": spend,
                }
            )
    return pd.DataFrame(rows)


def large_hillstrom_fixture() -> pd.DataFrame:
    """Repeat test-only rows to exercise the predeclared low-sample abstention gate."""
    return pd.concat([hillstrom_fixture()] * 300, ignore_index=True)


def test_contract_accepts_real_publisher_schema_and_keeps_repeated_rows() -> None:
    frame = pd.concat([hillstrom_fixture(), hillstrom_fixture().iloc[[0]]], ignore_index=True)

    result = validate_hillstrom_frame(frame)

    assert result["valid"] is True
    assert result["duplicate_full_rows_retained"] == 1
    assert "retained" in result["duplicate_note"]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda frame: frame.drop(columns="spend"), "missing required columns"),
        (lambda frame: frame.assign(segment="unknown"), "unsupported labels"),
        (lambda frame: frame.assign(spend=-1.0), "negative values"),
        (lambda frame: frame.assign(conversion=0, spend=2.0), "zero conversion rows"),
        (lambda frame: frame.assign(conversion=1, visit=0), "conversion cannot be 1"),
        (lambda frame: frame.assign(recency=float("inf")), "invalid or non-finite"),
    ],
)
def test_contract_rejects_invalid_data(mutate, expected: str) -> None:
    result = validate_hillstrom_frame(mutate(hillstrom_fixture()))

    assert result["valid"] is False
    assert any(expected in error for error in result["errors"])


def test_primary_effect_is_itt_and_includes_every_assigned_row() -> None:
    result = evaluate_hillstrom_frame(
        hillstrom_fixture(),
        HillstromAnalysisConfig(primary_outcome="spend"),
    )

    mens = result["comparisons"][0]
    assert mens["treatment_n"] == 4
    assert mens["control_n"] == 4
    assert mens["incremental_effect_per_person"] == pytest.approx(5.0)
    assert mens["incremental_effect_per_1000_people"] == pytest.approx(5000)
    # This deliberately tiny fixture cannot support a manager-facing decision.
    assert mens["statistical_direction_status"] == "insufficient_sample"
    assert mens["business_goal_status"] == "insufficient_sample"
    assert "not contribution margin or profit" in result["interpretation"][1]
    assert len(result["comparisons"]) == 3
    mens_vs_womens = result["comparisons"][2]
    assert mens_vs_womens["contrast_type"] == "treatment_vs_treatment"
    assert mens_vs_womens["control_arm"] == "Womens E-Mail"
    assert mens_vs_womens["incremental_effect_per_person"] == pytest.approx(4.25)
    assert mens_vs_womens["business_goal_status"] == "not_applicable_variant_comparison"


def test_declared_hurdle_changes_commercial_status_without_rewriting_effect() -> None:
    base = evaluate_hillstrom_frame(
        large_hillstrom_fixture(), HillstromAnalysisConfig()
    )
    target = evaluate_hillstrom_frame(
        large_hillstrom_fixture(),
        HillstromAnalysisConfig(minimum_effect_per_person=100.0),
    )

    assert target["comparisons"][0]["incremental_effect_per_person"] == base["comparisons"][0]["incremental_effect_per_person"]
    assert target["comparisons"][0]["business_goal_status"] == "goal_not_supported"


def test_adjusted_welch_interval_matches_hand_calculation() -> None:
    result = evaluate_hillstrom_frame(large_hillstrom_fixture())
    comparison = result["comparisons"][0]
    frame = large_hillstrom_fixture()
    treatment = frame.loc[frame.segment.eq("Mens E-Mail"), "spend"].to_numpy()
    control = frame.loc[frame.segment.eq("No E-Mail"), "spend"].to_numpy()
    standard_error = (
        treatment.var(ddof=1) / len(treatment) + control.var(ddof=1) / len(control)
    ) ** 0.5
    from statistics import NormalDist

    critical = NormalDist().inv_cdf(1 - (0.05 / 3 / 2))
    point = treatment.mean() - control.mean()

    assert comparison["standard_error_per_person"] == pytest.approx(standard_error)
    assert comparison["familywise_ci_lower_per_person"] == pytest.approx(point - critical * standard_error)
    assert comparison["familywise_ci_upper_per_person"] == pytest.approx(point + critical * standard_error)
    assert comparison["statistical_direction_status"] == "positive_evidence_vs_zero"
    assert comparison["multiplicity_method"].startswith("Welch")


def test_no_control_arm_is_rejected() -> None:
    frame = hillstrom_fixture().query("segment != 'No E-Mail'")

    with pytest.raises(ValueError, match="required experiment arms are empty"):
        evaluate_hillstrom_frame(frame)


def test_binary_goal_threshold_must_be_a_probability() -> None:
    with pytest.raises(ValueError, match="probability between 0 and 1"):
        HillstromAnalysisConfig(primary_outcome="conversion", minimum_effect_per_person=1.2)


def test_small_groups_never_receive_a_business_verdict_even_with_a_large_effect() -> None:
    result = evaluate_hillstrom_frame(
        hillstrom_fixture(), HillstromAnalysisConfig(minimum_effect_per_person=0.0)
    )

    assert all(
        item["business_goal_status"] == "insufficient_sample"
        for item in result["comparisons"][:2]
    )
    assert result["comparisons"][2]["business_goal_status"] == "not_applicable_variant_comparison"
