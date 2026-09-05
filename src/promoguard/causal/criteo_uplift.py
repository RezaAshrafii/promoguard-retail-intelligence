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

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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
DEFAULT_SPLIT_SEED = 20260905
DEFAULT_TRAIN_SAMPLE_MODULUS = 20
DEFAULT_BOOTSTRAP_REPLICATES = 50
LOGISTIC_MAX_ITER = 1_000


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


def _stable_row_hash(frame: pd.DataFrame, seed: int) -> pd.Series:
    """Hash pre-treatment features only, so assignment is stable under row reordering."""
    keys = frame[list(FEATURE_COLUMNS)].copy()
    keys["_seed"] = seed
    return pd.util.hash_pandas_object(keys, index=False).astype("uint64")


def _split_bucket(frame: pd.DataFrame, seed: int) -> pd.Series:
    """Assign deterministic buckets without using outcomes, treatment, or source row position."""
    return (_stable_row_hash(frame, seed) % 100).astype("int16")


def _fit_logistic(frame: pd.DataFrame, features: list[str]) -> Pipeline:
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    max_iter=LOGISTIC_MAX_ITER,
                    solver="lbfgs",
                    random_state=DEFAULT_SPLIT_SEED,
                ),
            ),
        ]
    )
    model.fit(frame[features], frame["visit"])
    return model


def _fit_learner(frame: pd.DataFrame, learner: str) -> tuple[Pipeline, Pipeline | None]:
    features = list(FEATURE_COLUMNS)
    if learner == "s_learner":
        return _fit_logistic(frame, features + [TREATMENT_COLUMN]), None
    if learner == "t_learner":
        return (
            _fit_logistic(frame.loc[frame[TREATMENT_COLUMN].eq(1)], features),
            _fit_logistic(frame.loc[frame[TREATMENT_COLUMN].eq(0)], features),
        )
    raise ValueError(f"unknown uplift learner: {learner}")


def _uplift_scores(
    frame: pd.DataFrame,
    learner: str,
    models: tuple[Pipeline, Pipeline | None],
) -> pd.Series:
    features = list(FEATURE_COLUMNS)
    if learner == "s_learner":
        model = models[0]
        treated = frame[features].assign(treatment=1)
        control = frame[features].assign(treatment=0)
        return pd.Series(model.predict_proba(treated)[:, 1] - model.predict_proba(control)[:, 1])
    if learner == "t_learner":
        treated_model, control_model = models
        assert control_model is not None
        return pd.Series(
            treated_model.predict_proba(frame[features])[:, 1]
            - control_model.predict_proba(frame[features])[:, 1]
        )
    raise ValueError(f"unknown uplift learner: {learner}")


def _model_diagnostics(models: tuple[Pipeline, Pipeline | None]) -> dict[str, Any]:
    iterations = [
        int(model.named_steps["logistic"].n_iter_.max()) for model in models if model is not None
    ]
    return {
        "pipelines": len(iterations),
        "iterations": iterations,
        "max_iter": LOGISTIC_MAX_ITER,
        "all_converged": all(iteration < LOGISTIC_MAX_ITER for iteration in iterations),
        "scaled": True,
    }


def _qini_curve(frame: pd.DataFrame, score: pd.Series) -> dict[str, Any]:
    ranked = (
        frame.assign(
            _score=score.to_numpy(),
            _tie_breaker=_stable_row_hash(frame, DEFAULT_SPLIT_SEED + 2_000).to_numpy(),
        )
        .sort_values(["_score", "_tie_breaker"], ascending=[False, True], kind="mergesort")
        .reset_index(drop=True)
    )
    treated = ranked["treatment"].eq(1)
    control = ~treated
    treated_cumulative = treated.cumsum()
    control_cumulative = control.cumsum()
    treated_successes = (treated & ranked["visit"].eq(1)).cumsum()
    control_successes = (control & ranked["visit"].eq(1)).cumsum()
    control_count = control_cumulative.to_numpy(dtype="float64")
    control_rate = np.divide(
        control_successes.to_numpy(dtype="float64"),
        control_count,
        out=np.zeros(len(ranked), dtype="float64"),
        where=control_count != 0,
    )
    qini = pd.Series(
        treated_successes.to_numpy(dtype="float64")
        - treated_cumulative.to_numpy(dtype="float64") * control_rate
    )
    x = pd.Series(range(1, len(ranked) + 1), dtype="float64") / len(ranked)
    raw_auqc = float(
        0.5 * (qini.shift(1, fill_value=0) + qini).mul(x.diff().fillna(x.iloc[0])).sum()
    )
    random_line_auqc = 0.5 * float(qini.iloc[-1])
    qini_coefficient = raw_auqc - random_line_auqc
    points = []
    for fraction in (0.10, 0.20, 0.30):
        index = min(len(ranked) - 1, max(0, math.ceil(len(ranked) * fraction) - 1))
        points.append({"fraction": fraction, "qini": float(qini.iloc[index])})
    return {
        "raw_auqc": raw_auqc,
        "random_line_auqc": random_line_auqc,
        "qini_coefficient": qini_coefficient,
        "qini_at": points,
        "n": len(ranked),
        "qini_final": float(qini.iloc[-1]),
    }


def _poisson_bootstrap_qini(
    frame: pd.DataFrame,
    score: pd.Series,
    *,
    replicates: int = DEFAULT_BOOTSTRAP_REPLICATES,
    seed: int = DEFAULT_SPLIT_SEED + 3_000,
) -> dict[str, Any]:
    """Estimate fixed-ranking Qini uncertainty with reproducible Poisson multiplier weights."""
    if replicates < 2:
        raise ValueError("replicates must be at least 2.")
    ranked = (
        frame.assign(
            _score=score.to_numpy(),
            _tie_breaker=_stable_row_hash(frame, DEFAULT_SPLIT_SEED + 2_000).to_numpy(),
        )
        .sort_values(["_score", "_tie_breaker"], ascending=[False, True], kind="mergesort")
        .reset_index(drop=True)
    )
    treatment = ranked[TREATMENT_COLUMN].to_numpy(dtype="float64")
    outcome = ranked["visit"].to_numpy(dtype="float64")
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(replicates):
        weights = rng.poisson(1.0, len(ranked)).astype("float64")
        treated = weights * treatment
        control = weights * (1.0 - treatment)
        treated_count = np.cumsum(treated)
        control_count = np.cumsum(control)
        treated_successes = np.cumsum(treated * outcome)
        control_successes = np.cumsum(control * outcome)
        control_rate = np.divide(
            control_successes,
            control_count,
            out=np.zeros(len(ranked), dtype="float64"),
            where=control_count != 0,
        )
        qini = treated_successes - treated_count * control_rate
        population = np.cumsum(weights)
        x = population / population[-1]
        dx = np.diff(np.concatenate(([0.0], x)))
        raw_auqc = float(0.5 * np.sum((np.concatenate(([0.0], qini[:-1])) + qini) * dx))
        estimates.append(raw_auqc - 0.5 * float(qini[-1]))
    lower, upper = np.percentile(estimates, [2.5, 97.5])
    return {
        "method": "Poisson(1) multiplier bootstrap conditional on the frozen ranking",
        "replicates": replicates,
        "seed": seed,
        "standard_error": float(np.std(estimates, ddof=1)),
        "confidence_level": 0.95,
        "ci_lower": float(lower),
        "ci_upper": float(upper),
    }


def _split_diagnostics(frame: pd.DataFrame) -> dict[str, Any]:
    counts = (
        frame.groupby([TREATMENT_COLUMN, "visit"], observed=True)
        .size()
        .rename("rows")
        .reset_index()
    )
    return {
        "rows": len(frame),
        "treatment_fraction": float(frame[TREATMENT_COLUMN].mean()),
        "strata": {
            f"{int(row.treatment)}{int(row.visit)}": int(row.rows)
            for row in counts.itertuples(index=False)
        },
        "both_treatment_arms_present": bool(frame[TREATMENT_COLUMN].nunique() == 2),
        "both_outcome_classes_present": bool(frame["visit"].nunique() == 2),
    }


def _frame_balance(frame: pd.DataFrame) -> dict[str, Any]:
    arm_statistics = _empty_arm_statistics()
    feature_statistics = _empty_feature_statistics()
    _update_statistics(frame, arm_statistics, feature_statistics)
    features = _feature_balance(feature_statistics)
    return {
        "features": features,
        "maximum_absolute_smd": max(
            abs(float(row["standardized_mean_difference"])) for row in features
        ),
    }


def _randomization_diagnostics(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    propensity = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    max_iter=LOGISTIC_MAX_ITER,
                    solver="lbfgs",
                    random_state=DEFAULT_SPLIT_SEED + 4_000,
                ),
            ),
        ]
    )
    propensity.fit(train[list(FEATURE_COLUMNS)], train[TREATMENT_COLUMN])
    probability = propensity.predict_proba(test[list(FEATURE_COLUMNS)])[:, 1]
    iterations = int(propensity.named_steps["logistic"].n_iter_.max())
    return {
        "purpose": "detect feature-predictable treatment assignment; not used for outcome modeling",
        "test_roc_auc": float(roc_auc_score(test[TREATMENT_COLUMN], probability)),
        "test_brier_score": float(brier_score_loss(test[TREATMENT_COLUMN], probability)),
        "probability_quantiles": {
            "p01": float(np.quantile(probability, 0.01)),
            "p50": float(np.quantile(probability, 0.50)),
            "p99": float(np.quantile(probability, 0.99)),
        },
        "common_support_fraction_0_05_to_0_95": float(
            np.mean((probability >= 0.05) & (probability <= 0.95))
        ),
        "iterations": iterations,
        "converged": iterations < LOGISTIC_MAX_ITER,
    }


def evaluate_uplift_models(
    input_path: str | Path,
    *,
    chunksize: int = 250_000,
    train_sample_modulus: int = DEFAULT_TRAIN_SAMPLE_MODULUS,
) -> dict[str, Any]:
    """Train transparent S/T learners on real Criteo rows and score a locked real test split."""
    if train_sample_modulus <= 0:
        raise ValueError("train_sample_modulus must be positive.")
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Criteo Uplift source not found: {path}")
    train_parts: list[pd.DataFrame] = []
    validation_parts: list[pd.DataFrame] = []
    test_parts: list[pd.DataFrame] = []
    counts = {"train": 0, "validation": 0, "test": 0}
    for chunk in pd.read_csv(path, compression="infer", chunksize=chunksize):
        _require_valid_chunk(chunk)
        chunk = chunk.reset_index(drop=True)
        buckets = _split_bucket(chunk, DEFAULT_SPLIT_SEED).reset_index(drop=True)
        split = pd.Series("train", index=chunk.index)
        split.loc[buckets >= 70] = "validation"
        split.loc[buckets >= 85] = "test"
        for name, destination in (("train", train_parts), ("validation", validation_parts), ("test", test_parts)):
            selected = chunk.loc[split.eq(name)].copy()
            counts[name] += len(selected)
            if name == "train":
                sample_hash = _stable_row_hash(selected, DEFAULT_SPLIT_SEED + 1_000)
                selected = selected.loc[sample_hash.mod(train_sample_modulus).eq(0)]
            destination.append(selected)
    train = pd.concat(train_parts, ignore_index=True)
    validation = pd.concat(validation_parts, ignore_index=True)
    test = pd.concat(test_parts, ignore_index=True)
    results: dict[str, Any] = {}
    scores: dict[str, dict[str, pd.Series]] = {}
    convergence: dict[str, Any] = {}
    for learner in ("s_learner", "t_learner"):
        models = _fit_learner(train, learner)
        validation_score = _uplift_scores(validation, learner, models)
        test_score = _uplift_scores(test, learner, models)
        scores[learner] = {"validation": validation_score, "test": test_score}
        convergence[learner] = _model_diagnostics(models)
        validation_curve = _qini_curve(validation, validation_score)
        test_curve = _qini_curve(test, test_score)
        results[learner] = {"validation": validation_curve, "test": test_curve}
    selected_learner = max(
        results, key=lambda name: results[name]["validation"]["qini_coefficient"]
    )
    random_curves = []
    for seed in (DEFAULT_SPLIT_SEED, DEFAULT_SPLIT_SEED + 1, DEFAULT_SPLIT_SEED + 2, DEFAULT_SPLIT_SEED + 3, DEFAULT_SPLIT_SEED + 4):
        random_scores = pd.Series(np.random.default_rng(seed).random(len(test)), index=test.index)
        random_curves.append(_qini_curve(test, random_scores))
    random_curve = {
        "raw_auqc": float(np.mean([curve["raw_auqc"] for curve in random_curves])),
        "random_line_auqc": float(
            np.mean([curve["random_line_auqc"] for curve in random_curves])
        ),
        "qini_coefficient": float(
            np.mean([curve["qini_coefficient"] for curve in random_curves])
        ),
        "qini_at": [
            {"fraction": fraction, "qini": float(np.mean([curve["qini_at"][index]["qini"] for curve in random_curves]))}
            for index, fraction in enumerate((0.10, 0.20, 0.30))
        ],
        "n": len(test),
        "qini_final": float(np.mean([curve["qini_final"] for curve in random_curves])),
        "permutations": 5,
        "seeds": [DEFAULT_SPLIT_SEED + offset for offset in range(5)],
    }
    selected_beats_random = (
        results[selected_learner]["test"]["qini_coefficient"]
        > random_curve["qini_coefficient"]
    )
    selected_uncertainty = _poisson_bootstrap_qini(
        test, scores[selected_learner]["test"]
    )
    balance = {
        "train": _frame_balance(train),
        "validation": _frame_balance(validation),
        "test": _frame_balance(test),
    }
    randomization = _randomization_diagnostics(train, test)
    return {
        "benchmark": "criteo-uplift-v2.1-uplift-ranking",
        "outcome": "visit",
        "metric": {
            "curve": "Radcliffe-style cumulative Qini with local prefix arm ratio",
            "raw_area": "trapezoidal AUQC over population fraction",
            "qini_coefficient": "raw AUQC minus triangular random-targeting line area",
            "normalized": False,
        },
        "learners": results,
        "selection": {
            "criterion": "highest validation Qini coefficient; test is not used for selection",
            "selected_learner": selected_learner,
        },
        "convergence": convergence,
        "selected_model_uncertainty": selected_uncertainty,
        "covariate_balance": balance,
        "randomization_diagnostics": randomization,
        "random_ranking_baseline": random_curve,
        "split": {
            "method": "stable hash of pre-treatment features; independent of source row order",
            "seed": DEFAULT_SPLIT_SEED,
            "row_counts": counts,
            "ratios": {"train": 0.70, "validation": 0.15, "test": 0.15},
        },
        "coverage": {
            "train": _split_diagnostics(train),
            "validation": _split_diagnostics(validation),
            "test": _split_diagnostics(test),
        },
        "training": {
            "sampling": "deterministic pre-treatment-feature hash; independent of treatment and outcome",
            "sample_modulus": train_sample_modulus,
            "expected_fraction": 1 / train_sample_modulus,
            "rows_used": len(train),
            "rows_by_treatment_visit_stratum": _split_diagnostics(train)["strata"],
        },
        "features": list(FEATURE_COLUMNS),
        "boundaries": [
            "Scores use only pre-treatment features f0-f11.",
            "Exposure is excluded because it is post-treatment.",
            "Qini/AUUC ranks policy value on this randomized benchmark; it is not individual counterfactual truth.",
            "This does not identify causal retail promotion impact or Iranian market impact.",
        ],
        "gate": {
            "finite_model_metrics": all(
                math.isfinite(results[name][split]["qini_coefficient"])
                for name in results
                for split in ("validation", "test")
            ),
            "all_models_converged": all(
                diagnostic["all_converged"] for diagnostic in convergence.values()
            ),
            "selected_model_ci_above_zero": selected_uncertainty["ci_lower"] > 0,
            "covariate_balance_acceptable": all(
                split_balance["maximum_absolute_smd"] < 0.1
                for split_balance in balance.values()
            ),
            "randomization_auc_acceptable": randomization["test_roc_auc"] < 0.55,
            "common_support_acceptable": (
                randomization["common_support_fraction_0_05_to_0_95"] >= 0.99
            ),
            "test_rows_match_split": len(test) == counts["test"],
            "selected_model_beats_random_baseline": selected_beats_random,
            "promotion_allowed": False,
            "reason": (
                "Ranking screen passed, but uncertainty and policy review are still required."
                if selected_beats_random
                else "Ranking screen failed; no learner may be promoted."
            ),
        },
        "source": {"filename": path.name, "sha256": sha256_file(path), "raw_data_committed_to_git": False},
    }
