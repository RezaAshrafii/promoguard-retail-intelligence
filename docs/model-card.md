# Model card — observational promotion-audit baseline

## Intended use

Screen one documented store-product promotion episode for an observed-minus-forecast-baseline units
difference, uncertainty, data warnings, and whether a controlled experiment is worth prioritizing.

## Not intended for

- causal treatment-effect claims;
- autonomous price or campaign changes;
- promotion profit, gross-margin impact, or financial approval;
- stockout or cannibalization conclusions without the required fields and diagnostics.

## Data and model

- Source: dunnhumby Breakfast at the Frat weekly public panel.
- Grain: week × store × UPC.
- Baseline: recursive one-week persistence initialized from non-promotion pre-event history.
- Audit interval: 90th percentile absolute one-week residual from pre-event history.
- Phase-2 reference: recursive naive WAPE 0.34828 on 41,516 paired non-promotion rows.

## Abstention behavior

The result returns `needs_more_evidence` when diagnostics block interpretation or the interval
crosses zero. A positive interval can only produce `candidate_for_controlled_test`; a negative
interval can only produce `deprioritize_and_investigate`. None is a rollout or financial decision.

An optional contribution sensitivity linearly multiplies the units difference by a typed,
user-approved assumption with currency and source. It never changes the recommendation and does not
model margin lost on baseline units, trade spend, funding, or other costs.

## Known limitations

See `docs/limitations.md`. The most important limitation is that observational lift is not a causal
effect and public-data performance is not business impact in Iran.

