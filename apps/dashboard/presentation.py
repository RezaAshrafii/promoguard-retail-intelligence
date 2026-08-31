"""Pure presentation mappings for the Streamlit adapter.

These helpers do not estimate, aggregate, or alter analytical values. They only map typed domain
results into reviewer-facing labels and chart records.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from promoguard.insights.promotion_audit import AuditRecommendation, PromotionAuditResult


@dataclass(frozen=True)
class RecommendationPresentation:
    """Persian label and Streamlit message style for a domain recommendation."""

    title: str
    explanation: str
    style: str


RECOMMENDATION_PRESENTATIONS = {
    AuditRecommendation.CANDIDATE_FOR_CONTROLLED_TEST: RecommendationPresentation(
        title="این فرضیه ارزش آزمون کنترل‌شده دارد",
        explanation="این خروجی مجوز rollout نیست؛ فقط اولویت طراحی یک آزمایش واقعی را بالا می‌برد.",
        style="success",
    ),
    AuditRecommendation.DEPRIORITIZE_AND_INVESTIGATE: RecommendationPresentation(
        title="فعلاً کم‌اولویت شود و علت اختلاف بررسی شود",
        explanation="قبل از هزینه‌کرد بیشتر، کیفیت داده و عوامل مخدوش‌کننده باید بررسی شوند.",
        style="warning",
    ),
    AuditRecommendation.NEEDS_MORE_EVIDENCE: RecommendationPresentation(
        title="برای نتیجه‌گیری، شواهد بیشتری لازم است",
        explanation="یک هشدار مسدودکننده اجازه توصیه اجرایی یا مالی نمی‌دهد.",
        style="info",
    ),
}

WARNING_PRESENTATIONS = {
    "OBSERVATIONAL_ONLY": "این مقایسه مشاهده‌ای است و اثر علّی را شناسایی نمی‌کند.",
    "ECONOMIC_IMPACT_UNAVAILABLE": (
        "هزینه، بودجه ترویج و اقتصاد کامل در داده نیست؛ اثر مالی قابل ادعا نیست."
    ),
    "STOCKOUT_UNOBSERVABLE": (
        "فیلد موجودی در منبع وجود ندارد؛ تقاضای ازدست‌رفته بر اثر اتمام موجودی قابل تشخیص نیست."
    ),
    "FORWARD_BUY_RISK": (
        "افت فروش پس از پروموشن از آستانه سیاست عبور کرده و می‌تواند نشانه جابه‌جایی زمان خرید باشد."
    ),
}

SEVERITY_LABELS = {"info": "اطلاع", "warning": "هشدار", "blocking": "مسدودکننده"}


def demo_mode_requested(argv: Sequence[str]) -> bool:
    """Return whether Streamlit was launched with the explicit ``--demo`` app argument."""

    return "--demo" in argv


def recommendation_presentation(
    recommendation: AuditRecommendation,
) -> RecommendationPresentation:
    """Return the fixed reviewer-facing copy for a typed domain recommendation."""

    return RECOMMENDATION_PRESENTATIONS[recommendation]


def audit_comparison_records(result: PromotionAuditResult) -> list[dict[str, Any]]:
    """Map observed and baseline values to chart records without recalculation."""

    return [
        {
            "label": "فروش مشاهده‌شده",
            "value": result.observed_units,
            "kind": "observed",
            "lower": None,
            "upper": None,
        },
        {
            "label": "فروش مبنا",
            "value": result.baseline_units.point,
            "kind": "baseline",
            "lower": result.baseline_units.lower,
            "upper": result.baseline_units.upper,
        },
    ]


def audit_event_summary(result: PromotionAuditResult) -> list[tuple[str, str]]:
    """Expose event identity fields exactly as carried by the domain result."""

    return [
        ("فروشگاه", result.store_id),
        ("کالا (UPC)", result.upc),
        ("شروع", result.start_date.isoformat()),
        ("مدت", f"{result.duration_weeks} هفته"),
    ]


def warning_presentation_records(result: PromotionAuditResult) -> list[dict[str, str]]:
    """Translate warning codes for Persian UI while preserving their typed identity."""

    return [
        {
            "کد": warning.code,
            "سطح": SEVERITY_LABELS[warning.severity.value],
            "معنی برای تصمیم": WARNING_PRESENTATIONS.get(warning.code, warning.message),
        }
        for warning in result.warnings
    ]


def claim_boundary_copy() -> tuple[str, str]:
    """Return bounded Persian copy for the existing domain claim and decision scope."""

    return (
        "این عدد اختلاف مشاهده‌شده با خط مبناست؛ اثر علّی و اثر مالی شناسایی نشده‌اند.",
        "فقط برای اولویت‌بندی آزمایش کنترل‌شده؛ نه rollout و نه تأیید مالی.",
    )
