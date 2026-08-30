from __future__ import annotations

import pandas as pd

from promoguard.forecasting.evaluation import (
    TimeSplit,
    evaluate_backtest,
    forecast_split,
    make_rolling_splits,
    prepare_panel,
)


def panel_fixture() -> pd.DataFrame:
    weeks = pd.date_range("2024-01-07", periods=16, freq="7D")
    rows = []
    for store_id, upc, offset in [(1, 10, 0), (2, 20, 100)]:
        for index, week in enumerate(weeks):
            rows.append(
                {
                    "week_end_date": week,
                    "store_id": store_id,
                    "upc": upc,
                    "units": offset + 10 + index,
                    "promotion_flag": 0,
                }
            )
    return pd.DataFrame(rows)


def test_rolling_splits_are_temporally_ordered() -> None:
    weeks = pd.date_range("2024-01-07", periods=16, freq="7D")
    splits = make_rolling_splits(weeks, min_train_weeks=8, horizon=2, step=2, max_folds=3)
    assert len(splits) == 3
    assert all(split.train_end < split.test_start for split in splits)
    assert all(split.test_start <= split.test_end for split in splits)
    assert [split.train_weeks for split in splits] == [8, 10, 12]


def test_seasonal_prediction_uses_only_the_requested_historical_lag() -> None:
    panel = panel_fixture()
    split = make_rolling_splits(
        panel["week_end_date"].unique(), min_train_weeks=8, horizon=2, max_folds=1
    )[0]
    result = forecast_split(panel, split, seasonal_period=4, exclude_promotions=False)
    first = result[(result["store_id"] == "1") & (result["upc"] == "10")].iloc[0]
    assert first["seasonal_naive_52"] == 14
    assert first["naive_1"] == 17


def test_future_value_cannot_change_an_earlier_forecast() -> None:
    panel = panel_fixture()
    split = make_rolling_splits(
        panel["week_end_date"].unique(), min_train_weeks=8, horizon=2, max_folds=1
    )[0]
    original = forecast_split(panel, split, seasonal_period=4, exclude_promotions=False)
    changed = panel.copy()
    changed.loc[changed["week_end_date"] > split.test_end, "units"] = 999999
    rerun = forecast_split(changed, split, seasonal_period=4, exclude_promotions=False)
    assert original["seasonal_naive_52"].equals(rerun["seasonal_naive_52"])
    assert original["naive_1"].equals(rerun["naive_1"])


def test_mase_scale_uses_only_consecutive_non_promotion_weeks() -> None:
    weeks = pd.date_range("2024-01-07", periods=5, freq="7D")
    panel = pd.DataFrame(
        {
            "week_end_date": weeks,
            "store_id": 1,
            "upc": 10,
            "units": [10.0, 999.0, 20.0, 22.0, 25.0],
            "promotion_flag": [0, 1, 0, 0, 0],
        }
    )
    split = TimeSplit(
        fold=1,
        train_end=weeks[3],
        test_start=weeks[4],
        test_end=weeks[4],
        train_weeks=4,
        test_weeks=1,
    )

    result = forecast_split(panel, split, seasonal_period=2, exclude_promotions=True)

    assert result.iloc[0]["mase_scale"] == 2.0


def test_forecast_domain_rejects_blank_grain_identifier() -> None:
    panel = panel_fixture()
    panel.loc[0, "store_id"] = None

    try:
        prepare_panel(panel)
    except ValueError as error:
        assert "store_id=1" in str(error)
    else:
        raise AssertionError("Missing store_id must be rejected before forecasting.")


def test_backtest_returns_baselines_and_segment_metrics() -> None:
    result = evaluate_backtest(
        panel_fixture(),
        min_train_weeks=8,
        horizon=2,
        step=2,
        max_folds=3,
        seasonal_period=4,
        exclude_promotions=False,
    )
    assert result["configuration"]["folds_evaluated"] == 3
    assert result["models"]["seasonal_naive_52"]["overall"]["n"] == 12
    assert len(result["segment_metrics"]["upc"]) == 2
    assert result["models"]["seasonal_naive_52"]["overall"]["interval_coverage"] is not None
    assert result["configuration"]["mase_scale_pairing"].endswith("exactly 7 days apart")
    assert result["eligibility"]["paired_coverage_ratio"] == 1.0
    assert len(result["eligibility"]["folds"]) == 3


def test_backtest_explains_paired_coverage_exclusions_by_fold() -> None:
    panel = panel_fixture()
    first_two_weeks = sorted(panel["week_end_date"].unique())[:2]
    panel = panel.drop(
        index=panel.loc[
            panel["store_id"].eq(2) & panel["week_end_date"].isin(first_two_weeks)
        ].index
    )

    result = evaluate_backtest(
        panel,
        min_train_weeks=4,
        horizon=1,
        step=1,
        max_folds=1,
        seasonal_period=4,
        exclude_promotions=False,
    )

    eligibility = result["eligibility"]
    assert eligibility["non_promotion_rows_in_test_windows"] == 2
    assert eligibility["paired_rows_scored_for_both_models"] == 1
    assert eligibility["paired_coverage_ratio"] == 0.5
    assert eligibility["rows_excluded_from_paired_comparison"] == 1
    assert eligibility["exclusion_reasons"] == {
        "missing_seasonal_only": 1,
        "missing_naive_only": 0,
        "missing_both_predictions": 0,
    }
    assert eligibility["folds"][0]["paired_coverage_ratio"] == 0.5
