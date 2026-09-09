from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from promoguard.optimization import (
    EconomicsEvidence,
    EvidenceKind,
    FeasibilityCode,
    OptimizationInput,
    ProjectionInterval,
    PromotionScenario,
    assess_scenarios,
)

ECONOMICS_FIELDS = [
    "regular_unit_price",
    "promotion_unit_price",
    "unit_cost",
    "supplier_funding_per_unit",
    "fixed_trade_spend",
    "variable_trade_spend_per_unit",
    "available_inventory_units",
    "baseline_demand_units",
    "projected_demand_units",
]


def evidence() -> list[EconomicsEvidence]:
    return [
        EconomicsEvidence(
            field_name=field,
            kind=(
                EvidenceKind.MODEL_OUTPUT
                if field == "projected_demand_units"
                else EvidenceKind.PARTNER_EXPORT
            ),
            reference=f"partner-export-2026-09-09:{field}",
            as_of_date=date(2026, 9, 9),
            approved_by="commercial-owner",
        )
        for field in ECONOMICS_FIELDS
    ]


def scenario(**overrides: object) -> PromotionScenario:
    values: dict[str, object] = {
        "scenario_id": "scenario-10pct",
        "store_id": "store-1",
        "sku_id": "sku-1",
        "start_date": date(2026, 10, 1),
        "end_date": date(2026, 10, 7),
        "currency": "irr",
        "regular_unit_price": "100000",
        "promotion_unit_price": "90000",
        "unit_cost": "70000",
        "supplier_funding_per_unit": "5000",
        "fixed_trade_spend": "100000",
        "variable_trade_spend_per_unit": "1000",
        "available_inventory_units": 200,
        "baseline_demand_units": 80,
        "projected_demand_units": ProjectionInterval(point=100, lower=90, upper=120),
        "evidence": evidence(),
    }
    values.update(overrides)
    return PromotionScenario(**values)


def request(candidate: PromotionScenario | None = None, **overrides: object) -> OptimizationInput:
    values: dict[str, object] = {
        "request_id": "campaign-1",
        "currency": "IRR",
        "total_trade_spend_budget": "250000",
        "minimum_unit_contribution": "20000",
        "maximum_discount_rate": "0.20",
        "inventory_reserve_units": 20,
        "scenarios": [candidate or scenario()],
        "human_approval_required": True,
        "automatic_execution_allowed": False,
    }
    values.update(overrides)
    return OptimizationInput(**values)


def test_valid_real_input_contract_normalizes_currency_and_identifiers() -> None:
    candidate = scenario(scenario_id=" scenario-10pct ")
    assert candidate.currency == "IRR"
    assert candidate.scenario_id == "scenario-10pct"
    assert request(candidate).automatic_execution_allowed is False


def test_contract_rejects_missing_evidence() -> None:
    with pytest.raises(ValidationError, match="missing evidence"):
        scenario(evidence=evidence()[:-1])


def test_contract_rejects_duplicate_evidence() -> None:
    records = evidence()
    records[-1] = records[0]
    with pytest.raises(ValidationError, match="exactly one evidence"):
        scenario(evidence=records)


def test_contract_rejects_inverted_projection_interval() -> None:
    with pytest.raises(ValidationError, match="lower <= point <= upper"):
        ProjectionInterval(point=100, lower=110, upper=120)


def test_contract_rejects_non_finite_projection() -> None:
    with pytest.raises(ValidationError):
        ProjectionInterval(point=float("nan"), lower=0, upper=10)


def test_contract_rejects_duplicate_scenario_ids() -> None:
    duplicate = scenario()
    with pytest.raises(ValidationError, match="scenario_id values must be unique"):
        request(scenarios=[duplicate, duplicate])


def test_contract_rejects_mixed_currency_request() -> None:
    with pytest.raises(ValidationError, match="currency must match"):
        request(scenario(currency="USD"))


def test_contract_cannot_disable_human_approval_or_enable_execution() -> None:
    with pytest.raises(ValidationError):
        request(human_approval_required=False)
    with pytest.raises(ValidationError):
        request(automatic_execution_allowed=True)


def test_eligible_scenario_exposes_only_constraint_screening() -> None:
    result = assess_scenarios(request())[0]
    assert result.status == "eligible"
    assert result.reasons == []
    assert result.discount_rate == Decimal("0.1")
    assert result.projected_unit_contribution == Decimal(24000)
    assert result.projected_trade_spend == Decimal("200000.0")
    assert "not a profit forecast" in result.limitation


def test_all_infeasibility_reasons_are_reported_together() -> None:
    candidate = scenario(
        promotion_unit_price="110000",
        unit_cost="120000",
        supplier_funding_per_unit="0",
        fixed_trade_spend="300000",
        variable_trade_spend_per_unit="5000",
        available_inventory_units=10,
        projected_demand_units=ProjectionInterval(point=100, lower=90, upper=140),
    )
    result = assess_scenarios(
        request(
            candidate,
            maximum_discount_rate="0.05",
            inventory_reserve_units=20,
            total_trade_spend_budget="250000",
        )
    )[0]
    assert result.status == "infeasible"
    assert set(result.reasons) == {
        FeasibilityCode.PROMOTION_PRICE_ABOVE_REGULAR,
        FeasibilityCode.INVENTORY_RESERVE_NOT_MET,
        FeasibilityCode.PROJECTED_DEMAND_EXCEEDS_SELLABLE_INVENTORY,
        FeasibilityCode.UNIT_CONTRIBUTION_BELOW_FLOOR,
        FeasibilityCode.TRADE_SPEND_BUDGET_EXCEEDED,
    }


def test_discount_limit_is_checked_at_exact_decimal_boundary() -> None:
    candidate = scenario(promotion_unit_price="79999")
    result = assess_scenarios(request(candidate, maximum_discount_rate="0.20"))[0]
    assert result.status == "infeasible"
    assert FeasibilityCode.DISCOUNT_LIMIT_EXCEEDED in result.reasons


def test_unknown_fields_are_rejected_instead_of_silently_ignored() -> None:
    payload = scenario().model_dump()
    payload["estimated_profit"] = 999999999
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PromotionScenario.model_validate(payload)
