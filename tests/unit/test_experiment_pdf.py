from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from apps.api.pdf import build_experiment_report_pdf


def experiment_report() -> dict:
    return {
        "report_id": "rpt_pdf_test_1234",
        "analysis_type": "randomized_experiment",
        "configuration": {
            "analysis": {
                "financial_assumptions": {
                    "common_contribution_margin": 0.3,
                    "margin_source": "test-source <not a tag> & ampersand",
                    "mens_cost_source": "test only",
                    "womens_cost_source": "test only",
                }
            }
        },
        "result": {
            "source": {
                "sha256": "a" * 64,
                "license_status": "No explicit license stated",
                "dataset_page": "https://example.org/hillstrom?a=1&b=2",
            },
            "design": {
                "sample_rows": 64_000,
                "outcome_window": "two weeks after email campaign",
                "arm_counts": {"No E-Mail": 21_306, "Mens E-Mail": 21_307, "Womens E-Mail": 21_387},
            },
            "primary_outcome": {"name": "spend", "unit": "USD gross revenue per assigned customer"},
            "uncertainty": {
                "method": "Welch normal interval",
                "contrast_count": 3,
                "multiple_comparison_adjustment": "Bonferroni",
                "bootstrap": {
                    "method": "Empirical nonparametric percentile bootstrap",
                    "repetitions": 10_000,
                    "seed": 20_261_012,
                },
            },
            "comparisons": [
                {
                    "treatment_arm": "Mens E-Mail", "control_arm": "No E-Mail",
                    "treatment_mean_per_person": 1.42, "control_mean_per_person": 0.65,
                    "incremental_effect_per_person": 0.77,
                    "familywise_ci_lower_per_person": 0.42,
                    "familywise_ci_upper_per_person": 1.12,
                    "bootstrap_ci_lower_per_person": 0.40,
                    "bootstrap_ci_upper_per_person": 1.14,
                    "bootstrap_stability_status": "consistent",
                    "statistical_direction_status": "positive_evidence_vs_zero",
                    "revenue_details": {"conditional_economics": {
                        "incremental_campaign_cost_per_1000": 90,
                        "contribution_per_1000": {"point": 140.95, "lower": 36.63, "upper": 245.26},
                    }},
                },
                {
                    "treatment_arm": "Womens E-Mail", "control_arm": "No E-Mail",
                    "treatment_mean_per_person": 1.08, "control_mean_per_person": 0.65,
                    "incremental_effect_per_person": 0.42,
                    "familywise_ci_lower_per_person": 0.11,
                    "familywise_ci_upper_per_person": 0.74,
                    "bootstrap_ci_lower_per_person": 0.09,
                    "bootstrap_ci_upper_per_person": 0.76,
                    "bootstrap_stability_status": "consistent",
                    "statistical_direction_status": "positive_evidence_vs_zero",
                    "revenue_details": {"conditional_economics": {
                        "incremental_campaign_cost_per_1000": 60,
                        "contribution_per_1000": {"point": 67.32, "lower": -26.28, "upper": 160.93},
                    }},
                },
                {
                    "treatment_arm": "Mens E-Mail", "control_arm": "Womens E-Mail",
                    "treatment_mean_per_person": 1.42, "control_mean_per_person": 1.08,
                    "incremental_effect_per_person": 0.35,
                    "familywise_ci_lower_per_person": -0.04,
                    "familywise_ci_upper_per_person": 0.73,
                    "bootstrap_ci_lower_per_person": -0.06,
                    "bootstrap_ci_upper_per_person": 0.75,
                    "bootstrap_stability_status": "sensitive_to_method",
                    "statistical_direction_status": "inconclusive_vs_zero",
                    "revenue_details": {"conditional_economics": {
                        "incremental_campaign_cost_per_1000": 30,
                        "contribution_per_1000": {"point": 73.62, "lower": -41.01, "upper": 188.26},
                    }},
                },
            ],
            "interpretation": [
                "Gross spend is not profit.",
                "The email benchmark is not a retail discount study.",
            ],
        },
    }


def test_experiment_pdf_contains_evidence_financial_sources_and_limits() -> None:
    pdf_bytes = build_experiment_report_pdf(experiment_report())
    reader = PdfReader(BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(reader.pages) == 2
    assert reader.metadata.title == "PromoGuard | گزارش ارزیابی آزمایش کمپین"
    assert "rpt_pdf_test_1234" in text
    assert "USD 140.95" in text
    assert any("\ufb50" <= char <= "\ufdff" for char in text)
    assert "USD (0.04)" in text
    assert "https://example.org/hillstrom?a=1&b=2" in text
    assert "USD 0.40" in text
    assert "USD 1.14" in text


def test_experiment_pdf_escapes_user_source_markup() -> None:
    pdf_bytes = build_experiment_report_pdf(experiment_report())
    reader = PdfReader(BytesIO(pdf_bytes))

    assert pdf_bytes.startswith(b"%PDF")
    assert len(reader.pages) >= 1


def test_experiment_pdf_still_renders_legacy_report_without_bootstrap_fields() -> None:
    report = experiment_report()
    report["result"]["uncertainty"].pop("bootstrap")
    for comparison in report["result"]["comparisons"]:
        comparison.pop("bootstrap_ci_lower_per_person")
        comparison.pop("bootstrap_ci_upper_per_person")
        comparison.pop("bootstrap_stability_status")

    reader = PdfReader(BytesIO(build_experiment_report_pdf(report)))

    assert len(reader.pages) >= 1
