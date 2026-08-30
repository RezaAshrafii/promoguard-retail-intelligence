# Evidence index — Phase 5 submission claims

| Claim in the submission | Evidence | What it does not prove |
|---|---|---|
| Runnable MVP exists | `apps/api/main.py`, `apps/dashboard/app.py`, `demo/phase4_smoke.py` | Customer adoption or revenue |
| Real public retail panel was processed | `reports/phase-04/demo-smoke.json` | Iranian-company performance |
| 524,950 rows and 3,909 series passed the path | `reports/phase-04/demo-smoke.json` | Data representativeness for any future client |
| Application quality gate passed | `reports/phase-04/quality-report.json` | Production reliability at scale |
| 47 automated tests passed | `reports/phase-04/quality-report.json`, `tests/` | Absence of every possible defect |
| Output is observational, not causal | `src/promoguard/insights/promotion_audit.py`, Phase 3 artifact | Treatment effect or ROI |
| The dashboard is reviewer-facing and Persian | `apps/dashboard/app.py`, `learning/04-api-dashboard/README.fa.md` | Product-market fit |
| A 90-day pilot is planned | `architecture-and-90day-plan-fa.md` | A signed pilot, interview, or customer |

## Claim-audit rule

Before submitting, take each sentence that contains a number, customer statement, technical
capability, or market assertion. Link it to one row above. If no evidence exists, convert the
sentence to a labeled hypothesis or remove it.
