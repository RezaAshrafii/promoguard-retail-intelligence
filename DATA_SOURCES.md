# PromoGuard public data sources

## Recommended primary source

Use **dunnhumby Breakfast at the Frat** first. It is the closest public source to promotion-effectiveness analysis: 156 weeks, five products, three brands, four categories, unit sales, households, visits, spend, base price, shelf price, and promotional support.

The publisher describes it as a representation/inspired real-world source, not raw identifiable company production data. State that accurately in the README and application materials.

## Download links

### 1. Promotion analysis: dunnhumby Breakfast at the Frat

- Publisher download page: https://www.dunnhumby.com/source-files/
- Select **Download 'Breakfast at the Frat'** on that page.
- Keep the archive under `data/raw/breakfast-at-the-frat/` and do not commit it.

### 2. Forecasting scale: Walmart M5

- Kaggle data page: https://www.kaggle.com/competitions/m5-forecasting-accuracy/data
- Files: `sales_train_validation.csv`, `calendar.csv`, `sell_prices.csv`.
- Use for daily hierarchical forecasting and price features.
- Do not treat every price change as a verified promotion or claim causal lift from M5 alone.

### 3. Causal marketing benchmark: Criteo Uplift v2.1

- Official page: https://ailab.criteo.com/criteo-uplift-prediction-dataset/
- Direct compressed download: http://go.criteo.net/criteo-research-uplift-v2.1.csv.gz
- Use only for uplift/ITE benchmarking; it has no retail SKU, price, cost, or inventory semantics.

### 4. Stockout research: FreshRetailNet-50K

- Dataset card: https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K
- Paper: https://arxiv.org/abs/2505.16319
- Baseline code: https://github.com/Dingdong-Inc/frn-50k-baseline
- Use for stockout-aware demand recovery, not promotion analysis unless the schema proves a promotion treatment exists.

## Recommended order

1. Download Breakfast at the Frat and finish the primary adapter.
2. Build the weekly promotion audit without claiming profit if cost is unavailable.
3. Add M5 as a separate forecasting benchmark.
4. Add Criteo as a separate causal/uplift benchmark.
5. Add FreshRetailNet only if stockout analysis is needed.

## What “real” means here

These are public, anonymized or research-use sources—not live Iranian company data. They are suitable for reproducible engineering and research. A commercial-impact claim still requires a design partner and an approved experiment with actual business data.

