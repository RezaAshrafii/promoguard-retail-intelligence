"""Verified insight objects and evidence-grounded narrative generation."""

from promoguard.insights.promotion_audit import (
    AuditDecision,
    PromotionAuditResult,
    audit_promotion_event,
    detect_promotion_episodes,
    select_representative_event,
)

__all__ = [
    "AuditDecision",
    "PromotionAuditResult",
    "audit_promotion_event",
    "detect_promotion_episodes",
    "select_representative_event",
]

