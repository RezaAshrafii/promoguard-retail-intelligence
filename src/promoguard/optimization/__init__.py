"""Transparent contracts and constraint checks for promotion scenarios."""

from promoguard.optimization.contracts import (
    EconomicsEvidence,
    EvidenceKind,
    OptimizationInput,
    ProjectionInterval,
    PromotionScenario,
)
from promoguard.optimization.feasibility import (
    FeasibilityCode,
    ScenarioFeasibility,
    assess_scenarios,
)

__all__ = [
    "EconomicsEvidence",
    "EvidenceKind",
    "FeasibilityCode",
    "OptimizationInput",
    "ProjectionInterval",
    "PromotionScenario",
    "ScenarioFeasibility",
    "assess_scenarios",
]
