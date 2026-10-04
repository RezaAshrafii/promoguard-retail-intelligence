"""Conservative manager-facing actions derived from observational audit results."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from promoguard.insights.promotion_audit import AuditRecommendation, PromotionAuditResult


class ManagerAction(StrEnum):
    """Four decision states shown to a manager; none is an automatic execution command."""

    REPEAT = "repeat"
    MODIFY = "modify"
    MORE_TESTING = "more_testing"
    DEPRIORITIZE = "deprioritize"


class DecisionOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: ManagerAction
    label: str
    availability: str
    explanation: str


class ManagerDecisionSupport(BaseModel):
    """Explain which next-step state is supported and which evidence is still absent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    recommended_action: ManagerAction
    label: str
    explanation: str
    evidence_basis: str
    options: tuple[DecisionOption, ...]
    limitation: str = (
        "این غربالگری مشاهده‌ای است؛ هیچ گزینه‌ای خودکار اجرا یا به‌عنوان اثر علّی و سود قطعی ثبت نمی‌شود."
    )


def build_manager_decision_support(
    audit: PromotionAuditResult,
) -> ManagerDecisionSupport:
    """Map a screening result to a cautious next step without inferring a causal effect."""

    if audit.recommendation == AuditRecommendation.DEPRIORITIZE_AND_INVESTIGATE:
        recommended = ManagerAction.DEPRIORITIZE
        label = "فعلاً کم‌اولویت و علت بررسی شود"
        explanation = (
            "فروش مشاهده‌شده نسبت به خط مبنا ضعیف بوده است؛ این گزارش توقف قطعی را تجویز نمی‌کند. "
            "ابتدا کیفیت اجرا، قیمت، موجودی و شرایط بازار را بررسی کنید."
        )
        basis = "نتیجهٔ غربالگری ممیزی: deprioritize_and_investigate"
    else:
        recommended = ManagerAction.MORE_TESTING
        label = "آزمایش بیشتر؛ هنوز برای تکرار زود است"
        if audit.recommendation == AuditRecommendation.CANDIDATE_FOR_CONTROLLED_TEST:
            explanation = (
                "این رویداد فقط نامزد یک آزمون کنترل‌شده است. یک گروه مقایسهٔ معتبر و سنجش هزینه و "
                "حاشیهٔ سود لازم است؛ تکرار گسترده هنوز پشتیبانی نمی‌شود."
            )
            basis = "نتیجهٔ غربالگری ممیزی: candidate_for_controlled_test"
        else:
            explanation = (
                "هشدارها یا کمبود داده اجازهٔ پیشنهاد اجرایی نمی‌دهد. ابتدا داده و شرایط اجرای کمپین را "
                "کامل کنید؛ سپس آزمون کنترل‌شده طراحی کنید."
            )
            basis = "نتیجهٔ غربالگری ممیزی: needs_more_evidence"

    options = (
        DecisionOption(
            action=ManagerAction.REPEAT,
            label="تکرار",
            availability="requires_verified_pilot_and_economics",
            explanation="برای تکرار، نتیجهٔ آزمون کنترل‌شده و سود خالصِ تأییدشده لازم است؛ این فایل آن‌ها را ندارد.",
        ),
        DecisionOption(
            action=ManagerAction.MODIFY,
            label="اصلاح",
            availability="requires_human_operational_review",
            explanation="این گزارش به‌تنهایی مشخص نمی‌کند کدام اهرم کمپین باید تغییر کند.",
        ),
        DecisionOption(
            action=ManagerAction.MORE_TESTING,
            label="آزمایش بیشتر",
            availability=("recommended" if recommended == ManagerAction.MORE_TESTING else "available"),
            explanation="با گروه مقایسهٔ ازپیش‌تعریف‌شده، معیار نتیجه و سنجش هزینه ادامه دهید.",
        ),
        DecisionOption(
            action=ManagerAction.DEPRIORITIZE,
            label="توقف یا کم‌اولویت‌کردن",
            availability=("recommended_for_human_review" if recommended == ManagerAction.DEPRIORITIZE else "not_recommended_by_this_audit"),
            explanation="کم‌اولویت‌کردن نیازمند بازبینی انسانی است؛ گزارش به‌تنهایی کمپین را متوقف نمی‌کند.",
        ),
    )
    return ManagerDecisionSupport(
        recommended_action=recommended,
        label=label,
        explanation=explanation,
        evidence_basis=basis,
        options=options,
    )
