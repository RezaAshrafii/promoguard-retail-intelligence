"""Permission-gated preparation of a partner export for observational work only."""

from __future__ import annotations

from datetime import date
from hashlib import sha256
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from promoguard.data.intake import _normalise_columns, assess_partner_intake


class PartnerExportContract(BaseModel):
    """Human-supplied facts that must accompany an export, not inferred from its rows."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    data_owner: str = Field(min_length=1)
    permission_reference: str = Field(min_length=1)
    extraction_date: date
    permitted_purpose: Literal["observational_data_readiness_audit"]
    retention_days: int = Field(gt=0, le=365)
    grain: Literal["daily_store_sku", "weekly_store_sku"]
    calendar_reference: str = Field(min_length=1)
    units_definition: str = Field(min_length=1)
    zero_units_meaning: Literal["observed_zero", "unknown"]
    promotion_signal_definition: str = Field(min_length=1)

    @field_validator(
        "source_id", "data_owner", "permission_reference", "calendar_reference",
        "units_definition", "promotion_signal_definition",
    )
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("contract text must not be blank")
        return value.strip()


class PartnerPrepared(BaseModel):
    """Non-row-level audit metadata returned alongside a prepared frame."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    source_sha256: str
    status: Literal["prepared_for_observational_audit", "blocked"]
    intake_status: str
    rows: int
    column_mapping: dict[str, str]
    limitation: Literal[
        "Schema and permission gate only; no causal, economics, or rollout approval."
    ] = "Schema and permission gate only; no causal, economics, or rollout approval."


def prepare_partner_export(
    frame: pd.DataFrame, contract: PartnerExportContract, *, source_sha256: str
) -> tuple[pd.DataFrame | None, PartnerPrepared]:
    """Gate a partner export; return no data frame when intake or contract semantics block it.

    The SHA256 must be computed from the original source file by the caller. This function
    never hashes a reserialized frame, imputes values, or writes partner rows to Git.
    """

    digest = source_sha256.lower()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("source_sha256 must be a SHA256 hex digest of the original source file")
    intake = assess_partner_intake(frame)
    weekly_source = any(
        raw.strip().lower() == "week_end_date" and normalized == "date"
        for raw, normalized in intake["column_mapping"].items()
    )
    blocked = (
        intake["status"] != "ready_for_observational_audit"
        or contract.zero_units_meaning != "observed_zero"
        or (contract.grain == "weekly_store_sku" and not weekly_source)
        or (contract.grain == "daily_store_sku" and weekly_source)
    )
    result = PartnerPrepared(
        source_id=contract.source_id,
        source_sha256=digest,
        status="blocked" if blocked else "prepared_for_observational_audit",
        intake_status=intake["status"],
        rows=intake["rows"],
        column_mapping=intake["column_mapping"],
    )
    if blocked:
        return None, result
    canonical, _ = _normalise_columns(frame)
    return canonical, result


def sha256_file(path: str) -> str:
    """Compute provenance on original bytes without keeping partner content in the report."""

    digest = sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
