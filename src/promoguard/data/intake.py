"""Partner-data intake checks before any customer analysis is allowed."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from promoguard.data.contracts import (
    CUSTOMER_OPTIONAL_COLUMNS,
    CUSTOMER_REQUIRED_COLUMNS,
    CustomerDataContract,
    standard_customer_data_contract,
)

ALIASES = {
    "week_end_date": "date",
    "transaction_date": "date",
    "upc": "sku_id",
    "product_id": "sku_id",
    "store_num": "store_id",
    "quantity": "units",
}
OPTIONAL_COLUMNS = {
    *CUSTOMER_OPTIONAL_COLUMNS,
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
ECONOMICS_INTAKE_COLUMNS = ("unit_cost", "contribution_margin")
MISSING_ECONOMICS_MESSAGE = (
    "تحلیل فروش انجام شد؛ تحلیل سود به‌دلیل نبود اطلاعات هزینه قابل انجام نیست."
)


def _normalise_columns(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    rename_map: dict[str, str] = {}
    for raw in frame.columns:
        clean = str(raw).strip().lower()
        rename_map[raw] = ALIASES.get(clean, clean)
    renamed = frame.rename(columns=rename_map).copy()
    return renamed, {str(key): value for key, value in rename_map.items()}


def assess_partner_intake(
    frame: pd.DataFrame,
    *,
    max_rows: int = 1_000_000,
    contract: CustomerDataContract | None = None,
) -> dict[str, Any]:
    """Assess a customer export without imputing, dropping, or changing business values.

    ``contract=None`` keeps the historical intake behavior but still reports the standard
    contract version. Passing a contract turns owner-declared date, grain, and promotion fields
    into explicit gate checks.
    """

    effective_contract = contract or standard_customer_data_contract()
    contract_mode = "explicit" if contract is not None else "standard_default"
    working, column_mapping = _normalise_columns(frame)
    columns = set(working.columns)
    raw_columns = {str(column).strip().lower() for column in frame.columns}
    duplicate_columns = sorted(
        {column for column in working.columns if list(working.columns).count(column) > 1}
    )
    missing_required = sorted(set(effective_contract.required_columns) - columns)
    contract_failures: list[str] = []
    contract_warnings: list[str] = []
    if contract_mode == "explicit":
        if effective_contract.grain == "auto":
            contract_failures.append("grain_not_declared")
        if effective_contract.date_column == "auto":
            contract_failures.append("date_column_not_declared")
        if effective_contract.zero_units_meaning == "not_declared":
            contract_failures.append("zero_units_meaning_not_declared")
        if effective_contract.units_definition == "not_declared":
            contract_failures.append("units_definition_not_declared")
        undeclared_columns = sorted(
            columns
            - set(effective_contract.required_columns)
            - set(effective_contract.optional_columns)
        )
        if undeclared_columns:
            contract_failures.append(
                "columns_not_declared:" + ",".join(undeclared_columns)
            )
    if effective_contract.date_column != "auto" and effective_contract.date_column not in raw_columns:
        contract_failures.append(f"declared_date_column_missing:{effective_contract.date_column}")
    if (
        effective_contract.grain == "weekly_store_sku"
        and effective_contract.date_column == "transaction_date"
    ):
        contract_failures.append("weekly_grain_declared_with_transaction_date")
    if (
        effective_contract.grain == "daily_store_sku"
        and effective_contract.date_column == "week_end_date"
    ):
        contract_failures.append("daily_grain_declared_with_week_end_date")
    missing_declared_promotion = sorted(
        set(effective_contract.promotion_signal_columns) - columns
    )
    if missing_declared_promotion:
        contract_failures.extend(
            f"declared_promotion_column_missing:{column}" for column in missing_declared_promotion
        )
    if effective_contract.zero_units_meaning == "not_declared" and contract_mode != "explicit":
        contract_warnings.append("zero_units_meaning_not_declared")
    privacy_columns = sorted(
        column
        for column in columns
        if any(token in column for token in PII_TOKENS)
    )
    report: dict[str, Any] = {
        "dataset": "partner-data-intake",
        "contract_version": effective_contract.contract_version,
        "contract_mode": contract_mode,
        "contract_grain": effective_contract.grain,
        "contract_failures": contract_failures,
        "contract_warnings": contract_warnings,
        "contract_ready": not contract_failures,
        "contract": effective_contract.model_dump(mode="json"),
        "expected_grain": "date × store_id × sku_id",
        "rows": len(working),
        "columns": sorted(columns),
        "column_mapping": column_mapping,
        "missing_required_columns": missing_required,
        "duplicate_column_names": duplicate_columns,
        "unexpected_columns": sorted(columns - set(CUSTOMER_REQUIRED_COLUMNS) - OPTIONAL_COLUMNS),
        "privacy_columns": privacy_columns,
        "max_rows": max_rows,
        "oversized_row_count": len(working) > max_rows,
        "empty": working.empty,
        "date_parse_errors": None,
        "missing_identifier_rows": {"store_id": None, "sku_id": None},
        "duplicate_grain_rows": None,
        "numeric_parse_errors": {},
        "missing_numeric_rows": {},
        "negative_value_rows": {},
        "invalid_binary_rows": {},
        "date_min": None,
        "date_max": None,
        "has_promotion_signal": False,
        "has_economics_fields": False,
        "economics_ready": False,
        "economics_readiness_status": "not_assessed",
        "economics_missing_fields": [],
        "economics_readiness_message": "",
        "has_inventory_signal": False,
        "warnings": [],
    }
    if duplicate_columns:
        report["warnings"].append("Duplicate normalized column names require manual mapping review.")
    if privacy_columns:
        report["warnings"].append("Potential personal-data columns require removal or privacy review.")
    if missing_required or duplicate_columns:
        report["status"] = "blocked_data_quality"
        report["valid"] = False
        return report
    if privacy_columns:
        report["status"] = "blocked_privacy_review"
        report["valid"] = not contract_failures
        return report
    if contract_failures:
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
    working["date"] = parsed_dates.dt.date

    for column in sorted(NUMERIC_COLUMNS & columns):
        numeric = pd.to_numeric(working[column], errors="coerce")
        report["numeric_parse_errors"][column] = int(
            (working[column].notna() & numeric.isna()).sum()
        )
        report["missing_numeric_rows"][column] = int(numeric.isna().sum())
        report["negative_value_rows"][column] = int((numeric < 0).sum())
        non_finite = numeric.notna() & ~np.isfinite(numeric)
        report["numeric_parse_errors"][column] += int(non_finite.sum())
        working[column] = numeric

    if "promotion_flag" in columns:
        flag = pd.to_numeric(working["promotion_flag"], errors="coerce")
        report["invalid_binary_rows"]["promotion_flag"] = int(
            (working["promotion_flag"].notna() & ~flag.isin([0, 1])).sum()
        )
        working["promotion_flag"] = flag
    if "stockout_flag" in columns:
        flag = pd.to_numeric(working["stockout_flag"], errors="coerce")
        report["invalid_binary_rows"]["stockout_flag"] = int(
            (working["stockout_flag"].notna() & ~flag.isin([0, 1])).sum()
        )

    report["duplicate_grain_rows"] = int(
        working.duplicated(["date", "store_id", "sku_id"]).sum()
    )
    report["has_promotion_signal"] = bool(
        ("promotion_flag" in columns and working["promotion_flag"].eq(1).any())
        or (
            "promotion_id" in columns
            and working["promotion_id"].astype("string").str.strip().fillna("").ne("").any()
        )
    )
    report["has_economics_fields"] = bool(
        set(ECONOMICS_INTAKE_COLUMNS).issubset(columns)
    )
    report["economics_missing_fields"] = sorted(set(ECONOMICS_INTAKE_COLUMNS) - columns)
    if report["economics_missing_fields"]:
        report["economics_readiness_status"] = (
            "missing_cost_data"
            if len(report["economics_missing_fields"]) == len(ECONOMICS_INTAKE_COLUMNS)
            else "partial_cost_data"
        )
        report["economics_readiness_message"] = MISSING_ECONOMICS_MESSAGE
    else:
        report["economics_readiness_status"] = "scenario_evidence_required"
        report["economics_readiness_message"] = (
            "ستون‌های بهای تمام‌شده و حاشیهٔ مشارکت موجودند؛ برای تحلیل سود پروموشن باید منبع و "
            "اعتبار این اعداد و نیز قیمت کمپین، هزینه‌های ثابت و متغیر، کمک تأمین‌کننده، بودجه، "
            "موجودی و تقاضای مبنا و پیش‌بینی‌شده تأیید شوند."
        )
    report["has_inventory_signal"] = bool(
        {"inventory_on_hand", "stockout_flag"}.intersection(columns)
    )

    fatal_values = [
        report["empty"],
        report["oversized_row_count"],
        report["date_parse_errors"],
        *report["missing_identifier_rows"].values(),
        report["duplicate_grain_rows"],
        *report["numeric_parse_errors"].values(),
        report["missing_numeric_rows"].get("units", 0),
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
    if report["economics_missing_fields"]:
        report["warnings"].append(
            MISSING_ECONOMICS_MESSAGE
        )
    else:
        report["warnings"].append(
            "Cost and margin columns alone do not satisfy the Phase 8 scenario-evidence contract."
        )
    return report
