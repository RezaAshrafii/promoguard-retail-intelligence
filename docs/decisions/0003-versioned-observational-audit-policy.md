# ADR 0003: Version the observational audit screening policy

- Status: accepted under Release Gate 5.1
- Date: 2026-08-31
- Owner: Reza
- Policy: `promoguard-observational-screening` version `1.0.0`

## Context

The audit used sensible but implicit numeric thresholds for minimum history, pre/post windows,
severe pre-event shift, and forward-buy risk. The numbers were documented, but they were embedded
inside function defaults and conditional statements. A result therefore did not carry the policy
that produced its warnings.

This is a reproducibility risk. If a threshold changes later, two payloads could have different
recommendations while appearing to use the same rules.

## Decision

Create a frozen, extra-forbidden Pydantic `AuditPolicy` and include the full policy in every
`PromotionAuditResult`. Version 1.0.0 records:

- 52 non-promotion history rows for deterministic representative-event selection;
- 26 rows for the audit short-history blocker;
- four-week pre and post windows;
- twelve older-history rows for the shift reference;
- severe-shift range 0.5 through 1.5;
- forward-buy ratio threshold 0.8.

The policy can be supplied as a typed object or loaded by the CLI from a JSON file. The default
configuration is committed at `configs/audit-policy-v1.json`.

## Interpretation boundary

These values are conservative product-screening rules. They are not learned from a causal loss
function, calibrated to promotion profit, approved by a retail design partner, or evidence that a
promotion should be rolled out. A custom policy changes warnings and screening recommendations;
it does not change observed units or the pre-event baseline calculation.

## Consequences

- every audit payload identifies its exact policy;
- invalid or unknown policy fields are rejected;
- a policy change requires a new version and regenerated evidence;
- tests prove that relaxing a warning threshold changes the warning, while observations and
  baseline remain unchanged;
- API and dashboard outputs gain policy metadata without accepting arbitrary public caller policy.

## Reversal condition

A later policy may replace these thresholds after a documented design-partner study, explicit loss
function, calibration data, and human approval. It must receive a new version rather than silently
changing v1.0.0.
