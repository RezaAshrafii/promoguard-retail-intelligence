# Evidence index — Phase 5 submission claims

| Claim in the submission | Evidence | What it does not prove |
|---|---|---|
| Runnable MVP exists | `apps/api/main.py`, `apps/dashboard/app.py`, `demo/phase4_smoke.py`, release `v0.5.2-park-demo` | Customer adoption or revenue |
| Real public retail panel was processed | `reports/foundation-correctness/release-quality-report.json`, `reports/phase-05/demo-mode-quality-report.json` | Iranian-company performance |
| 524,950 rows, 3,909 series, and 149,386 promotion rows passed the path | `reports/phase-05/submission-quality-report.json` | Data representativeness for any future client |
| Foundation correctness gate passed | `reports/foundation-correctness/release-quality-report.json`, tag `v0.5.1-foundation-correctness` | Production reliability at scale |
| 73 automated tests passed | `reports/phase-05/demo-mode-quality-report.json`, `tests/` | Absence of every possible defect |
| Output is observational, not causal | `src/promoguard/insights/promotion_audit.py`, Phase 3 artifact | Treatment effect or ROI |
| The dashboard is reviewer-facing and Persian | `apps/dashboard/app.py`, `learning/04-api-dashboard/README.fa.md` | Product-market fit |
| Reviewer Demo Mode runs without showing a local path | `reports/phase-05/demo-mode-quality-report.json`, screenshots 03/04 | Cloud or production deployment |
| Dashboard chart uses typed result values | `apps/dashboard/presentation.py`, `tests/unit/test_dashboard_presentation.py` | Causal validity of those values |
| A 90-day pilot is planned | `architecture-and-90day-plan-fa.md` | A signed pilot, interview, or customer |
| Public repository and release open without authentication | `reports/phase-05/submission-claim-audit.json` | Availability of the future video or official form |
| External submission claims are internally consistent | `reports/phase-05/submission-claim-audit.json` | Truth of private identity or eligibility fields not yet supplied |

## Claim-audit rule

Before submitting, take each sentence that contains a number, customer statement, technical
capability, or market assertion. Link it to one row above. If no evidence exists, convert the
sentence to a labeled hypothesis or remove it.
