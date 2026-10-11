import pandas as pd
import pytest

from promoguard.experiments.revenue_details import (
    FinancialAssumptions,
    build_revenue_details,
    revenue_profile,
)


def test_manual_decomposition_and_financial_bounds():
    treatment = pd.DataFrame({"spend": [10, 12, 0, 0]})
    control = pd.DataFrame({"spend": [2, 0, 0, 0]})
    result = build_revenue_details(treatment, control, (5, -1, 11))
    assert result["additional_buyers_per_1000_assigned"] == 250
    parts = result["decomposition"]
    assert parts["purchase_rate_component_per_customer"] == pytest.approx(1.625)
    assert parts["buyer_spend_component_per_customer"] == pytest.approx(3.375)
    case = result["break_even_scenarios"][2]
    assert case["maximum_incremental_cost_per_1000"] == pytest.approx(1500)
    assert case["lower_bound_cost_per_1000"] == pytest.approx(-300)
    assert case["basis"] == "hypothetical_margin_not_observed"


def test_zero_buyers_preserved_without_inventing_buyer_spend():
    zero = pd.DataFrame({"spend": [0, 0, 0]})
    profile = revenue_profile(zero)
    assert profile["assigned_customers"] == 3
    assert profile["spend_per_buyer"] is None
    assert profile["top_one_percent_customer_revenue_share"] is None
    assert build_revenue_details(zero, zero, (0, 0, 0))["decomposition"] is None


def test_permutation_invariant_and_negative_effect_not_clipped():
    first = pd.DataFrame({"spend": [0, 1, 20, 0]})
    second = pd.DataFrame({"spend": [2, 3, 30, 0]})
    result = build_revenue_details(first, second, (-3.5, -8, 1))
    reordered = build_revenue_details(first.iloc[::-1], second.iloc[::-1], (-3.5, -8, 1))
    assert result == reordered
    assert result["break_even_scenarios"][0]["maximum_incremental_cost_per_1000"] < 0
    assert result["treatment"]["buyers"] == 2


def test_concentration_rounds_up_and_keeps_full_population():
    profile = revenue_profile(pd.DataFrame({"spend": [0] * 100 + [100]}))
    assert profile["top_one_percent_customer_count"] == 2
    assert profile["assigned_customers"] == 101
    assert profile["top_one_percent_customer_revenue_share"] == 1


def test_user_financial_inputs_calculate_campaign_and_variant_cost_differences():
    inputs = FinancialAssumptions(
        common_contribution_margin=0.3,
        margin_source="finance memo, 2026-10-12",
        mens_campaign_cost_per_1000=90,
        mens_cost_source="mens send invoice",
        womens_campaign_cost_per_1000=60,
        womens_cost_source="womens send invoice",
    )
    treatment = pd.DataFrame({"spend": [10, 12, 0, 0]})
    control = pd.DataFrame({"spend": [2, 0, 0, 0]})
    vs_control = build_revenue_details(
        treatment, control, (5, 4, 6), inputs,
        treatment_arm="Mens E-Mail", control_arm="No E-Mail",
    )["conditional_economics"]
    assert vs_control["incremental_campaign_cost_per_1000"] == 90
    assert vs_control["contribution_per_1000"] == {
        "point": 1410,
        "lower": 1110,
        "upper": 1710,
    }
    assert vs_control["source_verification"].endswith("not_independently_verified")

    vs_variant = build_revenue_details(
        treatment, control, (5, 4, 6), inputs,
        treatment_arm="Mens E-Mail", control_arm="Womens E-Mail",
    )["conditional_economics"]
    assert vs_variant["incremental_campaign_cost_per_1000"] == 30
    assert vs_variant["contribution_per_1000"]["point"] == 1470


@pytest.mark.parametrize(
    "payload",
    [
        {"common_contribution_margin": 1.01, "margin_source": "x", "mens_campaign_cost_per_1000": 1, "mens_cost_source": "x", "womens_campaign_cost_per_1000": 1, "womens_cost_source": "x"},
        {"common_contribution_margin": 0.3, "margin_source": " ", "mens_campaign_cost_per_1000": 1, "mens_cost_source": "x", "womens_campaign_cost_per_1000": 1, "womens_cost_source": "x"},
        {"common_contribution_margin": 0.3, "margin_source": "x", "mens_campaign_cost_per_1000": -1, "mens_cost_source": "x", "womens_campaign_cost_per_1000": 1, "womens_cost_source": "x"},
        {"common_contribution_margin": 0.3, "margin_source": "x", "mens_campaign_cost_per_1000": 1, "mens_cost_source": "x", "womens_campaign_cost_per_1000": 1, "womens_cost_source": "x", "currency": "IRR"},
    ],
)
def test_financial_assumption_contract_rejects_invalid_values(payload):
    with pytest.raises(ValueError):
        FinancialAssumptions.model_validate(payload)
