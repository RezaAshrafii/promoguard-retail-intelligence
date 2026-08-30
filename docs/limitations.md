# Current limitations

- Phase 2 contains measured baselines, not a production-trained demand model.
- On the current public panel, the seasonal-naive baseline is weaker than the recursive one-week
  reference on the paired backtest; it must not be presented as a model improvement.
- No real company data or customer outcome is included.
- Observational promotion data cannot by itself prove causality.
- Public datasets may not represent Iranian retail behavior, pricing, inflation, or distribution.
- The public source has no product cost or inventory fields; profit and stockout claims are unavailable.
- Missing price values are preserved and reported; they are not silently imputed in phase 1.
- The phase-3 interval is based on historical persistence residuals; it is not a causal confidence
  interval and is not yet calibrated for business decision costs.
- The public phase-3 audit has no unit cost or inventory observations, so margin remains unavailable
  and stockout-censored demand cannot be ruled out.
- The current audit examines one SKU/store episode at a time; cross-SKU cannibalization is deferred
  to phase 7.
