import test from "node:test";
import assert from "node:assert/strict";
import { reportHref, isRetailResult, directionText, goalText, experimentNarrative, reportFormValues } from "./report-view.mjs";

const comparison = { treatment_arm: "Mens E-Mail", control_arm: "No E-Mail", contrast_type: "treatment_vs_control", statistical_direction_status: "positive_evidence_vs_zero", business_goal_status: "inconclusive_vs_goal" };

test("routes experiment, retail, and legacy IDs without treating an experiment as a trend", () => {
  assert.equal(reportHref({report_id:"rpt_A",analysis_type:"randomized_experiment"}), "/experiments?report=rpt_A");
  assert.equal(reportHref({report_id:"rpt_B"}), "/?report=rpt_B");
  assert.equal(reportHref({report_id:"a&b",result:{benchmark:"hillstrom-email-analytics-2008"}}), "/experiments?report=a%26b");
  assert.equal(isRetailResult({benchmark:"hillstrom-email-analytics-2008"}), false);
  assert.equal(isRetailResult({trend:[],audit:{},quality:{},decision_support:{}}),true);
});

test("positive change never silently becomes successful commercial goal", () => {
  assert.match(directionText(comparison,"spend"), /افزایش/);
  assert.equal(goalText(comparison,true),"رسیدن به هدف هنوز روشن نیست");
  for (const [status,expected] of [["goal_supported","به هدف تعیین‌شده رسیده"],["goal_not_supported","به هدف تعیین‌شده نرسیده"],["insufficient_sample","نمونه برای بررسی هدف کافی نیست"]]) {
    assert.equal(goalText({...comparison,business_goal_status:status},true),expected);
  }
  assert.equal(goalText(comparison,false),"هدف تجاری تعیین نشده");
  assert.equal(goalText({...comparison,contrast_type:"treatment_vs_treatment"},true),"هدف تجاری برای مقایسهٔ مستقیم تعریف نشده");
});

test("narrative follows actual outcome and direct comparison, not fixed spend copy", () => {
  const summary={primary_outcome:{name:"conversion",business_goal_configured:false},comparisons:[comparison,{...comparison,control_arm:"Womens E-Mail",contrast_type:"treatment_vs_treatment"}]};
  assert.match(experimentNarrative(summary),/نرخ خرید/);
  assert.match(experimentNarrative(summary),/نسخهٔ اول بالاتر است/);
  assert.doesNotMatch(experimentNarrative(summary),/درآمد/);
  assert.equal(directionText({...comparison,statistical_direction_status:"negative_evidence_vs_zero"},"visit"),"کاهش نرخ بازدید دیده شده");
  assert.equal(directionText({...comparison,statistical_direction_status:"insufficient_sample"},"spend"),"تعداد نمونه برای قضاوت کافی نیست");
});

test("restores all persisted assumptions including zero and clears old finances", () => {
  const report={configuration:{analysis:{primary_outcome:"spend",minimum_effect_per_person:0,financial_assumptions:{common_contribution_margin:0.3,margin_source:"margin",mens_campaign_cost_per_1000:0,mens_cost_source:"mens",womens_campaign_cost_per_1000:60,womens_cost_source:"womens"}}}};
  assert.deepEqual(reportFormValues(report), {outcome:"spend",threshold:"0",marginPercent:"30",marginSource:"margin",mensCost:"0",mensCostSource:"mens",womensCost:"60",womensCostSource:"womens"});
  const legacy=reportFormValues({result:{primary_outcome:{name:"visit",minimum_effect_per_person:0.01}}});
  assert.equal(legacy.outcome,"visit"); assert.equal(legacy.threshold,"0.01");
  assert.equal(legacy.marginSource,""); assert.equal(legacy.mensCost,"");
});
