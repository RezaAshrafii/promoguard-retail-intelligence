"""Human-owned hurdle policy for conditional scenario comparisons."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from promoguard.optimization.economics import ConditionalEconomics, EconomicSensitivity
from promoguard.optimization.feasibility import FeasibilityCode, ScenarioComparisonReport


class ScenarioDecision(StrEnum):
    """Bounded review states; none is an execution instruction."""

    BLOCKED_BY_CONSTRAINTS = "blocked_by_constraints"
    CANDIDATE_FOR_HUMAN_REVIEW = "candidate_for_human_review"
    BELOW_MANAGER_HURDLE = "below_manager_hurdle"
    HURDLE_NOT_RESOLVED = "hurdle_not_resolved"


class ManagerHurdlePolicy(BaseModel):
    """Business hurdle explicitly supplied and approved by a named owner."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    minimum_incremental_profit: Decimal = Field(ge=0, allow_inf_nan=False)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    reference: str = Field(min_length=1, max_length=300)
    approved_by: str = Field(min_length=1, max_length=120)
    as_of_date: date

    @field_validator("reference", "approved_by")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("hurdle reference and approver must not be blank")
        return normalized

class ScenarioDecisionAssessment(BaseModel):
    """One scenario's relation to the manager hurdle and feasibility gates."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    feasibility_status: Literal["eligible", "infeasible"]
    blocking_reasons: list[FeasibilityCode]
    decision: ScenarioDecision
    hurdle_amount: Decimal
    currency: str
    incremental_profit_lower: Decimal
    incremental_profit_point: Decimal
    incremental_profit_upper: Decimal
    conditional_economics: ConditionalEconomics
    economic_sensitivity: EconomicSensitivity
    discount_rate: Decimal
    projected_unit_contribution: Decimal
    projected_trade_spend: Decimal
    sellable_inventory_units: int
    explanation: str


class ManagerPolicyComparison(BaseModel):
    """Policy evaluation that preserves human ownership and abstention."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    policy: ManagerHurdlePolicy
    assessments: list[ScenarioDecisionAssessment]
    budget_scope: Literal["per_scenario_screen_only"] = "per_scenario_screen_only"
    selection_status: Literal["manual_review_required"] = "manual_review_required"
    selected_scenario_id: None = None
    limitation: str = (
        "سناریوهای تقاضا بازهٔ پیش‌بینی هستند، نه بازهٔ اطمینان یا اثر علّی. "
        "بودجه برای هر سناریو جداگانه غربال می‌شود و میان سبد تقسیم نشده است. "
        "مشخصات تأییدکننده در این نسخه فقط متن ثبت‌شده است و هویت او احراز نمی‌شود. "
        "عبور از آستانه فقط نامزدی برای بررسی انسانی است و تأیید اجرا نیست."
    )


def evaluate_manager_policy(
    comparison: ScenarioComparisonReport,
    policy: ManagerHurdlePolicy,
) -> ManagerPolicyComparison:
    """Classify each scenario against the human-set hurdle without ranking it."""

    if policy.currency != comparison.currency:
        raise ValueError("manager hurdle currency must match scenario currency")

    assessments: list[ScenarioDecisionAssessment] = []
    for scenario in comparison.scenarios:
        incremental = scenario.conditional_economics.incremental_profit
        if scenario.status != "eligible":
            decision = ScenarioDecision.BLOCKED_BY_CONSTRAINTS
            explanation = "سناریو دست‌کم یک محدودیت عملیاتی یا مالی را رد کرده است؛ ابتدا همان موارد بررسی شوند."
        elif incremental.lower >= policy.minimum_incremental_profit:
            decision = ScenarioDecision.CANDIDATE_FOR_HUMAN_REVIEW
            explanation = (
                "حتی حد پایین سناریوی تقاضا به آستانهٔ تعیین‌شده می‌رسد؛ "
                "این فقط نامزدی برای بررسی انسانی است."
            )
        elif incremental.upper < policy.minimum_incremental_profit:
            decision = ScenarioDecision.BELOW_MANAGER_HURDLE
            explanation = (
                "حتی حد بالای سناریوی تقاضا به آستانهٔ تعیین‌شده نمی‌رسد؛ "
                "این به‌تنهایی دستور توقف کمپین نیست."
            )
        else:
            decision = ScenarioDecision.HURDLE_NOT_RESOLVED
            explanation = (
                "بازهٔ سناریوی تقاضا از آستانه عبور می‌کند؛ با این داده نتیجه روشن نیست "
                "و باید اطلاعات یا آزمون بهتری تهیه شود."
            )
        assessments.append(
            ScenarioDecisionAssessment(
                scenario_id=scenario.scenario_id,
                feasibility_status=scenario.status,
                blocking_reasons=scenario.reasons,
                decision=decision,
                hurdle_amount=policy.minimum_incremental_profit,
                currency=policy.currency,
                incremental_profit_lower=incremental.lower,
                incremental_profit_point=incremental.point,
                incremental_profit_upper=incremental.upper,
                conditional_economics=scenario.conditional_economics,
                economic_sensitivity=scenario.economic_sensitivity,
                discount_rate=scenario.discount_rate,
                projected_unit_contribution=scenario.projected_unit_contribution,
                projected_trade_spend=scenario.projected_trade_spend,
                sellable_inventory_units=scenario.sellable_inventory_units,
                explanation=explanation,
            )
        )
    return ManagerPolicyComparison(
        request_id=comparison.request_id,
        policy=policy,
        assessments=assessments,
    )


