from __future__ import annotations

import json

import pandas as pd

from promoguard.insights.promotion_audit import (
    AuditPolicy,
    AuditRecommendation,
    ContributionAssumption,
    audit_promotion_event,
    detect_promotion_episodes,
)


def audit_fixture(*, promotion_units: float = 30, post_units: float = 10) -> pd.DataFrame:
    weeks = pd.date_range("2024-01-07", periods=20, freq="7D")
    units = [10.0] * len(weeks)
    promotion_flag = [0] * len(weeks)
    for index in (12, 13):
        units[index] = promotion_units
        promotion_flag[index] = 1
    for index in range(14, 18):
        units[index] = post_units
    return pd.DataFrame(
        {
            "week_end_date": weeks,
            "store_id": "1",
            "upc": "10",
            "units": units,
            "promotion_flag": promotion_flag,
            "inventory_on_hand": 100,
        }
    )


def category_neighbor_fixture(
    *,
    neighbor_during_units: float = 3,
    neighbor_promoted_during: bool = False,
) -> pd.DataFrame:
    """Clearly labeled synthetic fixture for cross-SKU diagnostic edge cases only."""
    focal = audit_fixture()
    focal["category"] = "SNACKS"
    focal["description"] = "FOCAL SKU"
    neighbor = focal.copy()
    neighbor["upc"] = "20"
    neighbor["description"] = "NEIGHBOR SKU"
    neighbor["units"] = 10.0
    neighbor["promotion_flag"] = 0
    neighbor.loc[12:13, "units"] = neighbor_during_units
    if neighbor_promoted_during:
        neighbor.loc[12:13, "promotion_flag"] = 1
    return pd.concat([focal, neighbor], ignore_index=True)


def contribution_assumption(amount: float = 1.0) -> ContributionAssumption:
    return ContributionAssumption(
        amount_per_incremental_unit=amount,
        currency="IRR",
        source="unit-test assumption",
    )


def run_audit(
    panel: pd.DataFrame,
    *,
    contribution: ContributionAssumption | None = None,
    policy: AuditPolicy | None = None,
):
    return audit_promotion_event(
        panel,
        store_id="1",
        upc="10",
        start_date="2024-03-31",
        contribution_assumption=contribution,
        policy=policy or AuditPolicy(audit_min_history_weeks=8),
    )


def test_consecutive_promotion_weeks_form_one_episode() -> None:
    episodes = detect_promotion_episodes(audit_fixture())
    assert len(episodes) == 1
    assert episodes.iloc[0]["duration_weeks"] == 2
    assert episodes.iloc[0]["start_date"] == pd.Timestamp("2024-03-31")


def test_positive_interval_is_only_a_candidate_for_controlled_test() -> None:
    result = run_audit(audit_fixture(), contribution=contribution_assumption())
    difference = result.estimated_units_difference_vs_baseline
    assert difference.point == 40
    assert difference.lower == 40
    assert result.contribution_sensitivity is not None
    sensitivity = result.contribution_sensitivity
    assert sensitivity.estimated_contribution_difference_vs_baseline.point == 40
    assert sensitivity.status == "sensitivity_only"
    assert result.recommendation == AuditRecommendation.CANDIDATE_FOR_CONTROLLED_TEST
    assert "never a rollout or financial approval" in result.recommendation_scope
    assert result.policy.version == "1.1.0"


def test_negative_interval_deprioritizes_but_does_not_claim_rejection() -> None:
    result = run_audit(audit_fixture(promotion_units=0))
    assert result.estimated_units_difference_vs_baseline.upper < 0
    assert result.recommendation == AuditRecommendation.DEPRIORITIZE_AND_INVESTIGATE


def test_missing_contribution_input_does_not_block_experiment_prioritization() -> None:
    result = run_audit(audit_fixture())
    codes = {warning.code for warning in result.warnings}
    assert "ECONOMIC_IMPACT_UNAVAILABLE" in codes
    assert result.contribution_sensitivity is None
    assert result.recommendation == AuditRecommendation.CANDIDATE_FOR_CONTROLLED_TEST


def test_contribution_assumption_never_changes_recommendation() -> None:
    without_sensitivity = run_audit(audit_fixture())
    with_negative_sensitivity = run_audit(
        audit_fixture(), contribution=contribution_assumption(amount=-100)
    )
    assert with_negative_sensitivity.contribution_sensitivity is not None
    assert (
        with_negative_sensitivity.contribution_sensitivity
        .estimated_contribution_difference_vs_baseline.point
        == -4000
    )
    assert with_negative_sensitivity.recommendation == without_sensitivity.recommendation


def test_forward_buy_warning_is_emitted() -> None:
    result = run_audit(audit_fixture(post_units=5))
    codes = {warning.code for warning in result.warnings}
    assert "FORWARD_BUY_RISK" in codes
    assert result.post_to_pre_ratio == 0.5
    assert result.recommendation == AuditRecommendation.NEEDS_MORE_EVIDENCE


def test_custom_policy_changes_forward_buy_warning_without_changing_observations() -> None:
    panel = audit_fixture(post_units=5)
    default_result = run_audit(panel)
    relaxed_result = run_audit(
        panel,
        policy=AuditPolicy(
            audit_min_history_weeks=8,
            forward_buy_ratio_threshold=0.4,
        ),
    )

    assert default_result.observed_units == relaxed_result.observed_units
    assert default_result.baseline_units == relaxed_result.baseline_units
    assert any(warning.code == "FORWARD_BUY_RISK" for warning in default_result.warnings)
    assert all(warning.code != "FORWARD_BUY_RISK" for warning in relaxed_result.warnings)
    assert relaxed_result.recommendation == AuditRecommendation.CANDIDATE_FOR_CONTROLLED_TEST


def test_audit_policy_rejects_inverted_shift_bounds() -> None:
    try:
        AuditPolicy(severe_shift_lower_ratio=2.0, severe_shift_upper_ratio=1.0)
    except ValueError as error:
        assert "lower ratio" in str(error)
    else:
        raise AssertionError("Inverted policy bounds must be rejected.")


def test_short_history_is_blocking() -> None:
    result = audit_promotion_event(
        audit_fixture(),
        store_id="1",
        upc="10",
        start_date="2024-03-31",
        contribution_assumption=contribution_assumption(),
        policy=AuditPolicy(audit_min_history_weeks=20),
    )
    assert any(warning.code == "SHORT_HISTORY" for warning in result.warnings)
    assert result.recommendation == AuditRecommendation.NEEDS_MORE_EVIDENCE


def test_severe_pre_event_shift_is_blocking() -> None:
    panel = audit_fixture()
    panel.loc[8:11, "units"] = 30
    result = run_audit(panel)
    assert any(warning.code == "SEVERE_SHIFT" for warning in result.warnings)
    assert result.pre_to_reference_ratio == 3
    assert result.recommendation == AuditRecommendation.NEEDS_MORE_EVIDENCE


def test_missing_inventory_emits_stockout_unobservable_warning() -> None:
    result = run_audit(audit_fixture().drop(columns="inventory_on_hand"))
    assert any(warning.code == "STOCKOUT_UNOBSERVABLE" for warning in result.warnings)


def test_same_category_neighbor_decline_is_a_blocking_candidate_not_a_causal_claim() -> None:
    result = run_audit(category_neighbor_fixture())

    assert result.cannibalization.status == "candidates_detected"
    assert result.cannibalization.category == "SNACKS"
    assert result.cannibalization.eligible_neighbor_count == 1
    candidate = result.cannibalization.candidates[0]
    assert candidate.upc == "20"
    assert candidate.during_to_pre_ratio == 0.3
    assert candidate.estimated_units_decline == 14
    assert any(warning.code == "CANNIBALIZATION_CANDIDATE" for warning in result.warnings)
    assert result.recommendation == AuditRecommendation.NEEDS_MORE_EVIDENCE
    assert "does not identify cannibalization" in result.cannibalization.limitation


def test_concurrently_promoted_neighbor_is_excluded_from_substitution_screening() -> None:
    result = run_audit(category_neighbor_fixture(neighbor_promoted_during=True))

    assert result.cannibalization.status == "no_candidates"
    assert result.cannibalization.eligible_neighbor_count == 0
    assert not any(warning.code == "CANNIBALIZATION_CANDIDATE" for warning in result.warnings)


def test_policy_v1_preserves_legacy_no_cross_sku_diagnostic_behavior() -> None:
    result = run_audit(
        category_neighbor_fixture(),
        policy=AuditPolicy(audit_min_history_weeks=8, version="1.0.0"),
    )

    assert result.cannibalization.status == "not_assessed"
    assert any(warning.code == "CANNIBALIZATION_UNAVAILABLE" for warning in result.warnings)


def test_audit_domain_rejects_blank_grain_identifier() -> None:
    panel = audit_fixture()
    panel.loc[0, "upc"] = "   "

    try:
        run_audit(panel)
    except ValueError as error:
        assert "upc=1" in str(error)
    else:
        raise AssertionError("Blank UPC must be rejected before audit logic.")


def test_post_event_values_do_not_change_during_event_estimate() -> None:
    original = run_audit(audit_fixture())
    changed = audit_fixture(post_units=999)
    rerun = run_audit(changed)
    assert original.baseline_units == rerun.baseline_units
    assert (
        original.estimated_units_difference_vs_baseline
        == rerun.estimated_units_difference_vs_baseline
    )


def test_typed_payload_never_uses_unsupported_causal_wording() -> None:
    payload = run_audit(audit_fixture()).model_dump(mode="json")
    serialized = json.dumps(payload).lower()
    assert "caused" not in serialized
    assert "margin_scenario" not in payload
    assert "unit_margin" not in serialized
    assert payload["claim_language"] == (
        "observed-minus-baseline estimate; causal treatment effect, cross-SKU substitution, "
        "and financial impact not identified"
    )
