from __future__ import annotations

import json

import pandas as pd

from promoguard.insights.promotion_audit import (
    AuditDecision,
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


def run_audit(panel: pd.DataFrame, *, unit_margin: float | None = 1.0):
    return audit_promotion_event(
        panel,
        store_id="1",
        upc="10",
        start_date="2024-03-31",
        unit_margin=unit_margin,
        min_history_weeks=8,
    )


def test_consecutive_promotion_weeks_form_one_episode() -> None:
    episodes = detect_promotion_episodes(audit_fixture())
    assert len(episodes) == 1
    assert episodes.iloc[0]["duration_weeks"] == 2
    assert episodes.iloc[0]["start_date"] == pd.Timestamp("2024-03-31")


def test_positive_interval_with_margin_approves_only_a_controlled_pilot() -> None:
    result = run_audit(audit_fixture())
    assert result.incremental_units.point == 40
    assert result.incremental_units.lower == 40
    assert result.margin_scenario is not None
    assert result.margin_scenario.estimate.point == 40
    assert result.decision == AuditDecision.APPROVE
    assert "controlled pilot" in result.decision_scope


def test_negative_interval_returns_reject() -> None:
    result = run_audit(audit_fixture(promotion_units=0))
    assert result.incremental_units.upper < 0
    assert result.decision == AuditDecision.REJECT


def test_missing_margin_blocks_profit_decision() -> None:
    result = run_audit(audit_fixture(), unit_margin=None)
    codes = {warning.code for warning in result.warnings}
    assert "MISSING_COST" in codes
    assert result.margin_scenario is None
    assert result.decision == AuditDecision.EXPERIMENT


def test_forward_buy_warning_is_emitted() -> None:
    result = run_audit(audit_fixture(post_units=5))
    codes = {warning.code for warning in result.warnings}
    assert "FORWARD_BUY_RISK" in codes
    assert result.post_to_pre_ratio == 0.5
    assert result.decision == AuditDecision.EXPERIMENT


def test_short_history_is_blocking() -> None:
    result = audit_promotion_event(
        audit_fixture(),
        store_id="1",
        upc="10",
        start_date="2024-03-31",
        unit_margin=1,
        min_history_weeks=20,
    )
    assert any(warning.code == "SHORT_HISTORY" for warning in result.warnings)
    assert result.decision == AuditDecision.EXPERIMENT


def test_severe_pre_event_shift_is_blocking() -> None:
    panel = audit_fixture()
    panel.loc[8:11, "units"] = 30
    result = run_audit(panel)
    assert any(warning.code == "SEVERE_SHIFT" for warning in result.warnings)
    assert result.pre_to_reference_ratio == 3
    assert result.decision == AuditDecision.EXPERIMENT


def test_missing_inventory_emits_stockout_unobservable_warning() -> None:
    result = run_audit(audit_fixture().drop(columns="inventory_on_hand"))
    assert any(warning.code == "STOCKOUT_UNOBSERVABLE" for warning in result.warnings)


def test_post_event_values_do_not_change_during_event_estimate() -> None:
    original = run_audit(audit_fixture())
    changed = audit_fixture(post_units=999)
    rerun = run_audit(changed)
    assert original.baseline_units == rerun.baseline_units
    assert original.incremental_units == rerun.incremental_units


def test_typed_payload_never_uses_unsupported_causal_wording() -> None:
    payload = run_audit(audit_fixture()).model_dump(mode="json")
    serialized = json.dumps(payload).lower()
    assert "caused" not in serialized
    assert payload["claim_language"] == (
        "observational incremental-units estimate; causal effect not identified"
    )
