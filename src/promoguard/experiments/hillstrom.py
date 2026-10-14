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

from promoguard.experiments.revenue_details import (
    FinancialAssumptions,
    build_revenue_details,
)

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
HISTORY_SEGMENTS = (
    "1) $0 - $100",
    "2) $100 - $200",
    "3) $200 - $350",
    "4) $350 - $500",
    "5) $500 - $750",
    "6) $750 - $1,000",
    "7) $1,000 +",
)
CONTROL_SEGMENT = "No E-Mail"
TREATMENT_SEGMENTS = ("Mens E-Mail", "Womens E-Mail")
MINIMUM_ARM_SIZE_FOR_DECISION = 1_000
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20_261_012
BOOTSTRAP_BATCH_SIZE = 1_000
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
    financial_assumptions: FinancialAssumptions | None = None

    @model_validator(mode="after")
    def validate_threshold(self) -> HillstromAnalysisConfig:
        if self.financial_assumptions is not None and self.primary_outcome != "spend":
            raise ValueError("Financial assumptions require spend as the primary outcome.")
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
        history_invalid = int((~frame["history_segment"].isin(HISTORY_SEGMENTS)).sum())
        if history_invalid:
            errors.append(
                f"history_segment contains {history_invalid} unsupported labels"
            )
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


def _bootstrap_arm_means(
    values: np.ndarray,
    *,
    rng: np.random.Generator,
    repetitions: int = BOOTSTRAP_RESAMPLES,
) -> np.ndarray:
    """Draw empirical means using multinomial counts over observed outcome values.

    This is exactly the ordinary nonparametric row bootstrap for the empirical distribution,
    but it avoids storing a full resampled row matrix. The calculation is batched to bound memory.
    """
    support, counts = np.unique(values, return_counts=True)
    probabilities = counts / values.size
    means = np.empty(repetitions, dtype=np.float64)
    for start in range(0, repetitions, BOOTSTRAP_BATCH_SIZE):
        stop = min(start + BOOTSTRAP_BATCH_SIZE, repetitions)
        frequencies = rng.multinomial(values.size, probabilities, size=stop - start)
        means[start:stop] = frequencies @ support / values.size
    return means


def _interval_direction(lower: float, upper: float) -> str:
    if lower > 0:
        return "positive_evidence_vs_zero"
    if upper < 0:
        return "negative_evidence_vs_zero"
    return "inconclusive_vs_zero"


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


def _chi_square_6_survival(statistic: float) -> float | None:
    """Return a numerically stable chi-square(6) survival probability.

    ``None`` marks a value outside the statistic's domain. Log-sum-exp avoids intermediate
    overflow for very large finite statistics; underflow of the final probability to zero is valid.
    """
    if not math.isfinite(statistic) or statistic < 0:
        return None
    half = statistic / 2
    if half == 0:
        return 1.0
    log_half = math.log(half)
    log_terms = (0.0, log_half, 2 * log_half - math.log(2))
    largest = max(log_terms)
    log_polynomial = largest + math.log(sum(math.exp(term - largest) for term in log_terms))
    log_probability = -half + log_polynomial
    if log_probability < math.log(float.fromhex("0x0.0000000000001p-1022")):
        return 0.0
    probability = math.exp(log_probability)
    return probability if math.isfinite(probability) else None


def _evaluate_history_heterogeneity(
    frame: pd.DataFrame,
    outcome: str,
    *,
    confidence_level: float,
) -> list[dict[str, Any]]:
    """Run a predeclared inverse-variance Q test for each treatment-vs-control contrast.

    Strata are disjoint, so stratum-level treatment-control estimates are independent under the
    randomized benchmark design. The asymptotic chi-square test is exploratory and is not a
    targeting rule. The two treatment-arm tests form one Bonferroni-adjusted family.
    """
    tests: list[dict[str, Any]] = []
    for treatment_arm in TREATMENT_SEGMENTS:
        effects: list[float] = []
        variances: list[float] = []
        minimum_cell_size: int | None = None
        present_strata = 0
        estimable_strata = 0
        invalid_variance = False
        for history_segment in HISTORY_SEGMENTS:
            stratum = frame.loc[frame["history_segment"].eq(history_segment)]
            treatment = pd.to_numeric(
                stratum.loc[stratum["segment"].eq(treatment_arm), outcome]
            ).to_numpy(dtype=np.float64)
            control = pd.to_numeric(
                stratum.loc[stratum["segment"].eq(CONTROL_SEGMENT), outcome]
            ).to_numpy(dtype=np.float64)
            cell_size = min(treatment.size, control.size)
            minimum_cell_size = (
                cell_size if minimum_cell_size is None else min(minimum_cell_size, cell_size)
            )
            if treatment.size and control.size:
                present_strata += 1
            if treatment.size < 2 or control.size < 2:
                invalid_variance = True
                continue
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                variance = float(
                    treatment.var(ddof=1) / treatment.size
                    + control.var(ddof=1) / control.size
                )
            if not math.isfinite(variance) or variance <= 0:
                invalid_variance = True
                continue
            estimable_strata += 1
            effects.append(float(treatment.mean() - control.mean()))
            variances.append(variance)

        minimum_cell_size_for_interpretation = MINIMUM_ARM_SIZE_FOR_DECISION
        common = {
            "treatment_arm": treatment_arm,
            "control_arm": CONTROL_SEGMENT,
            "method": "inverse-variance Cochran Q with asymptotic chi-square reference",
            "strata_count": present_strata,
            "estimable_strata_count": estimable_strata,
            "degrees_of_freedom": (
                len(HISTORY_SEGMENTS) - 1
                if present_strata == len(HISTORY_SEGMENTS)
                else None
            ),
            "minimum_cell_size": minimum_cell_size,
            "minimum_cell_size_for_interpretation": minimum_cell_size_for_interpretation,
            "interpretation_allowed": False,
            "statistic": None,
            "p_value": None,
            "familywise_adjusted_p_value": None,
            "familywise_test_count": len(TREATMENT_SEGMENTS),
        }
        if present_strata != len(HISTORY_SEGMENTS):
            tests.append(
                {
                    **common,
                    "status": "not_estimable",
                    "reason_code": "predeclared_stratum_or_arm_missing",
                }
            )
            continue

        if minimum_cell_size is None or minimum_cell_size < minimum_cell_size_for_interpretation:
            tests.append(
                {
                    **common,
                    "status": "insufficient_sample",
                    "reason_code": "below_minimum_cell_size_for_interpretation",
                }
            )
            continue

        if invalid_variance or len(effects) != len(HISTORY_SEGMENTS):
            tests.append(
                {
                    **common,
                    "status": "not_estimable",
                    "reason_code": "stratum_variance_not_estimable",
                }
            )
            continue

        variance_array = np.asarray(variances, dtype=np.float64)
        estimates = np.asarray(effects, dtype=np.float64)
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            # Ratios stay in [0, 1], unlike raw inverse variances for tiny measurement scales.
            minimum_variance = float(variance_array.min())
            weights = minimum_variance / variance_array
            normalized_weights = weights / weights.sum()
            effect_scale = float(np.max(np.abs(estimates)))
            if effect_scale == 0:
                statistic = 0.0
            else:
                scaled_estimates = estimates / effect_scale
                weighted_mean_scaled = float(np.dot(normalized_weights, scaled_estimates))
                dispersion = float(
                    np.dot(normalized_weights, np.square(scaled_estimates - weighted_mean_scaled))
                )
                if dispersion == 0:
                    statistic = 0.0
                else:
                    log_statistic = (
                        math.log(dispersion)
                        + 2 * math.log(effect_scale)
                        - math.log(minimum_variance)
                    )
                    if log_statistic > math.log(float.fromhex("0x1.fffffffffffffp+1023")):
                        statistic = math.inf
                    elif log_statistic < math.log(float.fromhex("0x0.0000000000001p-1022")):
                        statistic = 0.0
                    else:
                        statistic = math.exp(log_statistic)
        p_value = _chi_square_6_survival(statistic)
        if (
            not math.isfinite(statistic)
            or p_value is None
        ):
            tests.append(
                {
                    **common,
                    "status": "numerical_error",
                    "reason_code": "non_finite_test_statistic_or_probability",
                }
            )
            continue
        p_value = min(1.0, p_value)
        adjusted_p_value = min(1.0, p_value * len(TREATMENT_SEGMENTS))
        tests.append(
            {
                **common,
                "interpretation_allowed": True,
                "statistic": statistic,
                "p_value": p_value,
                "familywise_adjusted_p_value": adjusted_p_value,
                "status": (
                    "evidence_of_heterogeneity"
                    if adjusted_p_value < 1 - confidence_level
                    else "no_clear_heterogeneity_evidence"
                ),
                "reason_code": None,
            }
        )
    return tests


def _evaluate_history_subgroups(
    frame: pd.DataFrame,
    outcome: str,
    *,
    confidence_level: float,
) -> dict[str, Any]:
    """Estimate pre-treatment history-stratum contrasts as exploratory diagnostics.

    All 14 treatment-versus-control contrasts are declared by the data contract, including
    strata below the interpretation threshold. The Bonferroni family therefore does not shrink
    when sparse strata are encountered.
    """
    contrast_count = len(HISTORY_SEGMENTS) * len(TREATMENT_SEGMENTS)
    tail_probability = (1 - confidence_level) / (2 * contrast_count)
    contrasts: list[dict[str, Any]] = []

    for history_segment in HISTORY_SEGMENTS:
        stratum = frame.loc[frame["history_segment"].eq(history_segment)]
        control_frame = stratum.loc[stratum["segment"].eq(CONTROL_SEGMENT)]
        control = pd.to_numeric(control_frame[outcome]).to_numpy(dtype=np.float64)
        for treatment_arm in TREATMENT_SEGMENTS:
            treatment_frame = stratum.loc[stratum["segment"].eq(treatment_arm)]
            treatment = pd.to_numeric(treatment_frame[outcome]).to_numpy(dtype=np.float64)
            treatment_n = int(treatment.size)
            control_n = int(control.size)
            enough_sample = min(treatment_n, control_n) >= MINIMUM_ARM_SIZE_FOR_DECISION

            estimate: float | None = None
            standard_error: float | None = None
            lower: float | None = None
            upper: float | None = None
            if treatment_n >= 2 and control_n >= 2:
                estimate, standard_error, lower, upper = _welch_difference_interval(
                    treatment, control, tail_probability=tail_probability
                )

            if enough_sample and lower is not None and upper is not None:
                status = _interval_direction(lower, upper)
            else:
                status = "insufficient_sample"

            contrasts.append(
                {
                    "history_segment": history_segment,
                    "treatment_arm": treatment_arm,
                    "control_arm": CONTROL_SEGMENT,
                    "treatment_n": treatment_n,
                    "control_n": control_n,
                    "treatment_mean_per_person": (
                        float(treatment.mean()) if treatment_n else None
                    ),
                    "control_mean_per_person": float(control.mean()) if control_n else None,
                    "estimated_effect_per_person": estimate,
                    "estimated_effect_per_1000_people": (
                        estimate * 1_000 if estimate is not None else None
                    ),
                    "standard_error_per_person": standard_error,
                    "familywise_ci_lower_per_person": lower,
                    "familywise_ci_upper_per_person": upper,
                    "status": status,
                    "interpretation_allowed": enough_sample,
                }
            )

    return {
        "attribute": "history_segment",
        "label": "customer purchase history before assignment",
        "pre_treatment": True,
        "outcome": outcome,
        "familywise_confidence_level": confidence_level,
        "contrast_count": contrast_count,
        "multiplicity_method": "Bonferroni across all 14 predeclared treatment-versus-control contrasts",
        "interval_method": "Welch large-sample normal approximation",
        "minimum_arm_size_for_interpretation": MINIMUM_ARM_SIZE_FOR_DECISION,
        "contrasts": contrasts,
        "heterogeneity_tests": _evaluate_history_heterogeneity(
            frame, outcome, confidence_level=confidence_level
        ),
        "limitations": [
            "Exploratory stratum-level assignment comparisons; they are not validated targeting rules.",
            "The global heterogeneity test is exploratory and asymptotic; a non-significant result does not prove equal effects.",
            "No recommendation to target individuals or deploy a campaign is produced.",
        ],
    }


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
    bootstrap_rng = np.random.default_rng(BOOTSTRAP_SEED)
    bootstrap_arm_means = {
        arm: _bootstrap_arm_means(
            pd.to_numeric(frame.loc[frame["segment"].eq(arm), config.primary_outcome])
            .to_numpy(dtype=np.float64),
            rng=bootstrap_rng,
        )
        for arm in ("Mens E-Mail", "Womens E-Mail", CONTROL_SEGMENT)
    }
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
        bootstrap_differences = (
            bootstrap_arm_means[segment] - bootstrap_arm_means[control_segment]
        )
        bootstrap_lower, bootstrap_upper = np.quantile(
            bootstrap_differences,
            [tail_probability, 1 - tail_probability],
            method="linear",
        ).tolist()
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
        bootstrap_direction = (
            _interval_direction(float(bootstrap_lower), float(bootstrap_upper))
            if enough_sample
            else "insufficient_sample"
        )
        bootstrap_goal = (
            "insufficient_sample"
            if not enough_sample
            else
            _decision_for_threshold(
                float(bootstrap_lower),
                float(bootstrap_upper),
                config.minimum_effect_per_person,
            )[0]
            if enough_sample
            and contrast_type == "treatment_vs_control"
            and config.minimum_effect_per_person is not None
            else "not_applicable_variant_comparison"
            if contrast_type == "treatment_vs_treatment"
            else "not_set"
        )
        if not enough_sample:
            bootstrap_stability = "insufficient_sample"
        else:
            reference_status = (
                evidence
                if contrast_type == "treatment_vs_control"
                and config.minimum_effect_per_person is not None
                else _interval_direction(lower, upper)
            )
            bootstrap_status = (
                bootstrap_goal
                if contrast_type == "treatment_vs_control"
                and config.minimum_effect_per_person is not None
                else bootstrap_direction
            )
            bootstrap_stability = (
                "consistent" if reference_status == bootstrap_status else "sensitive_to_method"
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
                "bootstrap_ci_lower_per_person": float(bootstrap_lower),
                "bootstrap_ci_upper_per_person": float(bootstrap_upper),
                "bootstrap_standard_error_per_person": float(bootstrap_differences.std(ddof=1)),
                "bootstrap_direction_status": bootstrap_direction,
                "bootstrap_business_goal_status": bootstrap_goal,
                "bootstrap_stability_status": bootstrap_stability,
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
                "revenue_details": (
                    build_revenue_details(
                        treatment_frame,
                        comparison_control_frame,
                        (estimate, lower, upper),
                        config.financial_assumptions,
                        treatment_arm=segment,
                        control_arm=control_segment,
                    )
                    if config.primary_outcome == "spend"
                    else None
                ),
            }
        )
        if progress_callback is not None:
            progress_callback(40 + index * 20)

    unit = (
        "USD gross revenue per assigned customer"
        if config.primary_outcome == "spend"
        else f"{config.primary_outcome} probability per assigned customer"
    )
    subgroup_analysis = _evaluate_history_subgroups(
        frame,
        config.primary_outcome,
        confidence_level=confidence_level,
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
            "bootstrap": {
                "method": "Empirical nonparametric percentile bootstrap of group means",
                "resampling_unit": "customer rows resampled independently within assigned arm",
                "repetitions": BOOTSTRAP_RESAMPLES,
                "seed": BOOTSTRAP_SEED,
                "interval_quantile_method": "linear percentile quantiles",
                "multiple_comparison_adjustment": "Bonferroni-adjusted two-sided marginal quantiles",
                "familywise_confidence_level": confidence_level,
                "role": "stability diagnostic; does not replace the prespecified Welch interval or decision gate",
            },
        },
        "quality": quality,
        "comparisons": comparisons,
        "subgroup_analysis": subgroup_analysis,
        "interpretation": [
            "Effects are intention-to-treat differences by randomized assignment, including people who did not visit or buy.",
            "Spend is gross revenue in the publisher's data, not contribution margin or profit; campaign cost is absent.",
            "The published challenge is an email campaign benchmark, not a retail discount or Iranian-market study.",
            "The report includes exploratory assignment comparisons within pre-treatment purchase-history strata; it does not establish subgroup differences, individual treatment effects, or targeting rules.",
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
