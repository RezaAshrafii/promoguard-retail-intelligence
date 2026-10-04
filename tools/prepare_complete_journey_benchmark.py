"""Create a reproducible, provenance-labeled weekly panel from public source data."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/complete-journey/agg_promo_sales_weekly.parquet"
OUTPUT_DIR = ROOT / "data/processed/complete-journey"
PRODUCT_ID = 908846
ANCHOR = date(2010, 1, 3)  # Display-only anchor; source has week indices, not dates.


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing source parquet: {SOURCE}")
    source = pd.read_parquet(SOURCE)
    required = {
        "PRODUCT_ID", "WEEK_NO", "Units", "Sales",
        "OnDisplay_AnyStore", "InMailer_AnyStore",
    }
    missing = required - set(source.columns)
    if missing:
        raise SystemExit(f"Unexpected source schema; missing: {sorted(missing)}")

    selected = source.loc[source["PRODUCT_ID"].eq(PRODUCT_ID)].sort_values("WEEK_NO")
    if len(selected) != 102 or selected["WEEK_NO"].tolist() != list(range(1, 103)):
        raise SystemExit("Expected one complete, consecutive 102-week product series")
    event = selected["OnDisplay_AnyStore"].astype(bool) | selected["InMailer_AnyStore"].astype(bool)
    weeks = selected.loc[event, "WEEK_NO"].astype(int).tolist()
    if weeks != [93, 94]:
        raise SystemExit(f"Benchmark event changed; expected weeks 93-94, got {weeks}")

    frame = pd.DataFrame(
        {
            "week_end_date": [
                (ANCHOR + timedelta(weeks=int(week) - 1)).isoformat()
                for week in selected["WEEK_NO"]
            ],
            "store_id": "ALL_STORES",
            "upc": str(PRODUCT_ID),
            "units": selected["Units"].astype(float).to_list(),
            "promotion_flag": event.astype(int).to_list(),
        }
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "week-index-not-real-dates_complete-journey_product-908846.csv"
    frame.to_csv(output, index=False)
    metadata = {
        "source_dataset": "dunnhumby The Complete Journey derived weekly promotion-sales aggregate",
        "source_file": "agg_promo_sales_weekly.parquet",
        "source_sha256": "effc9d1ad57d3d9d1a5e31ea184436eedfba346769d06e73538327666b42153",
        "source_url": "https://github.com/bltap-plmarket/dunnhumby-complete-journey/releases/tag/v1.0-data",
        "official_dataset_page": "https://www.dunnhumby.com/source-files/",
        "product_id": PRODUCT_ID,
        "rows": len(frame),
        "week_index_range": [1, 102],
        "promotion_week_indices": weeks,
        "display_date_anchor": ANCHOR.isoformat(),
        "display_date_warning": "Dates are synthetic labels preserving weekly order; the source supplies week indices, not calendar dates.",
        "aggregation_warning": "All stores are aggregated; promotion is true if display or mailer is recorded for at least one store.",
        "sales_value_included_in_customer_panel": False,
        "limitation": "Observed association only. This dataset cannot establish incremental causal impact or profit.",
    }
    output.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Created {output.relative_to(ROOT)} ({len(frame)} rows)")
    print(f"Promotion weeks: {weeks}; preceding weeks: {weeks[0] - 1}; following weeks: {102 - weeks[-1]}")


if __name__ == "__main__":
    main()
