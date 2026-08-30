# PromoGuard Retail Intelligence

Reliable promotion-effect analysis for FMCG and retail decisions.

> Did a promotion create incremental profit, or only shift demand between products and time periods?

This repository is an initial research and product scaffold. It does not claim causal validity on observational data until the required diagnostics and experiments pass.

## Planned flow

```text
public workbook/CSV -> data contracts -> canonical weekly panel -> baseline forecast
       -> causal effect + cannibalization -> uncertainty/shift checks
       -> approve/reject/experiment -> verified insight JSON -> dashboard
```

## Repository map

- `apps/api`: FastAPI entry point
- `apps/dashboard`: Streamlit prototype entry point
- `src/promoguard`: domain modules
- `warehouse`: migrations and dbt placeholder
- `tests`: unit, integration, statistical, and golden-output tests
- `docs`: problem brief, evaluation protocol, model card, and decisions

## First run

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m promoguard.cli health
uvicorn apps.api.main:app --reload
streamlit run apps/dashboard/app.py
```

## Ingest the real public dataset

Download **Breakfast at the Frat** from the official dunnhumby Source Files page and extract
the workbook under `data/raw/breakfast-at-the-frat/`. Raw and processed data are intentionally
ignored by Git.

```powershell
promoguard ingest `
  --input data/raw/breakfast-at-the-frat `
  --output data/processed/breakfast-at-the-frat

promoguard validate --input data/processed/breakfast-at-the-frat
```

The ingest command creates `transactions.csv`, lookup tables, `weekly_panel.csv`,
`quality_report.json`, and `provenance.json`. It never invents cost or inventory fields.

## Run the forecasting baseline

After ingesting the public workbook, run the time-aware baseline evaluation:

```powershell
promoguard forecast-evaluate `
  --input data/processed/breakfast-at-the-frat `
  --output reports/phase-02
```

This writes a compact JSON summary, a fold-level comparison table, and SKU/store segment
metrics. The evaluation uses six expanding windows, a 52-week seasonal-naive model, and a
recursive one-week naive reference. Promotion rows are excluded from lag history and scoring is
paired on rows where both models have a valid prediction.

## Start the implementation agent

The repository includes a durable agent prompt and an active, phase-gated roadmap. The safe default implements only the current phase, validates it, updates the roadmap, and stops before the next phase:

```powershell
Set-Location "C:\Users\Reza\Desktop\promoguard-ai"
powershell -ExecutionPolicy Bypass -File .\start-agent.ps1
```

Use a stronger model for an architecture-critical phase:

```powershell
.\start-agent.ps1 -Model gpt-5.6-sol -Reasoning high -RunMode phase
```

For DeepSeek V4 Pro, first configure DeepSeek as the Codex provider using its official Windows setup and choose option 2. This changes the shared global Codex provider configuration and requires a DeepSeek API key, so review and run it yourself:

```powershell
irm https://cdn.deepseek.com/api-docs/codex-deepseek-setup-en.ps1 | iex
Set-Location "C:\Users\Reza\Desktop\promoguard-ai"
.\start-agent.ps1 -Model deepseek-v4-pro -Reasoning high -RunMode phase
```

Run the DeepSeek setup again and choose its restore option to return to the previous Codex provider configuration.

Read `IMPLEMENTATION_AGENT_PROMPT.md` for the full operating contract and `ROADMAP.md` for the current phase, deadlines, acceptance gates, and completion evidence.

## Persian learning notes

Each completed phase has a standalone Persian study guide under `learning/`. Start with
`learning/01-real-data-foundation/README.fa.md`; it explains the implementation, data-quality
decisions, commands, tests, limitations, and interview preparation for the completed foundation.

## Current status

- [x] Real-data contract, ingestion, validation, provenance, and canonical weekly panel
- [x] Seasonal-naive baseline and recursive naive reference
- [x] Time-aware backtest with WAPE, MASE, bias, and interval coverage
- [ ] Real-experiment causal benchmark
- [ ] Cannibalization diagnostics
- [ ] Uncertainty and abstention policy
- [ ] Profit scenario optimizer
- [ ] Evidence-grounded Persian report generation

## Evidence policy

Public data supports reproducible engineering and research; it is not evidence of impact on an
Iranian company. A real business-impact claim requires a design partner and an approved experiment.
