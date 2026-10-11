const evidenceFields = [
  "regular_unit_price",
  "promotion_unit_price",
  "unit_cost",
  "supplier_funding_per_unit",
  "fixed_trade_spend",
  "variable_trade_spend_per_unit",
  "available_inventory_units",
  "baseline_demand_units",
  "projected_demand_units",
];

const decimalFields = [
  "total_trade_spend_budget",
  "minimum_unit_contribution",
  "maximum_discount_rate",
  "regular_unit_price",
  "promotion_unit_price",
  "unit_cost",
  "supplier_funding_per_unit",
  "fixed_trade_spend",
  "variable_trade_spend_per_unit",
  "baseline_demand_units",
  "demand_lower",
  "demand_point",
  "demand_upper",
  "policy_minimum_incremental_profit",
];

const identifierFields = [
  "request_id",
  "scenario_id",
  "store_id",
  "sku_id",
  "currency",
  "scenario_currency",
  "start_date",
  "end_date",
  "inventory_reserve_units",
  "available_inventory_units",
  "policy_currency",
  "policy_reference",
  "policy_approved_by",
  "policy_as_of_date",
];

function isIsoDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
}

/** Build one manager-reviewed scenario request without inventing missing inputs. */
export function buildScenarioRequest(form) {
  const errors = [];
  for (const key of [...identifierFields, ...decimalFields]) {
    if (!String(form[key] ?? "").trim()) errors.push(`${key}:required`);
  }

  for (const key of decimalFields) {
    const value = String(form[key] ?? "").trim();
    if (value && !/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value)) {
      errors.push(`${key}:number`);
    }
  }

  for (const key of ["start_date", "end_date", "policy_as_of_date", ...evidenceFields.map((_, i) => `evidence_${i}_as_of_date`)]) {
    const value = String(form[key] ?? "").trim();
    if (value && !isIsoDate(value)) errors.push(`${key}:date`);
  }

  for (const key of ["currency", "scenario_currency", "policy_currency"]) {
    const value = String(form[key] ?? "").trim();
    if (value && !/^[A-Za-z]{3}$/.test(value)) errors.push(`${key}:currency`);
  }

  for (const key of ["inventory_reserve_units", "available_inventory_units"]) {
    const value = String(form[key] ?? "").trim();
    if (value && (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value)))) errors.push(`${key}:integer`);
  }

  const evidence = evidenceFields.map((field, index) => {
    const values = {
      kind: String(form[`evidence_${index}_kind`] ?? "").trim(),
      reference: String(form[`evidence_${index}_reference`] ?? "").trim(),
      as_of_date: String(form[`evidence_${index}_as_of_date`] ?? "").trim(),
      approved_by: String(form[`evidence_${index}_approved_by`] ?? "").trim(),
    };
    for (const [key, value] of Object.entries(values)) {
      if (!value) errors.push(`evidence_${index}_${key}:required`);
    }
    if (values.kind && !["partner_export", "approved_contract", "model_output", "approved_assumption"].includes(values.kind)) {
      errors.push(`evidence_${index}_kind:choice`);
    }
    return { field_name: field, ...values };
  });

  if (errors.length) return { ok: false, errors };

  const value = (key) => String(form[key]).trim();
  const inventory = Number(value("available_inventory_units"));
  const reserve = Number(value("inventory_reserve_units"));
  const currency = value("currency").toUpperCase();
  const payload = {
    optimization: {
      request_id: value("request_id"),
      currency,
      total_trade_spend_budget: value("total_trade_spend_budget"),
      minimum_unit_contribution: value("minimum_unit_contribution"),
      maximum_discount_rate: value("maximum_discount_rate"),
      inventory_reserve_units: reserve,
      human_approval_required: true,
      automatic_execution_allowed: false,
      scenarios: [{
        scenario_id: value("scenario_id"),
        store_id: value("store_id"),
        sku_id: value("sku_id"),
        start_date: value("start_date"),
        end_date: value("end_date"),
        currency: value("scenario_currency").toUpperCase(),
        regular_unit_price: value("regular_unit_price"),
        promotion_unit_price: value("promotion_unit_price"),
        unit_cost: value("unit_cost"),
        supplier_funding_per_unit: value("supplier_funding_per_unit"),
        fixed_trade_spend: value("fixed_trade_spend"),
        variable_trade_spend_per_unit: value("variable_trade_spend_per_unit"),
        available_inventory_units: inventory,
        baseline_demand_units: value("baseline_demand_units"),
        projected_demand_units: {
          lower: value("demand_lower"),
          point: value("demand_point"),
          upper: value("demand_upper"),
        },
        evidence,
      }],
    },
    policy: {
      minimum_incremental_profit: value("policy_minimum_incremental_profit"),
      currency: value("policy_currency").toUpperCase(),
      reference: value("policy_reference"),
      approved_by: value("policy_approved_by"),
      as_of_date: value("policy_as_of_date"),
    },
  };
  return { ok: true, payload, json: JSON.stringify(payload, null, 2) };
}
