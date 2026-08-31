# PromoGuard active development roadmap

Last updated: 2026-08-31
Roadmap owner: Reza  
Execution rule: exactly one phase or release gate is `ACTIVE`.

## Outcome and deadline tracks

The roadmap has two speeds:

- **Submission track:** produce a narrow but honest MVP package by **2026-09-04 (13 Shahrivar 1405)**. This is a five-day sprint, so the submission should promise a validated pilot, not a complete enterprise platform.
- **Professional track:** extend the same codebase after submission into a production-minded portfolio project with causal validation, monitoring, optimization, and verified AI explanations.

## Active Park-submission execution overlay

The official deadline remains 2026-09-04, but the internal send deadline is **2026-09-02 at 15:00
Tehran time**. The Park sprint does not change the single-active-gate rule: Release Gate 5.1 and
reviewer Demo Mode are closed, final submission evidence refresh is ACTIVE, and Phase 6 remains
PAUSED.

Execution documents:

- `submission/park-application-1405/MASTER-SUBMISSION-ROADMAP-FA.md` — dated delivery gates,
  package manifest, reviewer questions, and send criteria;
- `submission/park-application-1405/video-production-plan-fa.md` — reviewer demo mode, shot list,
  recording QA, and prohibited edits;
- `docs/research/park-competitive-profile-benchmark-fa.md` — evidence-based benchmark of accepted
  team patterns and application quality;
- `PARK_SUBMISSION_AGENT_HANDOFF.md` — continuation contract for any future coding agent.

Submission work must not create a second active development phase. Correctness and evidence refresh
come before UI polish; external PDFs and video come only after release numbers are frozen.

## System architecture

```text
                         PromoGuard modular monolith

  dunnhumby workbook + store lookup + product lookup
       \                    |                    /
        +------ ingestion + Pydantic contracts ------+
                              |
                    canonical weekly panel
                              |
          +-------------------+-------------------+
          |                   |                   |
     forecasting       promotion effect    cannibalization
          |                   |                   |
          +---------- diagnostics + uncertainty --+
                              |
                 profit scenario + abstention
                              |
                    verified insight JSON
                         /           \
                    FastAPI       Streamlit
```

The first submission implements the center path with a documented public retail dataset. Later phases deepen causal claims and production engineering without replacing the first slice.

## Phase-state summary

| Phase | Deliverable | Target | State |
|---|---|---:|---|
| 0 | Repository scaffold and evidence policy | complete | DONE |
| 1 | Real-data acquisition, contracts, and validation slice | 2026-08-30 | DONE |
| 2 | Forecasting baseline and rolling-origin evaluation | 2026-08-31 | DONE |
| 3 | Honest promotion-audit MVP | 2026-09-01 | DONE |
| 4 | End-to-end API/dashboard demo | 2026-09-02 | DONE |
| 5 | Park submission evidence package | 2026-09-03/04 | DONE |
| 5.1 | Foundation correctness release | before Demo Mode | DONE |
| 5.2 | Reviewer-focused real-data Demo Mode | immediately after 5.1 | DONE |
| 5.3 | Final submission evidence refresh | before recording/submission | ACTIVE |
| 6 | Real-experiment causal benchmarking | after correctness gate | PAUSED |
| 7 | Cannibalization, forward-buy, uncertainty, abstention | 2026-09-15 to 09-24 | PENDING |
| 8 | Constrained profit optimization | 2026-09-25 to 10-04 | PENDING |
| 9 | Production data, monitoring, and optional verified LLM layer | 2026-10-05 to 10-19 | PENDING |
| 10 | Portfolio, AIIF, and job-application packaging | 2026-10-20 to 10-25 | PENDING |

## Phase 0 — DONE — Scaffold and evidence policy

Delivered:

- Python package, FastAPI health endpoint, Streamlit placeholder, tests, and CI scaffold.
- Domain module boundaries.
- Problem brief, evaluation protocol, limitations, model-card scaffold, and initial ADR.
- Explicit rule against unsupported causal and business-impact claims.

Evidence:

- `python -m compileall` passed when the initial scaffold was created.
- Full pytest execution was not available at scaffold time because development dependencies were not installed.

## Phase 1 — DONE — Real-data acquisition and validation

Plain-language goal: download a documented public retail dataset, understand its grain and limitations, and reject broken input before any model sees it. The product path must not depend on synthetic business data.

### Selected data stack

Use these sources as separate, clearly labeled evidence tracks:

1. **Primary promotion dataset — dunnhumby Breakfast at the Frat:** 156 weeks, five products, three brands, four categories, unit sales, households, visits, spend, base price, shelf price, and promotional support. This is the closest public match to promotion-effectiveness analysis. The publisher describes it as a representation/inspired real-world source, not raw identifiable production data; state that accurately.
2. **Forecasting scale dataset — Walmart M5:** daily item/store sales, calendar events, and sell prices. Use it for hierarchical forecasting and price-response engineering. Do not call price changes a verified promotion flag, and do not claim causal promotion lift from M5 alone.
3. **Causal marketing benchmark — Criteo Uplift v2.1:** anonymized randomized incrementality-test records with treatment, visit, and conversion. Use it only for uplift/ITE evaluation; it has no SKU, price, cost, or retail inventory semantics.
4. **Stockout research track — FreshRetailNet-50K:** public fresh-retail panel with stockout annotation. Use it for censored-demand and stockout diagnostics, not as a promotion dataset unless its schema proves promotion fields exist.

The first demo should use **Breakfast at the Frat** only. Add the other sources as separate adapters after the primary path works.

Required deliverables:

- A data acquisition note recording source URL, download date, terms, file hashes, columns, grain, and known limitations.
- A raw/processed directory convention that keeps downloaded data out of Git and preserves a reproducible transformation script.
- Explicit contracts for the actual primary dataset fields; do not invent inventory or cost columns. If cost is absent, report units/revenue and label profit as unavailable.
- CSV loaders that return a structured quality report with row counts, missing columns, invalid values, duplicates, date gaps, and price/promotion consistency checks.
- A canonical weekly panel builder matching the source grain. Do not force weekly data into a fake daily panel.
- CLI commands:
  - `promoguard ingest --input data/raw/breakfast-at-the-frat`
  - `promoguard validate --input data/processed/breakfast-at-the-frat`
  - existing `promoguard health`
- Unit tests for valid input and at least six important invalid-input cases, plus a small checked-in schema fixture with no real customer identifiers.
- README instructions that work from a clean local environment.

Acceptance gate:

- The source can be downloaded manually from its publisher page and the transformation is reproducible from a documented command.
- Valid primary files pass with a machine-readable quality summary.
- Tests prove negative units, impossible prices/discounts, duplicate grain, missing columns, invalid dates, and inconsistent promotion fields are rejected or clearly flagged.
- Ruff, pytest, compileall, and CLI smoke checks pass.
- No forecasting, causal, optimization, or LLM code is added in this phase.

Completion evidence:

- Date/time: 2026-08-30 09:06 +03:30.
- Source: official dunnhumby workbook; SHA-256 and provenance recorded in
  `docs/data-acquisition.md` and generated `provenance.json`.
- Delivered: weekly source contract, workbook/processed loaders, canonical 27-column weekly panel,
  lookup-safe joins, CLI ingestion/validation, machine-readable quality report, schema fixture,
  and source/quality/reproduction documentation.
- Validation commands: `python -m ruff check .`, `python -m pytest -q`,
  `python -m compileall -q src apps`, `python -m promoguard.cli health`, real-data `ingest`, and
  processed-data `validate`.
- Results: Ruff passed; 19 tests passed; compile and CLI smoke checks passed; 524,950 canonical
  rows; 0 duplicate grain rows; 0 date/numeric parse errors; 0 negative discounts; 149,386
  promotion rows; complete product/store lookup coverage.
- Quality warnings: 23 missing observed prices, 185 missing base prices, one zero-price/free-promotion
  row, 6,047 observed prices above base price, and four duplicate store-lookup rows collapsed
  without discarding conflicting segment metadata.
- Learning guide: `learning/01-real-data-foundation/README.fa.md` documents the phase in Persian,
  including the architecture, code changes, reproduction steps, results, tests, limitations, and
  interview preparation.
- Remaining limitations: no cost, margin, inventory, stockout, or causal identification fields;
  public data does not establish Iranian business impact.

## Phase 2 — DONE — Forecasting baseline and evaluation

Plain-language goal: estimate what normal sales would have looked like without a promotion, and prove the estimate is better than a naive reference on past time windows.

Deliverables and gate:

- Seasonal-naive baseline first; add one simple statistical or tree model only if it beats the baseline consistently.
- Expanding/rolling-origin splits with no future information in features.
- WAPE, MASE, bias, and interval coverage by SKU/store and overall.
- Tests for leakage and temporal ordering.
- A compact JSON evaluation artifact and one readable plot/table.
- Gate: pipeline runs from the documented public dataset, metrics are reproducible, and any claimed improvement includes uncertainty across folds.

Completion evidence:

- Date/time: 2026-08-30.
- Delivered: seasonal-naive and recursive naive baselines, expanding rolling-origin splits,
  paired eligibility filtering, WAPE/MASE/bias metrics, training-only 90% intervals, segment
  metrics by UPC and store, CLI execution, tests, and machine-readable artifacts.
- Command: `python -m promoguard.cli forecast-evaluate --input data/processed/breakfast-at-the-frat --output reports/phase-02`.
- Artifacts: `reports/phase-02/forecast-evaluation.json`,
  `reports/phase-02/forecast-evaluation.csv`, and
  `reports/phase-02/forecast-segment-metrics.csv`.
- Six folds were evaluated with 104-week minimum history, four-week horizon, and eight-week
  step. The paired comparison scored 41,516 non-promotion rows.
- Seasonal-naive overall: WAPE 0.40046, MASE 1.20059, bias -0.01822, interval coverage 0.88108.
- Recursive naive overall: WAPE 0.34828, MASE 1.09469, bias 0.03114. Seasonal-naive WAPE
  improvement versus reference was -0.05218, so no model improvement is claimed.
- Tests cover temporal ordering and future-value invariance. Ruff, 23 tests, compileall, CLI
  health, and real-data evaluation passed.
- Learning guide: `learning/02-forecasting-baseline/README.fa.md`.

## Phase 3 — DONE — Honest promotion-audit MVP

Plain-language goal: compare observed promotion-period sales with the validated no-promotion baseline, while labeling the result as an audit estimate rather than a causal claim.

Deliverables and gate:

- Incremental units and gross-margin scenario computed from observed minus baseline.
- Stockout, missing-cost, short-history, and severe-shift warnings.
- Pre-, during-, and post-promotion windows to reveal forward-buy risk.
- Typed result with estimate, interval, assumptions, evidence references, and `approve/reject/experiment` decision.
- Gate: documented observational cases trigger expected signs and warnings; output never says “caused” without a defensible identification design.

Completion evidence:

- Date/time: 2026-08-30.
- Model/reasoning review: `gpt-5.6-sol` with `xhigh` was selected for the statistical and claim-language risk of this phase.
- Delivered: deterministic promotion-episode detection, pre-event-only recursive baseline,
  incremental-unit interval, optional margin scenario, pre/during/post summaries, shift/stockout/
  short-history/forward-buy diagnostics, typed evidence payload, and `approve/reject/experiment`
  screening logic.
- Real-data selection rule: earliest episode with at least 52 non-promotion history rows and a
  complete four-week post window; no outcome-based event cherry-picking.
- Selected audit: store 23345, UPC 2840004768, 2010-01-13 through 2010-02-10. Observed units 128;
  baseline 185 [115, 255]; observational incremental estimate -57 [-127, 13].
- Decision: `experiment`. Blocking evidence: source cost is unavailable and post/pre ratio 0.725
  triggers forward-buy risk. Inventory is unavailable, so stockout status is unknown.
- Artifacts: `reports/phase-03/promotion-audit.json` and
  `reports/phase-03/promotion-audit-windows.csv`.
- Validation: Ruff passed; 33 tests passed; compileall, health CLI, and real-data promotion-audit
  command passed. Tests cover positive/negative signs, margin scenario, short history, severe shift,
  forward-buy, missing inventory, future-value invariance, and unsupported causal wording.
- Learning guide: `learning/03-promotion-audit/README.fa.md`.

## Phase 4 — DONE — End-to-end API and dashboard demo

Plain-language goal: let a reviewer run one command, load demo CSVs, select a promotion, and understand the result without reading the code.

Deliverables and gate:

- FastAPI endpoints for validation and analysis with generated OpenAPI schemas.
- Streamlit flow: download/ingest/upload → quality report → choose promotion → result and diagnostics.
- No analytical calculations inside UI/API modules.
- Empty, malformed, and oversized-input handling.
- Gate: fresh-machine setup documentation, API integration tests, and one scripted demo path pass.

Completion evidence:

- Date/time: 2026-08-30.
- Model/reasoning: `gpt-5.6-sol` with `high`; no statistical estimator changed in this phase.
- Delivered: canonical application-panel quality report, typed Pydantic request/response contracts,
  local-path and bounded-upload validation, promotion listing and audit endpoints, generated
  OpenAPI, and a Persian Streamlit reviewer flow.
- Boundaries: missing/malformed/invalid/empty/oversized inputs and incomplete event keys are
  handled before domain analysis. Upload is capped at 120 MiB and application panels at one
  million rows.
- Real-data HTTP smoke: 524,950 rows, 3,909 store-product series, 149,386 promotion rows, and
  49,384 promotion episodes. The representative Phase 3 audit was reproduced with decision
  `experiment` and explicit non-causal claim language.
- Artifacts: `reports/phase-04/demo-smoke.json` and
  `reports/phase-04/quality-report.json`.
- Validation at Phase 4 completion: Ruff, the then-current full test suite, compileall, real-data
  HTTP smoke, and the local Streamlit flow passed. Current release evidence is tracked separately
  under Phase 5.2.
- Documentation: `docs/api-dashboard.md` and `learning/04-api-dashboard/README.fa.md`.
- Remaining limitations: no API authentication/rate limiting, no database-backed query/cache,
  no measured business cost/inventory, and no causal or Iranian-company impact evidence.

## Phase 5 — DONE — Park submission package

Plain-language goal: submit evidence of a focused, testable innovation—not an inflated list of future technologies.

Deliverables and gate:

- One-page problem/solution/market/pilot brief in Persian.
- Architecture and 90-day validation plan.
- Two-minute demo script and screenshots.
- Honest traction section: prototype evidence, interviews actually completed, and next pilot request.
- Risk table covering data access, causal validity, adoption, and privacy.
- Gate: every claim links to runnable code, an artifact, a real interview note, or is explicitly labeled as a hypothesis.

Completion evidence:

- Date/time: 2026-08-30.
- Model/reasoning: `gpt-5.6-terra` with `high`; final claim audit applied the repository evidence
  policy. No new statistical or causal claim was introduced.
- Delivered: Persian one-page brief, fill-ready official-form responses with personal placeholders,
  architecture and 90-day validation plan, risk register, two-minute demo script, evidence index,
  and real dashboard screenshots under `submission/park-application-1405/`.
- Honest traction: runnable public-data prototype evidence is documented; no customer interview,
  pilot, contract, revenue, patent, award, or Iranian business impact is claimed.
- Screenshots: `01-quality-report.png` records the validated real panel and
  `02-observational-audit.png` records the conservative experiment recommendation.
- Quality report: `reports/phase-05/submission-quality-report.json` records claim coverage and
  remaining applicant/external-validation steps.
- Learning guide: `learning/05-park-submission/README.fa.md` explains each document, all changes,
  the form answers, demo, likely review questions, and the send-day checklist in Persian.
- Remaining action outside repository: the applicant must fill personal fields, verify the receiving
  organization's current rules/deadline, and submit the form personally. Any future traction claim
  requires its own evidence.

## Release gate 5.1 — DONE — Foundation correctness

Plain-language goal: repair ambiguous financial semantics, the non-consecutive MASE scale, and
missing grain-identifier validation before any causal model depends on this foundation.

Approved scope and gate:

- Decision record: `docs/decisions/0002-foundation-correctness-gate.md`.
- Tracking: GitHub Issue #1.
- Each correctness change is committed and verified independently.
- Affected real-data reports are regenerated with an old-versus-new explanation.
- Phase 6 resumes only after tests, Ruff, compileall, CI, learning documentation, and a correctness
  release tag pass.

Local release-candidate evidence on 2026-08-31:

- 67 tests passed; Ruff and compileall passed;
- the 524,950-row real panel validated with no missing grain identifier or duplicate grain row;
- forecast evaluation regenerated with 41,516 paired rows and 71.42% paired coverage;
- the versioned real-data audit and local API smoke passed;
- package and API version are aligned at `0.5.1`;
- GitHub CI passed on the clean Ubuntu/Python 3.11 runner after upgrading runtime actions.

Machine-readable evidence:
`reports/foundation-correctness/release-quality-report.json`.

## Release 5.2 — DONE — Reviewer-focused real-data Demo Mode

Plain-language goal: make the already verified deterministic result understandable in a two-minute
review without exposing a personal path or adding any analytical formula to the UI. This work starts
only after the correctness tag exists and does not resume Phase 6.

Completion evidence on 2026-08-31:

- explicit `--demo` launch and one-click full real-data path;
- three visible reviewer steps and deterministic representative-event selection;
- observed/baseline/interval visualization sourced only from `PromotionAuditResult`;
- Persian recommendation, warnings, and non-causal/non-financial boundary;
- 73-test full suite, Ruff, compileall, GitHub CI, real browser execution, privacy text check, and
  screenshots;
- machine-readable report: `reports/phase-05/demo-mode-quality-report.json`.

## Work package 5.3 — DONE — Final submission evidence refresh

Plain-language goal: replace stale version/test references in the external Park package with values
from the verified 0.5.2 evidence, then run the placeholder and claim audit before recording.

Completion evidence on 2026-08-31:

- all external package references use the verified 0.5.2 release and 73-test suite;
- 524,950 rows, 3,909 series, 149,386 promotion rows, and the representative audit are frozen in
  one machine-readable source of truth;
- stale-reference, placeholder, JSON, claim-boundary, and anonymous public-access checks passed;
- exactly seven approved identity placeholders remain in the public draft and no private value was
  committed;
- machine-readable reports: `reports/phase-05/submission-quality-report.json` and
  `reports/phase-05/submission-claim-audit.json`.

## Work package 5.4 — ACTIVE — Owner-only form, PDFs, and final video

Plain-language goal: Reza verifies eligibility, completes the official form and private attachments
outside Git, records the 110–118 second demo, and checks every final link without authentication.
Repository development remains frozen unless this packaging pass finds a factual or technical defect.

## Phase 6 — PAUSED — Real-experiment causal benchmarking

Plain-language goal: use a real public randomized marketing experiment to benchmark treatment-effect methods, then test retail observational analyses with explicit refusal rules.

Deliverables and gate:

- Criteo Uplift v2.1 adapter and a reproducible treatment-effect benchmark.
- At least one transparent panel/DiD-style estimator for the retail observational track and one doubly robust method if justified.
- Pre-trend, overlap, placebo, missingness, sensitivity, and coverage diagnostics.
- Statistical tests use documented splits and confidence intervals, not a single lucky run.
- Gate: Criteo results use the dataset’s treatment/outcome definitions; retail outputs abstain when the public data cannot identify a causal effect.

## Phase 7 — PENDING — Cannibalization and uncertainty

Plain-language goal: detect when one SKU’s apparent win is another SKU’s loss or demand borrowed from next week.

Deliverables and gate:

- Category/SKU relationship graph or transparent candidate-neighbor rule.
- During-promotion substitution and post-promotion dip diagnostics.
- Prediction/effect intervals, data-shift checks, and an explicit abstention policy.
- Gate: documented public-data cases and, if necessary, separately labeled validation fixtures detect substitution and forward-buy behavior at documented error rates.

## Phase 8 — PENDING — Profit optimization

Plain-language goal: compare safe promotion scenarios under real constraints rather than automatically changing prices.

Deliverables and gate:

- Scenario optimizer with budget, margin, inventory, and business-rule constraints.
- Transparent baseline comparison and sensitivity analysis.
- Human approval required; no autonomous campaign execution.
- Gate: solver output always satisfies tested constraints and reports infeasible cases clearly.

## Phase 9 — PENDING — Production and verified AI layer

Plain-language goal: demonstrate the production skills employers ask for without turning the repository into infrastructure theater.

Deliverables and gate:

- PostgreSQL/DuckDB analytical schema, idempotent pipeline, logging, run metadata, and model/data monitoring.
- Add orchestration or MLflow only for a real repeatable workflow.
- Deterministic typed insight JSON is the source of truth.
- Optional Persian/English LLM explanation constrained to that JSON, with golden tests for numbers, unsupported claims, and abstention wording.
- Gate: the app works without an LLM key; generated prose cannot alter numerical facts.

## Phase 10 — PENDING — Portfolio and application packaging

Plain-language goal: make reviewers see evidence quickly and map it to the roles being targeted.

Deliverables and gate:

- Polished bilingual README, architecture decision records, model card, limitations, demo video, and reproducibility badge/checks.
- One technical case study: problem → assumptions → method → evaluation → failure cases → product decision.
- Role maps for data scientist, applied AI, analytics, and ML/data engineering vacancies.
- AIIF challenge mapping based only on verified current challenge requirements.
- Gate: a reviewer can understand the value in 60 seconds and reproduce the core result in under 10 minutes.

## Scope cuts if the submission clock slips

Cut in this order:

1. Styling and animations.
2. Extra forecasting models.
3. Database/orchestration integrations.
4. LLM narrative generation.
5. Optimization.

Do not cut data validation, time-aware evaluation, uncertainty wording, reproducibility, or the limitation statement. Those are the project’s differentiators.
