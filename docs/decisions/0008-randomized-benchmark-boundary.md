# ADR 0008: Separate the Criteo randomized benchmark from the retail audit

- Status: accepted
- Date: 2026-09-02
- Owner: Reza

## Context

The dunnhumby retail panel is real retail data, but promotion assignment is observational. Calling
an observed-minus-forecast difference causal lift would be incorrect. Criteo publishes a separate,
anonymized dataset from advertising incrementality tests with treatment, visit, and conversion.

## Decision

Use Criteo Uplift v2.1 only as an external randomized-experiment benchmark. The first benchmark is
an aggregate intention-to-treat (ITT) risk difference for visit and conversion, with feature-balance
diagnostics and normal-approximation 95% intervals. Read the 14M-row CSV in chunks and retain only
aggregate sums in the report.

Do not use `exposure` as a predictor, covariate, or outcome because it is post-treatment. Do not
treat this benchmark as validation of a causal effect for a retail SKU, the dunnhumby panel, an
Iranian customer, or a financial decision.

## Consequences

- PromoGuard demonstrates real randomized-data engineering without overstating the retail audit.
- Code, metadata, checksum, and aggregate results are versioned; raw Criteo data remains ignored
  and retains the publisher's CC BY-NC-SA 4.0 terms.
- Future CATE ranking requires a separately predeclared holdout, policy metric, and leakage review.
