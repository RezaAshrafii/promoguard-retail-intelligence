import assert from "node:assert/strict";
import test from "node:test";
import { buildScenarioRequest } from "./request-builder.mjs";

function completeForm() {
  const form = {
    request_id: "audit-1", currency: "irr", total_trade_spend_budget: "250000.00", minimum_unit_contribution: "20000",
    maximum_discount_rate: "0.2", inventory_reserve_units: "20", scenario_id: "campaign-1", store_id: "store-1", sku_id: "sku-1",
    start_date: "2026-10-01", end_date: "2026-10-07", scenario_currency: "irr", regular_unit_price: "100000.123456789012345678",
    promotion_unit_price: "90000", unit_cost: "70000", supplier_funding_per_unit: "5000", fixed_trade_spend: "100000",
    variable_trade_spend_per_unit: "1000", available_inventory_units: "200", baseline_demand_units: "80",
    demand_lower: "90", demand_point: "100", demand_upper: "120", policy_minimum_incremental_profit: "500000",
    policy_currency: "irr", policy_reference: "meeting-1", policy_approved_by: "sales-manager", policy_as_of_date: "2026-10-11",
  };
  const fields = [
    "regular_unit_price", "promotion_unit_price", "unit_cost", "supplier_funding_per_unit", "fixed_trade_spend",
    "variable_trade_spend_per_unit", "available_inventory_units", "baseline_demand_units", "projected_demand_units",
  ];
  fields.forEach((_, index) => {
    form[`evidence_${index}_kind`] = index === 8 ? "model_output" : "partner_export";
    form[`evidence_${index}_reference`] = `source-${index}`;
    form[`evidence_${index}_as_of_date`] = "2026-10-11";
    form[`evidence_${index}_approved_by`] = "data-owner";
  });
  return form;
}

test("builds one evidenced request with no invented values and safe execution flags", () => {
  const result = buildScenarioRequest(completeForm());
  assert.equal(result.ok, true);
  const parsed = JSON.parse(result.json);
  assert.equal(parsed.optimization.currency, "IRR");
  assert.equal(parsed.optimization.scenarios.length, 1);
  assert.equal(parsed.optimization.scenarios[0].evidence.length, 9);
  assert.equal(parsed.optimization.scenarios[0].regular_unit_price, "100000.123456789012345678");
  assert.equal(parsed.optimization.scenarios[0].available_inventory_units, 200);
  assert.equal(parsed.optimization.human_approval_required, true);
  assert.equal(parsed.optimization.automatic_execution_allowed, false);
});

test("keeps an empty form empty and returns missing-field guidance", () => {
  const result = buildScenarioRequest({});
  assert.equal(result.ok, false);
  assert.ok(result.errors.includes("request_id:required"));
  assert.ok(result.errors.includes("evidence_8_approved_by:required"));
});

test("rejects malformed dates, decimal commas, invalid currency and unsafe integer values", () => {
  const form = completeForm();
  form.start_date = "1405/07/10";
  form.regular_unit_price = "100,000";
  form.currency = "ریال";
  form.available_inventory_units = "9007199254740993";
  const result = buildScenarioRequest(form);
  assert.equal(result.ok, false);
  assert.ok(result.errors.includes("start_date:date"));
  assert.ok(result.errors.includes("regular_unit_price:number"));
  assert.ok(result.errors.includes("currency:currency"));
  assert.ok(result.errors.includes("available_inventory_units:integer"));
});
