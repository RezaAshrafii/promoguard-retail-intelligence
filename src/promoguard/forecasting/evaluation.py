"""Time-aware forecasting baselines and rolling-origin evaluation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from promoguard.data.grain import normalize_required_identifiers

GROUP_COLUMNS = ["store_id", "upc"]
REQUIRED_PANEL_COLUMNS = ["week_end_date", "store_id", "upc", "units", "promotion_flag"]


@dataclass(frozen=True)
class TimeSplit:
    """One expanding-window forecast split."""

    fold: int
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    train_weeks: int
    test_weeks: int


def prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the minimum weekly panel required by the baselines."""
    missing = sorted(set(REQUIRED_PANEL_COLUMNS) - set(panel.columns))
    if missing:
        raise ValueError(f"Forecast panel is missing required columns: {', '.join(missing)}")
    result = panel[REQUIRED_PANEL_COLUMNS].copy()
    result = normalize_required_identifiers(result, context="Forecast panel")
    result["week_end_date"] = pd.to_datetime(result["week_end_date"], errors="coerce")
    if result["week_end_date"].isna().any():
        raise ValueError("Forecast panel contains invalid week_end_date values.")
    if result["units"].isna().any() or (result["units"] < 0).any():
        raise ValueError("Forecast panel units must be present and non-negative.")
    if not result["promotion_flag"].isin([0, 1]).all():
        raise ValueError("Forecast panel promotion_flag must contain only 0 or 1.")
    if result.duplicated(GROUP_COLUMNS + ["week_end_date"]).any():
        raise ValueError("Forecast panel contains duplicate store_id × upc × week rows.")
    return result.sort_values(GROUP_COLUMNS + ["week_end_date"]).reset_index(drop=True)


def make_rolling_splits(
    weeks: Iterable[pd.Timestamp],
    *,
    min_train_weeks: int = 104,
    horizon: int = 4,
    step: int = 8,
    max_folds: int = 6,
) -> list[TimeSplit]:
    """Create expanding-window splits from an ordered global weekly calendar."""
    ordered = pd.Series(pd.to_datetime(list(weeks))).drop_duplicates().sort_values().tolist()
    if min_train_weeks < 1 or horizon < 1 or step < 1 or max_folds < 1:
        raise ValueError("min_train_weeks, horizon, step, and max_folds must be positive.")
    if len(ordered) < min_train_weeks + horizon:
        raise ValueError("Not enough weeks for the requested train window and forecast horizon.")

    splits: list[TimeSplit] = []
    cutoff_index = min_train_weeks - 1
    while cutoff_index + horizon < len(ordered) and len(splits) < max_folds:
        test_start_index = cutoff_index + 1
        test_end_index = cutoff_index + horizon
        splits.append(
            TimeSplit(
                fold=len(splits) + 1,
                train_end=pd.Timestamp(ordered[cutoff_index]),
                test_start=pd.Timestamp(ordered[test_start_index]),
                test_end=pd.Timestamp(ordered[test_end_index]),
                train_weeks=cutoff_index + 1,
                test_weeks=horizon,
            )
        )
        cutoff_index += step
    if not splits:
        raise ValueError("No valid rolling-origin split could be constructed.")
    return splits


def _lag_lookup(
    current: pd.DataFrame,
    history: pd.DataFrame,
    lag_weeks: int,
) -> pd.Series:
    """Look up historical units at an exact weekly lag without using future rows."""
    left = current[GROUP_COLUMNS + ["week_end_date"]].copy()
    left["source_week"] = left["week_end_date"] - pd.Timedelta(weeks=lag_weeks)
    right = history[GROUP_COLUMNS + ["week_end_date", "units"]].rename(
        columns={"week_end_date": "source_week", "units": "source_units"}
    )
    merged = left.merge(
        right,
        on=GROUP_COLUMNS + ["source_week"],
        how="left",
        validate="many_to_one",
    )
    return merged["source_units"]


def _recursive_naive_predictions(test: pd.DataFrame, history: pd.DataFrame) -> pd.Series:
    """Forecast with persistence, recursively extending predictions across the horizon."""
    ordered_test = test[GROUP_COLUMNS + ["week_end_date"]].copy()
    ordered_test = ordered_test.sort_values(GROUP_COLUMNS + ["week_end_date"])
    history_lookup = history.set_index(GROUP_COLUMNS + ["week_end_date"])["units"].to_dict()
    last_history = (
        history.sort_values("week_end_date")
        .groupby(GROUP_COLUMNS)
        .tail(1)
        .set_index(GROUP_COLUMNS)["units"]
        .to_dict()
    )
    predictions: dict[tuple[Any, ...], float] = {}
    output: dict[tuple[Any, ...], float] = {}
    for row in ordered_test.itertuples(index=False):
        store_id, upc, week_end_date = row
        group = (store_id, upc)
        source_week = week_end_date - pd.Timedelta(weeks=1)
        key = (*group, source_week)
        prediction = history_lookup.get(key)
        if prediction is None:
            prediction = predictions.get(key)
        if prediction is None:
            prediction = last_history.get(group)
        key_with_week = (*group, week_end_date)
        predictions[key_with_week] = prediction
        output[key_with_week] = prediction
    return pd.Series(
        [output.get((row.store_id, row.upc, row.week_end_date)) for row in test.itertuples()],
        index=test.index,
        dtype="float64",
    )


def _training_scales(history: pd.DataFrame, seasonal_period: int) -> tuple[pd.DataFrame, pd.DataFrame, float, float]:
    """Calculate per-series MASE and interval scales using training rows only."""
    ordered = history.sort_values(GROUP_COLUMNS + ["week_end_date"]).copy()
    ordered["previous_units"] = ordered.groupby(GROUP_COLUMNS, sort=False)["units"].shift(1)
    ordered["previous_week_end_date"] = ordered.groupby(GROUP_COLUMNS, sort=False)[
        "week_end_date"
    ].shift(1)
    consecutive_week = (ordered["week_end_date"] - ordered["previous_week_end_date"]).dt.days.eq(7)
    naive_diffs = (ordered["units"] - ordered["previous_units"]).abs().where(consecutive_week)
    scales = (
        ordered.assign(absolute_difference=naive_diffs)
        .groupby(GROUP_COLUMNS, as_index=False)["absolute_difference"]
        .mean()
        .rename(columns={"absolute_difference": "mase_scale"})
    )
    global_mase_scale = float(naive_diffs.dropna().mean()) if naive_diffs.notna().any() else 0.0

    seasonal_source = history.copy()
    seasonal_source["source_week"] = seasonal_source["week_end_date"] - pd.Timedelta(
        weeks=seasonal_period
    )
    lagged = seasonal_source.merge(
        history[GROUP_COLUMNS + ["week_end_date", "units"]].rename(
            columns={"week_end_date": "source_week", "units": "source_units"}
        ),
        on=GROUP_COLUMNS + ["source_week"],
        how="left",
        validate="many_to_one",
    )
    residuals = (lagged["units"] - lagged["source_units"]).abs()
    global_interval_scale = float(residuals.dropna().quantile(0.9)) if residuals.notna().any() else 0.0
    interval_scales = (
        lagged.assign(absolute_residual=residuals)
        .groupby(GROUP_COLUMNS, as_index=False)["absolute_residual"]
        .quantile(0.9)
        .rename(columns={"absolute_residual": "interval_half_width"})
    )
    return scales, interval_scales, global_mase_scale, global_interval_scale


def forecast_split(
    panel: pd.DataFrame,
    split: TimeSplit,
    *,
    seasonal_period: int = 52,
    exclude_promotions: bool = True,
) -> pd.DataFrame:
    """Forecast one test window using only rows available at the split cutoff."""
    prepared = prepare_panel(panel)
    history = prepared[prepared["week_end_date"] <= split.train_end].copy()
    if exclude_promotions:
        history = history[history["promotion_flag"].eq(0)].copy()
    test = prepared[
        (prepared["week_end_date"] >= split.test_start)
        & (prepared["week_end_date"] <= split.test_end)
    ].copy()
    if test.empty:
        raise ValueError(f"Fold {split.fold} has no test rows.")

    seasonal = _lag_lookup(test, history, seasonal_period)
    naive = _recursive_naive_predictions(test, history)
    scales, interval_scales, global_mase_scale, global_interval_scale = _training_scales(
        history, seasonal_period
    )
    result = test.reset_index(drop=True)
    result["seasonal_naive_52"] = seasonal.reset_index(drop=True)
    result["naive_1"] = naive.reset_index(drop=True)
    result = result.merge(scales, on=GROUP_COLUMNS, how="left", validate="many_to_one")
    result = result.merge(
        interval_scales, on=GROUP_COLUMNS, how="left", validate="many_to_one"
    )
    result["mase_scale"] = result["mase_scale"].fillna(global_mase_scale)
    result["interval_half_width"] = result["interval_half_width"].fillna(global_interval_scale)
    result["seasonal_lower"] = (result["seasonal_naive_52"] - result["interval_half_width"]).clip(
        lower=0
    )
    result["seasonal_upper"] = result["seasonal_naive_52"] + result["interval_half_width"]
    result["fold"] = split.fold
    return result


def _metric_dict(frame: pd.DataFrame, prediction_column: str, *, interval: bool = False) -> dict[str, Any]:
    """Compute transparent forecast metrics for a frame."""
    valid = frame[frame[prediction_column].notna()].copy()
    if valid.empty:
        return {"n": 0, "wape": None, "mase": None, "bias": None, "interval_coverage": None}
    errors = valid[prediction_column] - valid["units"]
    absolute_errors = errors.abs()
    actual_total = float(valid["units"].abs().sum())
    wape = float(absolute_errors.sum() / actual_total) if actual_total else None
    bias = float(errors.sum() / actual_total) if actual_total else None
    series = (
        valid.assign(absolute_error=absolute_errors)
        .groupby(GROUP_COLUMNS)
        .agg(mae=("absolute_error", "mean"), scale=("mase_scale", "first"))
    )
    usable_scales = series[series["scale"] > 0]
    mase = float((usable_scales["mae"] / usable_scales["scale"]).mean()) if not usable_scales.empty else None
    coverage = None
    if interval:
        covered = valid["units"].between(valid["seasonal_lower"], valid["seasonal_upper"])
        coverage = float(covered.mean())
    return {
        "n": len(valid),
        "wape": wape,
        "mase": mase,
        "bias": bias,
        "interval_coverage": coverage,
    }


def _segment_metrics(predictions: pd.DataFrame, segment: str) -> list[dict[str, Any]]:
    """Return seasonal-naive metrics by SKU or store for an interpretable table."""
    rows: list[dict[str, Any]] = []
    for value, group in predictions.groupby(segment, dropna=False):
        metrics = _metric_dict(group, "seasonal_naive_52", interval=True)
        rows.append({"segment": segment, "value": str(value), **metrics})
    return rows


def _paired_eligibility_summary(
    non_promotion: pd.DataFrame,
    splits: list[TimeSplit],
) -> dict[str, Any]:
    """Explain how much of each test fold supports a paired model comparison."""
    fold_rows: list[dict[str, Any]] = []
    total_reasons = {
        "missing_seasonal_only": 0,
        "missing_naive_only": 0,
        "missing_both_predictions": 0,
    }
    for split in splits:
        fold = non_promotion[non_promotion["fold"].eq(split.fold)]
        seasonal_available = fold["seasonal_naive_52"].notna()
        naive_available = fold["naive_1"].notna()
        paired = seasonal_available & naive_available
        reasons = {
            "missing_seasonal_only": int((~seasonal_available & naive_available).sum()),
            "missing_naive_only": int((seasonal_available & ~naive_available).sum()),
            "missing_both_predictions": int((~seasonal_available & ~naive_available).sum()),
        }
        for reason, count in reasons.items():
            total_reasons[reason] += count
        eligible_rows = len(fold)
        paired_rows = int(paired.sum())
        fold_rows.append(
            {
                "fold": split.fold,
                "non_promotion_test_rows": eligible_rows,
                "paired_rows": paired_rows,
                "paired_coverage_ratio": paired_rows / eligible_rows if eligible_rows else None,
                "rows_excluded": eligible_rows - paired_rows,
                "exclusion_reasons": reasons,
            }
        )

    total_rows = len(non_promotion)
    paired_rows = total_rows - sum(total_reasons.values())
    return {
        "definition": (
            "Paired rows are non-promotion test rows with both seasonal-naive and "
            "recursive-naive predictions available."
        ),
        "non_promotion_rows_in_test_windows": total_rows,
        "paired_rows_scored_for_both_models": paired_rows,
        "paired_coverage_ratio": paired_rows / total_rows if total_rows else None,
        "rows_excluded_from_paired_comparison": total_rows - paired_rows,
        "exclusion_reasons": total_reasons,
        "folds": fold_rows,
    }


def evaluate_backtest(
    panel: pd.DataFrame,
    *,
    min_train_weeks: int = 104,
    horizon: int = 4,
    step: int = 8,
    max_folds: int = 6,
    seasonal_period: int = 52,
    exclude_promotions: bool = True,
) -> dict[str, Any]:
    """Run both baselines and return JSON-safe evidence plus readable tables."""
    prepared = prepare_panel(panel)
    splits = make_rolling_splits(
        prepared["week_end_date"].unique(),
        min_train_weeks=min_train_weeks,
        horizon=horizon,
        step=step,
        max_folds=max_folds,
    )
    predictions = pd.concat(
        [forecast_split(prepared, split, seasonal_period=seasonal_period, exclude_promotions=exclude_promotions) for split in splits],
        ignore_index=True,
    )
    non_promotion = predictions[predictions["promotion_flag"].eq(0)].copy()
    eligibility = _paired_eligibility_summary(non_promotion, splits)
    evaluated = non_promotion[
        non_promotion["seasonal_naive_52"].notna()
        & non_promotion["naive_1"].notna()
    ].copy()
    model_names = [("seasonal_naive_52", True), ("naive_1", False)]
    models: dict[str, Any] = {}
    table_rows: list[dict[str, Any]] = []
    for model_name, has_interval in model_names:
        fold_metrics = []
        for split in splits:
            fold = evaluated[evaluated["fold"].eq(split.fold)]
            metrics = _metric_dict(fold, model_name, interval=has_interval)
            fold_metrics.append({"fold": split.fold, **metrics})
            table_rows.append({"scope": f"fold_{split.fold}", "model": model_name, **metrics})
        overall = _metric_dict(evaluated, model_name, interval=has_interval)
        table_rows.append({"scope": "overall", "model": model_name, **overall})
        models[model_name] = {"folds": fold_metrics, "overall": overall}

    seasonal_wape = models["seasonal_naive_52"]["overall"]["wape"]
    naive_wape = models["naive_1"]["overall"]["wape"]
    comparison = {
        "wape_improvement_of_seasonal_vs_naive": (
            float(naive_wape - seasonal_wape) if seasonal_wape is not None and naive_wape is not None else None
        ),
        "interpretation": "positive means seasonal-naive has lower WAPE; this is forecast evidence, not causal promotion impact.",
    }
    return {
        "dataset": "dunnhumby-breakfast-at-the-frat",
        "evaluation_target": "non-promotion rows only",
        "training_history": "promotion rows excluded; MASE scale uses consecutive weekly non-promotion pairs only",
        "eligibility": eligibility,
        "configuration": {
            "seasonal_period_weeks": seasonal_period,
            "min_train_weeks": min_train_weeks,
            "horizon_weeks": horizon,
            "step_weeks": step,
            "max_folds": max_folds,
            "folds_evaluated": len(splits),
            "mase_scale_pairing": "same series, non-promotion observations exactly 7 days apart",
        },
        "splits": [asdict(split) | {key: value.isoformat() for key, value in asdict(split).items() if isinstance(value, pd.Timestamp)} for split in splits],
        "models": models,
        "comparison": comparison,
        "segment_metrics": {"upc": _segment_metrics(evaluated, "upc"), "store_id": _segment_metrics(evaluated, "store_id")},
        "table_rows": table_rows,
    }
