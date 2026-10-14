from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

import promoguard.experiments.hillstrom as hillstrom_module
from promoguard.experiments.hillstrom import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    HillstromAnalysisConfig,
    _chi_square_6_survival,
    _evaluate_history_heterogeneity,
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


def heterogeneity_fixture(rows_per_cell: int = 1_000) -> pd.DataFrame:
    """Build balanced test-only cells; the values are not business evidence."""
    source = hillstrom_fixture()
    cells = []
    for history_segment in hillstrom_module.HISTORY_SEGMENTS:
        for arm in hillstrom_module.HILLSTROM_SEGMENTS:
            arm_rows = source.loc[source["segment"].eq(arm)]
            selected = arm_rows.iloc[np.arange(rows_per_cell) % len(arm_rows)].copy()
            selected["history_segment"] = history_segment
            cells.append(selected)
    return pd.concat(cells, ignore_index=True)


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
        (lambda frame: frame.assign(history_segment="unknown"), "history_segment contains"),
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
    assert mens["revenue_details"]["revenue_effect_per_1000"]["point"] == 5000
    assert mens["revenue_details"]["treatment"]["assigned_customers"] == 4
    mens_vs_womens = result["comparisons"][2]
    assert mens_vs_womens["contrast_type"] == "treatment_vs_treatment"
    assert mens_vs_womens["control_arm"] == "Womens E-Mail"
    assert mens_vs_womens["incremental_effect_per_person"] == pytest.approx(4.25)
    assert mens_vs_womens["business_goal_status"] == "not_applicable_variant_comparison"
    subgroup = result["subgroup_analysis"]
    assert subgroup["attribute"] == "history_segment"
    assert subgroup["pre_treatment"] is True
    assert subgroup["contrast_count"] == 14
    assert len(subgroup["contrasts"]) == 14
    assert all(item["status"] == "insufficient_sample" for item in subgroup["contrasts"])
    assert all(not item["interpretation_allowed"] for item in subgroup["contrasts"])
    assert any("global heterogeneity test" in item for item in subgroup["limitations"])


def test_bootstrap_goal_preserves_insufficient_sample_with_declared_goal() -> None:
    result = evaluate_hillstrom_frame(hillstrom_fixture(), HillstromAnalysisConfig(minimum_effect_per_person=1))
    for comparison in result["comparisons"]:
        assert comparison["bootstrap_business_goal_status"] == "insufficient_sample"
        assert comparison["bootstrap_stability_status"] == "insufficient_sample"


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
    assert target["comparisons"][0]["bootstrap_business_goal_status"] == "goal_not_supported"


def test_bootstrap_is_reproducible_familywise_and_only_a_stability_diagnostic() -> None:
    frame = large_hillstrom_fixture()

    first = evaluate_hillstrom_frame(frame)
    second = evaluate_hillstrom_frame(frame)

    bootstrap = first["uncertainty"]["bootstrap"]
    assert bootstrap["repetitions"] == 10_000
    assert bootstrap["seed"] == 20_261_012
    assert "Bonferroni-adjusted" in bootstrap["multiple_comparison_adjustment"]
    assert "does not replace" in bootstrap["role"]
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    bootstrap_means = {}
    for arm in ("Mens E-Mail", "Womens E-Mail", "No E-Mail"):
        values = frame.loc[frame.segment.eq(arm), "spend"].to_numpy(dtype=float)
        support, counts = np.unique(values, return_counts=True)
        frequencies = rng.multinomial(
            len(values), counts / len(values), size=BOOTSTRAP_RESAMPLES
        )
        bootstrap_means[arm] = frequencies @ support / len(values)
    expected_lower, expected_upper = np.quantile(
        bootstrap_means["Mens E-Mail"] - bootstrap_means["No E-Mail"],
        [0.05 / 6, 1 - 0.05 / 6],
        method="linear",
    )
    assert first["comparisons"][0]["bootstrap_ci_lower_per_person"] == expected_lower
    assert first["comparisons"][0]["bootstrap_ci_upper_per_person"] == expected_upper
    for first_comparison, second_comparison in zip(
        first["comparisons"], second["comparisons"], strict=True
    ):
        assert first_comparison["incremental_effect_per_person"] == second_comparison[
            "incremental_effect_per_person"
        ]
        assert first_comparison["bootstrap_ci_lower_per_person"] == second_comparison[
            "bootstrap_ci_lower_per_person"
        ]
        assert first_comparison["bootstrap_ci_upper_per_person"] == second_comparison[
            "bootstrap_ci_upper_per_person"
        ]
        assert first_comparison["bootstrap_stability_status"] == "consistent"
        assert first_comparison["bootstrap_ci_lower_per_person"] <= first_comparison[
            "incremental_effect_per_person"
        ] <= first_comparison["bootstrap_ci_upper_per_person"]


def test_disagreement_with_welch_is_explicitly_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        hillstrom_module,
        "_welch_difference_interval",
        lambda *_args, **_kwargs: (-1.0, 0.1, -1.2, -0.8),
    )

    result = evaluate_hillstrom_frame(large_hillstrom_fixture())

    assert result["comparisons"][0]["statistical_direction_status"] == "negative_evidence_vs_zero"
    assert result["comparisons"][0]["bootstrap_direction_status"] == "positive_evidence_vs_zero"
    assert result["comparisons"][0]["bootstrap_stability_status"] == "sensitive_to_method"
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


def test_financial_assumptions_require_revenue_as_primary_outcome() -> None:
    assumptions = {
        "common_contribution_margin": 0.3,
        "margin_source": "test fixture",
        "mens_campaign_cost_per_1000": 1,
        "mens_cost_source": "test fixture",
        "womens_campaign_cost_per_1000": 1,
        "womens_cost_source": "test fixture",
    }
    with pytest.raises(ValueError, match="require spend as the primary outcome"):
        HillstromAnalysisConfig(
            primary_outcome="conversion", financial_assumptions=assumptions
        )


def test_small_groups_never_receive_a_business_verdict_even_with_a_large_effect() -> None:
    result = evaluate_hillstrom_frame(
        hillstrom_fixture(), HillstromAnalysisConfig(minimum_effect_per_person=0.0)
    )

    assert all(
        item["business_goal_status"] == "insufficient_sample"
        for item in result["comparisons"][:2]
    )
    assert all(
        item["bootstrap_stability_status"] == "insufficient_sample"
        for item in result["comparisons"]
    )
    assert result["comparisons"][2]["business_goal_status"] == "not_applicable_variant_comparison"


def test_subgroup_family_uses_fixed_multiplicity_and_hides_small_stratum_verdicts() -> None:
    result = evaluate_hillstrom_frame(large_hillstrom_fixture())
    subgroup = result["subgroup_analysis"]
    populated = [
        item for item in subgroup["contrasts"] if item["history_segment"] == "1) $0 - $100"
    ]
    sparse = [
        item for item in subgroup["contrasts"] if item["history_segment"] == "7) $1,000 +"
    ]

    assert len(populated) == 2
    assert all(item["status"] == "positive_evidence_vs_zero" for item in populated)
    assert all(item["treatment_n"] == item["control_n"] == 1_200 for item in populated)
    assert len(sparse) == 2
    assert all(item["status"] == "insufficient_sample" for item in sparse)
    assert all(item["estimated_effect_per_person"] is None for item in sparse)
    assert subgroup["contrast_count"] == 14
    assert "all 14" in subgroup["multiplicity_method"]
    from statistics import NormalDist

    frame = large_hillstrom_fixture()
    treatment = frame.loc[
        frame.segment.eq("Mens E-Mail") & frame.history_segment.eq("1) $0 - $100"),
        "spend",
    ].to_numpy()
    control = frame.loc[
        frame.segment.eq("No E-Mail") & frame.history_segment.eq("1) $0 - $100"),
        "spend",
    ].to_numpy()
    standard_error = (
        treatment.var(ddof=1) / len(treatment) + control.var(ddof=1) / len(control)
    ) ** 0.5
    critical = NormalDist().inv_cdf(1 - 0.05 / (2 * 14))
    expected_lower = treatment.mean() - control.mean() - critical * standard_error
    expected_upper = treatment.mean() - control.mean() + critical * standard_error
    first = populated[0]
    assert first["familywise_ci_lower_per_person"] == pytest.approx(expected_lower)
    assert first["familywise_ci_upper_per_person"] == pytest.approx(expected_upper)


def test_global_heterogeneity_test_does_not_mistake_equal_effects_for_segment_winners() -> None:
    frame = heterogeneity_fixture()

    tests = _evaluate_history_heterogeneity(frame, "spend", confidence_level=0.95)

    assert len(tests) == 2
    assert all(item["strata_count"] == 7 for item in tests)
    assert all(item["degrees_of_freedom"] == 6 for item in tests)
    assert all(item["familywise_test_count"] == 2 for item in tests)
    assert all(item["p_value"] == pytest.approx(1.0) for item in tests)
    assert all(item["familywise_adjusted_p_value"] == pytest.approx(1.0) for item in tests)
    assert all(item["status"] == "no_clear_heterogeneity_evidence" for item in tests)
    assert all(item["interpretation_allowed"] for item in tests)


def test_global_heterogeneity_test_detects_large_predeclared_effect_difference() -> None:
    frame = heterogeneity_fixture()
    shifted = (
        frame["history_segment"].eq(hillstrom_module.HISTORY_SEGMENTS[-1])
        & frame["segment"].eq("Womens E-Mail")
        & frame["conversion"].eq(1)
    )
    frame.loc[shifted, "spend"] += 100

    tests = _evaluate_history_heterogeneity(frame, "spend", confidence_level=0.95)
    womens = next(item for item in tests if item["treatment_arm"] == "Womens E-Mail")

    assert womens["familywise_adjusted_p_value"] < 0.05
    assert womens["status"] == "evidence_of_heterogeneity"


def test_global_heterogeneity_test_abstains_when_a_predeclared_stratum_is_absent() -> None:
    tests = _evaluate_history_heterogeneity(hillstrom_fixture(), "spend", confidence_level=0.95)

    assert all(item["status"] == "not_estimable" for item in tests)
    assert all(item["statistic"] is None for item in tests)
    assert all(item["strata_count"] == 1 for item in tests)
    assert all(item["minimum_cell_size"] == 0 for item in tests)


def test_global_test_suppresses_p_values_below_the_existing_sample_gate() -> None:
    tests = _evaluate_history_heterogeneity(
        heterogeneity_fixture(rows_per_cell=999), "spend", confidence_level=0.95
    )

    assert all(item["status"] == "insufficient_sample" for item in tests)
    assert all(item["minimum_cell_size"] == 999 for item in tests)
    assert all(item["minimum_cell_size_for_interpretation"] == 1_000 for item in tests)
    assert all(not item["interpretation_allowed"] for item in tests)
    assert all(item["familywise_adjusted_p_value"] is None for item in tests)


def test_global_test_scans_all_strata_before_reporting_incomplete_cell_metadata() -> None:
    frame = heterogeneity_fixture()
    frame = frame.loc[
        ~(
            frame["history_segment"].eq(hillstrom_module.HISTORY_SEGMENTS[2])
            & frame["segment"].eq("Mens E-Mail")
        )
    ]

    result = _evaluate_history_heterogeneity(frame, "spend", confidence_level=0.95)[0]

    assert result["status"] == "not_estimable"
    assert result["strata_count"] == 6
    assert result["minimum_cell_size"] == 0
    assert result["reason_code"] == "predeclared_stratum_or_arm_missing"


def test_global_test_reports_non_estimable_variance_without_losing_full_sample_metadata() -> None:
    frame = heterogeneity_fixture()
    affected = frame["history_segment"].eq(hillstrom_module.HISTORY_SEGMENTS[0])
    frame.loc[affected, "spend"] = 0.0

    result = _evaluate_history_heterogeneity(frame, "spend", confidence_level=0.95)[0]

    assert result["status"] == "not_estimable"
    assert result["strata_count"] == 7
    assert result["estimable_strata_count"] == 6
    assert result["minimum_cell_size"] == 1_000
    assert result["reason_code"] == "stratum_variance_not_estimable"


def test_global_test_is_invariant_to_tiny_unit_scale_and_row_order() -> None:
    frame = heterogeneity_fixture()
    baseline = _evaluate_history_heterogeneity(frame, "spend", confidence_level=0.95)
    scaled = frame.copy()
    scaled["spend"] *= 1e-160
    tiny_units = _evaluate_history_heterogeneity(scaled, "spend", confidence_level=0.95)
    reordered = _evaluate_history_heterogeneity(
        frame.sample(frac=1, random_state=77), "spend", confidence_level=0.95
    )

    for expected, actual, shuffled in zip(baseline, tiny_units, reordered, strict=True):
        assert actual["status"] == expected["status"]
        assert actual["statistic"] == pytest.approx(expected["statistic"], rel=1e-8, abs=1e-10)
        assert actual["p_value"] == pytest.approx(expected["p_value"], rel=1e-8, abs=1e-10)
        assert shuffled["statistic"] == pytest.approx(expected["statistic"], rel=1e-10, abs=1e-12)


@pytest.mark.parametrize(
    ("statistic", "expected"),
    [(0.0, 1.0), (13.092157707838204, 0.04159559596527485), (1e200, 0.0)],
)
def test_chi_square_survival_is_stable_for_large_finite_statistics(
    statistic: float, expected: float
) -> None:
    assert _chi_square_6_survival(statistic) == pytest.approx(expected)


@pytest.mark.parametrize("statistic", [-1.0, math.nan, math.inf])
def test_chi_square_survival_rejects_values_outside_its_domain(statistic: float) -> None:
    assert _chi_square_6_survival(statistic) is None
