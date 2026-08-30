"""Ingestion and validation for dunnhumby Breakfast at the Frat."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

TRANSACTION_SHEET = "dh Transaction Data"
STORE_SHEET = "dh Store Lookup"
PRODUCT_SHEET = "dh Products Lookup"
REQUIRED_TRANSACTION_COLUMNS = {
    "WEEK_END_DATE",
    "STORE_NUM",
    "UPC",
    "UNITS",
    "VISITS",
    "HHS",
    "SPEND",
    "PRICE",
    "BASE_PRICE",
    "FEATURE",
    "DISPLAY",
    "TPR_ONLY",
}
NUMERIC_COLUMNS = ["UNITS", "VISITS", "HHS", "SPEND", "PRICE", "BASE_PRICE"]
PROMOTION_COLUMNS = ["FEATURE", "DISPLAY", "TPR_ONLY"]
GRAIN_COLUMNS = ["WEEK_END_DATE", "STORE_NUM", "UPC"]
GRAIN_COLUMNS_NORMALIZED = ["week_end_date", "store_id", "upc"]


def find_workbook(input_path: str | Path) -> Path:
    """Find the source workbook in a file or extracted directory."""
    path = Path(input_path)
    if path.is_file() and path.suffix.lower() in {".xlsx", ".xlsm"}:
        return path
    matches = sorted(path.rglob("*.xlsx")) if path.exists() else []
    if not matches:
        raise FileNotFoundError(f"No .xlsx workbook found under: {path}")
    return matches[0]


def load_workbook(input_path: str | Path) -> dict[str, pd.DataFrame]:
    """Load the three analytical sheets; row 2 contains the real headers."""
    workbook = find_workbook(input_path)
    return {
        "transactions": pd.read_excel(workbook, sheet_name=TRANSACTION_SHEET, header=1),
        "stores": pd.read_excel(workbook, sheet_name=STORE_SHEET, header=1),
        "products": pd.read_excel(workbook, sheet_name=PRODUCT_SHEET, header=1),
    }


def load_dataset(input_path: str | Path) -> dict[str, pd.DataFrame]:
    """Load either a source workbook or a previously processed directory."""
    path = Path(input_path)
    if path.is_dir() and (path / "transactions.csv").exists():
        frames = {"transactions": pd.read_csv(path / "transactions.csv")}
        for name in ("stores", "products"):
            candidate = path / f"{name}.csv"
            if candidate.exists():
                frames[name] = pd.read_csv(candidate)
        return frames
    return load_workbook(path)


def _non_numeric_counts(frame: pd.DataFrame, columns: list[str]) -> dict[str, int]:
    return {
        column: int(
            (
                frame[column].notna()
                & pd.to_numeric(frame[column], errors="coerce").isna()
            ).sum()
        )
        for column in columns
        if column in frame
    }


def _global_week_gaps(dates: pd.Series) -> int:
    unique_dates = pd.Series(pd.to_datetime(dates, errors="coerce").dropna().unique())
    valid_dates = unique_dates.sort_values()
    if len(valid_dates) < 2:
        return 0
    day_differences = valid_dates.diff().dropna().dt.days
    return int(((day_differences // 7) - 1).clip(lower=0).sum())


def validate_transactions(frame: pd.DataFrame) -> dict[str, Any]:
    """Return an auditable quality report without silently repairing business data."""
    working = frame.rename(columns=lambda column: str(column).strip()).copy()
    columns = set(working.columns)
    missing_columns = sorted(REQUIRED_TRANSACTION_COLUMNS - columns)

    date_parse_errors = None
    date_missing_values = None
    global_week_gaps = None
    if "WEEK_END_DATE" in working:
        raw_dates = working["WEEK_END_DATE"]
        parsed_dates = pd.to_datetime(raw_dates, errors="coerce", format="mixed")
        date_missing_values = int(raw_dates.isna().sum())
        date_parse_errors = int((raw_dates.notna() & parsed_dates.isna()).sum())
        global_week_gaps = _global_week_gaps(parsed_dates)
        working["WEEK_END_DATE"] = parsed_dates

    numeric_parse_errors = _non_numeric_counts(working, NUMERIC_COLUMNS)
    numeric_missing_values = {
        column: int(working[column].isna().sum())
        for column in NUMERIC_COLUMNS
        if column in working
    }
    negative_values = {
        column: int((pd.to_numeric(working[column], errors="coerce") < 0).sum())
        for column in NUMERIC_COLUMNS
        if column in working
    }

    duplicate_rows = None
    if set(GRAIN_COLUMNS).issubset(working.columns):
        duplicate_rows = int(working.duplicated(subset=GRAIN_COLUMNS).sum())

    invalid_promotion_values = {
        column: int((~working[column].isin([0, 1]) & working[column].notna()).sum())
        for column in PROMOTION_COLUMNS
        if column in working
    }
    missing_promotion_values = {
        column: int(working[column].isna().sum())
        for column in PROMOTION_COLUMNS
        if column in working
    }

    promotion_rows = 0
    promotion_flag_conflicts = 0
    if set(PROMOTION_COLUMNS).issubset(working.columns):
        promotion_rows = int(working[PROMOTION_COLUMNS].eq(1).any(axis=1).sum())
        promotion_flag_conflicts = int(
            (
                working["TPR_ONLY"].eq(1)
                & (working["FEATURE"].eq(1) | working["DISPLAY"].eq(1))
            ).sum()
        )

    price_above_base_rows = 0
    zero_price_with_sales_rows = 0
    if {"PRICE", "BASE_PRICE"}.issubset(working.columns):
        price = pd.to_numeric(working["PRICE"], errors="coerce")
        base_price = pd.to_numeric(working["BASE_PRICE"], errors="coerce")
        price_above_base_rows = int((price > base_price).sum())
        if "UNITS" in working:
            units = pd.to_numeric(working["UNITS"], errors="coerce")
            zero_price_with_sales_rows = int(((price <= 0) & (units > 0)).sum())

    fatal_counts = [
        date_parse_errors or 0,
        date_missing_values or 0,
        duplicate_rows or 0,
        promotion_flag_conflicts,
        *numeric_parse_errors.values(),
        *negative_values.values(),
        *invalid_promotion_values.values(),
        *missing_promotion_values.values(),
    ]
    warnings = []
    if any(numeric_missing_values.values()):
        warnings.append("Missing numeric values are preserved and must be handled downstream.")
    if price_above_base_rows:
        warnings.append("Some observed prices exceed base price; no discount is inferred there.")
    if zero_price_with_sales_rows:
        warnings.append("Zero-price sales are preserved as possible free promotions for review.")
    if global_week_gaps:
        warnings.append("The global weekly calendar contains gaps.")

    return {
        "dataset": "dunnhumby-breakfast-at-the-frat",
        "grain": "one row per week_end_date × store_num × upc",
        "rows": len(working),
        "columns": sorted(columns),
        "missing_required_columns": missing_columns,
        "date_parse_errors": date_parse_errors,
        "date_missing_values": date_missing_values,
        "global_week_gaps": global_week_gaps,
        "numeric_parse_errors": numeric_parse_errors,
        "numeric_missing_values": numeric_missing_values,
        "negative_values": negative_values,
        "duplicate_grain_rows": duplicate_rows,
        "invalid_promotion_values": invalid_promotion_values,
        "missing_promotion_values": missing_promotion_values,
        "promotion_flag_conflict_rows": promotion_flag_conflicts,
        "promotion_rows": promotion_rows,
        "zero_price_with_sales_rows": zero_price_with_sales_rows,
        "price_above_base_rows": price_above_base_rows,
        "warnings": warnings,
        "valid": not missing_columns and not any(fatal_counts),
    }


def _normalize_identifier(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="raise").astype("int64")
    return numeric.astype("string")


def _collapse_lookup(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    """Collapse duplicate lookup keys without arbitrarily discarding conflicting metadata."""

    def combine(values: pd.Series) -> Any:
        unique = values.dropna().drop_duplicates().tolist()
        if not unique:
            return pd.NA
        if len(unique) == 1:
            return unique[0]
        return " | ".join(sorted(str(value) for value in unique))

    return frame.groupby(key, as_index=False, dropna=False).agg(combine)


def build_weekly_panel(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build the canonical weekly panel and attach product/store metadata."""
    transactions = frames["transactions"].rename(
        columns={
            "WEEK_END_DATE": "week_end_date",
            "STORE_NUM": "store_id",
            "UPC": "upc",
            "UNITS": "units",
            "VISITS": "visits",
            "HHS": "households",
            "SPEND": "spend",
            "PRICE": "price",
            "BASE_PRICE": "base_price",
            "FEATURE": "feature",
            "DISPLAY": "display",
            "TPR_ONLY": "tpr_only",
        }
    ).copy()
    transactions["week_end_date"] = pd.to_datetime(transactions["week_end_date"])
    transactions["store_id"] = _normalize_identifier(transactions["store_id"])
    transactions["upc"] = _normalize_identifier(transactions["upc"])
    for column in ["feature", "display", "tpr_only"]:
        transactions[column] = transactions[column].astype("int8")
    transactions["promotion_flag"] = transactions[["feature", "display", "tpr_only"]].max(
        axis=1
    )
    discount_is_defined = (
        (transactions["base_price"] > 0)
        & transactions["price"].notna()
        & (transactions["price"] <= transactions["base_price"])
    )
    transactions["discount_depth"] = (
        (transactions["base_price"] - transactions["price"]) / transactions["base_price"]
    ).where(discount_is_defined)

    products = frames.get("products")
    if products is not None:
        products = products.rename(columns=lambda column: str(column).strip().lower()).copy()
        products["upc"] = _normalize_identifier(products["upc"])
        products = _collapse_lookup(products, "upc")
        transactions = transactions.merge(products, on="upc", how="left", validate="many_to_one")

    stores = frames.get("stores")
    if stores is not None:
        stores = stores.rename(columns=lambda column: str(column).strip().lower()).copy()
        stores["store_id"] = _normalize_identifier(stores["store_id"])
        stores = _collapse_lookup(stores, "store_id")
        transactions = transactions.merge(stores, on="store_id", how="left", validate="many_to_one")

    return transactions.sort_values(GRAIN_COLUMNS_NORMALIZED).reset_index(drop=True)


def sha256_file(path: Path) -> str:
    """Compute a source checksum without loading the whole file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_panel(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Convert the workbook into canonical CSVs and machine-readable evidence."""
    frames = load_workbook(input_path)
    report = validate_transactions(frames["transactions"])
    store_duplicates = int(frames["stores"].duplicated(subset="STORE_ID", keep=False).sum())
    product_duplicates = int(frames["products"].duplicated(subset="UPC", keep=False).sum())
    report["lookup_duplicate_rows"] = {
        "stores": store_duplicates,
        "products": product_duplicates,
    }
    if store_duplicates or product_duplicates:
        report["warnings"].append(
            "Duplicate lookup keys were collapsed without discarding conflicting metadata."
        )
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "quality_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    if not report["valid"]:
        raise ValueError(
            "Source data failed validation. Review quality_report.json before continuing."
        )

    for name, frame in frames.items():
        frame.to_csv(destination / f"{name}.csv", index=False)
    panel = build_weekly_panel(frames)
    panel.to_csv(destination / "weekly_panel.csv", index=False)

    workbook = find_workbook(input_path)
    provenance = {
        "dataset": "dunnhumby Breakfast at the Frat",
        "source_url": "https://www.dunnhumby.com/source-files/",
        "workbook": workbook.name,
        "workbook_sha256": sha256_file(workbook),
        "source_grain": report["grain"],
        "source_rows": report["rows"],
        "canonical_rows": len(panel),
    }
    (destination / "provenance.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )
    return {"source": str(workbook), "output_dir": str(destination), **report}
