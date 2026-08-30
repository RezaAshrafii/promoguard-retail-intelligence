"""Deterministic observational promotion audit; this module makes no causal claim."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from promoguard.data.grain import normalize_required_identifiers

GROUP_COLUMNS = ["store_id", "upc"]
REQUIRED_COLUMNS = ["week_end_date", "store_id", "upc", "units", "promotion_flag"]


class AuditRecommendation(StrEnum):
    """Non-rollout screening action returned by the observational audit."""

    CANDIDATE_FOR_CONTROLLED_TEST = "candidate_for_controlled_test"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    DEPRIORITIZE_AND_INVESTIGATE = "deprioritize_and_investigate"


class WarningSeverity(StrEnum):
    """Severity attached to one audit diagnostic."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class AuditWarning(BaseModel):
    """Machine-readable warning with a plain-language explanation."""

    code: str
    severity: WarningSeverity
    message: str


class EstimateInterval(BaseModel):
    """Point estimate and uncertainty bounds in units."""

    point: float
    lower: float
    upper: float


class WindowSummary(BaseModel):
    """Observed summary for one pre/during/post event window."""

    requested_weeks: int
    observed_weeks: int
    total_units: float
    mean_units: float | None
    promotion_weeks: int


class ContributionAssumption(BaseModel):
    """User-approved sensitivity input; it is not an observed financial field."""

    amount_per_incremental_unit: float = Field(allow_inf_nan=False)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    source: str = Field(min_length=1)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("source")
    @classmethod
    def reject_blank_source(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("contribution assumption source must not be blank")
        return normalized


class ContributionSensitivity(BaseModel):
    """Linear what-if sensitivity; not promotion profit or gross-margin impact."""

    assumption: ContributionAssumption
    estimated_contribution_difference_vs_baseline: EstimateInterval
    status: Literal["sensitivity_only"] = "sensitivity_only"
    limitation: Literal[
        "Does not model margin lost on baseline units, trade spend, funding, or other costs."
    ] = "Does not model margin lost on baseline units, trade spend, funding, or other costs."


class PromotionAuditResult(BaseModel):
    """Typed evidence payload for one observed promotion episode."""

    audit_id: str
    dataset: str
    store_id: str
    upc: str
    start_date: date
    end_date: date
    duration_weeks: int
    baseline_model: str
    history_weeks: int
    observed_units: float
    baseline_units: EstimateInterval
    estimated_units_difference_vs_baseline: EstimateInterval
    contribution_sensitivity: ContributionSensitivity | None
    pre_window: WindowSummary
    during_window: WindowSummary
    post_window: WindowSummary
    pre_to_reference_ratio: float | None
    post_to_pre_ratio: float | None
    recommendation: AuditRecommendation
    recommendation_scope: str
    recommendation_rationale: str
    warnings: list[AuditWarning]
    assumptions: list[str]
    evidence_refs: list[str]
    claim_language: str


def prepare_audit_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Validate the audit grain while retaining optional business columns."""
    missing = sorted(set(REQUIRED_COLUMNS) - set(panel.columns))
    if missing:
        raise ValueError(f"Audit panel is missing required columns: {', '.join(missing)}")
    result = panel.copy()
    result = normalize_required_identifiers(result, context="Audit panel")
    result["week_end_date"] = pd.to_datetime(result["week_end_date"], errors="coerce")
    if result["week_end_date"].isna().any():
        raise ValueError("Audit panel contains invalid week_end_date values.")
    if result["units"].isna().any() or (result["units"] < 0).any():
        raise ValueError("Audit panel units must be present and non-negative.")
    if not result["promotion_flag"].isin([0, 1]).all():
        raise ValueError("Audit panel promotion_flag must contain only 0 or 1.")
    if result.duplicated(GROUP_COLUMNS + ["week_end_date"]).any():
        raise ValueError("Audit panel contains duplicate store_id × upc × week rows.")
    return result.sort_values(GROUP_COLUMNS + ["week_end_date"]).reset_index(drop=True)


def detect_promotion_episodes(panel: pd.DataFrame) -> pd.DataFrame:
    """Group consecutive promoted weeks into deterministic store-product episodes."""
    prepared = prepare_audit_panel(panel)
    promoted = prepared[prepared["promotion_flag"].eq(1)].copy()
    if promoted.empty:
        return pd.DataFrame(
            columns=["audit_id", "store_id", "upc", "start_date", "end_date", "duration_weeks"]
        )
    previous_date = promoted.groupby(GROUP_COLUMNS)["week_end_date"].shift(1)
    starts_episode = previous_date.isna() | (promoted["week_end_date"] - previous_date).dt.days.ne(7)
    promoted["episode_number"] = starts_episode.groupby(
        [promoted["store_id"], promoted["upc"]]
    ).cumsum()
    episodes = (
        promoted.groupby(GROUP_COLUMNS + ["episode_number"], as_index=False)
        .agg(
            start_date=("week_end_date", "min"),
            end_date=("week_end_date", "max"),
            duration_weeks=("week_end_date", "size"),
        )
        .drop(columns="episode_number")
    )
    episodes["audit_id"] = episodes.apply(
        lambda row: f"{row.store_id}-{row.upc}-{row.start_date.date().isoformat()}", axis=1
    )
    return episodes[
        ["audit_id", "store_id", "upc", "start_date", "end_date", "duration_weeks"]
    ].sort_values(["start_date", "store_id", "upc"]).reset_index(drop=True)


def select_representative_event(
    panel: pd.DataFrame,
    *,
    min_history_weeks: int = 52,
    post_window_weeks: int = 4,
) -> dict[str, Any]:
    """Select the earliest event meeting predeclared history and post-window rules."""
    prepared = prepare_audit_panel(panel)
    episodes = detect_promotion_episodes(prepared)
    groups = {
        key: group
        for key, group in prepared.groupby(GROUP_COLUMNS, sort=False)
    }
    for event in episodes.itertuples(index=False):
        group = groups[(event.store_id, event.upc)]
        history = group[
            (group["week_end_date"] < event.start_date) & group["promotion_flag"].eq(0)
        ]
        post_end = event.end_date + pd.Timedelta(weeks=post_window_weeks)
        post = group[
            (group["week_end_date"] > event.end_date)
            & (group["week_end_date"] <= post_end)
        ]
        if len(history) >= min_history_weeks and post["week_end_date"].nunique() >= post_window_weeks:
            return event._asdict()
    raise ValueError("No promotion episode has the required history and complete post window.")


def _window_summary(frame: pd.DataFrame, requested_weeks: int) -> WindowSummary:
    observed_weeks = int(frame["week_end_date"].nunique())
    total_units = float(frame["units"].sum())
    return WindowSummary(
        requested_weeks=requested_weeks,
        observed_weeks=observed_weeks,
        total_units=total_units,
        mean_units=float(frame["units"].mean()) if not frame.empty else None,
        promotion_weeks=int(frame["promotion_flag"].eq(1).sum()),
    )


def _warning(code: str, severity: WarningSeverity, message: str) -> AuditWarning:
    return AuditWarning(code=code, severity=severity, message=message)


def _baseline_interval(history: pd.DataFrame, duration_weeks: int) -> EstimateInterval:
    ordered = history.sort_values("week_end_date").copy()
    point_per_week = float(ordered.iloc[-1]["units"])
    previous_units = ordered["units"].shift(1)
    consecutive = ordered["week_end_date"].diff().dt.days.eq(7)
    residuals = (ordered["units"] - previous_units).abs().where(consecutive).dropna()
    half_width = float(residuals.quantile(0.9)) if not residuals.empty else point_per_week
    return EstimateInterval(
        point=point_per_week * duration_weeks,
        lower=max(0.0, point_per_week - half_width) * duration_weeks,
        upper=(point_per_week + half_width) * duration_weeks,
    )


def _recommendation(
    units_difference: EstimateInterval,
    warnings: list[AuditWarning],
) -> tuple[AuditRecommendation, str]:
    blocking_codes = {
        warning.code for warning in warnings if warning.severity == WarningSeverity.BLOCKING
    }
    if blocking_codes:
        return (
            AuditRecommendation.NEEDS_MORE_EVIDENCE,
            "Blocking diagnostics require better data or a controlled experiment.",
        )
    if units_difference.upper < 0:
        return (
            AuditRecommendation.DEPRIORITIZE_AND_INVESTIGATE,
            "Observed units remain below the forecast baseline across the audit interval; investigate confounding before spending more.",
        )
    if units_difference.lower > 0:
        return (
            AuditRecommendation.CANDIDATE_FOR_CONTROLLED_TEST,
            "Observed units remain above the forecast baseline across the audit interval; test the hypothesis under controlled assignment.",
        )
    return (
        AuditRecommendation.NEEDS_MORE_EVIDENCE,
        "The observational interval crosses zero, so the direction is unresolved.",
    )


def audit_promotion_event(
    panel: pd.DataFrame,
    *,
    store_id: str,
    upc: str,
    start_date: str | date | pd.Timestamp,
    contribution_assumption: ContributionAssumption | None = None,
    pre_window_weeks: int = 4,
    post_window_weeks: int = 4,
    min_history_weeks: int = 26,
) -> PromotionAuditResult:
    """Audit one promotion episode with pre-event-only baseline and explicit limitations."""
    prepared = prepare_audit_panel(panel)
    store_key, upc_key = str(store_id), str(upc)
    event_start = pd.Timestamp(start_date)
    episodes = detect_promotion_episodes(prepared)
    matches = episodes[
        episodes["store_id"].eq(store_key)
        & episodes["upc"].eq(upc_key)
        & episodes["start_date"].eq(event_start)
    ]
    if matches.empty:
        raise ValueError("No promotion episode matches the requested store, UPC, and start date.")
    event = matches.iloc[0]
    event_end = pd.Timestamp(event["end_date"])
    duration_weeks = int(event["duration_weeks"])
    group = prepared[
        prepared["store_id"].eq(store_key) & prepared["upc"].eq(upc_key)
    ].copy()
    history = group[
        (group["week_end_date"] < event_start) & group["promotion_flag"].eq(0)
    ].copy()
    if history.empty:
        raise ValueError("The selected episode has no non-promotion history for a baseline.")

    pre_start = event_start - pd.Timedelta(weeks=pre_window_weeks)
    post_end = event_end + pd.Timedelta(weeks=post_window_weeks)
    pre = group[
        (group["week_end_date"] >= pre_start) & (group["week_end_date"] < event_start)
    ]
    during = group[
        (group["week_end_date"] >= event_start) & (group["week_end_date"] <= event_end)
    ]
    post = group[(group["week_end_date"] > event_end) & (group["week_end_date"] <= post_end)]
    baseline = _baseline_interval(history, duration_weeks)
    observed_units = float(during["units"].sum())
    units_difference = EstimateInterval(
        point=observed_units - baseline.point,
        lower=observed_units - baseline.upper,
        upper=observed_units - baseline.lower,
    )

    warnings: list[AuditWarning] = [
        _warning(
            "OBSERVATIONAL_ONLY",
            WarningSeverity.WARNING,
            "The estimate is an observational audit and does not identify a treatment effect.",
        )
    ]
    if len(history) < min_history_weeks:
        warnings.append(
            _warning(
                "SHORT_HISTORY",
                WarningSeverity.BLOCKING,
                f"Only {len(history)} non-promotion history rows are available; {min_history_weeks} are required.",
            )
        )
    warnings.append(
        _warning(
            "ECONOMIC_IMPACT_UNAVAILABLE",
            WarningSeverity.INFO,
            "Full promotion economics are unavailable; any contribution output is sensitivity-only and cannot drive the recommendation.",
        )
    )
    if "inventory_on_hand" not in prepared.columns:
        warnings.append(
            _warning(
                "STOCKOUT_UNOBSERVABLE",
                WarningSeverity.WARNING,
                "The source has no inventory field, so stockout-censored demand cannot be diagnosed.",
            )
        )
    elif during["inventory_on_hand"].le(0).any():
        warnings.append(
            _warning(
                "STOCKOUT_RISK",
                WarningSeverity.BLOCKING,
                "Inventory reached zero during the promotion window.",
            )
        )
    if pre["week_end_date"].nunique() < pre_window_weeks:
        warnings.append(
            _warning(
                "INCOMPLETE_PRE_WINDOW",
                WarningSeverity.WARNING,
                "The requested pre-promotion window is incomplete.",
            )
        )
    if post["week_end_date"].nunique() < post_window_weeks:
        warnings.append(
            _warning(
                "INCOMPLETE_POST_WINDOW",
                WarningSeverity.BLOCKING,
                "The requested post-promotion window is incomplete.",
            )
        )
    if post["promotion_flag"].eq(1).any():
        warnings.append(
            _warning(
                "POST_WINDOW_CONTAMINATED",
                WarningSeverity.WARNING,
                "Another promotion appears in the post window.",
            )
        )

    reference = history[history["week_end_date"] < pre_start].tail(12)
    pre_non_promotion = pre[pre["promotion_flag"].eq(0)]
    pre_ratio = None
    if not reference.empty and not pre_non_promotion.empty and reference["units"].mean() > 0:
        pre_ratio = float(pre_non_promotion["units"].mean() / reference["units"].mean())
        if pre_ratio < 0.5 or pre_ratio > 1.5:
            warnings.append(
                _warning(
                    "SEVERE_SHIFT",
                    WarningSeverity.BLOCKING,
                    "Recent pre-promotion demand differs by more than 50% from earlier history.",
                )
            )

    post_non_promotion = post[post["promotion_flag"].eq(0)]
    post_ratio = None
    if (
        not pre_non_promotion.empty
        and not post_non_promotion.empty
        and pre_non_promotion["units"].mean() > 0
    ):
        post_ratio = float(post_non_promotion["units"].mean() / pre_non_promotion["units"].mean())
        if post_ratio < 0.8:
            warnings.append(
                _warning(
                    "FORWARD_BUY_RISK",
                    WarningSeverity.BLOCKING,
                    "Post-promotion demand is more than 20% below the pre-promotion average.",
                )
            )

    contribution_sensitivity = None
    if contribution_assumption is not None:
        amount = contribution_assumption.amount_per_incremental_unit
        transformed_bounds = sorted(
            [units_difference.lower * amount, units_difference.upper * amount]
        )
        contribution_sensitivity = ContributionSensitivity(
            assumption=contribution_assumption,
            estimated_contribution_difference_vs_baseline=EstimateInterval(
                point=units_difference.point * amount,
                lower=transformed_bounds[0],
                upper=transformed_bounds[1],
            ),
        )
    recommendation, rationale = _recommendation(units_difference, warnings)
    return PromotionAuditResult(
        audit_id=str(event["audit_id"]),
        dataset="dunnhumby-breakfast-at-the-frat",
        store_id=store_key,
        upc=upc_key,
        start_date=event_start.date(),
        end_date=event_end.date(),
        duration_weeks=duration_weeks,
        baseline_model="recursive-naive-1 using non-promotion pre-event history",
        history_weeks=len(history),
        observed_units=observed_units,
        baseline_units=baseline,
        estimated_units_difference_vs_baseline=units_difference,
        contribution_sensitivity=contribution_sensitivity,
        pre_window=_window_summary(pre, pre_window_weeks),
        during_window=_window_summary(during, duration_weeks),
        post_window=_window_summary(post, post_window_weeks),
        pre_to_reference_ratio=pre_ratio,
        post_to_pre_ratio=post_ratio,
        recommendation=recommendation,
        recommendation_scope="observational screening for experiment prioritization; never a rollout or financial approval",
        recommendation_rationale=rationale,
        warnings=warnings,
        assumptions=[
            "The last observed non-promotion units are a usable short-horizon baseline.",
            "The 90th percentile of pre-event one-week residuals is a useful audit interval.",
            "No unobserved distribution or assortment change invalidates the comparison.",
        ],
        evidence_refs=[
            "docs/data-acquisition.md",
            "reports/phase-02/forecast-evaluation.json",
            "docs/evaluation-protocol.md",
        ],
        claim_language="observed-minus-baseline estimate; causal treatment effect and financial impact not identified",
    )
