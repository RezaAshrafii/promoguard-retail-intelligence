from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from promoguard.data.partner import PartnerExportContract, prepare_partner_export, sha256_file


def contract(**overrides: object) -> PartnerExportContract:
    values: dict[str, object] = {
        "source_id": "test-contract-only",
        "data_owner": "test-owner",
        "permission_reference": "test-permission-reference",
        "extraction_date": date(2026, 9, 16),
        "permitted_purpose": "observational_data_readiness_audit",
        "retention_days": 30,
        "grain": "weekly_store_sku",
        "calendar_reference": "test-calendar",
        "units_definition": "test-observed-units",
        "zero_units_meaning": "observed_zero",
        "promotion_signal_definition": "test-confirmed-flag",
    }
    values.update(overrides)
    return PartnerExportContract(**values)


def export() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "week_end_date": ["2025-01-07", "2025-01-14"],
            "store_id": ["s1", "s1"],
            "upc": ["p1", "p1"],
            "units": [0, 12],
            "promotion_flag": [0, 1],
        }
    )


def test_preparation_preserves_values_and_keeps_provenance_non_row_level() -> None:
    source = export()
    prepared, report = prepare_partner_export(source, contract(), source_sha256="a" * 64)
    assert prepared is not None
    assert report.status == "prepared_for_observational_audit"
    assert prepared["units"].tolist() == [0, 12]
    assert prepared["sku_id"].tolist() == ["p1", "p1"]
    assert "units" not in report.model_dump()
    assert "upc" in source.columns  # the caller's frame is untouched


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"zero_units_meaning": "unknown"}, "blocked"),
        ({"grain": "daily_store_sku"}, "blocked"),
    ],
)
def test_contract_semantics_control_preparation(change: dict[str, str], expected: str) -> None:
    prepared, report = prepare_partner_export(export(), contract(**change), source_sha256="a" * 64)
    assert report.status == expected
    assert (prepared is None) is (expected == "blocked")


def test_weekly_contract_refuses_undocumented_generic_date() -> None:
    source = export().rename(columns={"week_end_date": "date"})
    prepared, report = prepare_partner_export(source, contract(), source_sha256="a" * 64)
    assert prepared is None
    assert report.status == "blocked"


def test_daily_contract_accepts_daily_date_column() -> None:
    source = export().rename(columns={"week_end_date": "transaction_date"})
    prepared, report = prepare_partner_export(
        source, contract(grain="daily_store_sku"), source_sha256="a" * 64
    )
    assert report.status == "prepared_for_observational_audit"
    assert prepared is not None
    assert "date" in prepared.columns


def test_intake_and_privacy_blocks_cannot_be_bypassed_by_contract() -> None:
    for source in (
        export().assign(customer_phone=["1", "2"]),
        export().assign(units=[None, 12]),
        export().assign(promotion_flag=[0, 0]),
    ):
        prepared, report = prepare_partner_export(source, contract(), source_sha256="a" * 64)
        assert prepared is None
        assert report.status == "blocked"


def test_contract_rejects_missing_or_unapproved_permission() -> None:
    with pytest.raises(ValidationError):
        contract(permission_reference="  ")
    with pytest.raises(ValidationError):
        contract(permitted_purpose="automatic_campaign_execution")


def test_sha256_requires_original_file_digest(tmp_path) -> None:
    source = tmp_path / "bytes.csv"
    source.write_bytes(b"first\r\nsecond\r\n")
    assert sha256_file(str(source)) == "f8e0f1568dd9254c3262d199d5dcfc9ff6d4855e18ec53a7176f9eab948ed93e"
    with pytest.raises(ValueError, match="source_sha256"):
        prepare_partner_export(export(), contract(), source_sha256="not-a-hash")
