# ADR 0005: Preserve the negative seasonal-naive benchmark result

- Status: accepted retrospectively under the owner-approved foundation gate
- Date reviewed: 2026-08-31
- Record type: retrospective ADR

## Context

Forecast evidence is evaluated in six expanding time windows. Promotion rows are excluded from
lag history and scoring, MASE scaling uses consecutive non-promotion weeks, and model comparison is
paired only where both models produce a prediction.

On 41,516 paired rows, the 52-week seasonal-naive model has WAPE 0.4005 versus 0.3483 for the
recursive one-week naive reference. Seasonal-naive therefore does not beat the simpler reference.
Paired coverage is 71.42% of eligible non-promotion test rows and is disclosed separately.

## Decision

Keep both transparent baselines and publish the negative comparison. Use recursive naive as the
short-horizon audit baseline while retaining seasonal naive as a benchmark, not as a claimed win.
A future candidate must use the same leakage-safe splits and paired eligibility accounting.

## Alternatives considered

- hide the weaker model: rejected because it destroys falsifiability;
- tune on the test folds until it wins: rejected because it leaks evaluation information;
- introduce a complex model immediately: deferred until it has a predeclared gate and interpretable
  failure analysis.

## Consequences

- the portfolio demonstrates honest model selection rather than a guaranteed positive result;
- missing seasonal history remains visible through the 71.42% coverage figure;
- no forecasting metric is described as causal promotion impact.

## Reversal condition

Replace the audit baseline only when a documented candidate improves the predefined metrics across
time folds, preserves coverage or explains exclusions, and passes leakage and stability checks.

## Owner mastery check

The owner should be able to explain WAPE, MASE, paired comparison, why time splits replace random
splits, and why a negative result is useful evidence.
