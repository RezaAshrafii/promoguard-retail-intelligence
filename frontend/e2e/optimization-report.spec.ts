// Mocked values verify the export interaction only; they are not business evidence.
import { expect, test } from "@playwright/test";

const comparison = {
  request_id: "e2e-scenario",
  policy: { minimum_incremental_profit: "0", currency: "IRR", reference: "test-only", approved_by: "test-only", as_of_date: "2026-10-14" },
  assessments: [{
    scenario_id: "case-a",
    feasibility_status: "eligible",
    blocking_reasons: [],
    decision: "hurdle_not_resolved",
    hurdle_amount: "0",
    currency: "IRR",
    incremental_profit_lower: "-100",
    incremental_profit_point: "50",
    incremental_profit_upper: "200",
    conditional_economics: {
      baseline_profit: "1000",
      promoted_profit: { lower: "900", point: "1050", upper: "1200", currency: "IRR" },
      incremental_profit: { lower: "-100", point: "50", upper: "200", currency: "IRR" },
      baseline_profit_basis: "test only",
      promoted_profit_basis: "test only",
      limitation: "test only",
    },
    economic_sensitivity: {
      cases: ["downside", "expected", "upside"].map((kind) => ({ case: kind, projected_demand_units: 10, promoted_profit: 1000, incremental_profit: 0, currency: "IRR" })),
      limitation: "test only",
    },
    discount_rate: "0.1",
    projected_unit_contribution: "20",
    projected_trade_spend: "10",
    sellable_inventory_units: 20,
    explanation: "test only",
  }],
  budget_scope: "per_scenario_screen_only",
  selection_status: "manual_review_required",
  selected_scenario_id: null,
  limitation: "Test fixture only.",
};

test("downloads a PDF from the exact request that produced the visible scenario result", async ({ page }) => {
  const submittedBodies: string[] = [];
  await page.route("**/v1/optimization/comparisons", async (route) => {
    submittedBodies.push(route.request().postData() ?? "");
    await route.fulfill({ json: comparison });
  });
  await page.route("**/v1/optimization/comparisons/pdf", async (route) => {
    submittedBodies.push(route.request().postData() ?? "");
    await route.fulfill({
      status: 200,
      contentType: "application/pdf",
      headers: { "Content-Disposition": 'attachment; filename="promoguard-scenario-comparison.pdf"' },
      body: Buffer.from("%PDF-1.4 test-only"),
    });
  });

  await page.goto("/optimization");
  await page.getByRole("button", { name: "ورود JSON" }).click();
  const submittedRequest = '{"test_only":true,"request_id":"e2e-scenario"}';
  await page.getByLabel("متن درخواست").fill(submittedRequest);
  await page.getByRole("button", { name: "مقایسهٔ سناریوها" }).click();
  await expect(page.getByRole("heading", { name: "خلاصهٔ بررسی" })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "دانلود گزارش PDF برای بازبینی" }).click();
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toBe("promoguard-scenario-comparison.pdf");
  expect(submittedBodies).toEqual([submittedRequest, submittedRequest]);
});
