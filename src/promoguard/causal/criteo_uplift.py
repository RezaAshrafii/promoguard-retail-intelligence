"""Chunk-safe validation and intention-to-treat summaries for Criteo Uplift v2.1.

The Criteo source is a public randomized advertising-experiment benchmark.  This module is
deliberately separate from PromoGuard's retail panel: it does not make a retail causal claim,
estimate per-user counterfactual truth, or use post-treatment ``exposure`` as a feature.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

CRITEO_UPLIFT_V21_SOURCE_URL = (
    "https://criteostorage.blob.core.windows.net/criteo-research-datasets/"
    "criteo-uplift-v2.1.csv.gz"
)
CRITEO_UPLIFT_V21_DATASET_PAGE = "https://ailab.criteo.com/criteo-uplift-prediction-dataset/"
CRITEO_UPLIFT_V21_LICENSE = "CC BY-NC-SA 4.0"
FEATURE_COLUMNS = tuple(f"f{index}" for index in range(12))
TREATMENT_COLUMN = "treatment"
OUTCOME_COLUMNS = ("visit", "conversion")
POST_TREATMENT_COLUMNS = ("exposure",)
REQUIRED_COLUMNS = (*FEATURE_COLUMNS, TREATMENT_COLUMN, *OUTCOME_COLUMNS, *POST_TREATMENT_COLUMNS)
NORMAL_95_Z = 1.959963984540054


def sha256_file(path: Path) -> str:
    """Return a checksum while keeping the source file out of memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_criteo_uplift_frame(frame: pd.DataFrame) -> dict[str, Any]:
    """Validate one in-memory chunk against the documented Criteo v2.1 contract."""
    columns = set(frame.columns)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - columns)
    unexpected_columns = sorted(columns - set(REQUIRED_COLUMNS))
    binary_invalid_counts: dict[str, int] = {}
    feature_invalid_counts: dict[str, int] = {}

    for column in (TREATMENT_COLUMN, *OUTCOME_COLUMNS, *POST_TREATMENT_COLUMNS):
        if column not in frame:
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        binary_invalid_counts[column] = int((numeric.isna() | ~numeric.isin([0, 1])).sum())

    for column in FEATURE_COLUMNS:
        if column not in frame:
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        feature_invalid_counts[column] = int((numeric.isna() | ~numeric.map(math.isfinite)).sum())

    return {
        "rows": len(frame),
        "missing_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
        "binary_invalid_counts": binary_invalid_counts,
        "feature_invalid_counts": feature_invalid_counts,
        "valid": not missing_columns
        and not unexpected_columns
        and not any(binary_invalid_counts.values())
        and not any(feature_invalid_counts.values()),
    }


def _require_valid_chunk(frame: pd.DataFrame) -> None:
    report = validate_criteo_uplift_frame(frame)
    if not report["valid"]:
        raise ValueError(f"Criteo Uplift v2.1 contract failed: {report}")


def _empty_arm_statistics() -> dict[str, dict[str, float]]:
    return {
        "treated": {"n": 0.0, "visit": 0.0, "conversion": 0.0},
        "control": {"n": 0.0, "visit": 0.0, "conversion": 0.0},
    }


def _empty_feature_statistics() -> dict[str, dict[str, dict[str, float]]]:
    return {
        feature: {
            "treated": {"n": 0.0, "sum": 0.0, "sum_squares": 0.0},
            "control": {"n": 0.0, "sum": 0.0, "sum_squares": 0.0},
        }
        for feature in FEATURE_COLUMNS
    }


def _update_statistics(
    frame: pd.DataFrame,
    arm_statistics: dict[str, dict[str, float]],
    feature_statistics: dict[str, dict[str, dict[str, float]]],
) -> None:
    treatment = frame[TREATMENT_COLUMN].astype("int8")
    for arm_name, arm_value in (("treated", 1), ("control", 0)):
        mask = treatment.eq(arm_value)
        arm = arm_statistics[arm_name]
        arm["n"] += float(mask.sum())
        for outcome in OUTCOME_COLUMNS:
            arm[outcome] += float(frame.loc[mask, outcome].sum())
        for feature in FEATURE_COLUMNS:
            values = frame.loc[mask, feature]
            feature_arm = feature_statistics[feature][arm_name]
            feature_arm["n"] += float(mask.sum())
            feature_arm["sum"] += float(values.sum())
            feature_arm["sum_squares"] += float((values * values).sum())


def _proportion_effect(treated_successes: float, treated_n: float, control_successes: float, control_n: float) -> dict[str, float]:
    if not treated_n or not control_n:
        raise ValueError("Both treatment arms must contain at least one row.")
    treated_rate = treated_successes / treated_n
    control_rate = control_successes / control_n
    estimate = treated_rate - control_rate
    standard_error = math.sqrt(
        (treated_rate * (1 - treated_rate) / treated_n)
        + (control_rate * (1 - control_rate) / control_n)
    )
    return {
        "treated_rate": treated_rate,
        "control_rate": control_rate,
        "intention_to_treat_risk_difference": estimate,
        "normal_95_ci_low": estimate - NORMAL_95_Z * standard_error,
        "normal_95_ci_high": estimate + NORMAL_95_Z * standard_error,
        "standard_error": standard_error,
    }


def _feature_balance(feature_statistics: dict[str, dict[str, dict[str, float]]]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for feature in FEATURE_COLUMNS:
        treated = feature_statistics[feature]["treated"]
        control = feature_statistics[feature]["control"]
        treated_mean = treated["sum"] / treated["n"]
        control_mean = control["sum"] / control["n"]
        treated_variance = max(
            0.0, treated["sum_squares"] / treated["n"] - treated_mean * treated_mean
        )
        control_variance = max(
            0.0, control["sum_squares"] / control["n"] - control_mean * control_mean
        )
        pooled_standard_deviation = math.sqrt((treated_variance + control_variance) / 2)
        standardized_mean_difference = (
            (treated_mean - control_mean) / pooled_standard_deviation
            if pooled_standard_deviation
            else 0.0
        )
        rows.append(
            {
                "feature": feature,
                "treated_mean": treated_mean,
                "control_mean": control_mean,
                "standardized_mean_difference": standardized_mean_difference,
            }
        )
    return rows


def summarize_criteo_uplift_chunks(chunks: Iterable[pd.DataFrame]) -> dict[str, Any]:
    """Produce a reproducible, aggregate ITT benchmark without retaining person-level data."""
    arm_statistics = _empty_arm_statistics()
    feature_statistics = _empty_feature_statistics()
    chunks_read = 0
    rows_read = 0
    for chunk in chunks:
        _require_valid_chunk(chunk)
        _update_statistics(chunk, arm_statistics, feature_statistics)
        chunks_read += 1
        rows_read += len(chunk)
    if not rows_read:
        raise ValueError("Criteo Uplift source contained no rows.")

    treated = arm_statistics["treated"]
    control = arm_statistics["control"]
    effects = {
        outcome: _proportion_effect(treated[outcome], treated["n"], control[outcome], control["n"])
        for outcome in OUTCOME_COLUMNS
    }
    balance = _feature_balance(feature_statistics)
    return {
        "benchmark": "criteo-uplift-v2.1-randomized-itt",
        "analysis_type": "aggregate intention-to-treat comparison",
        "rows_read": rows_read,
        "chunks_read": chunks_read,
        "treatment": {
            "treated_rows": int(treated["n"]),
            "control_rows": int(control["n"]),
            "treated_fraction": treated["n"] / rows_read,
        },
        "outcome_effects": effects,
        "feature_balance": balance,
        "assumptions_and_boundaries": [
            "Uses the publisher's randomized treatment assignment as the identification basis.",
            "Estimates aggregate intention-to-treat risk differences, not individual treatment effects.",
            "Does not condition on exposure because exposure is post-treatment.",
            "Does not establish a causal effect for the dunnhumby retail panel or an Iranian business.",
            "Intervals are large-sample normal approximations for binary-outcome risk differences.",
        ],
    }


def evaluate_criteo_uplift(input_path: str | Path, *, chunksize: int = 250_000) -> dict[str, Any]:
    """Stream a publisher-downloaded Criteo CSV/GZIP file and return an aggregate benchmark."""
    if chunksize <= 0:
        raise ValueError("chunksize must be positive.")
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Criteo Uplift source not found: {path}")
    result = summarize_criteo_uplift_chunks(
        pd.read_csv(path, compression="infer", chunksize=chunksize)
    )
    result["source"] = {
        "dataset_page": CRITEO_UPLIFT_V21_DATASET_PAGE,
        "download_url": CRITEO_UPLIFT_V21_SOURCE_URL,
        "license": CRITEO_UPLIFT_V21_LICENSE,
        "filename": path.name,
        "sha256": sha256_file(path),
        "raw_data_committed_to_git": False,
    }
    return result
