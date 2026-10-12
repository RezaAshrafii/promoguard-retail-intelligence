// Test-only responses prove UI behavior, not campaign performance.
import { test, expect, Page } from "@playwright/test";

function experiment(outcome = "conversion", status = "ready") {
  const result = {
    benchmark: "hillstrom-email-analytics-2008",
    source: { sha256: "a".repeat(64), dataset_page: "https://example.org", license_status: "test only", filename: "test.csv" },
    design: { sample_rows: 3600, arm_counts: { "Mens E-Mail": 1200, "Womens E-Mail": 1200, "No E-Mail": 1200 }, outcome_window: "two weeks" },
    quality: { valid: true, rows: 3600, duplicate_full_rows_retained: 0 },
    primary_outcome: { name: outcome, unit: "test", minimum_effect_per_person: 0.01, business_goal_configured: true, business_goal_note: "test only" },
    uncertainty: { method: "Welch", critical_value: 2.4, contrast_count: 3, familywise_confidence_level: 0.95 },
    interpretation: [],
    comparisons: ["No E-Mail", "No E-Mail", "Womens E-Mail"].map((control_arm, index) => ({
      treatment_arm: index === 1 ? "Womens E-Mail" : "Mens E-Mail", control_arm,
      contrast_type: index === 2 ? "treatment_vs_treatment" : "treatment_vs_control",
      treatment_n: 1200, control_n: 1200, treatment_mean_per_person: 0.02, control_mean_per_person: 0.01,
      incremental_effect_per_person: 0.01, incremental_effect_per_1000_people: 10, standard_error_per_person: 0.001,
      familywise_ci_lower_per_person: 0.005, familywise_ci_upper_per_person: 0.015,
      statistical_direction_status: "positive_evidence_vs_zero", business_goal_status: index === 2 ? "not_applicable_variant_comparison" : "inconclusive_vs_goal",
      decision_explanation: "test only", descriptive_outcomes: { conversion: { difference: 0.01 }, visit: { difference: 0.02 } },
    })),
  };
  return { report_id: "rpt_e2e", dataset_id: "hillstrom-test", analysis_type: "randomized_experiment", status, progress: status === "ready" ? 100 : 20, configuration: { analysis: { primary_outcome: outcome, minimum_effect_per_person: 0.01, financial_assumptions: null } }, result: status === "ready" ? result : null, error: status === "failed" ? "test failure" : null };
}

async function mockReports(page: Page, record = experiment()) {
  await page.route("**/v1/reports**", async route => {
    const url = new URL(route.request().url());
    if (url.pathname === "/v1/reports") return route.fulfill({ json: { reports: [record,
      { report_id: "rpt_retail", dataset_id: "retail-test", analysis_type: "promotion_audit", status: "ready", progress: 100, result: null },
    ] } });
    if (url.pathname.endsWith("/retry")) return route.fulfill({ status: 202, json: { ...record, report_id: "rpt_retried", status: "queued", result: null } });
    return route.fulfill({ json: { ...record, report_id: url.pathname.split("/").at(-1) } });
  });
}

test("mixed report history opens experiment on its own page without a render crash", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await mockReports(page);
  await page.goto("/?section=history");
  await expect(page.locator('a[href="/?report=rpt_retail"]')).toBeVisible();
  await page.locator('a[href="/experiments?report=rpt_e2e"]').click();
  await expect(page).toHaveURL(/\/experiments\?report=rpt_e2e/);
  await expect(page.getByRole("heading", { name: "تنظیمات این گزارش" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("legacy wrong-page URL redirects rather than calling trend.map", async ({ page }) => {
  await mockReports(page);
  await page.goto("/?report=rpt_e2e");
  await expect(page).toHaveURL(/\/experiments\?report=rpt_e2e/);
  await expect(page.locator(".comparison-status").first()).toHaveText("رسیدن به هدف هنوز روشن نیست");
});

test("restores outcome and goal, uses dynamic direct-comparison copy, and links correct PDF", async ({ page }) => {
  await mockReports(page);
  await page.goto("/experiments?report=rpt_e2e");
  await expect(page.locator(".experiment-controls select")).toHaveValue("conversion");
  await expect(page.locator(".experiment-controls input").first()).toHaveValue("0.01");
  await expect(page.locator(".benchmark-details")).toContainText("نسخهٔ اول بالاتر است");
  await expect(page.locator(".benchmark-details")).not.toContainText("افزایش درآمد");
  await expect(page.locator('a[href$="/rpt_e2e/pdf"]')).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("نرخ خرید");
  await expect(page.locator(".large-status")).toContainText("۳٬۶۰۰");
});

test("restores financial references and a zero cost without inventing defaults", async ({ page }) => {
  const record = { ...experiment("spend"), configuration: { analysis: {
    primary_outcome: "spend", minimum_effect_per_person: 0.5,
    financial_assumptions: { common_contribution_margin: 0.3, margin_source: "test margin",
      mens_campaign_cost_per_1000: 0, mens_cost_source: "test mens",
      womens_campaign_cost_per_1000: 60, womens_cost_source: "test womens" },
  } } };
  await page.route("**/v1/reports/**", route => route.fulfill({ json: record }));
  await page.goto("/experiments?report=rpt_e2e");
  await page.locator(".financial-assumption-inputs summary").click();
  const inputs = page.locator(".financial-assumption-inputs input");
  for (const [index, value] of ["30", "test margin", "0", "test mens", "60", "test womens"].entries()) {
    await expect(inputs.nth(index)).toHaveValue(value);
  }
});

test("failed experiment retries to a new report ID", async ({ page }) => {
  await mockReports(page, experiment("conversion", "failed"));
  await page.route("**/v1/reports/rpt_retried", route => route.fulfill({ json: { ...experiment(), report_id: "rpt_retried" } }));
  await page.goto("/experiments?report=rpt_e2e");
  await page.getByRole("button", { name: "تلاش مجدد تحلیل" }).click();
  await expect(page).toHaveURL(/report=rpt_retried/);
  await expect(page.getByRole("heading", { name: "تنظیمات این گزارش" })).toBeVisible();
});
