# ADR 0002: Foundation correctness gate before causal benchmarking

- Status: accepted — `HUMAN_APPROVED`
- Date: 2026-08-30
- Owner: Reza
- Tracking issue: https://github.com/RezaAshrafii/promoguard-retail-intelligence/issues/1
- Scope: retrospective review of Phases 1–5 and prospective gate for Phase 6

## Context

Phases 1–5 produced a tested real-data promotion-audit MVP and Park submission package. Before
starting causal benchmarking, an adversarial review found three foundation risks:

1. an observational units difference and a user-supplied unit-margin assumption could be read as
   promotion profit and could affect an `approve` decision;
2. the MASE scale could bridge a removed promotion week and treat non-consecutive observations as a
   one-week difference;
3. canonical grain columns could exist while `store_id` or `upc` values were missing or blank.

These are correctness and claim-boundary risks. Adding a causal model before resolving them would
make the architecture wider without making its foundation more trustworthy.

## Decision

Pause Phase 6 and complete a versioned foundation-correctness release first.

The release must:

- separate observational units-difference evidence from financial sensitivity;
- prevent financial assumptions from driving the screening recommendation;
- compute MASE scale from consecutive non-promotion weeks only;
- enforce one shared grain-identifier policy across ingestion and application boundaries;
- regenerate affected evidence and preserve an old-versus-new explanation;
- keep the filesystem-path API local-only until a public storage and authorization boundary exists.

Scientific and portfolio evidence continues to use real data. A future bundled quick-demo fixture,
if added, is software execution evidence only and must never be reported as scientific or business
evidence.

## Human approval

The owner received a plain-language explanation of the failure modes, alternatives, and recommended
architecture, then explicitly approved all eight foundation decisions on 2026-08-30. This record
does not claim that earlier decisions were human-verified at the time they were first implemented.

## Alternatives considered

### Continue Phase 6 and fix the foundation later

Rejected. It would allow new causal outputs to depend on ambiguous contracts and metrics.

### Keep `approve/reject/experiment` and add stronger disclaimers

Rejected. Disclaimers do not remove the machine-readable financial and rollout implication.

### Remove every financial calculation

Not selected. A clearly isolated contribution-sensitivity calculation remains useful when its
assumption, currency, source, and non-profit limitation are explicit and it cannot change the
screening recommendation.

### Commit a small real-data extract for the quick demo

Deferred until redistribution rights are verified. No public-data subset will be committed merely
for convenience.

## Consequences

- The audit API contract will make a deliberate pre-production breaking change.
- Phase-2 and Phase-3 evidence must be regenerated after their respective fixes.
- Phase 6 resumes only after tests, documentation, CI, and the correctness release tag pass.
- Existing public claims that imply measured profit or unsupported rollout decisions must change.

## Reversal conditions

Financial decisioning may be introduced only when an approved data contract provides regular and
promotion price, unit cost, trade spend or funding, relevant variable costs, currency, and a defined
counterfactual economic formula. Rollout recommendations require causal evidence and an explicit
business policy; a positive observational units difference is not sufficient.
