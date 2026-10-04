"""Manager-facing evaluation of the public, randomized Hillstrom email experiment.

This module keeps the customer-level randomized benchmark separate from the retail weekly-panel
audit. It estimates assignment effects on the preselected outcome and never interprets revenue as
profit.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from pathlib import Path
from statistics import NormalDist
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

HILLSTROM_DATASET = "hillstrom-email-analytics-2008"
HILLSTROM_DATASET_PAGE = (
    "https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html"
)
HILLSTROM_DOWNLOAD_URL = (
    "http://www.minethatdata.com/"
    "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
)
HILLSTROM_LICENSE_STATUS = "No explicit dataset license found on the publisher page; do not redistribute."
HILLSTROM_SEGMENTS = ("Mens E-Mail", "Womens E-Mail", "No E-Mail")
CONTROL_SEGMENT = "No E-Mail"
TREATMENT_SEGMENTS = ("Mens E-Mail", "Womens E-Mail")
MINIMUM_ARM_SIZE_FOR_DECISION = 1_000
REQUIRED_COLUMNS = (
    "recency",
    "history_segment",
    "history",
    "mens",
    "womens",
    "zip_code",
    "newbie",
    "channel",
    "segment",
    "visit",
    "conversion",
    "spend",
)
BINARY_COLUMNS = ("mens", "womens", "newbie", "visit", "conversion")
NUMERIC_COLUMNS = ("recency", "history", "mens", "womens", "newbie", "visit", "conversion", "spend")


class HillstromAnalysisConfig(BaseModel):
    """Predeclare one primary metric and an optional business hurdle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    primary_outcome: Literal["spend", "conversion", "visit"] = "spend"
    minimum_effect_per_person: float | None = None

    @model_validator(mode="after")
    def validate_threshold(self) -> HillstromAnalysisConfig:
        if self.minimum_effect_per_person is not None and not math.isfinite(
            self.minimum_effect_per_person
        ):
            raise ValueError("minimum_effect_per_person must be finite")
        if self.primary_outcome in {"conversion", "visit"} and (
            self.minimum_effect_per_person is not None
            and not 0 <= self.minimum_effect_per_person <= 1
        ):
            raise ValueError("binary-outcome threshold must be a probability between 0 and 1")
        return self


def sha256_file(path: Path) -> str:
    """Hash a dataset without loading the file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_hillstrom_frame(frame: pd.DataFrame) -> dict[str, Any]:
    """Check the publisher schema and invariants without deduplicating customer rows."""
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    unexpected = sorted(set(frame.columns) - set(REQUIRED_COLUMNS))
    errors: list[str] = []
    if frame.empty:
        errors.append("dataset contains no rows")
    missing_values = {
        str(column): int(count)
        for column, count in frame.isna().sum().items()
        if count
    }
    if missing_values:
        errors.append(f"columns contain missing values: {missing_values}")
    if missing:
        errors.append(f"missing required columns: {missing}")
    if unexpected:
        errors.append(f"unexpected columns: {unexpected}")

    invalid_numeric: dict[str, int] = {}
    invalid_binary: dict[str, int] = {}
    if not missing:
        for column in NUMERIC_COLUMNS:
            numeric = pd.to_numeric(frame[column], errors="coerce")
            invalid_numeric[column] = int((numeric.isna() | ~np.isfinite(numeric)).sum())
        for column in BINARY_COLUMNS:
            numeric = pd.to_numeric(frame[column], errors="coerce")
            invalid_binary[column] = int((numeric.isna() | ~numeric.isin([0, 1])).sum())

        segment_invalid = int((~frame["segment"].isin(HILLSTROM_SEGMENTS)).sum())
        if segment_invalid:
            errors.append(f"segment contains {segment_invalid} unsupported labels")
        if any(invalid_numeric.values()):
            errors.append(f"numeric columns contain invalid or non-finite values: {invalid_numeric}")
        if any(invalid_binary.values()):
            errors.append(f"binary columns contain values other than 0/1: {invalid_binary}")
        spend = pd.to_numeric(frame["spend"], errors="coerce")
        conversion = pd.to_numeric(frame["conversion"], errors="coerce")
        visit = pd.to_numeric(frame["visit"], errors="coerce")
        if int((spend < 0).sum()):
            errors.append("spend contains negative values")
        if int(((conversion == 0) & (spend != 0)).sum()):
            errors.append("zero conversion rows must have zero spend")
        if int(((conversion == 1) & (spend <= 0)).sum()):
            errors.append("converted rows must have positive spend")
        if int((conversion > visit).sum()):
            errors.append("conversion cannot be 1 when visit is 0")
        empty_segments = [
            segment
            for segment in HILLSTROM_SEGMENTS
            if not bool(frame["segment"].eq(segment).any())
        ]
        if empty_segments:
            errors.append(f"required experiment arms are empty: {empty_segments}")

    duplicate_full_rows = int(frame.duplicated().sum())
    return {
        "dataset": HILLSTROM_DATASET,
        "rows": len(frame),
        "columns": list(frame.columns),
        "missing_columns": missing,
        "unexpected_columns": unexpected,
        "invalid_numeric_counts": invalid_numeric,
        "invalid_binary_counts": invalid_binary,
        "duplicate_full_rows_retained": duplicate_full_rows,
        "duplicate_note": (
            "The released file has no participant identifier; identical rows are retained because "
            "they may represent different randomized participants."
        ),
        "errors": errors,
        "valid": not errors,
    }


def load_hillstrom_csv(path: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load and validate the public CSV while retaining repeated participant profiles."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Hillstrom dataset was not found: {source}")
    frame = pd.read_csv(source)
    quality = validate_hillstrom_frame(frame)
    if not quality["valid"]:
        raise ValueError(f"Hillstrom data contract failed: {quality['errors']}")
    return frame, quality


def _welch_difference_interval(
    treatment: np.ndarray,
    control: np.ndarray,
    *,
    tail_probability: float,
) -> tuple[float, float, float, float]:
    """Compute a heteroskedastic large-sample interval for an independent mean difference."""
    estimate = float(treatment.mean() - control.mean())
    standard_error = math.sqrt(
        float(treatment.var(ddof=1) / treatment.size)
        + float(control.var(ddof=1) / control.size)
    )
    critical_value = NormalDist().inv_cdf(1 - tail_probability)
    return (
        estimate,
        standard_error,
        estimate - critical_value * standard_error,
        estimate + critical_value * standard_error,
    )


def _decision_for_threshold(
    lower: float, upper: float, threshold: float | None
) -> tuple[str, str]:
    if threshold is None:
        if lower > 0:
            return "positive_evidence_vs_zero", "The adjusted interval is entirely above zero."
        if upper < 0:
            return "negative_evidence_vs_zero", "The adjusted interval is entirely below zero."
        return "inconclusive_vs_zero", "The adjusted interval includes zero."
    if lower > threshold:
        return "goal_supported", "The adjusted interval is entirely above the declared goal."
    if upper < threshold:
        return "goal_not_supported", "The adjusted interval is entirely below the declared goal."
    return "inconclusive_vs_goal", "The adjusted interval overlaps the declared goal."


def evaluate_hillstrom_frame(
    frame: pd.DataFrame,
    config: HillstromAnalysisConfig | None = None,
    *,
    progress_callback: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Compare each randomized email arm with holdout on one predeclared outcome."""
    config = config or HillstromAnalysisConfig()
    quality = validate_hillstrom_frame(frame)
    if not quality["valid"]:
        raise ValueError(f"Hillstrom data contract failed: {quality['errors']}")

    control_frame = frame.loc[frame["segment"].eq(CONTROL_SEGMENT)]
    control = pd.to_numeric(control_frame[config.primary_outcome]).to_numpy(dtype=np.float64)
    if control.size < 2:
        raise ValueError("Control arm must contain at least two observations.")

    comparisons: list[dict[str, Any]] = []
    confidence_level = 0.95
    contrast_specs = (
        ("Mens E-Mail", "No E-Mail", "treatment_vs_control"),
        ("Womens E-Mail", "No E-Mail", "treatment_vs_control"),
        ("Mens E-Mail", "Womens E-Mail", "treatment_vs_treatment"),
    )
    comparisons_count = len(contrast_specs)
    # Bonferroni controls family-wise coverage across the two treatment-control contrasts and
    # the preplanned direct comparison of the two treatments.
    tail_probability = (1 - confidence_level) / (2 * comparisons_count)
    for index, (segment, control_segment, contrast_type) in enumerate(contrast_specs):
        if progress_callback is not None:
            progress_callback(20 + index * 20)
        treatment_frame = frame.loc[frame["segment"].eq(segment)]
        comparison_control_frame = frame.loc[frame["segment"].eq(control_segment)]
        treatment = pd.to_numeric(treatment_frame[config.primary_outcome]).to_numpy(
            dtype=np.float64
        )
        comparison_control = pd.to_numeric(
            comparison_control_frame[config.primary_outcome]
        ).to_numpy(dtype=np.float64)
        if treatment.size < 2:
            raise ValueError(f"Treatment arm {segment!r} must contain at least two observations.")
        if comparison_control.size < 2:
            raise ValueError(f"Comparison arm {control_segment!r} must contain at least two observations.")
        estimate, standard_error, lower, upper = _welch_difference_interval(
            treatment, comparison_control, tail_probability=tail_probability
        )
        enough_sample = min(treatment.size, comparison_control.size) >= MINIMUM_ARM_SIZE_FOR_DECISION
        if enough_sample:
            evidence, reason = _decision_for_threshold(
                lower,
                upper,
                config.minimum_effect_per_person
                if contrast_type == "treatment_vs_control"
                else None,
            )
        else:
            evidence = "insufficient_sample"
            reason = (
                f"At least {MINIMUM_ARM_SIZE_FOR_DECISION} assigned observations per arm are "
                "required before the manager-facing decision is shown."
            )
        treatment_mean = float(treatment.mean())
        control_mean = float(comparison_control.mean())

        descriptive_metrics: dict[str, dict[str, float]] = {}
        for metric in ("conversion", "visit", "spend"):
            treatment_metric = pd.to_numeric(treatment_frame[metric]).to_numpy(dtype=np.float64)
            control_metric = pd.to_numeric(comparison_control_frame[metric]).to_numpy(dtype=np.float64)
            descriptive_metrics[metric] = {
                "treatment_mean": float(treatment_metric.mean()),
                "control_mean": float(control_metric.mean()),
                "difference": float(treatment_metric.mean() - control_metric.mean()),
            }

        comparisons.append(
            {
                "treatment_arm": segment,
                "control_arm": control_segment,
                "contrast_type": contrast_type,
                "treatment_n": int(treatment.size),
                "control_n": int(comparison_control.size),
                "treatment_mean_per_person": treatment_mean,
                "control_mean_per_person": control_mean,
                "incremental_effect_per_person": estimate,
                "incremental_effect_per_1000_people": estimate * 1_000,
                "relative_change_percent": (
                    (estimate / control_mean) * 100 if control_mean != 0 else None
                ),
                "standard_error_per_person": standard_error,
                "familywise_ci_lower_per_person": lower,
                "familywise_ci_upper_per_person": upper,
                "familywise_confidence_level": confidence_level,
                "multiplicity_method": "Welch normal approximation; Bonferroni across three preplanned campaign contrasts",
                "business_goal_status": (
                    "not_applicable_variant_comparison"
                    if contrast_type == "treatment_vs_treatment"
                    else "insufficient_sample"
                    if not enough_sample
                    else evidence
                    if config.minimum_effect_per_person is not None
                    else "not_set"
                ),
                "statistical_direction_status": (
                    _decision_for_threshold(lower, upper, None)[0]
                    if enough_sample
                    else "insufficient_sample"
                ),
                "decision_explanation": reason,
                "descriptive_outcomes": descriptive_metrics,
            }
        )
        if progress_callback is not None:
            progress_callback(40 + index * 20)

    unit = (
        "USD gross revenue per assigned customer"
        if config.primary_outcome == "spend"
        else f"{config.primary_outcome} probability per assigned customer"
    )
    return {
        "benchmark": HILLSTROM_DATASET,
        "analysis_type": "randomized intention-to-treat campaign evaluation",
        "source": {
            "dataset_page": HILLSTROM_DATASET_PAGE,
            "download_url": HILLSTROM_DOWNLOAD_URL,
            "license_status": HILLSTROM_LICENSE_STATUS,
            "provenance": "Publisher-described randomized three-arm email test; source fields are retained as released.",
            "raw_data_committed_to_git": False,
        },
        "design": {
            "randomization_unit": "customer",
            "assignment_field": "segment",
            "control_arm": CONTROL_SEGMENT,
            "treatment_arms": list(TREATMENT_SEGMENTS),
            "planned_contrasts": [
                {"treatment": treatment, "comparison": comparison, "type": kind}
                for treatment, comparison, kind in contrast_specs
            ],
            "outcome_window": "two weeks after email campaign",
            "sample_rows": len(frame),
            "arm_counts": {
                str(arm): int(count)
                for arm, count in frame["segment"].value_counts().items()
            },
        },
        "primary_outcome": {
            "name": config.primary_outcome,
            "unit": unit,
            "minimum_effect_per_person": config.minimum_effect_per_person,
            "business_goal_configured": config.minimum_effect_per_person is not None,
            "business_goal_note": (
                "A zero threshold is only a statistical direction check. It does not mean profitable or commercially worthwhile."
                if config.minimum_effect_per_person is None
                else "The threshold is a user-supplied goal; confirm its business meaning and source before using it operationally."
            ),
        },
        "uncertainty": {
            "method": "Welch large-sample normal interval using separate arm variances",
            "critical_value": NormalDist().inv_cdf(1 - tail_probability),
            "familywise_confidence_level": confidence_level,
            "contrast_count": comparisons_count,
            "multiple_comparison_adjustment": "Bonferroni",
        },
        "quality": quality,
        "comparisons": comparisons,
        "interpretation": [
            "Effects are intention-to-treat differences by randomized assignment, including people who did not visit or buy.",
            "Spend is gross revenue in the publisher's data, not contribution margin or profit; campaign cost is absent.",
            "The published challenge is an email campaign benchmark, not a retail discount or Iranian-market study.",
            "Subgroup targeting and individual treatment effects are not evaluated in this report.",
        ],
    }


def evaluate_hillstrom_csv(
    path: str | Path,
    config: HillstromAnalysisConfig | None = None,
    *,
    progress_callback: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Load, validate, evaluate, and attach file provenance for the public CSV."""
    source = Path(path)
    frame, _quality = load_hillstrom_csv(source)
    result = evaluate_hillstrom_frame(frame, config, progress_callback=progress_callback)
    result["source"]["filename"] = source.name
    result["source"]["sha256"] = sha256_file(source)
    return result
