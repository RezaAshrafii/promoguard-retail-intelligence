# Current limitations

- Phase 2 contains measured baselines, not a production-trained demand model.
- On the current public panel, the seasonal-naive baseline is weaker than the recursive one-week
  reference on the paired backtest; it must not be presented as a model improvement.
- No real company data or customer outcome is included.
- Observational promotion data cannot by itself prove causality.
- Public datasets may not represent Iranian retail behavior, pricing, inflation, or distribution.
- The public source has no product cost or inventory fields; promotion-profit and stockout claims
  are unavailable.
- Missing price values are preserved and reported; they are not silently imputed in phase 1.
- The phase-3 interval is based on historical persistence residuals; it is not a causal confidence
  interval and is not yet calibrated for business decision costs.
- The public phase-3 audit has no unit cost or inventory observations. An optional contribution
  sensitivity is assumption-driven, not measured financial impact, and stockout-censored demand
  cannot be ruled out.
- Policy v1.1.0 adds a same-store, same-category co-movement screen, but it is not a causal
  cannibalization estimator. It excludes missing and concurrently promoted neighbors and reports
  only candidates for controlled follow-up.
- Phase 8.1 validates real promotion-economics inputs and screens constraints only. `eligible` does
  not mean profitable, causal, optimal, or approved; scenario ranking and portfolio optimization
  remain unimplemented, and the public demo has no partner economics data.
- Hillstrom's purchase-history breakdown is an exploratory randomized email assignment analysis
  with 14 Bonferroni-adjusted within-stratum contrasts and two Bonferroni-adjusted global
  Cochran-Q heterogeneity tests. The tests use an asymptotic chi-square reference and do not identify
  which stratum differs, provide individual treatment effects, identify a profitable audience, or
  validate targeting. A non-significant test does not establish equal effects. Inferential global
  Q/p-values are hidden unless every treatment/control cell has at least 1,000 assigned rows; this
  reuses the individual-stratum display gate as a conservative product policy, not as a power or
  calibration guarantee. Missing/unstable calculations abstain with explicit statuses instead of
  reporting a no-evidence p-value.
