"""Verified insight objects and evidence-grounded narrative generation."""

from promoguard.insights.decision_support import (
    DecisionOption,
    ManagerAction,
    ManagerDecisionSupport,
    build_manager_decision_support,
)
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
    "DecisionOption",
    "ManagerAction",
    "ManagerDecisionSupport",
    "PromotionAuditResult",
    "SubstitutionCandidate",
    "audit_promotion_event",
    "build_manager_decision_support",
    "detect_promotion_episodes",
    "select_representative_event",
]

