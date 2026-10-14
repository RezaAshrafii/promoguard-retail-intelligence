# Evaluation protocol

1. The public dunnhumby panel is used for engineering, forecasting, and observational audit evidence.
2. A documented public randomized experiment such as Criteo Uplift is required before benchmarking treatment-effect estimators.
3. The initial Criteo benchmark is an aggregate ITT risk difference for visit and conversion. It
   validates published schema, treatment-arm counts, feature balance, and normal-approximation
   intervals; it does not condition on post-treatment exposure or claim CATE truth.
4. All forecasting evaluation uses rolling-origin time splits.
5. Every proposed *retail* causal result reports overlap, pre-trend, placebo, missingness, and
   sensitivity diagnostics. Criteo has no retail time series or SKU structure, so it cannot supply
   those retail diagnostics.
6. Every recommendation has an uncertainty interval and may abstain.
7. Business evaluation prioritizes decision regret and harmful approvals over a single accuracy metric.
8. A real retail causal/business-impact claim requires a design partner and an approved experiment.

## Hillstrom subgroup diagnostic

- `history_segment` is treated as a pre-assignment characteristic. The report compares each of two
  assigned email arms with the no-email arm inside each of the seven publisher-defined categories.
- The confirmatory primary report remains the three overall predeclared contrasts. Subgroup estimates
  are exploratory and do not replace or revise those overall results.
- The family is fixed at 14 contrasts (seven strata times two treatment arms). Welch normal intervals
  use a Bonferroni two-sided tail probability based on all 14, even when one or more strata have too
  few observations to interpret.
- Direction is withheld unless each arm has at least 1,000 assigned rows. This product guardrail is
  not a power calculation and does not guarantee useful precision.
- No interaction test is performed. “Evidence in one subgroup but not another” is not evidence that
  subgroup effects differ. The output must not be used to target people, select a rollout audience,
  or claim a validated CATE model.

## Forecasting baseline protocol

- The source calendar is weekly, so the seasonal-naive lag is 52 weeks; no daily frequency is
  fabricated.
- Splits are expanding windows with a 104-week minimum history, four-week horizon, and eight-week
  step. Every prediction is generated from rows at or before that fold's cutoff.
- Promotion rows are excluded from lag history and the evaluation target is non-promotion rows.
- The seasonal baseline is compared with a recursive one-week persistence reference on paired rows
  where both predictions are available. Every report exposes the paired coverage ratio, excluded
  row count, mutually exclusive missing-prediction reasons, and the same accounting per fold.
- WAPE is total absolute error divided by total absolute actual units. Bias is signed error divided
  by total actual units. MASE is the mean per-series MAE divided by that series' training
  one-step-difference scale. The scale uses only non-promotion observations exactly seven days
  apart; it never bridges a removed promotion week or another calendar gap.
- The seasonal interval is a non-parametric 90th percentile absolute seasonal residual interval
  computed from training history only. Coverage is the fraction of held-out actuals inside it.
- A lower WAPE is forecast evidence only. It is not evidence that a promotion caused lift or profit.

## Promotion-audit protocol

- Consecutive promoted weeks for one store and UPC form one episode. A gap longer than seven days
  starts a new episode.
- The audit baseline is recursive one-week persistence initialized from the last non-promotion
  observation before the event. During-event or post-event outcomes never enter the baseline.
- The audit interval uses the 90th percentile absolute one-week residual from consecutive
  non-promotion history before the event. It is a screening interval, not a causal confidence
  interval.
- Screening thresholds are emitted as typed `AuditPolicy` metadata. Policy v1.0.0 uses four-week
  pre/post windows, a post-to-pre ratio below 0.8 for a blocking forward-buy warning, and a
  recent-pre to older-history ratio outside 0.5–1.5 for severe shift. Policy v1.1.0 adds an
  opt-in same-store, same-category neighbor screen: a neighbor must have complete pre/during
  windows and no promotion in either window, and is reported only when its during-to-pre ratio is
  below 0.8. A detected neighbor is a blocking *candidate* for investigation, not identified
  cannibalization. These are conservative screening rules, not learned causal or financial
  decision thresholds.
- Full promotion economics remain unavailable. An optional contribution assumption must include an
  amount per incremental unit, ISO currency, and source. Its sensitivity output never changes the
  screening recommendation and is not promotion profit or gross-margin impact.
- Missing inventory emits `STOCKOUT_UNOBSERVABLE`; observed zero inventory emits a blocking
  `STOCKOUT_RISK` warning.
- The cross-SKU screen never fills an absent neighbor week with zero, never uses a concurrently
  promoted neighbor as a comparator, and ranks at most three candidates by observed unit decline.
  It does not estimate a substitution effect because assortment changes, category demand shifts,
  price changes, and unobserved confounders remain possible.
- A positive units-difference interval returns `candidate_for_controlled_test`; a negative interval
  returns `deprioritize_and_investigate`; blockers or an interval crossing zero return
  `needs_more_evidence`. The output never approves rollout, identifies causal effect, or estimates
  financial impact.
