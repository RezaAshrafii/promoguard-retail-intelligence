# Evaluation protocol

1. The public dunnhumby panel is used for engineering, forecasting, and observational audit evidence.
2. A documented public randomized experiment such as Criteo Uplift is required before benchmarking treatment-effect estimators.
3. All forecasting evaluation uses rolling-origin time splits.
4. Every causal result reports overlap, pre-trend, placebo, and missingness diagnostics.
5. Every recommendation has an uncertainty interval and may abstain.
6. Business evaluation prioritizes decision regret and harmful approvals over a single accuracy metric.
7. A real retail causal/business-impact claim requires a design partner and an approved experiment.
