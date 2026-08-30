# Model card — observational promotion-audit baseline

## Intended use

Screen one documented store-product promotion episode for incremental-unit signals, uncertainty,
data warnings, and whether a controlled experiment is warranted.

## Not intended for

- causal treatment-effect claims;
- autonomous price or campaign changes;
- measured profit without approved cost inputs;
- stockout or cannibalization conclusions without the required fields and diagnostics.

## Data and model

- Source: dunnhumby Breakfast at the Frat weekly public panel.
- Grain: week × store × UPC.
- Baseline: recursive one-week persistence initialized from non-promotion pre-event history.
- Audit interval: 90th percentile absolute one-week residual from pre-event history.
- Phase-2 reference: recursive naive WAPE 0.34828 on 41,516 paired non-promotion rows.

## Abstention behavior

The result returns `experiment` when history is short, cost is missing, shift is severe, inventory
reaches zero, the post window is incomplete, forward-buy risk is detected, or the interval does not
support a directional screening decision.

## Known limitations

See `docs/limitations.md`. The most important limitation is that observational lift is not a causal
effect and public-data performance is not business impact in Iran.

