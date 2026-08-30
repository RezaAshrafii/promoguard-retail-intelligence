# AI Usage and Human Ownership

PromoGuard is openly AI-assisted. AI tools accelerate research, implementation drafts,
refactoring, test generation, documentation, adversarial review, and presentation iteration. They
do not replace evidence, executable tests, or the project owner's responsibility for submitted
claims.

## Responsibility boundary

| Area | AI may assist | Acceptance authority |
|---|---|---|
| Code and tests | propose, implement, review, find edge cases | repository gates and owner approval |
| Statistical design | compare methods and expose risks | documented protocol plus human review |
| Business claims | draft bounded wording | owner; only with linked evidence |
| Park application | organize and edit | Reza submits and owns every statement |
| Automated decisions | not enabled | future explicit human policy required |

No important output is accepted solely because a model recommended it. Material changes require a
diff review, relevant tests, real-data artifact regeneration, and a decision record when assumptions
or claim boundaries change. Numerical dashboard content must come from deterministic typed domain
results; an LLM is not in the current runtime path.

## Decision labels

- `HUMAN_APPROVED`: the owner explicitly authorized the decision after a plain-language review.
- `accepted retrospectively under the owner-approved foundation gate`: the implementation belongs
  to an approved cleanup scope, but the owner mastery checklist remains visible.
- `proposed`: not yet accepted for implementation or external claims.

These labels deliberately separate project authorization from the ability to defend every technical
detail in an interview. The Persian learning guides under `learning/` are the path to that mastery.

## Decision records

- [ADR 0001](docs/decisions/0001-initial-scope.md): narrow evidence-aware product scope.
- [ADR 0002](docs/decisions/0002-foundation-correctness-gate.md): pause expansion and repair the
  foundation first.
- [ADR 0003](docs/decisions/0003-versioned-observational-audit-policy.md): version screening rules.
- [ADR 0004](docs/decisions/0004-public-dataset-choice.md): real public dataset and provenance.
- [ADR 0005](docs/decisions/0005-forecast-baseline.md): preserve a negative benchmark result.
- [ADR 0006](docs/decisions/0006-observational-claim-boundary.md): observational, abstention-first
  output language.

## Current mastery status

The architecture and release-gate direction were owner-approved. Each ADR includes an “Owner
mastery check” because approval is not presented as proof of complete statistical mastery. Before
an external presentation, Reza should work through those checks and the matching Persian learning
folder, then record any disagreement as a new decision rather than silently rewriting history.

## Privacy and data policy

Raw/processed public data, API keys, personal application fields, and unverified traction are not
committed. Public benchmark evidence is never presented as customer impact. Dataset terms and
provenance remain separate from the source-code license.
