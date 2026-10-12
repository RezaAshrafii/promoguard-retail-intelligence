"""Adversarial input checks; fixtures are test-only, not business evidence."""
from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from promoguard.data.panel import read_panel_csv, validate_canonical_panel
from promoguard.insights.promotion_audit import (
    AuditPolicy,
    audit_promotion_event,
    detect_promotion_episodes,
)


def panel() -> pd.DataFrame:
    return pd.DataFrame({
        "week_end_date": pd.date_range("2024-01-07", periods=20, freq="7D"),
        "store_id": "001", "upc": "00010", "units": [10.] * 12 + [30.] * 2 + [10.] * 6,
        "promotion_flag": [0] * 12 + [1] * 2 + [0] * 6,
        "inventory_on_hand": 100.,
    })


@pytest.mark.parametrize("value", ["broken", -1, np.inf, -np.inf])
def test_bad_inventory_is_rejected_before_analysis(value):
    frame = panel().assign(inventory_on_hand=value)
    assert validate_canonical_panel(frame)["valid"] is False
    with pytest.raises(ValueError, match="inventory_on_hand"):
        detect_promotion_episodes(frame)


@pytest.mark.parametrize("value", [None, np.nan, "", "  "])
def test_missing_inventory_is_not_zero_or_observed_stock(value):
    frame = panel().assign(inventory_on_hand=value)
    assert validate_canonical_panel(frame)["valid"] is True
    result = audit_promotion_event(frame, store_id="001", upc="00010", start_date="2024-03-31",
                                  policy=AuditPolicy(audit_min_history_weeks=8))
    assert "STOCKOUT_UNOBSERVABLE" in {warning.code for warning in result.warnings}
    assert "STOCKOUT_RISK" not in {warning.code for warning in result.warnings}


def test_partial_inventory_preserves_both_missing_and_zero_warnings():
    frame = panel()
    frame.loc[12, "inventory_on_hand"] = np.nan
    frame.loc[13, "inventory_on_hand"] = 0
    result = audit_promotion_event(frame, store_id="001", upc="00010", start_date="2024-03-31")
    assert {"STOCKOUT_UNOBSERVABLE", "STOCKOUT_RISK"} <= {w.code for w in result.warnings}


def test_whitespace_headers_roundtrip_preserves_identifier_zeroes():
    frame = panel().rename(columns=lambda name: f" {name} ")
    assert validate_canonical_panel(frame)["valid"] is True
    assert len(detect_promotion_episodes(frame)) == 1
    restored = read_panel_csv(BytesIO(frame.to_csv(index=False).encode()))
    assert restored["store_id"].iloc[0] == "001"
    assert restored["upc"].iloc[0] == "00010"
    assert len(detect_promotion_episodes(restored)) == 1


def test_colliding_trimmed_headers_are_never_silently_merged():
    frame = panel()
    frame[" units "] = 999
    assert validate_canonical_panel(frame)["valid"] is False
    with pytest.raises(ValueError, match="duplicate"):
        detect_promotion_episodes(frame)
