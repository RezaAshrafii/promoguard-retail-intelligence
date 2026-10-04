"use client";

import { useEffect, useState } from "react";
import { BrandLogo } from "../components/BrandLogo";

type Outcome = "spend" | "conversion" | "visit";
type Comparison = {
  treatment_arm: string;
  control_arm: string;
  contrast_type: "treatment_vs_control" | "treatment_vs_treatment";
  treatment_n: number;
  control_n: number;
  treatment_mean_per_person: number;
  control_mean_per_person: number;
  incremental_effect_per_person: number;
  incremental_effect_per_1000_people: number;
  standard_error_per_person: number;
  familywise_ci_lower_per_person: number;
  familywise_ci_upper_per_person: number;
  statistical_direction_status: string;
  business_goal_status: string;
  decision_explanation: string;
  descriptive_outcomes: Record<string, { treatment_mean: number; control_mean: number; difference: number }>;
};
type ExperimentSummary = {
  benchmark: string;
  source: { dataset_page: string; filename: string; sha256: string; license_status: string };
  design: { sample_rows: number; arm_counts: Record<string, number>; outcome_window: string };
  primary_outcome: {
    name: Outcome;
    unit: string;
    minimum_effect_per_person: number | null;
    business_goal_configured: boolean;
    business_goal_note: string;
  };
  uncertainty: { method: string; critical_value: number; familywise_confidence_level: number; contrast_count: number };
  quality: { valid: boolean; rows: number; duplicate_full_rows_retained: number };
  comparisons: Comparison[];
  interpretation: string[];
};
type ReportJob = {
  report_id: string;
  status: string;
  progress: number;
  error?: string | null;
  result?: ExperimentSummary | null;
  cache_hit?: boolean | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const number = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 2 });
const money = (value: number) => `$${number.format(value)}`;

async function apiJson(path: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : "درخواست ارزیابی کامل نشد.");
  }
  return payload;
}

function outcomeLabel(outcome: Outcome) {
  if (outcome === "spend") return "درآمد ناخالص";
  if (outcome === "conversion") return "نرخ خرید";
  return "نرخ بازدید";
}

function statusText(comparison: Comparison, configuredGoal: boolean, outcome: Outcome) {
  if (comparison.statistical_direction_status === "insufficient_sample") return "تعداد نمونه برای حکم کافی نیست";
  if (comparison.contrast_type === "treatment_vs_treatment") {
    if (comparison.statistical_direction_status === "positive_evidence_vs_zero") return "نسخهٔ اول بالاتر است";
    if (comparison.statistical_direction_status === "negative_evidence_vs_zero") return "نسخهٔ دوم بالاتر است";
    return "تفاوت روشن نیست";
  }
  if (configuredGoal && comparison.business_goal_status === "goal_supported") return "به هدف تعیین‌شده رسیده";
  if (configuredGoal && comparison.business_goal_status === "goal_not_supported") return "به هدف تعیین‌شده نرسیده";
  if (comparison.statistical_direction_status === "positive_evidence_vs_zero") return `افزایش ${outcomeLabel(outcome)} دیده شده`;
  if (comparison.statistical_direction_status === "negative_evidence_vs_zero") return `کاهش ${outcomeLabel(outcome)} دیده شده`;
  return "نتیجه هنوز روشن نیست";
}

function displayEffect(value: number, outcome: Outcome) {
  if (outcome === "spend") return money(value);
  return `${number.format(value * 100)} واحد درصد`;
}

export default function ExperimentsPage() {
  const [outcome, setOutcome] = useState<Outcome>("spend");
  const [threshold, setThreshold] = useState("");
  const [job, setJob] = useState<ReportJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function poll(reportId: string) {
    setBusy(true);
    for (let attempt = 0; attempt < 180; attempt += 1) {
      const next: ReportJob = await apiJson(`/v1/reports/${reportId}`);
      setJob(next);
      if (next.status === "ready" || next.status === "failed") {
        if (next.status === "failed") throw new Error(next.error ?? "تحلیل آزمایش کامل نشد.");
        setBusy(false);
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 1_000));
    }
    throw new Error("گزارش هنوز در حال اجراست؛ با «بررسی وضعیت» دوباره پیگیری کن.");
  }

  async function openReport(reportId: string) {
    setError(null);
    try {
      await poll(reportId);
    } catch (caught) {
      setBusy(false);
      setError(caught instanceof Error ? caught.message : "گزارش دریافت نشد.");
    }
  }

  async function runAnalysis() {
    const parsedThreshold = threshold.trim() === "" ? null : Number(threshold);
    if (parsedThreshold !== null && !Number.isFinite(parsedThreshold)) {
      setError("حداقل اثر را به‌صورت عدد وارد کن.");
      return;
    }
    setBusy(true);
    setError(null);
    setJob(null);
    try {
      const created: ReportJob = await apiJson("/v1/experiments/hillstrom/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ primary_outcome: outcome, minimum_effect_per_person: parsedThreshold }),
      });
      setJob(created);
      const url = new URL(window.location.href);
      url.searchParams.set("report", created.report_id);
      window.history.replaceState(null, "", url);
      await poll(created.report_id);
    } catch (caught) {
      setBusy(false);
      setError(caught instanceof Error ? caught.message : "تحلیل آزمایش شروع نشد.");
    }
  }

  useEffect(() => {
    const reportId = new URLSearchParams(window.location.search).get("report");
    if (reportId) void openReport(reportId);
    // A report ID in the URL is the only automatic request on this page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const summary = job?.result ?? null;
  const primary = summary?.comparisons.filter((item) => item.contrast_type === "treatment_vs_control") ?? [];
  const spends = [
    { label: "بدون ایمیل", value: summary?.comparisons[0]?.control_mean_per_person ?? 0 },
    { label: "ایمیل مردانه", value: summary?.comparisons[0]?.treatment_mean_per_person ?? 0 },
    { label: "ایمیل زنانه", value: summary?.comparisons[1]?.treatment_mean_per_person ?? 0 },
  ];
  const maxSpend = Math.max(...spends.map((item) => item.value), 0.01);
  const bothTreatmentsPositive = primary.length === 2 && primary.every((item) => item.statistical_direction_status === "positive_evidence_vs_zero");
  const bothTreatmentsNegative = primary.length === 2 && primary.every((item) => item.statistical_direction_status === "negative_evidence_vs_zero");

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><BrandLogo size={44} /></div>
        <nav aria-label="مسیرهای اصلی">
          <a className="nav-item" href="/">⌂ <span>نمای کلی</span></a>
          <a className="nav-item" href="/">▣ <span>آمادگی داده</span></a>
          <a className="nav-item" href="/">▥ <span>ممیزی پروموشن</span></a>
          <a className="nav-item active" href="/experiments">◉ <span>ارزیابی با گروه کنترل</span></a>
        </nav>
        <div className="sidebar-footer"><small>آزمایش تصادفی عمومی · تحلیل محلی</small></div>
      </aside>

      <section className="content">
        <header className="topbar"><div className="top-actions">
          <button className="secondary" disabled={busy} onClick={() => job?.report_id && void openReport(job.report_id)}>بررسی وضعیت</button>
          <button className="primary" disabled={busy} onClick={() => void runAnalysis()}>{busy ? "در حال تحلیل…" : "اجرای ارزیابی کمپین"}</button>
        </div></header>

        <div className="page-heading"><div>
          <p className="eyebrow">CAMPAIGN EXPERIMENT EVALUATION</p>
          <h1>آیا کمپین درآمد افزوده ایجاد کرد؟</h1>
          <p className="subtitle">مقایسهٔ دو نسخهٔ ایمیل با گروه تصادفیِ بدون ایمیل، بر پایهٔ خرید ثبت‌شده در دو هفته</p>
        </div><span className="large-status ready">دادهٔ آزمایشی واقعی · ۶۴٬۰۰۰ نفر</span></div>

        <div className="notice"><span className="notice-icon">i</span><div>
          <strong>این صفحه یک آزمایش بازاریابی عمومی را تحلیل می‌کند</strong>
          <p>درآمد افزوده با سود فرق دارد؛ هزینهٔ کمپین و حاشیهٔ سود در فایل نیست. نتیجه هم نمایندهٔ تخفیف فروشگاهی یا بازار ایران نیست.</p>
        </div><a className="link-button" href="https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html" target="_blank" rel="noreferrer">منبع داده ↗</a></div>

        <section className="panel experiment-controls">
          <div><h2>معیار قضاوت را مشخص کن</h2><p>بدون هدف تجاری، محصول فقط می‌گوید افزایش یا کاهش درآمد از نظر آماری روشن است یا نه.</p></div>
          <label>پیامد اصلی
            <select value={outcome} onChange={(event) => setOutcome(event.target.value as Outcome)} disabled={busy}>
              <option value="spend">درآمد ناخالص در دو هفته</option>
              <option value="conversion">احتمال خرید</option>
              <option value="visit">احتمال بازدید</option>
            </select>
          </label>
          <label>حداقل افزایش موردنیاز به‌ازای هر نفر <span>{outcome === "spend" ? "دلار" : "درصد به‌صورت اعشاری؛ نمونه ۰٫۰۱ یعنی یک واحد درصد"}</span>
            <input type="number" inputMode="decimal" step={outcome === "spend" ? "0.01" : "0.001"} value={threshold} onChange={(event) => setThreshold(event.target.value)} placeholder="خالی بماند تا فقط جهت آماری بررسی شود" disabled={busy} />
          </label>
          <small>آستانه را مدیر کسب‌وکار تعیین می‌کند. اگر هدف، سود است باید هزینهٔ ارسال، تخفیف و حاشیهٔ سود هم وارد شود؛ این benchmark آن‌ها را ندارد.</small>
        </section>

        {busy && <section className="state-card" role="status" aria-live="polite"><div className="spinner" />در حال محاسبه و آماده‌سازی گزارش<div className="progress-track"><span style={{ width: `${job?.progress ?? 8}%` }} /></div><small>{number.format(job?.progress ?? 8)}٪ · شناسهٔ گزارش: {job?.report_id ?? "در حال ایجاد"}</small></section>}
        {error && <section className="state-card error" role="alert"><strong>گزارش آماده نشد</strong><p>{error}</p></section>}

        {summary && <>
          <section className="experiment-verdict">
            <div><span className="eyebrow">نتیجهٔ اصلی · {summary.primary_outcome.name === "spend" ? "درآمد ناخالص" : summary.primary_outcome.name === "conversion" ? "خرید" : "بازدید"}</span>
              <h2>{bothTreatmentsPositive ? `هر دو نسخه افزایش ${outcomeLabel(summary.primary_outcome.name)} نشان دادند` : bothTreatmentsNegative ? `هر دو نسخه کاهش ${outcomeLabel(summary.primary_outcome.name)} نشان دادند` : `نتیجهٔ ${outcomeLabel(summary.primary_outcome.name)} بین نسخه‌ها یکسان نیست یا هنوز روشن نشده`}</h2>
              <p>این نتیجه دربارهٔ میانگین اثرِ تخصیص به کمپین است؛ حکم سودآوری یا انتخاب خودکار نسخه نیست.</p></div>
            <div className="experiment-report-id"><span>شناسهٔ گزارش</span><strong>{job?.report_id}</strong><span>{job?.cache_hit ? "از گزارش ذخیره‌شده" : "گزارش تازه"}</span></div>
          </section>

          {summary.primary_outcome.name === "spend" && <section className="panel spend-panel">
            <div className="panel-heading"><div><h2>میانگین خرید ثبت‌شده برای هر نفر</h2><p>هر نفر بر اساس گروهی سنجیده شده که به آن تخصیص یافته است.</p></div><span>دلار آمریکا</span></div>
            <div className="spend-bars">{spends.map((item, index) => <div className="spend-bar-row" key={item.label}><span>{item.label}</span><div className="spend-bar-track"><i className={index === 0 ? "control-bar" : "treatment-bar"} style={{ width: `${Math.max(2, (item.value / maxSpend) * 100)}%` }} /></div><strong>{money(item.value)}</strong></div>)}</div>
          </section>}

          <section className="experiment-comparison-grid">
            {summary.comparisons.map((item, index) => {
              const direct = item.contrast_type === "treatment_vs_treatment";
              return <article className="panel experiment-comparison" key={`${item.treatment_arm}-${item.control_arm}`}>
                <span className="comparison-kind">{direct ? "مقایسهٔ مستقیم دو نسخه" : "مقایسه با گروه کنترل"}</span>
                <h3>{item.treatment_arm === "Mens E-Mail" ? "ایمیل محصولات مردانه" : "ایمیل محصولات زنانه"}<small> در برابر </small>{item.control_arm === "No E-Mail" ? "بدون ایمیل" : "ایمیل محصولات زنانه"}</h3>
                <div className="comparison-status">{statusText(item, summary.primary_outcome.business_goal_configured, summary.primary_outcome.name)}</div>
                <div className="comparison-main-number">{displayEffect(item.incremental_effect_per_person, summary.primary_outcome.name)} <small>به‌ازای هر نفر</small></div>
                <p className="comparison-scaled">به‌ازای ۱٬۰۰۰ نفر: <strong>{displayEffect(item.incremental_effect_per_1000_people, summary.primary_outcome.name)}</strong></p>
                <div className="comparison-ci"><span>بازهٔ هم‌زمان ۹۵٪</span><strong>{displayEffect(item.familywise_ci_lower_per_person, summary.primary_outcome.name)} تا {displayEffect(item.familywise_ci_upper_per_person, summary.primary_outcome.name)}</strong></div>
                <p className="comparison-sample">نمونه: {number.format(item.treatment_n)} در گروه اول و {number.format(item.control_n)} در گروه مقایسه</p>
                <div className="comparison-secondary"><span>تغییر احتمال خرید</span><strong>{displayEffect(item.descriptive_outcomes.conversion.difference, "conversion")}</strong><span>تغییر احتمال بازدید</span><strong>{displayEffect(item.descriptive_outcomes.visit.difference, "visit")}</strong></div>
              </article>;
            })}
          </section>

          <section className="notice experiment-caveat"><span className="notice-icon">!</span><div><strong>{summary.primary_outcome.business_goal_configured ? "هدف بررسی شد؛ تفسیر اقتصادی را با هزینه‌های واقعی کامل کن" : "هنوز هدف تجاری وارد نشده"}</strong><p>{summary.primary_outcome.business_goal_note} {summary.uncertainty.method}; تصحیح چندمقایسه‌ای برای {number.format(summary.uncertainty.contrast_count)} مقایسه اعمال شده است.</p></div></section>
          <section className="panel benchmark-details"><h2>این نتیجه دقیقاً از کجا آمده؟</h2>
            <p>ناشر، آزمایش را به‌صورت تصادفی بین دو گروه ایمیل و یک گروه بدون ایمیل توصیف می‌کند. ما ۲۱٬۳۰۶ نفر کنترل، ۲۱٬۳۰۷ نفر ایمیل مردانه و ۲۱٬۳۸۷ نفر ایمیل زنانه را در محاسبه نگه داشتیم.</p>
            <p>۶٬۵۶۲ ردیف کاملاً مشابه حذف نشده‌اند؛ فایل شناسهٔ فردی ندارد و افراد متفاوت می‌توانند نتیجه و مشخصات یکسان داشته باشند. بازه‌ها و محاسبه از کد ثابت محصول ساخته شده‌اند.</p>
            <p>نسخهٔ مردانه و زنانه هر دو در برابر کنترل افزایش درآمد نشان دادند؛ اما تفاوت مستقیم دو نسخه بازه‌ای شامل صفر دارد، پس برتری یکی بر دیگری هنوز روشن نیست.</p>
            <div className="benchmark-provenance"><span>SHA-256 فایل</span><code>{summary.source.sha256}</code></div>
            <div className="benchmark-provenance"><span>مجوز</span><span>{summary.source.license_status}</span></div>
          </section>
        </>}

        {!summary && !busy && <section className="panel experiment-empty"><span className="empty-icon">◉</span><h2>آمادهٔ بررسی یک آزمایش واقعی</h2><p>دادهٔ عمومی Hillstrom شامل ۶۴٬۰۰۰ تخصیص آزمایشی و نتیجهٔ خرید ثبت‌شده است. برای ساخت گزارش، دکمهٔ «اجرای ارزیابی کمپین» را بزن.</p><button className="primary" onClick={() => void runAnalysis()}>اجرای ارزیابی کمپین</button><small>فایل خام محلی است و در GitHub بارگذاری نمی‌شود.</small></section>}
      </section>
    </main>
  );
}
