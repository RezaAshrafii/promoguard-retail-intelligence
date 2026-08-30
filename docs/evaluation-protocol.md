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
  one-step-difference scale.
- The seasonal interval is a non-parametric 90th percentile absolute seasonal residual interval
  computed from training history only. Coverage is the fraction of held-out actuals inside it.
- A lower WAPE is forecast evidence only. It is not evidence that a promotion caused lift or profit.
