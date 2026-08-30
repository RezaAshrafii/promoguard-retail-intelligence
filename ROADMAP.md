# PromoGuard active development roadmap

Last updated: 2026-08-30  
Roadmap owner: Reza  
Execution rule: exactly one phase is `ACTIVE`.

## Outcome and deadline tracks

The roadmap has two speeds:

- **Submission track:** produce a narrow but honest MVP package by **2026-09-04 (13 Shahrivar 1405)**. This is a five-day sprint, so the submission should promise a validated pilot, not a complete enterprise platform.
- **Professional track:** extend the same codebase after submission into a production-minded portfolio project with causal validation, monitoring, optimization, and verified AI explanations.

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
| 3 | Honest promotion-audit MVP | 2026-09-01 | ACTIVE |
| 4 | End-to-end API/dashboard demo | 2026-09-02 | PENDING |
| 5 | Park submission evidence package | 2026-09-03/04 | PENDING |
| 6 | Real-experiment causal benchmarking | 2026-09-05 to 09-14 | PENDING |
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

## Phase 3 — PENDING — Honest promotion-audit MVP

Plain-language goal: compare observed promotion-period sales with the validated no-promotion baseline, while labeling the result as an audit estimate rather than a causal claim.

Deliverables and gate:

- Incremental units and gross-margin scenario computed from observed minus baseline.
- Stockout, missing-cost, short-history, and severe-shift warnings.
- Pre-, during-, and post-promotion windows to reveal forward-buy risk.
- Typed result with estimate, interval, assumptions, evidence references, and `approve/reject/experiment` decision.
- Gate: documented observational cases trigger expected signs and warnings; output never says “caused” without a defensible identification design.

## Phase 4 — PENDING — End-to-end API and dashboard demo

Plain-language goal: let a reviewer run one command, load demo CSVs, select a promotion, and understand the result without reading the code.

Deliverables and gate:

- FastAPI endpoints for validation and analysis with generated OpenAPI schemas.
- Streamlit flow: download/ingest/upload → quality report → choose promotion → result and diagnostics.
- No analytical calculations inside UI/API modules.
- Empty, malformed, and oversized-input handling.
- Gate: fresh-machine setup documentation, API integration tests, and one scripted demo path pass.

## Phase 5 — PENDING — Park submission package

Plain-language goal: submit evidence of a focused, testable innovation—not an inflated list of future technologies.

Deliverables and gate:

- One-page problem/solution/market/pilot brief in Persian.
- Architecture and 90-day validation plan.
- Two-minute demo script and screenshots.
- Honest traction section: prototype evidence, interviews actually completed, and next pilot request.
- Risk table covering data access, causal validity, adoption, and privacy.
- Gate: every claim links to runnable code, an artifact, a real interview note, or is explicitly labeled as a hypothesis.

## Phase 6 — PENDING — Real-experiment causal benchmarking

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
