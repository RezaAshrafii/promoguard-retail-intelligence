"""Descriptive revenue drivers and explicitly hypothetical break-even scenarios."""

from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FinancialAssumptions(BaseModel):
    """User-supplied assumptions used only for conditional contribution scenarios."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    common_contribution_margin: float = Field(ge=0, le=1, allow_inf_nan=False)
    margin_source: str = Field(min_length=1, max_length=500)
    mens_campaign_cost_per_1000: float = Field(ge=0, allow_inf_nan=False)
    mens_cost_source: str = Field(min_length=1, max_length=500)
    womens_campaign_cost_per_1000: float = Field(ge=0, allow_inf_nan=False)
    womens_cost_source: str = Field(min_length=1, max_length=500)
    currency: Literal["USD"] = "USD"

    @field_validator("margin_source", "mens_cost_source", "womens_cost_source")
    @classmethod
    def require_nonblank_reference(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("برای هر مقدار مالی، مرجع یا توضیح وارد کن.")
        return normalized


def revenue_profile(frame: pd.DataFrame) -> dict[str, Any]:
    """Summarize all assigned customers without filtering the ITT population."""
    spend = frame["spend"].to_numpy(dtype=float)
    buyers = spend[spend > 0]
    total = float(spend.sum())
    top_count = max(1, int(np.ceil(len(spend) * 0.01)))
    return {
        "assigned_customers": len(spend),
        "buyers": len(buyers),
        "purchase_probability": len(buyers) / len(spend),
        "revenue_per_assigned_customer": float(spend.mean()),
        "spend_per_buyer": float(buyers.mean()) if len(buyers) else None,
        "top_one_percent_customer_revenue_share": (
            float(np.sort(spend)[-top_count:].sum() / total) if total > 0 else None
        ),
        "top_one_percent_customer_count": top_count,
    }


def build_revenue_details(
    treatment: pd.DataFrame,
    control: pd.DataFrame,
    revenue_interval: tuple[float, float, float],
    financial_assumptions: FinancialAssumptions | None = None,
    *,
    treatment_arm: str | None = None,
    control_arm: str | None = None,
) -> dict[str, Any]:
    """Create a fixed assumption grid; it is not observed company economics."""
    first, second = revenue_profile(treatment), revenue_profile(control)
    point, lower, upper = revenue_interval
    decomposition = None
    if first["buyers"] and second["buyers"]:
        p1, p0 = first["purchase_probability"], second["purchase_probability"]
        a1, a0 = first["spend_per_buyer"], second["spend_per_buyer"]
        # Symmetric algebraic decomposition splits the interaction equally.
        decomposition = {
            "purchase_rate_component_per_customer": (p1 - p0) * (a1 + a0) / 2,
            "buyer_spend_component_per_customer": (a1 - a0) * (p1 + p0) / 2,
            "method": "symmetric product decomposition; descriptive, not causal mediation",
        }
    conditional_economics = None
    if financial_assumptions is not None:
        treatment_cost = (
            financial_assumptions.mens_campaign_cost_per_1000
            if treatment_arm == "Mens E-Mail"
            else financial_assumptions.womens_campaign_cost_per_1000
        )
        control_cost = (
            financial_assumptions.mens_campaign_cost_per_1000
            if control_arm == "Mens E-Mail"
            else financial_assumptions.womens_campaign_cost_per_1000
            if control_arm == "Womens E-Mail"
            else 0.0
        )
        cost_difference = treatment_cost - control_cost
        margin = financial_assumptions.common_contribution_margin
        conditional_economics = {
            "currency": financial_assumptions.currency,
            "common_contribution_margin": margin,
            "incremental_campaign_cost_per_1000": cost_difference,
            "contribution_per_1000": {
                "point": round(point * margin * 1000 - cost_difference, 2),
                "lower": round(lower * margin * 1000 - cost_difference, 2),
                "upper": round(upper * margin * 1000 - cost_difference, 2),
            },
            "assumption_sources": {
                "margin": financial_assumptions.margin_source,
                "treatment_campaign_cost": (
                    financial_assumptions.mens_cost_source
                    if treatment_arm == "Mens E-Mail"
                    else financial_assumptions.womens_cost_source
                ),
                "control_campaign_cost": (
                    financial_assumptions.mens_cost_source
                    if control_arm == "Mens E-Mail"
                    else financial_assumptions.womens_cost_source
                    if control_arm == "Womens E-Mail"
                    else "گروه بدون ایمیل؛ هزینهٔ افزوده صفر فرض شده است"
                ),
            },
            "source_verification": "references_are_user_supplied_and_not_independently_verified",
            "limitation": "Only revenue uncertainty is propagated; the margin and cost inputs are treated as fixed.",
        }

    return {
        "version": "1.0.0",
        "treatment": first,
        "control": second,
        "additional_buyers_per_1000_assigned": (
            first["purchase_probability"] - second["purchase_probability"]
        ) * 1000,
        "decomposition": decomposition,
        "revenue_effect_per_1000": {"point": point * 1000, "lower": lower * 1000, "upper": upper * 1000},
        "break_even_scenarios": [
            {
                "assumed_common_contribution_margin": margin,
                "maximum_incremental_cost_per_1000": point * margin * 1000,
                "lower_bound_cost_per_1000": lower * margin * 1000,
                "upper_bound_cost_per_1000": upper * margin * 1000,
                "basis": "hypothetical_margin_not_observed",
            }
            for margin in (0.1, 0.2, 0.3, 0.4)
        ],
        "conditional_economics": conditional_economics,
        "currency": "USD",
        "limitations": [
            "Buyer spend and its decomposition are descriptive; buyers are selected after treatment.",
            "Top 1% is by assigned-customer count, rounded up; no customers were removed.",
            "Margins are hypothetical and common to both arms; actual cost and margin are absent.",
            "Bounds propagate revenue uncertainty only, not financial-input uncertainty.",
            "A negative cost threshold means no nonnegative campaign cost is covered at that estimate.",
            "Spend is per buyer, not per order; order counts are unavailable.",
        ],
    }
