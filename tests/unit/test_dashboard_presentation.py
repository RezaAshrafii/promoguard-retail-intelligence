from __future__ import annotations

import pandas as pd

from apps.dashboard.presentation import (
    audit_comparison_records,
    audit_event_summary,
    claim_boundary_copy,
    demo_mode_requested,
    recommendation_presentation,
    warning_presentation_records,
)
from promoguard.insights.promotion_audit import (
    AuditPolicy,
    AuditRecommendation,
    audit_promotion_event,
)


def _result():
    weeks = pd.date_range("2024-01-07", periods=20, freq="7D")
    units = [10.0] * len(weeks)
    promotion_flag = [0] * len(weeks)
    for index in (12, 13):
        units[index] = 30.0
        promotion_flag[index] = 1
    panel = pd.DataFrame(
        {
            "week_end_date": weeks,
            "store_id": "1",
            "upc": "10",
            "units": units,
            "promotion_flag": promotion_flag,
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


def test_demo_mode_requires_explicit_app_argument() -> None:
    assert demo_mode_requested(["streamlit", "run", "app.py", "--", "--demo"])
    assert not demo_mode_requested(["streamlit", "run", "app.py"])


def test_chart_records_copy_domain_values_without_recalculation() -> None:
    result = _result()
    records = audit_comparison_records(result)

    assert records[0] == {
        "label": "فروش مشاهده‌شده",
        "value": result.observed_units,
        "kind": "observed",
        "lower": None,
        "upper": None,
    }
    assert records[1]["value"] == result.baseline_units.point
    assert records[1]["lower"] == result.baseline_units.lower
    assert records[1]["upper"] == result.baseline_units.upper


def test_recommendation_copy_preserves_abstention_boundary() -> None:
    presentation = recommendation_presentation(AuditRecommendation.NEEDS_MORE_EVIDENCE)
    assert presentation.style == "info"
    assert "شواهد بیشتری" in presentation.title
    assert "اجازه توصیه اجرایی یا مالی نمی‌دهد" in presentation.explanation


def test_event_summary_uses_typed_result_identity() -> None:
    result = _result()
    summary = dict(audit_event_summary(result))
    assert summary == {
        "فروشگاه": result.store_id,
        "کالا (UPC)": result.upc,
        "شروع": result.start_date.isoformat(),
        "مدت": f"{result.duration_weeks} هفته",
    }


def test_warning_copy_preserves_codes_and_blocking_severity() -> None:
    result = _result()
    records = warning_presentation_records(result)
    by_code = {record["کد"]: record for record in records}
    assert by_code["OBSERVATIONAL_ONLY"]["سطح"] == "هشدار"
    assert "علّی" in by_code["OBSERVATIONAL_ONLY"]["معنی برای تصمیم"]


def test_claim_boundary_is_explicitly_non_causal_and_non_financial() -> None:
    claim, scope = claim_boundary_copy()
    assert "اثر علّی" in claim
    assert "اثر مالی" in claim
    assert "نه rollout" in scope
