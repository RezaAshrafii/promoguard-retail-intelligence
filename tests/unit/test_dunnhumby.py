from pathlib import Path

import pandas as pd

from promoguard.data.dunnhumby import build_weekly_panel, load_dataset, validate_transactions

FIXTURE = Path(__file__).parents[1] / "fixtures" / "dunnhumby_transactions.csv"


def valid_frame() -> pd.DataFrame:
    return pd.read_csv(FIXTURE)


def test_quality_report_accepts_valid_fixture() -> None:
    report = validate_transactions(valid_frame())
    assert report["valid"] is True
    assert report["promotion_rows"] == 1
    assert report["global_week_gaps"] == 0


def test_quality_report_flags_negative_units() -> None:
    frame = valid_frame()
    frame.loc[0, "UNITS"] = -1
    report = validate_transactions(frame)
    assert report["negative_values"]["UNITS"] == 1
    assert report["valid"] is False


def test_quality_report_flags_missing_column() -> None:
    report = validate_transactions(valid_frame().drop(columns="BASE_PRICE"))
    assert report["missing_required_columns"] == ["BASE_PRICE"]
    assert report["valid"] is False


def test_quality_report_flags_invalid_date() -> None:
    frame = valid_frame()
    frame.loc[0, "WEEK_END_DATE"] = "not-a-date"
    report = validate_transactions(frame)
    assert report["date_parse_errors"] == 1
    assert report["valid"] is False


def test_quality_report_flags_duplicate_grain() -> None:
    frame = pd.concat([valid_frame(), valid_frame().iloc[[0]]], ignore_index=True)
    report = validate_transactions(frame)
    assert report["duplicate_grain_rows"] == 1
    assert report["valid"] is False


def test_quality_report_flags_non_numeric_price() -> None:
    frame = valid_frame()
    frame["PRICE"] = frame["PRICE"].astype("object")
    frame.loc[0, "PRICE"] = "unknown"
    report = validate_transactions(frame)
    assert report["numeric_parse_errors"]["PRICE"] == 1
    assert report["valid"] is False


def test_quality_report_flags_invalid_promotion_value() -> None:
    frame = valid_frame()
    frame.loc[0, "FEATURE"] = 2
    report = validate_transactions(frame)
    assert report["invalid_promotion_values"]["FEATURE"] == 1
    assert report["valid"] is False


def test_quality_report_flags_tpr_only_conflict() -> None:
    frame = valid_frame()
    frame.loc[0, ["FEATURE", "TPR_ONLY"]] = 1
    report = validate_transactions(frame)
    assert report["promotion_flag_conflict_rows"] == 1
    assert report["valid"] is False


def test_missing_price_is_preserved_as_warning() -> None:
    frame = valid_frame()
    frame.loc[0, "PRICE"] = None
    report = validate_transactions(frame)
    assert report["numeric_missing_values"]["PRICE"] == 1
    assert report["valid"] is True
    assert report["warnings"]


def test_zero_price_promotion_is_preserved_as_warning() -> None:
    frame = valid_frame()
    frame.loc[0, ["PRICE", "SPEND"]] = 0
    report = validate_transactions(frame)
    assert report["zero_price_with_sales_rows"] == 1
    assert report["valid"] is True
    assert any("Zero-price" in warning for warning in report["warnings"])


def test_processed_directory_loader(tmp_path: Path) -> None:
    valid_frame().to_csv(tmp_path / "transactions.csv", index=False)
    frames = load_dataset(tmp_path)
    assert len(frames["transactions"]) == 2


def test_canonical_panel_derives_promotion_and_discount() -> None:
    panel = build_weekly_panel({"transactions": valid_frame()})
    assert panel.loc[0, "promotion_flag"] == 1
    assert panel.loc[0, "discount_depth"] == 0.2
    assert list(panel.columns[:3]) == ["week_end_date", "store_id", "upc"]


def test_canonical_panel_collapses_conflicting_store_lookup() -> None:
    stores = pd.DataFrame(
        {
            "STORE_ID": [101, 101],
            "STORE_NAME": ["Example", "Example"],
            "SEG_VALUE_NAME": ["MAINSTREAM", "UPSCALE"],
        }
    )
    panel = build_weekly_panel({"transactions": valid_frame(), "stores": stores})
    assert len(panel) == 2
    assert panel.loc[0, "seg_value_name"] == "MAINSTREAM | UPSCALE"


def test_price_above_base_does_not_create_negative_discount() -> None:
    frame = valid_frame()
    frame.loc[0, ["PRICE", "BASE_PRICE"]] = [3.0, 2.5]
    panel = build_weekly_panel({"transactions": frame})
    assert pd.isna(panel.loc[0, "discount_depth"])
