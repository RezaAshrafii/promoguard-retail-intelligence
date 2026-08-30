# Data contracts

The current public-source contract is implemented in `promoguard.data.contracts` and validated at
the ingestion boundary.

Canonical grain:

```text
one row per week_end_date × store_id × upc
```

Every grain identifier is mandatory. `store_id` and `upc` are normalized to trimmed strings; null,
empty, and whitespace-only values are fatal. Duplicate grain is checked after normalization, so
values such as `"1"` and `" 1 "` cannot create two artificial series. The same policy is reused by
ingestion, application validation, forecasting, and promotion audit boundaries.

Required measures are units, visits, households, spend, observed price, base price, and the three
binary promotion-support fields: feature, display, and temporary-price-reduction-only. Price and
base price may be missing and are reported as warnings. Cost and inventory are not present and are
never fabricated.

Store versioned schemas and validation examples here. Do not commit private customer data.
