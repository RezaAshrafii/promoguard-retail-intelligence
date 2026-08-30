# PromoGuard agent instructions

Before making changes, read these files completely:

1. `PARK_SUBMISSION_AGENT_HANDOFF.md` while the Park submission sprint is active
2. `IMPLEMENTATION_AGENT_PROMPT.md`
3. `ROADMAP.md`
4. `README.md`
5. `docs/problem-brief.md`
6. `docs/evaluation-protocol.md`
7. `docs/limitations.md`
8. `docs/decisions/0001-initial-scope.md`

`ROADMAP.md` is the source of truth for phase state. Work on the single `ACTIVE` phase unless the launch prompt explicitly selects continuous mode. Preserve the evidence policy: public benchmark data must never be presented as measured business impact.

Keep calculations in `src/promoguard`; API and dashboard code are adapters. Prefer a small, tested vertical slice over additional frameworks. Do not add LLM calls until deterministic analytical outputs and their tests exist.

Before each phase execution, select the model and reasoning level using
`docs/model-selection-plan-fa.md`; record any model change and its reason in the phase report.

For every completed roadmap phase, create a dedicated Persian learning folder under
`learning/NN-phase-name/` with `README.fa.md`. Explain the goal, architecture, every changed file,
commands, test evidence, data assumptions, limitations, common interview questions, and a simple
step-by-step explanation. Update the folder in the same phase commit as the code.

Use professional Git history after the user reviews the changes: commits use
`type(phase-NN): concise outcome`, such as `feat(phase-01): ingest and validate public retail data`;
tags use annotated names such as `v0.1.0-phase-01`; never commit raw/processed datasets, credentials,
virtual environments, or large archives; and never push until a configured remote and authorized
authentication are available.
