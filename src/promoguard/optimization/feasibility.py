"""Deterministic pre-optimization checks; no scenario is selected or executed here."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from promoguard.optimization.contracts import OptimizationInput, PromotionScenario


class FeasibilityCode(StrEnum):
    PROMOTION_PRICE_ABOVE_REGULAR = "promotion_price_above_regular"
    DISCOUNT_LIMIT_EXCEEDED = "discount_limit_exceeded"
    INVENTORY_RESERVE_NOT_MET = "inventory_reserve_not_met"
    PROJECTED_DEMAND_EXCEEDS_SELLABLE_INVENTORY = (
        "projected_demand_exceeds_sellable_inventory"
    )
    UNIT_CONTRIBUTION_BELOW_FLOOR = "unit_contribution_below_floor"
    TRADE_SPEND_BUDGET_EXCEEDED = "trade_spend_budget_exceeded"


class ScenarioFeasibility(BaseModel):
    """Auditable constraint result for one candidate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    status: Literal["eligible", "infeasible"]
    reasons: list[FeasibilityCode]
    discount_rate: Decimal
    projected_unit_contribution: Decimal
    projected_trade_spend: Decimal
    sellable_inventory_units: int
    limitation: Literal[
        "Constraint screening only; not a profit forecast, causal estimate, or rollout approval."
    ] = "Constraint screening only; not a profit forecast, causal estimate, or rollout approval."


def _assess_one(request: OptimizationInput, scenario: PromotionScenario) -> ScenarioFeasibility:
    reasons: list[FeasibilityCode] = []
    discount_rate = (scenario.regular_unit_price - scenario.promotion_unit_price) / (
        scenario.regular_unit_price
    )
    projected_unit_contribution = (
        scenario.promotion_unit_price
        - scenario.unit_cost
        + scenario.supplier_funding_per_unit
        - scenario.variable_trade_spend_per_unit
    )
    projected_trade_spend = scenario.fixed_trade_spend + (
        scenario.variable_trade_spend_per_unit
        * Decimal(str(scenario.projected_demand_units.point))
    )
    sellable_inventory = max(
        scenario.available_inventory_units - request.inventory_reserve_units, 0
    )

    if scenario.promotion_unit_price > scenario.regular_unit_price:
        reasons.append(FeasibilityCode.PROMOTION_PRICE_ABOVE_REGULAR)
    if discount_rate > request.maximum_discount_rate:
        reasons.append(FeasibilityCode.DISCOUNT_LIMIT_EXCEEDED)
    if scenario.available_inventory_units < request.inventory_reserve_units:
        reasons.append(FeasibilityCode.INVENTORY_RESERVE_NOT_MET)
    if scenario.projected_demand_units.upper > sellable_inventory:
        reasons.append(FeasibilityCode.PROJECTED_DEMAND_EXCEEDS_SELLABLE_INVENTORY)
    if projected_unit_contribution < request.minimum_unit_contribution:
        reasons.append(FeasibilityCode.UNIT_CONTRIBUTION_BELOW_FLOOR)
    if projected_trade_spend > request.total_trade_spend_budget:
        reasons.append(FeasibilityCode.TRADE_SPEND_BUDGET_EXCEEDED)

    return ScenarioFeasibility(
        scenario_id=scenario.scenario_id,
        status="infeasible" if reasons else "eligible",
        reasons=reasons,
        discount_rate=discount_rate,
        projected_unit_contribution=projected_unit_contribution,
        projected_trade_spend=projected_trade_spend,
        sellable_inventory_units=sellable_inventory,
    )


def assess_scenarios(request: OptimizationInput) -> list[ScenarioFeasibility]:
    """Assess every candidate without ranking, selecting, or executing one."""
    return [_assess_one(request, scenario) for scenario in request.scenarios]
