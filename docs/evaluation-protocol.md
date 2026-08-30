# Evaluation protocol

1. The public dunnhumby panel is used for engineering, forecasting, and observational audit evidence.
2. A documented public randomized experiment such as Criteo Uplift is required before benchmarking treatment-effect estimators.
3. All forecasting evaluation uses rolling-origin time splits.
4. Every causal result reports overlap, pre-trend, placebo, and missingness diagnostics.
5. Every recommendation has an uncertainty interval and may abstain.
6. Business evaluation prioritizes decision regret and harmful approvals over a single accuracy metric.
7. A real retail causal/business-impact claim requires a design partner and an approved experiment.

## Forecasting baseline protocol

- The source calendar is weekly, so the seasonal-naive lag is 52 weeks; no daily frequency is
  fabricated.
- Splits are expanding windows with a 104-week minimum history, four-week horizon, and eight-week
  step. Every prediction is generated from rows at or before that fold's cutoff.
- Promotion rows are excluded from lag history and the evaluation target is non-promotion rows.
- The seasonal baseline is compared with a recursive one-week persistence reference on paired rows
  where both predictions are available.
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
- Pre and post windows are four weeks by default. A post-to-pre ratio below 0.8 triggers a blocking
  forward-buy warning; a recent-pre to older-history ratio outside 0.5–1.5 triggers severe shift.
- Full promotion economics remain unavailable. An optional contribution assumption must include an
  amount per incremental unit, ISO currency, and source. Its sensitivity output never changes the
  screening recommendation and is not promotion profit or gross-margin impact.
- Missing inventory emits `STOCKOUT_UNOBSERVABLE`; observed zero inventory emits a blocking
  `STOCKOUT_RISK` warning.
- A positive units-difference interval returns `candidate_for_controlled_test`; a negative interval
  returns `deprioritize_and_investigate`; blockers or an interval crossing zero return
  `needs_more_evidence`. The output never approves rollout, identifies causal effect, or estimates
  financial impact.
