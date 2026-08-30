# ADR 0006: Keep promotion audit observational and abstention-first

- Status: accepted retrospectively under the owner-approved foundation gate
- Date reviewed: 2026-08-31
- Record type: retrospective ADR

## Context

Observed promotion-period units and a forecast baseline can be compared, but the missing
counterfactual is not observed. Demand may also be affected by distribution, stockouts, competitor
actions, assortment changes, seasonality, and forward buying. The dataset does not identify all of
these mechanisms.

## Decision

Name the output `estimated_units_difference_vs_baseline`, describe it as observational screening,
and restrict recommendations to `candidate_for_controlled_test`, `deprioritize_for_now`, or
`needs_more_evidence`. Blocking diagnostics force abstention. Optional contribution sensitivity is
isolated from the recommendation and is never called promotion profit.

## Alternatives considered

- call observed minus forecast “causal lift”: rejected because no identification design supports it;
- use stronger disclaimers while keeping rollout approval: rejected because machine-readable
  semantics still imply unsupported action;
- remove every useful comparison: rejected because transparent screening can still prioritize
  experiments when its limitations travel with the result.

## Consequences

- the dashboard and API render domain results without inventing new analytical formulas;
- every result carries warnings, assumptions, evidence references, and policy version;
- a representative real-data audit may correctly end in `needs_more_evidence`.

## Reversal condition

Causal language requires a defensible experiment or identification design, treatment/outcome
definitions, overlap and pre-trend diagnostics where relevant, uncertainty calibration, and a
documented human approval gate.

## Owner mastery check

The owner should be able to explain the missing counterfactual, why forecast error is not treatment
effect, and why abstaining can be the most valuable product output.
