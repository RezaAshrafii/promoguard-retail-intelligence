"""Transparent contracts and constraint checks for promotion scenarios."""

from promoguard.optimization.contracts import (
    EconomicsEvidence,
    EvidenceKind,
    OptimizationInput,
    ProjectionInterval,
    PromotionScenario,
)
from promoguard.optimization.decision_policy import (
    ManagerHurdlePolicy,
    ManagerPolicyComparison,
    ScenarioDecision,
    ScenarioDecisionAssessment,
    evaluate_manager_policy,
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
    "ManagerHurdlePolicy",
    "ManagerPolicyComparison",
    "MonetaryInterval",
    "OptimizationInput",
    "ProjectionInterval",
    "PromotionScenario",
    "ScenarioComparisonReport",
    "ScenarioDecision",
    "ScenarioDecisionAssessment",
    "ScenarioFeasibility",
    "SensitivityCase",
    "assess_scenarios",
    "build_economic_sensitivity",
    "calculate_conditional_economics",
    "compare_scenarios",
    "evaluate_manager_policy",
]
