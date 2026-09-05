from __future__ import annotations

import pandas as pd
import pytest

from promoguard.causal.criteo_uplift import (
    DEFAULT_SPLIT_SEED,
    FEATURE_COLUMNS,
    _fit_learner,
    _model_diagnostics,
    _poisson_bootstrap_qini,
    _qini_curve,
    _split_bucket,
    _training_sample_mask,
    _uplift_scores,
    summarize_criteo_uplift_chunks,
    validate_criteo_uplift_frame,
)


def criteo_test_fixture() -> pd.DataFrame:
    """Tiny test-only fixture; production evidence always uses the publisher file."""
    rows = []
    for treatment, visit, conversion, exposure, offset in [
        (1, 1, 1, 1, 0.0),
        (1, 1, 0, 1, 0.5),
        (0, 0, 0, 0, 0.0),
        (0, 1, 0, 0, 0.5),
    ]:
        row = {feature: float(index) + offset for index, feature in enumerate(FEATURE_COLUMNS)}
        row.update(
            {
                "treatment": treatment,
                "visit": visit,
                "conversion": conversion,
                "exposure": exposure,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def test_contract_accepts_documented_columns_and_binary_values() -> None:
    report = validate_criteo_uplift_frame(criteo_test_fixture())

    assert report["valid"] is True
    assert report["missing_columns"] == []
    assert report["unexpected_columns"] == []


def test_contract_rejects_invalid_binary_outcome() -> None:
    frame = criteo_test_fixture()
    frame.loc[0, "visit"] = 2

    report = validate_criteo_uplift_frame(frame)

    assert report["valid"] is False
    assert report["binary_invalid_counts"]["visit"] == 1


def test_contract_rejects_non_finite_feature() -> None:
    frame = criteo_test_fixture()
    frame.loc[0, "f3"] = float("inf")

    report = validate_criteo_uplift_frame(frame)

    assert report["valid"] is False
    assert report["feature_invalid_counts"]["f3"] == 1


def test_chunked_summary_reports_itt_and_never_uses_exposure_as_an_outcome() -> None:
    frame = criteo_test_fixture()

    result = summarize_criteo_uplift_chunks([frame.iloc[:2], frame.iloc[2:]])

    assert result["rows_read"] == 4
    assert result["chunks_read"] == 2
    assert result["treatment"] == {
        "treated_rows": 2,
        "control_rows": 2,
        "treated_fraction": 0.5,
    }
    assert result["outcome_effects"]["visit"]["intention_to_treat_risk_difference"] == 0.5
    assert result["outcome_effects"]["conversion"]["intention_to_treat_risk_difference"] == 0.5
    assert "exposure" not in result["outcome_effects"]
    assert len(result["feature_balance"]) == 12


def test_summary_refuses_invalid_chunk_before_aggregation() -> None:
    frame = criteo_test_fixture().drop(columns="conversion")

    with pytest.raises(ValueError, match="contract failed"):
        summarize_criteo_uplift_chunks([frame])


def test_feature_hash_split_is_invariant_to_row_order() -> None:
    frame = criteo_test_fixture().reset_index(names="row_id")
    original = dict(zip(frame["row_id"], _split_bucket(frame, DEFAULT_SPLIT_SEED), strict=True))
    shuffled = frame.sample(frac=1, random_state=42).reset_index(drop=True)
    reordered = dict(
        zip(shuffled["row_id"], _split_bucket(shuffled, DEFAULT_SPLIT_SEED), strict=True)
    )

    assert original == reordered


def test_training_sample_is_independent_of_treatment_and_outcome() -> None:
    frame = pd.concat([criteo_test_fixture()] * 20, ignore_index=True)
    original = _training_sample_mask(frame, 7)
    mutated = frame.copy()
    mutated["treatment"] = 1 - mutated["treatment"]
    mutated["visit"] = 1 - mutated["visit"]
    mutated["conversion"] = 1 - mutated["conversion"]

    assert original.equals(_training_sample_mask(mutated, 7))


def test_qini_area_uses_trapezoids_and_reports_random_line_separately() -> None:
    frame = criteo_test_fixture()
    frame["treatment"] = [1, 0, 1, 0]
    frame["visit"] = [1, 0, 0, 1]
    scores = pd.Series([4.0, 3.0, 2.0, 1.0])

    result = _qini_curve(frame, scores)

    assert result["qini_final"] == pytest.approx(0.0)
    assert result["raw_auqc"] == pytest.approx(0.5)
    assert result["random_line_auqc"] == pytest.approx(0.0)
    assert result["qini_coefficient"] == pytest.approx(0.5)
    assert result["qini_at"][0]["prefix_rows"] == 1
    assert result["qini_at"][0]["qini_per_ranked_row"] == pytest.approx(0.0)
    assert result["qini_at"][0]["difference_in_means_incremental_rate"] is None
    assert "ipw_incremental_rate" in result["qini_at"][0]


def test_qini_policy_rates_distinguish_scaled_qini_from_prefix_ate() -> None:
    frame = pd.concat([criteo_test_fixture(), criteo_test_fixture(), criteo_test_fixture().iloc[:2]], ignore_index=True)
    frame["treatment"] = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    frame["visit"] = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    scores = pd.Series(range(10, 0, -1), dtype="float64")

    point = _qini_curve(frame, scores)["qini_at"][1]

    assert point["prefix_rows"] == 2
    assert point["treated_rows"] == 1
    assert point["control_rows"] == 1
    assert point["qini"] == pytest.approx(1.0)
    assert point["qini_per_ranked_row"] == pytest.approx(0.5)
    assert point["difference_in_means_incremental_rate"] == pytest.approx(1.0)
    assert point["ipw_incremental_rate"] == pytest.approx(1.0)


@pytest.mark.parametrize("treatment", [0, 1])
def test_qini_refuses_a_single_treatment_arm(treatment: int) -> None:
    frame = criteo_test_fixture()
    frame["treatment"] = treatment

    with pytest.raises(ValueError, match="treated and one control"):
        _qini_curve(frame, pd.Series(range(len(frame)), dtype="float64"))


def test_qini_refuses_non_finite_or_wrong_length_scores() -> None:
    frame = criteo_test_fixture()
    with pytest.raises(ValueError, match="length"):
        _qini_curve(frame, pd.Series([1.0]))
    with pytest.raises(ValueError, match="finite"):
        _qini_curve(frame, pd.Series([1.0, 2.0, float("nan"), 4.0]))


def test_poisson_bootstrap_is_reproducible_for_a_frozen_ranking() -> None:
    frame = pd.concat([criteo_test_fixture()] * 20, ignore_index=True)
    scores = pd.Series(range(len(frame)), dtype="float64")

    first = _poisson_bootstrap_qini(frame, scores, replicates=10, seed=7)
    second = _poisson_bootstrap_qini(frame, scores, replicates=10, seed=7)

    assert first == second
    assert first["ci_lower"] <= first["ci_upper"]
    assert first["standard_error"] >= 0


def test_poisson_bootstrap_retries_invalid_tiny_two_arm_draws() -> None:
    frame = criteo_test_fixture().iloc[[0, 2]].reset_index(drop=True)
    scores = pd.Series([1.0, 0.0])

    result = _poisson_bootstrap_qini(frame, scores, replicates=20, seed=1)

    assert result["replicates"] == 20
    assert result["invalid_draws_skipped"] > 0
    assert result["draws_attempted"] == 20 + result["invalid_draws_skipped"]


def test_logistic_learner_scales_features_and_reports_convergence() -> None:
    frame = pd.concat([criteo_test_fixture()] * 30, ignore_index=True)
    models = _fit_learner(frame, "s_learner")

    diagnostics = _model_diagnostics(models)

    assert diagnostics["scaled"] is True
    assert diagnostics["pipelines"] == 1
    assert diagnostics["all_converged"] is True


def test_histogram_uplift_learner_produces_finite_scores() -> None:
    frame = pd.concat([criteo_test_fixture()] * 60, ignore_index=True)
    models = _fit_learner(frame, "s_learner_hist_gb")

    scores = _uplift_scores(frame, "s_learner_hist_gb", models)
    diagnostics = _model_diagnostics(models)

    assert scores.notna().all()
    assert diagnostics["algorithm"] == "histogram gradient boosting"
    assert diagnostics["training_completed"] is True
