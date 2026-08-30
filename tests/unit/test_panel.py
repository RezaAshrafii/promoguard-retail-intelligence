from __future__ import annotations

import pandas as pd
import pytest

from promoguard.data.panel import load_weekly_panel, validate_canonical_panel


def canonical_panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "week_end_date": ["2024-01-07", "2024-01-14"],
            "store_id": ["1", "1"],
            "upc": ["10", "10"],
            "units": [10.0, 12.0],
            "promotion_flag": [0, 1],
        }
    )


def test_valid_panel_returns_application_metrics() -> None:
    report = validate_canonical_panel(canonical_panel())
    assert report["valid"] is True
    assert report["rows"] == 2
    assert report["series"] == 1
    assert report["promotion_rows"] == 1
    assert report["date_min"] == "2024-01-07"


@pytest.mark.parametrize(
    ("mutation", "field"),
    [
        (lambda frame: frame.drop(columns="units"), "missing_required_columns"),
        (lambda frame: frame.assign(units=[-1, 2]), "negative_units_rows"),
        (lambda frame: frame.assign(promotion_flag=[0, 2]), "invalid_promotion_rows"),
        (lambda frame: pd.concat([frame, frame.iloc[[0]]]), "duplicate_grain_rows"),
    ],
)
def test_invalid_panel_is_blocked(mutation, field: str) -> None:
    report = validate_canonical_panel(mutation(canonical_panel()))
    assert report["valid"] is False
    assert report[field]


def test_row_safety_limit_is_enforced() -> None:
    report = validate_canonical_panel(canonical_panel(), max_rows=1)
    assert report["oversized_row_count"] is True
    assert report["valid"] is False


def test_loader_resolves_processed_directory(tmp_path) -> None:
    canonical_panel().to_csv(tmp_path / "weekly_panel.csv", index=False)
    loaded = load_weekly_panel(tmp_path)
    assert len(loaded) == 2


def test_loader_rejects_missing_panel(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Weekly panel not found"):
        load_weekly_panel(tmp_path)
