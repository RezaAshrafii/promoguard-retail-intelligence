# Phase 8.1 real promotion-economics input contract

Phase 8.1 defines what must exist before PromoGuard compares financially constrained promotion
scenarios. It deliberately does not add sample business values to the public demo.

## Required scenario fields

Each scenario identifies a store, SKU, campaign window, and currency, then supplies regular and
promotion price, unit cost, supplier funding, fixed and variable trade spend, available inventory,
baseline demand, and a bounded demand projection. Every financially material field has exactly one
evidence record with a type, reference, date, and approver.

Evidence types are `partner_export`, `approved_contract`, `model_output`, and
`approved_assumption`. These labels preserve the difference between observed inputs and an explicit
what-if assumption.

## Request-level constraints

One request declares total trade-spend budget, minimum unit contribution, maximum discount rate,
inventory reserve, and one or more uniquely identified candidates. All candidates must use the
request currency. Human approval is permanently required and automatic execution is permanently
disabled in the schema.

## Feasibility output

The deterministic pre-check reports every applicable reason:

- promotion price above regular price;
- discount above the approved maximum;
- inventory below the required reserve;
- upper demand projection above sellable inventory;
- projected unit contribution below its floor;
- projected trade spend above budget.

Budget screening uses the **upper** supplied demand projection, not its point estimate:
`fixed_trade_spend + variable_trade_spend_per_unit × projected_demand_units.upper`.
The output exposes `budget_risk_basis=upper_projected_demand`. This is a conservative
constraint convention, not a confidence guarantee: the interval may be miscalibrated or
miss demand outside its bounds. A single request budget is screened per candidate; this
does not approve a portfolio of simultaneous promotions.

The check does not rank candidates. Its contribution calculation is a constraint component, not a
profit forecast: promotion price minus unit cost plus supplier funding minus variable trade spend.
It excludes baseline-margin loss, substitution, forward-buy, taxes, logistics, fixed overhead,
causal incrementality, and forecast error outside the supplied interval.

## Partner data request

The first real pilot should provide source references for each field, one currency, field owners,
an extraction date, units of measure, and permission to use the data. Private partner exports stay
outside Git. Only schema-level fixtures may appear in tests, and they are never presented as
business evidence.
