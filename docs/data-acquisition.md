# Data acquisition record — dunnhumby Breakfast at the Frat

## Provenance

- Publisher: dunnhumby
- Official source page: https://www.dunnhumby.com/source-files/
- Downloaded: 2026-08-30
- Source archive: `dunnhumby_Breakfast-at-the-Frat.zip`
- Archive SHA-256: `74cb41cb8b19dc61bb8a5731c3774b802e9a8da3b64cdd1872640890d0b54216`
- Workbook SHA-256: `61b1d77dd6d9298fed204cc231f2b853a4c7f79376cfc30231646e1e51d0daba`
- User-guide SHA-256: `368ab32478d6fa19433f3e5e9edf6debc380a4ad92ed590aabb9ae12cb5f5a0`

The publisher describes Source Files as datasets inspired by/representative of real-world retail
patterns. This repository does not redistribute the archive and does not describe it as live or
identifiable company production data. Users must review the publisher's current terms before use.

## Source structure

- `Glossary`: source field definitions.
- `dh Store Lookup`: store geography and segment metadata.
- `dh Products Lookup`: UPC, manufacturer, category, subcategory, and size.
- `dh Transaction Data`: 524,950 weekly store-product observations from 2009 through 2011.

Source grain:

```text
WEEK_END_DATE × STORE_NUM × UPC
```

Transaction fields:

```text
UNITS, VISITS, HHS, SPEND, PRICE, BASE_PRICE, FEATURE, DISPLAY, TPR_ONLY
```

## Known limitations

- The panel is weekly, not daily.
- Product cost, margin, inventory, stockout, and customer-level identifiers are absent.
- Promotion assignment is observational, so association does not establish causal lift.
- The public source may not represent Iranian pricing, inflation, availability, or shopper behavior.
- Phase 1 preserves missing prices and reports them; it does not impute them.

## Reproduction

Place the downloaded/extracted source under `data/raw/breakfast-at-the-frat/`, then run:

```powershell
promoguard ingest `
  --input data/raw/breakfast-at-the-frat `
  --output data/processed/breakfast-at-the-frat

promoguard validate --input data/processed/breakfast-at-the-frat
```

