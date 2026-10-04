from __future__ import annotations

import pandas as pd

from promoguard.insights.decision_support import ManagerAction, build_manager_decision_support
from promoguard.insights.promotion_audit import (
    AuditPolicy,
    AuditRecommendation,
    audit_promotion_event,
)


def _audit():
    weeks = pd.date_range("2024-01-07", periods=20, freq="7D")
    units = [10.0] * len(weeks)
    flags = [0] * len(weeks)
    for index in (12, 13):
        units[index] = 30.0
        flags[index] = 1
    panel = pd.DataFrame(
        {
            "week_end_date": weeks,
            "store_id": "1",
            "upc": "10",
            "units": units,
            "promotion_flag": flags,
            "inventory_on_hand": 100,
        }
    )
    return audit_promotion_event(
        panel,
        store_id="1",
        upc="10",
        start_date="2024-03-31",
        policy=AuditPolicy(audit_min_history_weeks=8),
    )


def test_observational_candidate_never_becomes_repeat_recommendation() -> None:
    decision = build_manager_decision_support(_audit())

    assert decision.recommended_action == ManagerAction.MORE_TESTING
    assert [option.action for option in decision.options] == list(ManagerAction)
    repeat = next(option for option in decision.options if option.action == ManagerAction.REPEAT)
    assert repeat.availability == "requires_verified_pilot_and_economics"
    assert "سود خالصِ تأییدشده" not in decision.explanation
    assert "اثر علّی" in decision.limitation


def test_negative_screening_is_deprioritization_for_review_not_auto_stop() -> None:
    negative = _audit().model_copy(
        update={"recommendation": AuditRecommendation.DEPRIORITIZE_AND_INVESTIGATE}
    )

    decision = build_manager_decision_support(negative)
    stop_option = next(option for option in decision.options if option.action == ManagerAction.DEPRIORITIZE)

    assert decision.recommended_action == ManagerAction.DEPRIORITIZE
    assert stop_option.availability == "recommended_for_human_review"
    assert "توقف قطعی" in decision.explanation


def test_insufficient_evidence_maps_to_more_testing_and_human_operation_review() -> None:
    incomplete = _audit().model_copy(update={"recommendation": AuditRecommendation.NEEDS_MORE_EVIDENCE})

    decision = build_manager_decision_support(incomplete)

    assert decision.recommended_action == ManagerAction.MORE_TESTING
    modify = next(option for option in decision.options if option.action == ManagerAction.MODIFY)
    assert modify.availability == "requires_human_operational_review"
