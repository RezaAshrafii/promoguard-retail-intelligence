"""Shared canonical grain-identifier normalization and missing-value policy."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

CANONICAL_IDENTIFIER_COLUMNS = ("store_id", "upc")


def normalize_identifier_values(series: pd.Series) -> pd.Series:
    """Return nullable trimmed strings without inventing missing identifiers."""
    return series.astype("string").str.strip()


def missing_identifier_mask(series: pd.Series) -> pd.Series:
    """Treat null and whitespace-only values as missing identifiers."""
    normalized = normalize_identifier_values(series)
    return normalized.isna() | normalized.eq("").fillna(True)


def missing_identifier_counts(
    frame: pd.DataFrame,
    columns: Iterable[str],
) -> dict[str, int]:
    """Count invalid identifier rows for every available requested column."""
    return {
        column: int(missing_identifier_mask(frame[column]).sum())
        for column in columns
        if column in frame
    }


def normalize_required_identifiers(
    frame: pd.DataFrame,
    *,
    columns: Iterable[str] = CANONICAL_IDENTIFIER_COLUMNS,
    context: str,
) -> pd.DataFrame:
    """Normalize identifiers and raise before domain logic when any are empty."""
    requested = tuple(columns)
    counts = missing_identifier_counts(frame, requested)
    invalid = {column: count for column, count in counts.items() if count}
    if invalid:
        details = ", ".join(f"{column}={count}" for column, count in invalid.items())
        raise ValueError(f"{context} contains missing or blank grain identifiers: {details}.")
    result = frame.copy()
    for column in requested:
        if column in result:
            result[column] = normalize_identifier_values(result[column])
    return result
