# Evidence index — Phase 5 submission claims

| Claim in the submission | Evidence | What it does not prove |
|---|---|---|
| Runnable MVP exists | `apps/api/main.py`, `apps/dashboard/app.py`, `demo/phase4_smoke.py`, release `v0.6.4` | Customer adoption or revenue |
| Real public retail panel was processed | `reports/foundation-correctness/release-quality-report.json`, `reports/phase-05/demo-mode-quality-report.json` | Iranian-company performance |
| 524,950 rows, 3,909 series, and 149,386 promotion rows passed the path | `reports/phase-05/submission-quality-report.json` | Data representativeness for any future client |
| Foundation correctness gate passed | `reports/foundation-correctness/release-quality-report.json`, tag `v0.5.1-foundation-correctness` | Production reliability at scale |
| 116 automated tests and 72% combined coverage passed | `reports/phase-06/release-0.6.4-quality-report.json`, `tests/`, GitHub CI for `v0.6.4` | Absence of every possible defect |
| Full Criteo randomized benchmark was rerun on 13,979,592 rows | `reports/phase-06/criteo-uplift-model-ranking.json` | Iranian retail impact, profit, or transportability |
| Output is observational, not causal | `src/promoguard/insights/promotion_audit.py`, Phase 3 artifact | Treatment effect or ROI |
| The dashboard is reviewer-facing and Persian | `apps/dashboard/app.py`, `learning/04-api-dashboard/README.fa.md` | Product-market fit |
| Reviewer Demo Mode runs without showing a local path | `reports/phase-05/demo-mode-quality-report.json`, screenshots 03/04 | Cloud or production deployment |
| Dashboard chart uses typed result values | `apps/dashboard/presentation.py`, `tests/unit/test_dashboard_presentation.py` | Causal validity of those values |
| A 90-day pilot is planned | `architecture-and-90day-plan-fa.md` | A signed pilot, interview, or customer |
| Public repository and release open without authentication | release `v0.6.4` and its successful tag CI | Availability of the future video or official form |
| External submission claims are internally consistent | `reports/phase-05/submission-claim-audit.json` | Truth of private identity or eligibility fields not yet supplied |

## Claim-audit rule

Before submitting, take each sentence that contains a number, customer statement, technical
capability, or market assertion. Link it to one row above. If no evidence exists, convert the
sentence to a labeled hypothesis or remove it.
