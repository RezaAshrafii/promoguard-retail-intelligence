# ADR 0004: Use dunnhumby Breakfast at the Frat as engineering evidence

- Status: accepted retrospectively under the owner-approved foundation gate
- Date reviewed: 2026-08-31
- Record type: retrospective ADR

## Context

The project needs non-synthetic promotion and sales records that can exercise ingestion,
time-aware forecasting, and an observational audit. Breakfast at the Frat provides 156 weeks of
retail data with product, store, units, price, and promotion-support fields.

It does not provide inventory, complete promotion economics, randomized assignment, Iranian
market evidence, or permission to redistribute a copy inside this repository.

## Decision

Use the official dunnhumby source as the primary reproducible engineering dataset. Keep raw and
processed files outside Git, record provenance, and never describe its outputs as measured impact
for an Iranian retailer. Do not generate synthetic business data to fill missing economic fields.

## Alternatives considered

- Walmart M5: valuable for forecasting scale, but price changes are not verified promotions.
- Criteo Uplift: valuable for later causal benchmarking, but lacks retail SKU and price semantics.
- synthetic fixtures: useful for isolated software tests, but explicitly rejected as portfolio
  evidence and not used for the real-data reports.

## Consequences

- a reviewer must obtain the official dataset for a fresh full run;
- the recorded demo may use the owner's local official copy, while the repository publishes only
  code, contracts, and derived aggregate evidence;
- unavailable inventory and cost questions become visible limitations, not invented columns.

## Reversal condition

Adopt a different primary dataset when its license and schema provide stronger promotion,
inventory, economics, and experimental evidence without weakening reproducibility.

## Owner mastery check

The owner should be able to name what the dataset contains, what it lacks, and why it proves
engineering reproducibility but not Iranian product-market fit.
