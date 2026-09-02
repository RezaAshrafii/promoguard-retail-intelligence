"""Verified insight objects and evidence-grounded narrative generation."""

from promoguard.insights.promotion_audit import (
    AuditRecommendation,
    CannibalizationSummary,
    ContributionAssumption,
    ContributionSensitivity,
    PromotionAuditResult,
    SubstitutionCandidate,
    audit_promotion_event,
    detect_promotion_episodes,
    select_representative_event,
)

__all__ = [
    "AuditRecommendation",
    "CannibalizationSummary",
    "ContributionAssumption",
    "ContributionSensitivity",
    "PromotionAuditResult",
    "SubstitutionCandidate",
    "audit_promotion_event",
    "detect_promotion_episodes",
    "select_representative_event",
]

