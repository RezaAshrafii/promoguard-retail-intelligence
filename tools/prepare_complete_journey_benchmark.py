"""Create a reproducible, provenance-labeled weekly panel from public source data."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/complete-journey/agg_promo_sales_weekly.parquet"
SOURCE_ARCHIVE = ROOT / "data/raw/complete-journey/dunnhumby-complete-journey-data.zip"
OUTPUT_DIR = ROOT / "data/processed/complete-journey"
PRODUCT_ID = 908846
ANCHOR = date(2010, 1, 3)  # Display-only anchor; source has week indices, not dates.


def _build_from_raw_archive() -> tuple[pd.DataFrame, list[int], str]:
    """Aggregate the publisher-linked raw CSV archive without adding it to Git."""
    if not SOURCE_ARCHIVE.is_file():
        raise SystemExit(f"Missing source archive: {SOURCE_ARCHIVE}")
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        transactions = pd.read_csv(
            archive.open("transaction_data.csv"),
            usecols=["PRODUCT_ID", "WEEK_NO", "QUANTITY"],
        )
        coupons = pd.read_csv(archive.open("coupon.csv"), usecols=["PRODUCT_ID", "CAMPAIGN"])
        campaigns = pd.read_csv(
            archive.open("campaign_desc.csv"), usecols=["CAMPAIGN", "START_DAY", "END_DAY"]
        )

    product_rows = transactions.loc[transactions["PRODUCT_ID"].eq(PRODUCT_ID)].copy()
    if sorted(product_rows["WEEK_NO"].unique().tolist()) != list(range(1, 103)):
        raise SystemExit("Expected one complete, consecutive 102-week product series")
    weekly = product_rows.groupby("WEEK_NO", as_index=False)["QUANTITY"].sum()
    product_campaigns = set(coupons.loc[coupons["PRODUCT_ID"].eq(PRODUCT_ID), "CAMPAIGN"])
    campaigns = campaigns.loc[campaigns["CAMPAIGN"].isin(product_campaigns)].copy()
    promotion_weeks = [
        week
        for week in range(1, 103)
        if bool(
            (
                (campaigns["START_DAY"] <= week * 7)
                & (campaigns["END_DAY"] >= (week - 1) * 7 + 1)
            ).any()
        )
    ]
    weekly["promotion_flag"] = weekly["WEEK_NO"].isin(promotion_weeks).astype(int)
    frame = pd.DataFrame(
        {
            "week_end_date": [
                (ANCHOR + timedelta(weeks=int(week) - 1)).isoformat()
                for week in weekly["WEEK_NO"]
            ],
            "store_id": "ALL_STORES",
            "upc": str(PRODUCT_ID),
            "units": weekly["QUANTITY"].astype(float).to_list(),
            "promotion_flag": weekly["promotion_flag"].to_list(),
        }
    )
    return frame, promotion_weeks, "coupon-product campaign intervals inferred from raw publisher-linked CSVs"


def main() -> None:
    if SOURCE.is_file():
        source = pd.read_parquet(SOURCE)
        required = {
            "PRODUCT_ID", "WEEK_NO", "Units", "Sales",
            "OnDisplay_AnyStore", "InMailer_AnyStore",
        }
        missing = required - set(source.columns)
        if missing:
            raise SystemExit(f"Unexpected source schema; missing: {sorted(missing)}")
        selected = source.loc[source["PRODUCT_ID"].eq(PRODUCT_ID)].sort_values("WEEK_NO")
        event = selected["OnDisplay_AnyStore"].astype(bool) | selected["InMailer_AnyStore"].astype(bool)
        weeks = selected.loc[event, "WEEK_NO"].astype(int).tolist()
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
        promotion_definition = "display or mailer recorded for at least one store"
    else:
        frame, weeks, promotion_definition = _build_from_raw_archive()
    source_for_metadata = SOURCE if SOURCE.is_file() else SOURCE_ARCHIVE
    source_digest = hashlib.sha256(source_for_metadata.read_bytes()).hexdigest()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "week-index-not-real-dates_complete-journey_product-908846.csv"
    frame.to_csv(output, index=False)
    metadata = {
        "source_dataset": "dunnhumby The Complete Journey derived weekly promotion-sales aggregate",
        "source_file": source_for_metadata.name,
        "source_sha256": source_digest,
        "source_url": "https://github.com/bltap-plmarket/dunnhumby-complete-journey/releases/tag/v1.0-data",
        "official_dataset_page": "https://www.dunnhumby.com/source-files/",
        "product_id": PRODUCT_ID,
        "rows": len(frame),
        "week_index_range": [1, 102],
        "promotion_week_indices": weeks,
        "display_date_anchor": ANCHOR.isoformat(),
        "display_date_warning": "Dates are synthetic labels preserving weekly order; the source supplies week indices, not calendar dates.",
        "aggregation_warning": f"All stores are aggregated; promotion flag definition: {promotion_definition}.",
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
