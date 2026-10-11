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
    EconomicSensitivity,
    MonetaryInterval,
    SensitivityCase,
    build_economic_sensitivity,
    calculate_conditional_economics,
)
from promoguard.optimization.feasibility import (
    FeasibilityCode,
    ScenarioComparisonReport,
    ScenarioFeasibility,
    assess_scenarios,
    compare_scenarios,
)

__all__ = [
    "ConditionalEconomics",
    "EconomicSensitivity",
    "EconomicsEvidence",
    "EvidenceKind",
    "FeasibilityCode",
    "MonetaryInterval",
    "OptimizationInput",
    "ProjectionInterval",
    "PromotionScenario",
    "ScenarioComparisonReport",
    "ScenarioFeasibility",
    "SensitivityCase",
    "assess_scenarios",
    "build_economic_sensitivity",
    "calculate_conditional_economics",
    "compare_scenarios",
]
