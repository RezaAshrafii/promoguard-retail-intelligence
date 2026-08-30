# Park Submission Agent Handoff

This file is the machine-readable and human-readable continuation contract for any coding agent
working on the University of Tehran Science and Technology Park submission. It must be usable
without access to the original chat history.

## 1. Mission

Finish and quality-assure the PromoGuard submission package before the internal deadline:

- Official deadline: 1405-06-13 / 2026-09-04.
- Internal send deadline: 1405-06-11 at 15:00 Tehran time / 2026-09-02.
- Applicant and final decision owner: Reza.
- Repository: `promoguard-retail-intelligence`.
- Current release line: Phase 5 complete; Release Gate 5.1 is ACTIVE; Phase 6 is PAUSED.

The submission must present a runnable, evidence-first MVP. It must not claim an Iranian customer,
revenue, causal impact, profit improvement, patent, award, or production readiness unless Reza adds
real evidence.

## 2. Mandatory read order

Read these files completely before changing code or submission content:

1. `AGENTS.md`
2. `ROADMAP.md`
3. `submission/park-application-1405/MASTER-SUBMISSION-ROADMAP-FA.md`
4. `docs/research/park-competitive-profile-benchmark-fa.md`
5. `submission/park-application-1405/video-production-plan-fa.md`
6. `submission/park-application-1405/evidence-index.md`
7. `docs/decisions/0002-foundation-correctness-gate.md`
8. `docs/limitations.md`
9. `docs/evaluation-protocol.md`
10. `docs/model-selection-plan-fa.md`

Do not rely on chat memory when repository evidence disagrees with it.

## 3. Current verified state

As of 2026-08-31:

- Branch: `main`, tracking `origin/main`.
- Latest release tag before the active gate: `v0.5.0-phase-05`.
- Phase 5 package exists under `submission/park-application-1405/`.
- Real public dunnhumby panel path is expected under
  `data/processed/breakfast-at-the-frat/` and is intentionally not tracked by Git.
- The latest known full check before this handoff passed 64 tests, Ruff, compileall, real ingestion,
  forecasting, audit, API smoke, and dashboard flow. An agent must rerun checks; this sentence is not
  a substitute for a fresh quality report.
- Completed Release Gate 5.1 fixes: audit contribution semantics, consecutive-week MASE scale,
  canonical grain identifiers, and local API path confinement.
- Remaining Gate 5.1 items: explicit paired-coverage accounting; versioned configurable audit
  policy; AI/governance docs and retrospective ADRs; README/quick-demo polish; license and repository
  metadata; final report, tag, and release.
- The submission text is stale in places: it still contains `v0.4.0-phase-04` and `47 tests`.
  Never manually replace these with a guessed number. Generate the final quality evidence first,
  then update every reference from that source of truth.

## 4. Active execution order

Only one work package may be ACTIVE at a time.

### Package A — Foundation correctness closure

Deliver:

- paired eligibility coverage ratio, exclusions, and per-fold reasons in artifacts;
- typed/versioned `AuditPolicy` replacing unexplained hard-coded decision thresholds;
- unit, regression, and real-data tests;
- regenerated affected reports with comparison notes;
- Persian learning documentation for each material change.

Gate:

```powershell
python -m ruff check .
python -m pytest -q
python -m compileall -q src apps demo
python -m promoguard.cli health
python -m demo.phase4_smoke
```

Do not resume Phase 6 until this package and the release gate pass.

### Package B — Reviewer demo mode

Use the existing Streamlit adapter. Do not introduce React, Next.js, a JavaScript build chain, a
design framework, authentication, a cloud deployment, or LLM calls for the Park demo.

Deliver:

- one-click local real-data demo mode;
- hidden local filesystem path in demo mode;
- three-step reviewer flow;
- observed/baseline/interval visualization;
- clear recommendation and limitation cards;
- tests for any pure formatting/transformation helper;
- deterministic numbers sourced only from domain result models.

Gate:

- no analytical formula in `apps/dashboard`;
- no duplicate calculation between UI and `src/promoguard`;
- no stack trace or personal path in the recorded flow;
- dashboard works without an external API key;
- screenshots match the final release.

### Package C — Submission evidence refresh

Create one machine-readable source-of-truth report for submission claims. It should include at least:

- release/tag/commit;
- validation date;
- test count and status;
- row, series, promotion-row and event counts;
- representative audit key and output;
- known warnings and limitations;
- paths to evidence artifacts.

Update these files from verified evidence:

- `submission/park-application-1405/README.fa.md`
- `submission/park-application-1405/form-response-fa.md`
- `submission/park-application-1405/one-page-brief-fa.md`
- `submission/park-application-1405/evidence-index.md`
- `reports/phase-05/submission-quality-report.json`

Gate: `rg -n "v0\.4\.0|47 tests|۴۷ تست|<[^>]+>|TODO|PLACEHOLDER"` must return only explicitly
approved personal placeholders before Reza supplies private information. Final external files may
contain no placeholders.

### Package D — Repository release readiness

Deliver:

- concise bilingual or English-first README opening;
- three-command quick demo;
- Apache-2.0 license unless Reza explicitly chooses another license;
- AI usage/governance disclosure;
- repository description/topics checklist;
- final `v0.5.1-foundation-correctness` annotated tag after all gates pass.

Do not delete user work, raw local data, or unrelated files. Do not rewrite Git history.

### Package E — External documents and video

The official form contains private identity data. Never commit a filled form, national ID,
enrollment certificate, address, signature, personal phone number, or private interview notes.

Use the master roadmap and video plan. External deliverables are produced only after the code/release
numbers are frozen. The agent may create redacted templates in Git, but Reza must review every
private field and authorize the final submission.

## 5. Model routing

- Statistical, causal, policy-threshold, security, or release-claim decisions:
  `gpt-5.6-sol`, reasoning `xhigh`.
- Implementation with an already-approved design:
  `gpt-5.6-sol high` or `gpt-5.6-terra high`.
- Persian document polishing and package consistency:
  `gpt-5.6-terra high`.
- Final independent claim/evidence audit:
  `gpt-5.6-sol xhigh`.
- Low-risk formatting after facts are frozen:
  `gpt-5.6-luna high` is acceptable.

Record a model change and reason in the relevant report. A stronger model never authorizes a
stronger business claim.

## 6. Evidence and privacy rules

1. Public benchmark execution proves technical capability, not Iranian business impact.
2. Observational audit output is not a causal treatment effect.
3. Contribution sensitivity is not profit or margin impact.
4. Cost and inventory are absent from the current public source.
5. Interview, customer, pilot, revenue, award, patent, and market-size claims require evidence.
6. Personal documents stay outside Git and should be sent only through the official channel.
7. Do not use synthetic business data in the product demonstration.
8. Test fixtures may be synthetic only when clearly labeled as fixtures and never presented as
   business evidence.
9. No third-party model key is required for the MVP or demo.
10. Never expose local absolute paths in screenshots, video, README output, or API responses.

## 7. Git protocol

Use small, reviewable commits. Suggested sequence:

1. `docs(research): benchmark competitive Park profiles`
2. `docs(submission): define Park delivery and video roadmap`
3. `docs(agents): add independent Park submission handoff`
4. `fix(evaluation): expose paired forecast coverage`
5. `refactor(audit): version decision policy`
6. `feat(demo): add reviewer-focused dashboard mode`
7. `docs(submission): refresh evidence and final claims`
8. `chore(release): finalize foundation correctness release`

Before every commit:

- inspect `git diff --check`;
- run checks proportional to the change;
- preserve unrelated user changes;
- do not commit data, credentials, private documents, videos, or archives.

Push only after the commit is complete and tests/document checks pass. Create the annotated release
tag only at the end of the gate, never on a partial state.

## 8. Status update contract

At the end of every work package, update this block and the main roadmap:

```text
Active package: A
Last completed task: research and submission execution documents
Current blocker: none in repository; applicant eligibility and private fields require Reza
Next command: inspect Release Gate 5.1 coverage and policy backlog
Expected next artifact: paired coverage report and AuditPolicy tests
```

If a blocking condition needs private information or external authority, stop and ask Reza. Do not
invent a value or silently omit a mandatory field.

## 9. Definition of done

The Park sprint is complete only when:

- the release is reproducible and tagged;
- the final claim report matches every external document;
- demo mode and video pass the documented checklist;
- official form and mandatory documents are complete;
- all links work from an anonymous browser;
- the submission email has been sent by Reza and receipt evidence is retained.

After that, set Release Gate 5.1 to DONE and resume Phase 6 in a separate commit.
