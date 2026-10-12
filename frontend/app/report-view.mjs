// Pure presentation rules shared by the pages and their regression tests.
export function reportHref(report) {
  const experiment = report.analysis_type === "randomized_experiment" || report.result?.benchmark === "hillstrom-email-analytics-2008";
  return `${experiment ? "/experiments" : "/"}?report=${encodeURIComponent(report.report_id)}`;
}

export function isRetailResult(result) {
  return !!result && Array.isArray(result.trend) && !!result.audit && !!result.quality && !!result.decision_support;
}

export function outcomeLabel(outcome) {
  return outcome === "spend" ? "درآمد ناخالص" : outcome === "conversion" ? "نرخ خرید" : "نرخ بازدید";
}

export function directionText(comparison, outcome) {
  if (comparison.statistical_direction_status === "insufficient_sample") return "تعداد نمونه برای قضاوت کافی نیست";
  const direct = comparison.contrast_type === "treatment_vs_treatment";
  if (comparison.statistical_direction_status === "positive_evidence_vs_zero") return direct ? "نسخهٔ اول بالاتر است" : `افزایش ${outcomeLabel(outcome)} دیده شده`;
  if (comparison.statistical_direction_status === "negative_evidence_vs_zero") return direct ? "نسخهٔ دوم بالاتر است" : `کاهش ${outcomeLabel(outcome)} دیده شده`;
  return direct ? "تفاوت روشن نیست" : "نتیجه هنوز روشن نیست";
}

export function goalText(comparison, configured) {
  if (comparison.contrast_type === "treatment_vs_treatment") return "هدف تجاری برای مقایسهٔ مستقیم تعریف نشده";
  if (comparison.business_goal_status === "insufficient_sample") return "نمونه برای بررسی هدف کافی نیست";
  if (!configured) return "هدف تجاری تعیین نشده";
  const labels = {
    goal_supported: "به هدف تعیین‌شده رسیده",
    goal_not_supported: "به هدف تعیین‌شده نرسیده",
    inconclusive_vs_goal: "رسیدن به هدف هنوز روشن نیست",
  };
  return labels[comparison.business_goal_status] ?? "وضعیت هدف در این گزارش ثبت نشده";
}

export function experimentNarrative(summary) {
  const names = {"Mens E-Mail": "ایمیل محصولات مردانه", "Womens E-Mail": "ایمیل محصولات زنانه", "No E-Mail": "بدون ایمیل"};
  return summary.comparisons.map(item => `${names[item.treatment_arm] ?? item.treatment_arm} در برابر ${names[item.control_arm] ?? item.control_arm}: ${directionText(item, summary.primary_outcome.name)}.${item.contrast_type === "treatment_vs_control" ? ` ${goalText(item, summary.primary_outcome.business_goal_configured)}.` : ""}`).join(" ");
}

export function reportFormValues(report) {
  const config = report.configuration?.analysis ?? {};
  const outcome = config.primary_outcome ?? report.result?.primary_outcome?.name ?? "spend";
  const threshold = config.minimum_effect_per_person ?? report.result?.primary_outcome?.minimum_effect_per_person;
  const financial = config.financial_assumptions;
  return {
    outcome,
    threshold: threshold == null ? "" : String(threshold),
    marginPercent: financial ? String(Number((financial.common_contribution_margin * 100).toPrecision(12))) : "",
    marginSource: financial?.margin_source ?? "",
    mensCost: financial ? String(financial.mens_campaign_cost_per_1000) : "",
    mensCostSource: financial?.mens_cost_source ?? "",
    womensCost: financial ? String(financial.womens_campaign_cost_per_1000) : "",
    womensCostSource: financial?.womens_cost_source ?? "",
  };
}
