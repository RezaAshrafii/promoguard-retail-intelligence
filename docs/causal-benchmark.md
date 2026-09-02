# Criteo Uplift v2.1 randomized benchmark

## Purpose and boundary

This external public randomized advertising benchmark proves that PromoGuard can validate and
summarize a large treatment/outcome dataset with reproducible, conservative statistics. It is **not**
a causal evaluation of the dunnhumby retail audit and does not establish Iranian market impact.

## Source and license

- Publisher page: <https://ailab.criteo.com/criteo-uplift-prediction-dataset/>.
- Official v2.1 download: <https://criteostorage.blob.core.windows.net/criteo-research-datasets/criteo-uplift-v2.1.csv.gz>.
- License: CC BY-NC-SA 4.0. Raw data is never committed, redistributed, or covered by the project's
  Apache-2.0 code license.
- Expected columns: dense features `f0`–`f11`, binary `treatment`, `visit`, `conversion`, and
  `exposure`.

The publisher describes anonymized incrementality-test records. v2.1 is its debiased replacement
for an earlier version with an advertiser-related leak. Cite Diemert et al. (AdKDD 2018) when using
this dataset externally.

## Method

For `visit` and `conversion`, calculate aggregate **intention-to-treat risk difference**:

```text
mean(outcome | treatment = 1) - mean(outcome | treatment = 0)
```

The reader streams CSV chunks, rejects schema/value errors, reports treatment-arm counts and 12
standardized mean differences, then calculates a two-sided normal-approximation 95% interval. It
does not train a CATE model, use exposure, or invent individual treatment-effect labels.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -m promoguard.cli causal-benchmark `
  --input data/raw/criteo-uplift/criteo-uplift-v2.1.csv.gz `
  --output reports/phase-06
```

The JSON contains aggregate evidence and source SHA-256. The recorded real run is
[`reports/phase-06/criteo-uplift-itt-benchmark.json`](../reports/phase-06/criteo-uplift-itt-benchmark.json).

## Real-run result

| Quantity | Result |
|---|---:|
| Rows streamed | 13,979,592 |
| Treatment fraction | 85.00% |
| Visit ITT risk difference | +1.034pp, 95% CI [+1.006, +1.063] |
| Conversion ITT risk difference | +0.115pp, 95% CI [+0.108, +0.122] |
| Largest absolute feature SMD | 0.049 (`f3`) |

These are aggregate results in Criteo's anonymized advertising benchmark; they do not identify an
individual, prove a retail promotional effect, or authorize a business decision.

## Before the next claim

CATE ranking needs a predeclared holdout policy metric (for example Qini/AUUC), leakage checks, and
a threshold. Retail causality needs a real retail experiment or a defensible identification design
with overlap, pre-trend, placebo, missingness, and sensitivity diagnostics.
