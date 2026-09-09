# ADR 0009: Require evidenced promotion economics before optimization

- Status: accepted for Phase 8.1
- Date: 2026-09-09
- Decision class: financial-input and safety boundary

## Context

The public retail source does not contain unit cost, trade spend, supplier funding, or inventory.
Optimizing with invented values would produce precise-looking but unsupported financial output.
Financial floats, silently defaulted costs, mixed currencies, and untraceable assumptions would
also make later results difficult to audit.

## Decision

Before implementing scenario ranking or optimization, require a frozen typed contract that:

- uses decimal financial values and one ISO-style currency per request;
- requires explicit values for cost, funding, fixed and variable trade spend, and inventory;
- records one provenance item for every financially material field;
- distinguishes partner exports, contracts, model output, and approved assumptions;
- requires human approval and forbids automatic execution;
- reports all failed constraints without ranking or selecting a scenario.

An approved assumption is allowed only when it is labeled as such. It is not converted into an
observed value or customer evidence.

## Consequences

- Phase 8 can progress without fabricating business data.
- A future partner export has a concrete data request and validation target.
- Infeasible candidates remain visible for diagnosis instead of disappearing silently.
- The current feasibility output is not a profit forecast, causal estimate, recommendation, or
  rollout approval.

## Deferred work

Portfolio selection, objective functions, uncertainty-aware comparison, and solver tests remain in
Phase 8.2. They may use only validated inputs that satisfy this contract.
