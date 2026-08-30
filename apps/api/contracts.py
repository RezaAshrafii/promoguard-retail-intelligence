"""HTTP boundary contracts for PromoGuard API v1."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator

from promoguard.insights.promotion_audit import ContributionAssumption


class DatasetPathRequest(BaseModel):
    """Reference a local processed directory or canonical panel CSV."""

    input_path: str = Field(min_length=1)


class PromotionListRequest(DatasetPathRequest):
    """Request a bounded list of detected promotion episodes."""

    limit: int = Field(default=100, ge=1, le=500)


class AuditRequest(DatasetPathRequest):
    """Audit an explicit event or auto-select the first eligible one."""

    store_id: str | None = None
    upc: str | None = None
    start_date: date | None = None
    contribution_assumption: ContributionAssumption | None = None

    @model_validator(mode="after")
    def require_complete_event_key(self) -> AuditRequest:
        values = [self.store_id, self.upc, self.start_date]
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("store_id, upc, and start_date must be supplied together")
        return self


class PanelQualityResponse(BaseModel):
    """Stable application quality-report schema."""

    dataset: str
    grain: str
    rows: int
    columns: list[str]
    missing_required_columns: list[str]
    max_rows: int
    oversized_row_count: bool
    empty: bool
    date_parse_errors: int | None
    duplicate_grain_rows: int | None
    negative_units_rows: int | None
    missing_units_rows: int | None
    invalid_promotion_rows: int | None
    promotion_rows: int | None
    series: int | None
    date_min: str | None
    date_max: str | None
    warnings: list[str]
    valid: bool


class PromotionEpisodeResponse(BaseModel):
    audit_id: str
    store_id: str
    upc: str
    start_date: date
    end_date: date
    duration_weeks: int


class PromotionListResponse(BaseModel):
    count: int
    returned: int
    events: list[PromotionEpisodeResponse]


class ErrorResponse(BaseModel):
    detail: str | dict[str, Any]
