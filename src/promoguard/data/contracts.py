"""Typed contracts for source boundaries and future partner data."""

from datetime import date

from pydantic import BaseModel, Field, model_validator


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
