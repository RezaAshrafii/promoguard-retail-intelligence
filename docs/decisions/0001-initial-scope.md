# ADR 0001: Start with an evidence-aware promotion-audit vertical slice

- Status: accepted retrospectively under the owner-approved foundation gate
- Date reviewed: 2026-08-31
- Decision class: architecture accepted; owner mastery checklist remains explicit
- Record type: retrospective ADR

## Context

PromoGuard targets a real retail decision: whether an observed promotion deserves a controlled
test. The public dataset contains weekly sales, prices, and promotion support, but it does not
contain inventory, full cost economics, assignment probabilities, or a verified counterfactual.
The largest early risk is therefore unsupported interpretation, not lack of model complexity.

## Decision

Build one deterministic and auditable vertical slice first:

```text
real public workbook -> validated weekly panel -> time-aware forecast evidence
    -> observational promotion audit -> typed recommendation and limitations -> local demo
```

Do not add autonomous execution, an LLM narrator, causal-effect language, or production
infrastructure until the deterministic contracts and evidence gates exist.

## Alternatives considered

### Start with a broad marketing copilot

Rejected. Natural-language breadth would hide missing data and make numerical verification harder.

### Start with a production warehouse and orchestration stack

Deferred. Those components become useful only when a repeatable external data flow exists.

### Start immediately with causal estimation

Deferred. A causal benchmark needs treatment/outcome definitions and diagnostics that this retail
dataset alone cannot provide.

## Consequences

- the current product is an experiment-prioritization aid, not an automatic promotion optimizer;
- every result preserves assumptions, warnings, policy version, and provenance;
- planned modules remain in the roadmap instead of appearing as empty runtime packages;
- business validation requires a design partner and controlled experiment.

## Reversal condition

Broaden the architecture only when a concrete phase has a real dataset, an acceptance test, an
identified user decision, and evidence that the added component reduces a measured bottleneck.

## Owner mastery check

Before presenting this ADR, the owner should be able to explain why a narrow trustworthy result is
more valuable than a feature-rich system whose causal and financial claims cannot be verified.

