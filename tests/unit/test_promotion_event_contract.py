from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from promoguard.data.contracts import PromotionEventContract, PromotionEventRegistry


def event(**overrides: object) -> PromotionEventContract:
    values: dict[str, object] = {
        "promotion_id": "promo-1",
        "sku_ids": ("sku-1", "sku-2"),
        "start_date": "2025-02-01",
        "end_date": "2025-02-14",
        "discount_type": "percentage_price_reduction",
        "discount_depth": 0.15,
        "discount_depth_unit": "fraction",
        "channel": "retail-store",
        "region": "region-01",
    }
    values.update(overrides)
    return PromotionEventContract(**values)


def test_percentage_event_accepts_fraction_and_cleans_identifiers() -> None:
    result = event(promotion_id=" promo-1 ", sku_ids=(" sku-1 ",))

    assert result.discount_depth == 0.15
    assert result.sku_ids == ("sku-1",)
    assert result.promotion_id == "promo-1"


def test_fixed_amount_event_requires_amount_unit_and_currency() -> None:
    result = event(
        discount_type="fixed_amount_reduction",
        discount_depth=12_500,
        discount_depth_unit="currency_per_unit",
        currency="IRR",
    )

    assert result.currency == "IRR"


def test_non_price_mechanic_has_no_misleading_numeric_depth() -> None:
    result = event(
        discount_type="multibuy",
        discount_depth=None,
        discount_depth_unit="not_reported",
    )

    assert result.discount_depth is None


@pytest.mark.parametrize(
    "changes",
    [
        {"end_date": "2025-01-31"},
        {"discount_depth": 1.01},
        {"discount_depth": float("inf")},
        {"discount_depth": float("nan")},
        {"discount_depth_unit": "currency_per_unit"},
        {"discount_type": "fixed_amount_reduction"},
        {"discount_type": "bundle", "discount_depth": 0.2},
        {"currency": "IR"},
        {"sku_ids": ("sku-1", " sku-1 ")},
        {"sku_ids": ("",)},
        {"unknown_field": "not accepted"},
    ],
)
def test_event_contract_rejects_invalid_semantics(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        event(**changes)


def test_registry_rejects_duplicate_event_ids() -> None:
    with pytest.raises(ValidationError, match="promotion_id must be unique"):
        PromotionEventRegistry(events=(event(), event()))


def test_committed_event_registry_example_matches_contract() -> None:
    path = Path(__file__).parents[2] / "data_contracts" / "promotion_event_registry.v1.example.json"
    registry = PromotionEventRegistry.model_validate_json(path.read_text(encoding="utf-8"))

    assert len(registry.events) == 1
    assert registry.events[0].sku_ids == ("sku-1001", "sku-1002")
