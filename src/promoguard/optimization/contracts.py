"""Strict real-input contracts used before any promotion optimization."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EconomicsField = Literal[
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

REQUIRED_EVIDENCE_FIELDS: frozenset[str] = frozenset(
    EconomicsField.__args__  # type: ignore[attr-defined]
)


class EvidenceKind(StrEnum):
    """Allowed provenance classes; none silently upgrades an assumption to observation."""

    PARTNER_EXPORT = "partner_export"
    APPROVED_CONTRACT = "approved_contract"
    MODEL_OUTPUT = "model_output"
    APPROVED_ASSUMPTION = "approved_assumption"


class EconomicsEvidence(BaseModel):
    """Provenance for one financially material scenario field."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field_name: EconomicsField
    kind: EvidenceKind
    reference: str = Field(min_length=1, max_length=300)
    as_of_date: date
    approved_by: str = Field(min_length=1, max_length=120)

    @field_validator("reference", "approved_by")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("evidence text must not be blank")
        return normalized


class ProjectionInterval(BaseModel):
    """Demand projection and bounds; this is predictive, not a causal effect interval."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    point: float = Field(ge=0, allow_inf_nan=False)
    lower: float = Field(ge=0, allow_inf_nan=False)
    upper: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_order(self) -> ProjectionInterval:
        if not self.lower <= self.point <= self.upper:
            raise ValueError("projection bounds must satisfy lower <= point <= upper")
        return self


class PromotionScenario(BaseModel):
    """One candidate supplied from real or explicitly approved business inputs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str = Field(min_length=1, max_length=120)
    store_id: str = Field(min_length=1, max_length=120)
    sku_id: str = Field(min_length=1, max_length=120)
    start_date: date
    end_date: date
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    regular_unit_price: Decimal = Field(gt=0, allow_inf_nan=False)
    promotion_unit_price: Decimal = Field(ge=0, allow_inf_nan=False)
    unit_cost: Decimal = Field(ge=0, allow_inf_nan=False)
    supplier_funding_per_unit: Decimal = Field(ge=0, allow_inf_nan=False)
    fixed_trade_spend: Decimal = Field(ge=0, allow_inf_nan=False)
    variable_trade_spend_per_unit: Decimal = Field(ge=0, allow_inf_nan=False)
    available_inventory_units: int = Field(ge=0)
    baseline_demand_units: float = Field(ge=0, allow_inf_nan=False)
    projected_demand_units: ProjectionInterval
    evidence: list[EconomicsEvidence] = Field(min_length=1, max_length=9)

    @field_validator("scenario_id", "store_id", "sku_id")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("scenario identifiers must not be blank")
        return normalized

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_structure_and_evidence(self) -> PromotionScenario:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        evidence_fields = [item.field_name for item in self.evidence]
        if len(evidence_fields) != len(set(evidence_fields)):
            raise ValueError("each economics field must have exactly one evidence record")
        missing = sorted(REQUIRED_EVIDENCE_FIELDS - set(evidence_fields))
        if missing:
            raise ValueError(f"missing evidence for: {', '.join(missing)}")
        return self


class OptimizationInput(BaseModel):
    """Campaign constraints and candidates; validation does not select or execute a promotion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1, max_length=120)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    total_trade_spend_budget: Decimal = Field(ge=0, allow_inf_nan=False)
    minimum_unit_contribution: Decimal = Field(allow_inf_nan=False)
    maximum_discount_rate: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    inventory_reserve_units: int = Field(default=0, ge=0)
    scenarios: list[PromotionScenario] = Field(min_length=1, max_length=10_000)
    human_approval_required: Literal[True] = True
    automatic_execution_allowed: Literal[False] = False

    @field_validator("request_id")
    @classmethod
    def reject_blank_request_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("request_id must not be blank")
        return normalized

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_candidates(self) -> OptimizationInput:
        scenario_ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("scenario_id values must be unique within one request")
        mismatched = sorted(
            scenario.scenario_id
            for scenario in self.scenarios
            if scenario.currency != self.currency
        )
        if mismatched:
            raise ValueError(
                "scenario currency must match request currency: " + ", ".join(mismatched)
            )
        return self
