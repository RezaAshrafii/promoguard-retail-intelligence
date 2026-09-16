from __future__ import annotations

import pandas as pd

from promoguard.data.intake import assess_partner_intake


def valid_partner_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-02"],
            "store_id": ["s1", "s1"],
            "sku_id": ["p1", "p1"],
            "units": [10, 12],
            "regular_price": [100, 100],
            "selling_price": [90, 100],
            "promotion_flag": [1, 0],
            "unit_cost": [60, 60],
            "contribution_margin": [30, 40],
            "stockout_flag": [0, 0],
        }
    )


def test_partner_intake_is_ready_for_observational_audit() -> None:
    report = assess_partner_intake(valid_partner_frame())

    assert report["valid"] is True
    assert report["status"] == "ready_for_observational_audit"
    assert report["has_promotion_signal"] is True
    assert report["has_economics_fields"] is True
    assert report["economics_ready"] is False
    assert report["has_inventory_signal"] is True


def test_partner_intake_accepts_documented_common_aliases() -> None:
    frame = valid_partner_frame().rename(
        columns={"date": "week_end_date", "sku_id": "UPC", "store_id": "STORE_NUM"}
    )
    report = assess_partner_intake(frame)

    assert report["valid"] is True
    assert report["status"] == "ready_for_observational_audit"


def test_partner_intake_downgrades_when_promotion_signal_is_absent() -> None:
    frame = valid_partner_frame().drop(
        columns=["regular_price", "selling_price", "promotion_flag"]
    )
    report = assess_partner_intake(frame)

    assert report["valid"] is True
    assert report["status"] == "limited_observational_report"
    assert report["has_promotion_signal"] is False


def test_partner_intake_blocks_duplicate_grain() -> None:
    frame = pd.concat([valid_partner_frame(), valid_partner_frame().iloc[[0]]], ignore_index=True)
    report = assess_partner_intake(frame)

    assert report["valid"] is False
    assert report["status"] == "blocked_data_quality"
    assert report["duplicate_grain_rows"] == 1


def test_partner_intake_blocks_personal_data_for_review() -> None:
    frame = valid_partner_frame().assign(customer_phone=["0912", "0913"])
    report = assess_partner_intake(frame)

    assert report["valid"] is True
    assert report["status"] == "blocked_privacy_review"
    assert "customer_phone" in report["privacy_columns"]


def test_partner_intake_blocks_missing_required_columns() -> None:
    report = assess_partner_intake(valid_partner_frame().drop(columns=["units"]))

    assert report["valid"] is False
    assert report["status"] == "blocked_data_quality"
    assert report["missing_required_columns"] == ["units"]


def test_empty_export_is_not_ready() -> None:
    report = assess_partner_intake(valid_partner_frame().iloc[:0])
    assert report["status"] == "blocked_data_quality"
    assert report["empty"] is True


def test_missing_units_are_blocked() -> None:
    report = assess_partner_intake(valid_partner_frame().assign(units=[None, 12]))
    assert report["status"] == "blocked_data_quality"
    assert report["missing_numeric_rows"]["units"] == 1


def test_all_zero_or_null_promotion_downgrades_audit() -> None:
    for flag_values in ([0, 0], [None, None]):
        report = assess_partner_intake(valid_partner_frame().assign(promotion_flag=flag_values))
        assert report["status"] == "limited_observational_report"
        assert report["has_promotion_signal"] is False


def test_price_columns_alone_do_not_identify_a_promotion() -> None:
    frame = valid_partner_frame().drop(columns="promotion_flag")
    report = assess_partner_intake(frame)
    assert report["status"] == "limited_observational_report"


def test_duplicate_calendar_day_after_date_parsing_is_blocked() -> None:
    frame = valid_partner_frame().assign(date=["2025-01-01", "2025-01-01T00:00:00"])
    report = assess_partner_intake(frame)
    assert report["duplicate_grain_rows"] == 1
    assert report["status"] == "blocked_data_quality"


def test_string_binary_flags_are_parsed_for_csv_exports() -> None:
    frame = valid_partner_frame().assign(promotion_flag=["1", "0"])
    report = assess_partner_intake(frame)
    assert report["status"] == "ready_for_observational_audit"


def test_duplicate_normalized_names_return_blocked_report_without_crash() -> None:
    frame = valid_partner_frame().assign(UPC=["x", "y"])
    report = assess_partner_intake(frame)
    assert report["status"] == "blocked_data_quality"
    assert report["duplicate_column_names"] == ["sku_id"]
