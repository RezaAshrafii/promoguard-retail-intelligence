"""Transparent conditional economics for one promotion scenario.

The functions in this module compare a promoted scenario with the same-period
baseline demand at the regular price. They are deliberately descriptive and
conditional: they do not estimate causal lift and they do not select a
scenario for execution.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from promoguard.optimization.contracts import PromotionScenario


class MonetaryInterval(BaseModel):
    """Point and bounds for a monetary quantity in one scenario currency."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    point: Decimal
    lower: Decimal
    upper: Decimal
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")

    @classmethod
    def from_values(
        cls, point: Decimal, lower: Decimal, upper: Decimal, currency: str
    ) -> MonetaryInterval:
        if lower > point or point > upper:
            raise ValueError("monetary interval must satisfy lower <= point <= upper")
        return cls(point=point, lower=lower, upper=upper, currency=currency)


class ConditionalEconomics(BaseModel):
    """Economics conditional on the supplied demand projection and inputs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_profit: Decimal
    promoted_profit: MonetaryInterval
    incremental_profit: MonetaryInterval
    baseline_profit_basis: str = (
        "baseline demand at regular price minus unit cost; no promotion spend"
    )
    promoted_profit_basis: str = (
        "projected demand times promoted unit contribution minus fixed trade spend"
    )
    limitation: str = (
        "Conditional scenario economics only; demand is not a causal lift estimate "
        "and the result is not an execution approval."
    )


def _interval_product(
    demand_lower: Decimal,
    demand_point: Decimal,
    demand_upper: Decimal,
    unit_value: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    values = (
        demand_lower * unit_value,
        demand_point * unit_value,
        demand_upper * unit_value,
    )
    return values[1], min(values), max(values)


def calculate_conditional_economics(
    scenario: PromotionScenario,
) -> ConditionalEconomics:
    """Calculate a transparent baseline-versus-promotion profit interval.

    The baseline uses ``baseline_demand_units`` at the regular price. The
    promoted interval uses the supplied projected-demand interval, promotional
    price, supplier funding, variable trade spend, and fixed trade spend. The
    calculation is intentionally conditional on these evidenced inputs.
    """

    baseline_unit_contribution = scenario.regular_unit_price - scenario.unit_cost
    promoted_unit_contribution = (
        scenario.promotion_unit_price
        - scenario.unit_cost
        + scenario.supplier_funding_per_unit
        - scenario.variable_trade_spend_per_unit
    )
    baseline_profit = (
        Decimal(str(scenario.baseline_demand_units)) * baseline_unit_contribution
    )
    promoted_point, promoted_lower, promoted_upper = _interval_product(
        Decimal(str(scenario.projected_demand_units.lower)),
        Decimal(str(scenario.projected_demand_units.point)),
        Decimal(str(scenario.projected_demand_units.upper)),
        promoted_unit_contribution,
    )
    promoted = MonetaryInterval.from_values(
        promoted_point - scenario.fixed_trade_spend,
        promoted_lower - scenario.fixed_trade_spend,
        promoted_upper - scenario.fixed_trade_spend,
        scenario.currency,
    )
    incremental = MonetaryInterval.from_values(
        promoted.point - baseline_profit,
        promoted.lower - baseline_profit,
        promoted.upper - baseline_profit,
        scenario.currency,
    )
    return ConditionalEconomics(
        baseline_profit=baseline_profit,
        promoted_profit=promoted,
        incremental_profit=incremental,
    )
