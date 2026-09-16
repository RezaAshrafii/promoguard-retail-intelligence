"""Partner-data intake checks before any customer analysis is allowed."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"date", "store_id", "sku_id", "units"}
ALIASES = {
    "week_end_date": "date",
    "transaction_date": "date",
    "upc": "sku_id",
    "product_id": "sku_id",
    "store_num": "store_id",
    "quantity": "units",
}
OPTIONAL_COLUMNS = {
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
}
PII_TOKENS = (
    "customer_name",
    "full_name",
    "email",
    "phone",
    "mobile",
    "national_id",
    "nationalcode",
    "postal_code",
)
NUMERIC_COLUMNS = {
    "units",
    "revenue",
    "regular_price",
    "selling_price",
    "inventory_on_hand",
    "unit_cost",
    "contribution_margin",
}


def _normalise_columns(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    rename_map: dict[str, str] = {}
    for raw in frame.columns:
        clean = str(raw).strip().lower()
        rename_map[raw] = ALIASES.get(clean, clean)
    renamed = frame.rename(columns=rename_map).copy()
    return renamed, {str(key): value for key, value in rename_map.items()}


def assess_partner_intake(frame: pd.DataFrame, *, max_rows: int = 1_000_000) -> dict[str, Any]:
    """Assess a customer export without imputing, dropping, or changing business values."""

    working, column_mapping = _normalise_columns(frame)
    columns = set(working.columns)
    duplicate_columns = sorted(
        {column for column in working.columns if list(working.columns).count(column) > 1}
    )
    missing_required = sorted(REQUIRED_COLUMNS - columns)
    privacy_columns = sorted(
        column
        for column in columns
        if any(token in column for token in PII_TOKENS)
    )
    report: dict[str, Any] = {
        "dataset": "partner-data-intake",
        "expected_grain": "date × store_id × sku_id",
        "rows": len(working),
        "columns": sorted(columns),
        "column_mapping": column_mapping,
        "missing_required_columns": missing_required,
        "duplicate_column_names": duplicate_columns,
        "unexpected_columns": sorted(columns - REQUIRED_COLUMNS - OPTIONAL_COLUMNS),
        "privacy_columns": privacy_columns,
        "max_rows": max_rows,
        "oversized_row_count": len(working) > max_rows,
        "date_parse_errors": None,
        "missing_identifier_rows": {"store_id": None, "sku_id": None},
        "duplicate_grain_rows": None,
        "numeric_parse_errors": {},
        "negative_value_rows": {},
        "invalid_binary_rows": {},
        "date_min": None,
        "date_max": None,
        "has_promotion_signal": False,
        "has_economics_fields": False,
        "has_inventory_signal": False,
        "warnings": [],
    }
    if duplicate_columns:
        report["warnings"].append("Duplicate normalized column names require manual mapping review.")
    if privacy_columns:
        report["warnings"].append("Potential personal-data columns require removal or privacy review.")
    if missing_required:
        report["status"] = "blocked_data_quality"
        report["valid"] = False
        return report

    parsed_dates = pd.to_datetime(working["date"], errors="coerce", format="mixed")
    report["date_parse_errors"] = int(parsed_dates.isna().sum())
    if parsed_dates.notna().any():
        report["date_min"] = parsed_dates.min().date().isoformat()
        report["date_max"] = parsed_dates.max().date().isoformat()
    for identifier in ("store_id", "sku_id"):
        values = working[identifier].astype("string").str.strip()
        report["missing_identifier_rows"][identifier] = int(values.isna().sum() + values.eq("").sum())
        working[identifier] = values

    for column in sorted(NUMERIC_COLUMNS & columns):
        numeric = pd.to_numeric(working[column], errors="coerce")
        report["numeric_parse_errors"][column] = int(
            (working[column].notna() & numeric.isna()).sum()
        )
        report["negative_value_rows"][column] = int((numeric < 0).sum())
        non_finite = numeric.notna() & ~np.isfinite(numeric)
        report["numeric_parse_errors"][column] += int(non_finite.sum())
        working[column] = numeric

    if "promotion_flag" in columns:
        report["invalid_binary_rows"]["promotion_flag"] = int(
            (~working["promotion_flag"].isin([0, 1]) & working["promotion_flag"].notna()).sum()
        )
    if "stockout_flag" in columns:
        report["invalid_binary_rows"]["stockout_flag"] = int(
            (~working["stockout_flag"].isin([0, 1]) & working["stockout_flag"].notna()).sum()
        )

    report["duplicate_grain_rows"] = int(
        working.duplicated(["date", "store_id", "sku_id"]).sum()
    )
    report["has_promotion_signal"] = bool(
        {"promotion_flag", "promotion_id"}.intersection(columns)
        or {"regular_price", "selling_price"}.issubset(columns)
    )
    report["has_economics_fields"] = bool(
        {"unit_cost", "contribution_margin"}.issubset(columns)
    )
    report["has_inventory_signal"] = bool(
        {"inventory_on_hand", "stockout_flag"}.intersection(columns)
    )

    fatal_values = [
        report["oversized_row_count"],
        report["date_parse_errors"],
        *report["missing_identifier_rows"].values(),
        report["duplicate_grain_rows"],
        *report["numeric_parse_errors"].values(),
        *report["negative_value_rows"].values(),
        *report["invalid_binary_rows"].values(),
    ]
    report["valid"] = not any(fatal_values) and not duplicate_columns
    if not report["valid"]:
        report["status"] = "blocked_data_quality"
    elif privacy_columns:
        report["status"] = "blocked_privacy_review"
    elif report["has_promotion_signal"]:
        report["status"] = "ready_for_observational_audit"
    else:
        report["status"] = "limited_observational_report"
        report["warnings"].append(
            "No promotion signal was found; promotion-effect analysis cannot start from this export."
        )
    if not report["has_economics_fields"]:
        report["warnings"].append(
            "Unit cost and contribution margin are absent; economics and profit approval remain unavailable."
        )
    return report
