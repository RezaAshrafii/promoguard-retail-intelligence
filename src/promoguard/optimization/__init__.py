"""Transparent contracts and constraint checks for promotion scenarios."""

from promoguard.optimization.contracts import (
    EconomicsEvidence,
    EvidenceKind,
    OptimizationInput,
    ProjectionInterval,
    PromotionScenario,
)
from promoguard.optimization.economics import (
    ConditionalEconomics,
    MonetaryInterval,
    calculate_conditional_economics,
)
from promoguard.optimization.feasibility import (
    FeasibilityCode,
    ScenarioFeasibility,
    assess_scenarios,
)

__all__ = [
    "ConditionalEconomics",
    "EconomicsEvidence",
    "EvidenceKind",
    "FeasibilityCode",
    "MonetaryInterval",
    "OptimizationInput",
    "ProjectionInterval",
    "PromotionScenario",
    "ScenarioFeasibility",
    "assess_scenarios",
    "calculate_conditional_economics",
]
