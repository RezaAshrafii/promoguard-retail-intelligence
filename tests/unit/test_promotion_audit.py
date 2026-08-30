from __future__ import annotations

import json

import pandas as pd

from promoguard.insights.promotion_audit import (
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
):
    return audit_promotion_event(
        panel,
        store_id="1",
        upc="10",
        start_date="2024-03-31",
        contribution_assumption=contribution,
        min_history_weeks=8,
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


def test_short_history_is_blocking() -> None:
    result = audit_promotion_event(
        audit_fixture(),
        store_id="1",
        upc="10",
        start_date="2024-03-31",
        contribution_assumption=contribution_assumption(),
        min_history_weeks=20,
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
        "observed-minus-baseline estimate; causal treatment effect and financial impact not identified"
    )
