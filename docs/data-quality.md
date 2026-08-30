# Data-quality policy

The phase-1 quality report separates fatal contract violations from reviewable source warnings.

## Fatal checks

- missing required columns;
- missing or unparseable week-ending dates;
- non-numeric values in numeric fields;
- negative sales, spend, or prices;
- duplicate `week_end_date × store_num × upc` rows;
- promotion flags outside `{0, 1}` or missing flags;
- `TPR_ONLY=1` together with `FEATURE=1` or `DISPLAY=1`;
- negative observed/base prices.

## Warnings

- missing observed/base prices are preserved for downstream abstention;
- observed price above base price does not become a negative discount claim;
- zero-price sales are preserved as possible free promotions and flagged for review;
- gaps in the global weekly calendar are reported.
- duplicate lookup keys are collapsed without discarding conflicting metadata, and their counts
  are recorded so joins cannot multiply transaction rows.

No phase-1 rule silently imputes, drops, clips, or corrects business values.
