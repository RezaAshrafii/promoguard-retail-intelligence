"""Typed contracts for source boundaries and future partner data."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CUSTOMER_DATA_CONTRACT_VERSION = "customer-data-contract.v1"
CUSTOMER_REQUIRED_COLUMNS = ("date", "store_id", "sku_id", "units")
CUSTOMER_OPTIONAL_COLUMNS = (
    "revenue",
    "currency",
    "regular_price",
    "selling_price",
    "promotion_id",
    "promotion_flag",
    "inventory_on_hand",
    "stockout_flag",
    "unit_cost",
    "contribution_margin",
)
class CustomerDataContract(BaseModel):
    """Versioned, customer-facing contract for one tabular retail export.

    This contract describes the minimum shape and business meaning that the owner must declare
    before an export enters the intake gate. It does not grant permission to use the data and it
    does not claim that the file supports causal or profit analysis.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["customer-data-contract.v1"] = CUSTOMER_DATA_CONTRACT_VERSION
    source_format: Literal["csv"] = "csv"
    grain: Literal["auto", "daily_store_sku", "weekly_store_sku"] = "auto"
    date_column: Literal["auto", "date", "week_end_date", "transaction_date"] = "auto"
    required_columns: tuple[str, ...] = CUSTOMER_REQUIRED_COLUMNS
    optional_columns: tuple[str, ...] = CUSTOMER_OPTIONAL_COLUMNS
    units_definition: str = Field(default="not_declared", min_length=1)
    zero_units_meaning: Literal["observed_zero", "unknown", "not_declared"] = "not_declared"
    promotion_signal_columns: tuple[Literal["promotion_flag", "promotion_id"], ...] = ()
    promotion_signal_definition: str | None = None
    personal_data_allowed: Literal["prohibited"] = "prohibited"

    @field_validator("units_definition")
    @classmethod
    def validate_units_definition(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("units_definition must not be blank")
        return cleaned

    @field_validator("promotion_signal_definition")
    @classmethod
    def clean_promotion_definition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("promotion_signal_definition must not be blank")
        return cleaned

    @field_validator("required_columns")
    @classmethod
    def validate_required_columns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(dict.fromkeys(value)) != CUSTOMER_REQUIRED_COLUMNS:
            raise ValueError(
                "required_columns must contain exactly date, store_id, sku_id, and units"
            )
        return value

    @field_validator("optional_columns")
    @classmethod
    def validate_optional_columns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("optional_columns must not contain duplicates")
        unknown = set(value) - set(CUSTOMER_OPTIONAL_COLUMNS)
        if unknown:
            raise ValueError(f"optional_columns contains unsupported fields: {sorted(unknown)}")
        if set(value) & set(CUSTOMER_REQUIRED_COLUMNS):
            raise ValueError("optional_columns must not repeat required columns")
        return value

    @model_validator(mode="after")
    def validate_semantics(self) -> "CustomerDataContract":
        if self.promotion_signal_columns and not self.promotion_signal_definition:
            raise ValueError(
                "promotion_signal_definition is required when promotion columns are declared"
            )
        if (
            self.grain == "weekly_store_sku"
            and self.date_column == "transaction_date"
        ):
            raise ValueError("weekly_store_sku cannot use transaction_date as its declared date")
        if self.grain == "daily_store_sku" and self.date_column == "week_end_date":
            raise ValueError("daily_store_sku cannot use week_end_date as its declared date")
        return self


def standard_customer_data_contract() -> CustomerDataContract:
    """Return the non-binding default schema used when no owner declaration is supplied."""

    return CustomerDataContract()


class PromotionEventContract(BaseModel):
    """A declared campaign event and the commercial context needed to identify its scope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["promotion-event-contract.v1"] = "promotion-event-contract.v1"
    promotion_id: str = Field(min_length=1)
    sku_ids: tuple[str, ...] = Field(min_length=1)
    start_date: date
    end_date: date
    discount_type: Literal[
        "percentage_price_reduction",
        "fixed_amount_reduction",
        "multibuy",
        "bundle",
        "coupon",
        "display_only",
        "feature_only",
        "other",
    ]
    discount_depth: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    discount_depth_unit: Literal["fraction", "currency_per_unit", "not_reported"]
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    channel: str = Field(min_length=1)
    region: str = Field(min_length=1)

    @field_validator("promotion_id", "channel", "region")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned

    @field_validator("sku_ids")
    @classmethod
    def validate_sku_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(sku.strip() for sku in value)
        if any(not sku for sku in cleaned):
            raise ValueError("sku_ids must not contain blank identifiers")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("sku_ids must not contain duplicates")
        return cleaned

    @model_validator(mode="after")
    def validate_event_semantics(self) -> "PromotionEventContract":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if self.discount_type == "percentage_price_reduction":
            if self.discount_depth is None or self.discount_depth_unit != "fraction":
                raise ValueError("percentage reductions require discount_depth as a fraction")
            if self.discount_depth > 1:
                raise ValueError("percentage discount_depth must be between 0 and 1")
            if self.currency is not None:
                raise ValueError("percentage discount events must not declare currency")
        elif self.discount_type == "fixed_amount_reduction":
            if (
                self.discount_depth is None
                or self.discount_depth_unit != "currency_per_unit"
                or self.currency is None
            ):
                raise ValueError(
                    "fixed amount reductions require a positive amount, currency, and currency_per_unit"
                )
        elif (
            self.discount_depth is not None
            or self.discount_depth_unit != "not_reported"
            or self.currency is not None
        ):
            raise ValueError(
                "non-price promotion mechanics must use not_reported and omit depth and currency"
            )
        return self


class PromotionEventRegistry(BaseModel):
    """A bounded collection of campaign records with unique promotion identifiers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["promotion-event-registry.v1"] = "promotion-event-registry.v1"
    events: tuple[PromotionEventContract, ...] = Field(min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_unique_promotion_ids(self) -> "PromotionEventRegistry":
        promotion_ids = [event.promotion_id for event in self.events]
        if len(set(promotion_ids)) != len(promotion_ids):
            raise ValueError("promotion_id must be unique within the event registry")
        return self


class DunnhumbyWeeklyRecord(BaseModel):
    """Canonical contract for one weekly store-product observation."""

    week_end_date: date
    store_id: str = Field(min_length=1)
    upc: str = Field(min_length=1)
    units: float = Field(ge=0)
    visits: float = Field(ge=0)
    households: float = Field(ge=0)
    spend: float = Field(ge=0)
    price: float | None = Field(default=None, ge=0)
    base_price: float | None = Field(default=None, gt=0)
    feature: int = Field(ge=0, le=1)
    display: int = Field(ge=0, le=1)
    tpr_only: int = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_tpr_only(self) -> "DunnhumbyWeeklyRecord":
        if self.tpr_only and (self.feature or self.display):
            raise ValueError("tpr_only cannot coexist with feature or display")
        return self


class SalesDailyRecord(BaseModel):
    date: date
    store_id: str = Field(min_length=1)
    sku_id: str = Field(min_length=1)
    units: float = Field(ge=0)
    revenue: float = Field(ge=0)


class PromotionRecord(BaseModel):
    promotion_id: str = Field(min_length=1)
    store_id: str = Field(min_length=1)
    sku_id: str = Field(min_length=1)
    start_date: date
    end_date: date
    discount_depth: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_date_range(self) -> "PromotionRecord":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self
