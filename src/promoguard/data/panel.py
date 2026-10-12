"""Canonical weekly-panel loading and quality checks for application adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from promoguard.data.grain import (
    missing_identifier_counts,
    normalize_identifier_values,
)

REQUIRED_CANONICAL_COLUMNS = {
    "week_end_date",
    "store_id",
    "upc",
    "units",
    "promotion_flag",
}
CANONICAL_GRAIN = ["week_end_date", "store_id", "upc"]


def normalize_panel_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Use the same header normalization for validation and domain analysis."""
    names = [str(column).strip() for column in frame.columns]
    if len(names) != len(set(names)):
        raise ValueError("Panel contains duplicate normalized column names.")
    result = frame.copy()
    result.columns = names
    return result


def parse_inventory_values(values: pd.Series) -> tuple[pd.Series, int, int]:
    """Distinguish missing inventory from malformed, negative, or infinite values."""
    missing = values.isna() | values.astype("string").str.strip().eq("").fillna(False)
    numeric = pd.to_numeric(values, errors="coerce")
    invalid = ~missing & (numeric.isna() | ~np.isfinite(numeric) | numeric.lt(0))
    return numeric, int(invalid.sum()), int(missing.sum())


def read_panel_csv(source: Any) -> pd.DataFrame:
    """Preserve identifier strings even when a CSV header contains whitespace."""
    header = pd.read_csv(source, nrows=0)
    if hasattr(source, "seek"):
        source.seek(0)
    identifiers = {
        column: "string" for column in header.columns
        if str(column).strip() in {"store_id", "upc"}
    }
    frame = pd.read_csv(source, dtype=identifiers)
    # Preserve collisions for the structured quality report; never analyze this frame.
    names = [str(column).strip() for column in frame.columns]
    return normalize_panel_columns(frame) if len(names) == len(set(names)) else frame


def resolve_weekly_panel(input_path: str | Path) -> Path:
    """Resolve either a direct CSV or a processed directory to weekly_panel.csv."""
    path = Path(input_path)
    candidate = path / "weekly_panel.csv" if path.is_dir() else path
    if not candidate.exists():
        raise FileNotFoundError(f"Weekly panel not found: {candidate}")
    if candidate.suffix.lower() != ".csv":
        raise ValueError("Weekly panel input must be a CSV file or processed-data directory.")
    return candidate


def load_weekly_panel(input_path: str | Path, *, max_bytes: int | None = None) -> pd.DataFrame:
    """Load a canonical panel with an optional byte-size safety limit."""
    panel_path = resolve_weekly_panel(input_path)
    if max_bytes is not None and panel_path.stat().st_size > max_bytes:
        raise ValueError(
            f"Weekly panel is {panel_path.stat().st_size} bytes; limit is {max_bytes} bytes."
        )
    try:
        return read_panel_csv(panel_path)
    except pd.errors.EmptyDataError as error:
        raise ValueError("Weekly panel CSV is empty.") from error
    except (pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError("Weekly panel CSV is malformed or has unsupported encoding.") from error


def validate_canonical_panel(frame: pd.DataFrame, *, max_rows: int = 1_000_000) -> dict[str, Any]:
    """Return a compact quality report for the application-facing weekly panel."""
    normalized_columns = [str(column).strip() for column in frame.columns]
    columns = set(normalized_columns)
    duplicate_column_names = sorted(
        {column for column in normalized_columns if normalized_columns.count(column) > 1}
    )
    missing_columns = sorted(REQUIRED_CANONICAL_COLUMNS - columns)
    report: dict[str, Any] = {
        "dataset": "canonical-weekly-panel",
        "grain": "week_end_date × store_id × upc",
        "rows": len(frame),
        "columns": sorted(columns),
        "missing_required_columns": missing_columns,
        "duplicate_column_names": duplicate_column_names,
        "max_rows": max_rows,
        "oversized_row_count": len(frame) > max_rows,
        "empty": frame.empty,
        "date_parse_errors": None,
        "missing_store_id_rows": None,
        "missing_upc_rows": None,
        "duplicate_grain_rows": None,
        "negative_units_rows": None,
        "missing_units_rows": None,
        "non_finite_units_rows": None,
        "invalid_inventory_rows": None,
        "missing_inventory_rows": None,
        "invalid_promotion_rows": None,
        "promotion_rows": None,
        "series": None,
        "date_min": None,
        "date_max": None,
        "warnings": [],
    }
    if missing_columns or duplicate_column_names:
        report["valid"] = False
        return report

    working = normalize_panel_columns(frame)
    identifier_counts = missing_identifier_counts(working, ["store_id", "upc"])
    working["store_id"] = normalize_identifier_values(working["store_id"])
    working["upc"] = normalize_identifier_values(working["upc"])
    raw_dates = working["week_end_date"]
    parsed_dates = pd.to_datetime(raw_dates, errors="coerce", format="mixed")
    units = pd.to_numeric(working["units"], errors="coerce")
    promotions = pd.to_numeric(working["promotion_flag"], errors="coerce")
    working["week_end_date"] = parsed_dates
    working["units"] = units
    working["promotion_flag"] = promotions
    non_finite_units = units.notna() & ~np.isfinite(units)
    invalid_inventory = 0
    missing_inventory = None
    if "inventory_on_hand" in working.columns:
        _, invalid_inventory, missing_inventory = parse_inventory_values(working["inventory_on_hand"])
        if missing_inventory:
            report["warnings"].append("Inventory is missing for some rows; stockout status may be unobservable.")
    report.update(
        {
            "date_parse_errors": int(parsed_dates.isna().sum()),
            "missing_store_id_rows": identifier_counts["store_id"],
            "missing_upc_rows": identifier_counts["upc"],
            "duplicate_grain_rows": int(working.duplicated(CANONICAL_GRAIN).sum()),
            "negative_units_rows": int((units < 0).sum()),
            "missing_units_rows": int(units.isna().sum()),
            "non_finite_units_rows": int(non_finite_units.sum()),
            "invalid_inventory_rows": invalid_inventory,
            "missing_inventory_rows": missing_inventory,
            "invalid_promotion_rows": int((~promotions.isin([0, 1])).sum()),
            "promotion_rows": int(promotions.eq(1).sum()),
            "series": int(working[["store_id", "upc"]].drop_duplicates().shape[0]),
            "date_min": parsed_dates.min().date().isoformat() if parsed_dates.notna().any() else None,
            "date_max": parsed_dates.max().date().isoformat() if parsed_dates.notna().any() else None,
        }
    )
    if report["oversized_row_count"]:
        report["warnings"].append("Row count exceeds the application safety limit.")
    fatal_values = [
        report["empty"],
        report["oversized_row_count"],
        report["date_parse_errors"],
        report["missing_store_id_rows"],
        report["missing_upc_rows"],
        report["duplicate_grain_rows"],
        report["negative_units_rows"],
        report["missing_units_rows"],
        report["non_finite_units_rows"],
        report["invalid_promotion_rows"],
        report["invalid_inventory_rows"],
    ]
    report["valid"] = not any(fatal_values)
    return report
