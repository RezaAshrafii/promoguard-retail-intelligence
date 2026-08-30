from datetime import date

import pytest
from pydantic import ValidationError

from promoguard.data.contracts import (
    DunnhumbyWeeklyRecord,
    PromotionRecord,
    SalesDailyRecord,
)


def test_sales_contract_accepts_minimum_record() -> None:
    record = SalesDailyRecord(
        date=date(2026, 1, 1), store_id="store-1", sku_id="sku-1", units=10, revenue=100
    )
    assert record.units == 10


def test_promotion_contract_accepts_discount_depth() -> None:
    record = PromotionRecord(
        promotion_id="promo-1",
        store_id="store-1",
        sku_id="sku-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 7),
        discount_depth=0.2,
    )
    assert record.discount_depth == 0.2


def test_promotion_contract_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        PromotionRecord(
            promotion_id="promo-1",
            store_id="store-1",
            sku_id="sku-1",
            start_date=date(2026, 1, 8),
            end_date=date(2026, 1, 1),
            discount_depth=0.2,
        )


def test_weekly_contract_rejects_tpr_only_conflict() -> None:
    with pytest.raises(ValidationError):
        DunnhumbyWeeklyRecord(
            week_end_date=date(2009, 1, 7),
            store_id="101",
            upc="1111111111",
            units=10,
            visits=8,
            households=7,
            spend=20,
            price=2,
            base_price=2.5,
            feature=1,
            display=0,
            tpr_only=1,
        )
