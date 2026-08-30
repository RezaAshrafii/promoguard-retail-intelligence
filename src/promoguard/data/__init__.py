"""Data ingestion, validation, and feature preparation."""

from promoguard.data.panel import (
    load_weekly_panel,
    resolve_weekly_panel,
    validate_canonical_panel,
)

__all__ = ["load_weekly_panel", "resolve_weekly_panel", "validate_canonical_panel"]

