# Data contracts

The current public-source contract is implemented in `promoguard.data.contracts` and validated at
the ingestion boundary.

Canonical grain:

```text
one row per week_end_date × store_id × upc
```

Required measures are units, visits, households, spend, observed price, base price, and the three
binary promotion-support fields: feature, display, and temporary-price-reduction-only. Price and
base price may be missing and are reported as warnings. Cost and inventory are not present and are
never fabricated.

Store versioned schemas and validation examples here. Do not commit private customer data.
