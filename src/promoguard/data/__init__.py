"""Data ingestion, validation, and feature preparation."""

from promoguard.data.contracts import (
    CustomerDataContract,
    PromotionEventContract,
    PromotionEventRegistry,
    standard_customer_data_contract,
)
from promoguard.data.intake import assess_partner_intake
from promoguard.data.panel import (
    load_weekly_panel,
    resolve_weekly_panel,
    validate_canonical_panel,
)
from promoguard.data.partner import (
    PartnerExportContract,
    prepare_partner_export,
    sha256_bytes,
    sha256_file,
)

__all__ = [
    "CustomerDataContract",
    "PartnerExportContract",
    "PromotionEventContract",
    "PromotionEventRegistry",
    "assess_partner_intake",
    "load_weekly_panel",
    "prepare_partner_export",
    "resolve_weekly_panel",
    "sha256_bytes",
    "sha256_file",
    "standard_customer_data_contract",
    "validate_canonical_panel",
]

