"use client";

import { useEffect, useMemo, useState } from "react";
import { BrandLogo } from "./components/BrandLogo";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Warning = { code: string; severity: string; message: string };
type TrendPoint = { week_end_date: string; units: number; promotion_flag: number };
type WindowSummary = { requested_weeks: number; observed_weeks: number; total_units: number; mean_units: number | null; promotion_weeks: number };
type PromotionEvent = { audit_id: string; store_id: string; upc: string; start_date: string; end_date: string; duration_weeks: number };
type DecisionOption = { action: "repeat" | "modify" | "more_testing" | "deprioritize"; label: string; availability: string; explanation: string };
type DecisionSupport = { recommended_action: DecisionOption["action"]; label: string; explanation: string; evidence_basis: string; options: DecisionOption[]; limitation: string };
type ReportRecord = { report_id: string; dataset_id: string; status: string; progress: number; result?: Summary; error?: string; created_at?: string };
type Summary = {
  dataset_name?: string;
  source_notes?: string[];
  quality: {
    valid: boolean;
    rows: number;
    series: number;
    promotion_rows: number;
    duplicate_grain_rows: number;
    date_min: string;
    date_max: string;
    warnings: string[];
  };
  audit: {
    audit_id: string;
    store_id: string;
    upc: string;
    start_date: string;
    end_date: string;
    duration_weeks: number;
    observed_units: number;
    baseline_units: { point: number; lower: number; upper: number };
    estimated_units_difference_vs_baseline: { point: number; lower: number; upper: number };
    recommendation: string;
    recommendation_rationale: string;
    claim_language: string;
    warnings: Warning[];
    pre_window: WindowSummary;
    during_window: WindowSummary;
    post_window: WindowSummary;
    cannibalization: { status: string; eligible_neighbor_count: number; limitation: string; candidates: Array<{ upc: string; focal_units_change_per_week: number | null; observed_units_change_per_week: number; limitation: string }> };
  };
  decision_support: DecisionSupport;
  trend: TrendPoint[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const DATASET_PATH = process.env.NEXT_PUBLIC_DATASET_PATH ?? "";

async function apiJson(path: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const payload = await response.json();
  if (!response.ok) {
    const detail = payload.detail;
    throw new Error(typeof detail === "string" ? detail : "ساختار فایل یا اطلاعات انتخاب‌شده نیاز به اصلاح دارد.");
  }
  return payload;
}

function faNumber(value: number, digits = 0) {
  return new Intl.NumberFormat("fa-IR", { maximumFractionDigits: digits }).format(value);
}

function pct(value: number) {
  return `${value > 0 ? "+" : ""}${faNumber(value, 1)}٪`;
}

function recommendationLabel(value: string) {
  if (value === "candidate_for_controlled_test") return "نامزد آزمون کنترل‌شده";
  if (value === "deprioritize_and_investigate") return "نیازمند بررسی و کم‌اولویت";
  return "شواهد فعلی کافی نیست";
}

function warningLabel(code: string) {
  const labels: Record<string, string> = {
    OBSERVATIONAL_ONLY: "این نتیجه اثر علّی پروموشن را ثابت نمی‌کند",
    ECONOMIC_IMPACT_UNAVAILABLE: "اطلاعات کامل هزینه و سود در فایل وجود ندارد",
    STOCKOUT_UNOBSERVABLE: "موجودی انبار در این داده قابل مشاهده نیست",
    FORWARD_BUY_RISK: "افت فروش پس از پروموشن نیازمند بررسی است",
  };
  return labels[code] ?? "این بخش از گزارش نیازمند بازبینی است";
}

function warningDetail(code: string) {
  const details: Record<string, string> = {
    OBSERVATIONAL_ONLY: "برای نتیجه علّی باید گروه کنترل یا آزمون معتبر داشته باشیم.",
    ECONOMIC_IMPACT_UNAVAILABLE: "این خروجی سود، هزینه تخفیف یا حاشیه سود را محاسبه نمی‌کند.",
    STOCKOUT_UNOBSERVABLE: "ممکن است فروش به دلیل تمام‌شدن موجودی کمتر از تقاضای واقعی ثبت شده باشد.",
    FORWARD_BUY_RISK: "کاهش فروش بعد از رویداد می‌تواند نشانه جابه‌جایی زمان خرید باشد.",
  };
  return details[code] ?? "برای تصمیم نهایی، منبع داده و زمینه کسب‌وکار بررسی شود.";
}

function rationaleLabel(recommendation: string) {
  if (recommendation === "candidate_for_controlled_test") {
    return "این رویداد برای یک آزمون کنترل‌شده مناسب به نظر می‌رسد، اما هنوز اثر واقعی پروموشن جدا نشده است.";
  }
  if (recommendation === "deprioritize_and_investigate") {
    return "فروش مشاهده‌شده پایین‌تر از خط مبناست؛ قبل از هر تصمیم، موجودی، قیمت و شرایط اجرای پروموشن بررسی شود.";
  }
  return "با داده فعلی نمی‌توان درباره افزایش یا توقف پروموشن تصمیم قطعی گرفت. ابتدا کیفیت شواهد و گروه مقایسه را بهتر کنید.";
}

export default function Home() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [events, setEvents] = useState<PromotionEvent[]>([]);
  const [selectedEventKey, setSelectedEventKey] = useState("");
  const [progress, setProgress] = useState(0);
  const [reportId, setReportId] = useState<string | null>(null);
  const [active, setActive] = useState("overview");
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [reportStatus, setReportStatus] = useState<string | null>(null);

  async function refreshReports() {
    const payload = await apiJson("/v1/reports");
    setReports(payload.reports);
  }

  async function pollReport(id: string) {
    setReportId(id);
    const url = new URL(window.location.href);
    url.searchParams.set("report", id);
    window.history.replaceState(null, "", url);
    for (let attempt = 0; attempt < 90; attempt += 1) {
      const report: ReportRecord = await apiJson(`/v1/reports/${id}`);
      setProgress(report.progress);
      setReportStatus(report.status);
      if (report.status === "ready" && report.result) {
        setSummary(report.result);
        setDatasetId(report.dataset_id);
        await refreshReports();
        return;
      }
      if (report.status === "failed") throw new Error(report.error ?? "تحلیل ناموفق بود؛ تلاش مجدد را بزنید.");
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    throw new Error("گزارش هنوز در حال پردازش است؛ با دکمهٔ بررسی وضعیت دوباره پیگیری کنید.");
  }

  async function openReport(id: string, retry = false) {
    setLoading(true); setError(null); setSummary(null); setActive("overview");
    try {
      if (retry) {
        const created = await apiJson(`/v1/reports/${id}/retry`, { method: "POST" });
        await pollReport(created.report_id);
      } else await pollReport(id);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "گزارش قابل دریافت نیست."); }
    finally { setLoading(false); }
  }

  function resetDataset() {
    setDatasetId(null); setEvents([]); setSelectedFile(null); setSummary(null);
    setReportId(null); setReportStatus(null); setError(null); setActive("overview");
    window.history.replaceState(null, "", window.location.pathname);
  }

  async function loadPromotionsForDataset(id: string) {
    const payload = await apiJson(`/v1/datasets/${id}/promotions`);
    const nextEvents = payload.events as PromotionEvent[];
    setEvents(nextEvents);
    setSelectedEventKey(nextEvents[0]?.audit_id ?? "");
    if (nextEvents.length === 0) setError("در فایل، رویداد پروموشن قابل انتخاب پیدا نشد.");
  }

  async function prepareDataset() {
    setLoading(true);
    setError(null);
    setProgress(5);
    try {
      let id = datasetId;
      if (selectedFile) {
        const form = new FormData();
        form.append("file", selectedFile);
        const dataset = await apiJson("/v1/datasets", { method: "POST", body: form });
        if (dataset.status !== "ready") throw new Error("دادهٔ ارسالی از کنترل‌های کیفیت عبور نکرد.");
        id = dataset.dataset_id;
        setDatasetId(id);
        setProgress(40);
      } else if (!id && DATASET_PATH) {
        const dataset = await apiJson("/v1/datasets/import-path", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ input_path: DATASET_PATH }) });
        if (dataset.status !== "ready") throw new Error("دادهٔ متصل از کنترل‌های کیفیت عبور نکرد.");
        id = dataset.dataset_id;
        setDatasetId(id);
      }
      if (!id) throw new Error("ابتدا فایل CSV را انتخاب کنید.");
      setProgress(65);
      await loadPromotionsForDataset(id);
      setProgress(100);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "ارتباط با سرویس تحلیل برقرار نشد");
    } finally {
      setLoading(false);
    }
  }

  async function createSelectedReport() {
    if (!datasetId || !selectedEventKey) return;
    const selected = events.find((event) => event.audit_id === selectedEventKey);
    if (!selected) return;
    const { store_id, upc, start_date } = selected;
    setLoading(true);
    setSummary(null);
    setError(null);
    setProgress(5);
    try {
      const created = await apiJson("/v1/reports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ dataset_id: datasetId, store_id, upc, start_date }) });
      await pollReport(created.report_id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "ساخت گزارش ناموفق بود.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const saved = new URL(window.location.href).searchParams.get("report");
    if (saved) void openReport(saved);
    else if (DATASET_PATH) void prepareDataset();
    void refreshReports().catch(() => {});
  }, []);

  const chartData = useMemo(
    () =>
      summary?.trend.map((point) => ({
        ...point,
        label: new Intl.DateTimeFormat("fa-IR", { month: "short", day: "numeric" }).format(
          new Date(point.week_end_date),
        ),
      })) ?? [],
    [summary],
  );

  const audit = summary?.audit;
  const change = audit && audit.baseline_units.point !== 0 ? (audit.estimated_units_difference_vs_baseline.point / audit.baseline_units.point) * 100 : null;

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><BrandLogo size={44} /></div>
        <nav aria-label="مسیرهای اصلی">
          <button className={active === "overview" ? "nav-item active" : "nav-item"} onClick={() => setActive("overview")}>⌂ <span>نمای کلی</span></button>
          <button className={active === "readiness" ? "nav-item active" : "nav-item"} onClick={() => setActive("readiness")}>▣ <span>آمادگی داده</span></button>
          <button className={active === "promotion" ? "nav-item active" : "nav-item"} onClick={() => setActive("promotion")}>▥ <span>ممیزی پروموشن</span></button>
          <a className="nav-item" href="/experiments">◉ <span>ارزیابی با گروه کنترل</span></a>
          <button className={active === "history" ? "nav-item active" : "nav-item"} onClick={() => { setActive("history"); void refreshReports().catch(() => setError("دریافت فهرست گزارش‌ها ناموفق بود.")); }}>▤ <span>گزارش‌های ذخیره‌شده</span></button>
        </nav>
        <div className="sidebar-footer"><small>محیط پایلوت خصوصی · بدون دسترسی عمومی</small></div>
      </aside>

      <section className="content">
        <header className="topbar"><div className="top-actions"><button className="secondary" disabled={loading} onClick={resetDataset}>فایل جدید</button><button className="primary" disabled={loading} onClick={() => reportId ? void openReport(reportId) : void prepareDataset()}>↻ بررسی وضعیت</button></div></header>
        <div className="page-heading"><div><p className="eyebrow">EVIDENCE-AWARE RETAIL INTELLIGENCE</p><h1>نمای کلی عملکرد پروموشن</h1><p className="subtitle">تصمیم‌گیری درباره پروموشن با داده واقعی و شواهد قابل بررسی</p></div><div className="scope-badge">غربالگری مشاهده‌ای</div></div>

        {summary?.source_notes?.map((note) => <div className="source-note" key={note}><strong>محدودیت منبع داده</strong><p>{note}</p></div>)}

        {loading && <div className="state-card" role="status" aria-live="polite"><div className="spinner" />در حال آماده‌سازی گزارش...<div className="progress-track"><span style={{ width: `${progress}%` }} /></div><small>{faNumber(progress)}٪ · {reportStatus === "running" ? "تحلیل رویداد در حال انجام است" : "فایل و اطلاعات گزارش بررسی می‌شود"}</small>{reportId && <p className="mono">{reportId}</p>}</div>}
        {error && <div className="state-card error" role="alert"><strong>بررسی نیاز به پیگیری دارد</strong><p>{error}</p><button className="primary" disabled={loading} onClick={() => reportId ? void openReport(reportId, reportStatus === "failed") : void prepareDataset()}>{reportStatus === "failed" ? "تلاش مجدد تحلیل" : "بررسی دوباره"}</button></div>}

        {!loading && active !== "history" && (!summary || events.length > 0) && <section className="upload-card">
          <h2>{datasetId ? "انتخاب رویداد پروموشن" : "شروع بررسی داده"}</h2>
          <p>فایل فروش هفتگی را بررسی کنید و سپس رویداد موردنظر را انتخاب کنید.</p>
          {!datasetId && <><label className="file-picker"><input type="file" accept=".csv,text/csv" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} /><span>{selectedFile ? selectedFile.name : "انتخاب فایل CSV"}</span></label><button className="primary upload-action" disabled={!selectedFile} onClick={() => void prepareDataset()}>بارگذاری و شناسایی رویدادها</button></>}
          {datasetId && events.length > 0 && <><label className="event-picker">رویداد<select value={selectedEventKey} onChange={(event) => setSelectedEventKey(event.target.value)}>{events.map((item) => <option key={item.audit_id} value={item.audit_id}>فروشگاه {item.store_id} · کالا {item.upc} · {item.start_date} تا {item.end_date}</option>)}</select></label><button className="primary upload-action" disabled={!selectedEventKey} onClick={() => void createSelectedReport()}>ساخت گزارش این رویداد</button></>}
          <small>فایل از نظر تاریخ، فروش، تکرار ردیف و وضعیت پروموشن کنترل می‌شود.</small>
        </section>}

        {summary && audit && active === "overview" && (
          <>
            <div className="notice"><span className="notice-icon">i</span><div><strong>این گزارش برای تصمیم‌سازی اولیه است</strong><p>مقایسه فروش قبل و هنگام پروموشن، اثر علّی یا سود خالص را ثابت نمی‌کند.</p></div><button className="link-button" onClick={() => setActive("promotion")}>جزئیات و محدودیت‌ها ←</button></div>
            <section className="kpi-grid">
              <article className="kpi"><span className="kpi-icon blue">▥</span><div><span>فروش در دوره پروموشن</span><strong>{faNumber(audit.observed_units)} <small>واحد</small></strong><em className="neutral">ثبت‌شده در داده</em></div></article>
              <article className="kpi"><span className="kpi-icon slate">⌁</span><div><span>خط مبنای برآوردی</span><strong>{faNumber(audit.baseline_units.point)} <small>واحد</small></strong><em className="neutral">بازه {faNumber(audit.baseline_units.lower)} تا {faNumber(audit.baseline_units.upper)}</em></div></article>
              <article className="kpi"><span className="kpi-icon amber">%</span><div><span>تفاوت با خط مبنا</span><strong className={change !== null && change >= 0 ? "positive" : "negative"}>{change === null ? "درصد قابل محاسبه نیست" : pct(change)}</strong><em>{faNumber(audit.estimated_units_difference_vs_baseline.point)} واحد</em></div></article>
              <article className="kpi"><span className="kpi-icon gold">!</span><div><span>وضعیت تصمیم</span><strong className="status-text">{recommendationLabel(audit.recommendation)}</strong><em className="neutral">نیازمند بررسی انسانی</em></div></article>
            </section>
            <DecisionPanel decision={summary.decision_support} />
            <section className="dashboard-grid">
              <article className="panel trend-panel"><div className="panel-heading"><div><h2>روند فروش رویداد منتخب</h2><p>فروش هفتگی همان کالا و فروشگاه؛ ناحیه رنگی دوره کمپین منتخب است</p></div><span className="legend"><i className="legend-dot blue-dot" /> فروش ثبت‌شده</span></div><div className="chart-wrap"><ResponsiveContainer width="100%" height={280}><LineChart data={chartData} margin={{ top: 14, right: 12, left: 0, bottom: 6 }}><CartesianGrid stroke="#e8edf5" vertical={false} /><XAxis dataKey="week_end_date" tickFormatter={(value) => new Intl.DateTimeFormat("fa-IR", { month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(value))} tick={{ fill: "#77839a", fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" /><YAxis tick={{ fill: "#77839a", fontSize: 11 }} axisLine={false} tickLine={false} width={45} /><Tooltip formatter={(value) => [faNumber(Number(value)), "واحد"]} labelFormatter={(label) => `هفته ${label}`} /><ReferenceArea x1={audit.start_date} x2={audit.end_date} fill="#00b6a4" fillOpacity={0.12} /><Line type="monotone" dataKey="units" stroke="#008e85" strokeWidth={3} dot={{ r: 3, fill: "#008e85", strokeWidth: 0 }} activeDot={{ r: 5 }} /></LineChart></ResponsiveContainer></div><div className="chart-caption"><span>پروموشن: {audit.start_date} تا {audit.end_date}</span><span>فروش مشاهده‌شده: {faNumber(audit.observed_units)} واحد</span></div></article>
              <article className="panel findings"><div className="panel-heading"><div><h2>شواهد و یافته‌ها</h2><p>یافته‌های همین رویداد</p></div><button className="link-button" onClick={() => setActive("promotion")}>مشاهده همه</button></div><div className="finding-list">
                <Finding tone="blue" title={audit.estimated_units_difference_vs_baseline.point > 0 ? "فروش بالاتر از خط مبنا ثبت شده" : audit.estimated_units_difference_vs_baseline.point < 0 ? "فروش پایین‌تر از خط مبنا ثبت شده" : "فروش برابر با خط مبنا ثبت شده"} text={`تفاوت ثبت‌شده ${faNumber(audit.estimated_units_difference_vs_baseline.point)} واحد است؛ علت این تفاوت هنوز اثبات نشده است.`} />
                {audit.warnings.slice(0, 2).map((warning) => <Finding key={warning.code} tone="amber" title={warningLabel(warning.code)} text={warningDetail(warning.code)} />)}
              </div><div className="next-action"><div><strong>پیشنهاد قدم بعدی</strong><p>{summary.decision_support.explanation}</p></div><button className="secondary" onClick={() => setActive("promotion")}>باز کردن جزئیات</button></div></article>
            </section>
              <article className="panel event-strip"><div><span className="label">رویداد منتخب</span><strong>فروشگاه {audit.store_id} · کالای {audit.upc}</strong></div><div><span className="label">مدت</span><strong>{faNumber(audit.duration_weeks)} هفته</strong></div><div><span className="label">شناسه گزارش</span><strong className="mono">{reportId}</strong></div><div><span className="label">وضعیت داده</span><strong className="ready">● معتبر</strong></div></article>
          </>
        )}
        {summary && active === "readiness" && <Readiness quality={summary.quality} />}
        {summary && audit && active === "promotion" && <><div className="report-toolbar"><span>شناسه گزارش: {reportId}</span></div><Promotion audit={audit} trend={chartData} onDownload={() => window.open(`${API_BASE}/v1/reports/${reportId}/pdf`, "_blank", "noopener,noreferrer")} /></>}
        {active === "history" && <section className="panel"><h2>گزارش‌های ذخیره‌شده</h2>{reports.length === 0 && <p>هنوز گزارشی ذخیره نشده است.</p>}{reports.map((report) => <div className="report-history-row" key={report.report_id}><span className="mono">{report.report_id}</span><span>{report.status === "ready" ? "آماده" : report.status === "failed" ? "نیازمند تلاش مجدد" : "در حال پردازش"}</span><button className="secondary" onClick={() => void openReport(report.report_id)}>باز کردن گزارش</button></div>)}</section>}
      </section>
    </main>
  );
}

function Finding({ tone, title, text }: { tone: string; title: string; text: string }) {
  return <div className="finding"><span className={`finding-icon ${tone}`}>{tone === "amber" ? "!" : tone === "blue" ? "i" : "▣"}</span><div><strong>{title}</strong><p>{text}</p></div><span className={`severity ${tone}`}>{tone === "amber" ? "توجه" : tone === "blue" ? "محدودیت" : "بررسی"}</span></div>;
}

function DecisionPanel({ decision }: { decision: DecisionSupport }) {
  const actionLabels: Record<DecisionOption["action"], string> = {
    repeat: "تکرار",
    modify: "اصلاح",
    more_testing: "آزمایش بیشتر",
    deprioritize: "توقف یا کم‌اولویت‌کردن",
  };
  return <section className="decision-panel"><div className="decision-heading"><div><h2>راهنمای تصمیم بعدی</h2><p>{decision.label}</p></div><span>پیشنهاد پشتیبانی‌شده از داده</span></div><p className="decision-explanation">{decision.explanation}</p><div className="decision-options">{decision.options.map((option) => <article className={option.action === decision.recommended_action ? "decision-option recommended" : "decision-option"} key={option.action}><strong>{actionLabels[option.action]}</strong><span>{option.action === decision.recommended_action ? "پیشنهاد این گزارش" : option.availability === "requires_verified_pilot_and_economics" ? "به شواهد پایلوت و سود نیاز دارد" : option.availability === "requires_human_operational_review" ? "نیازمند بررسی انسانی" : option.availability === "recommended_for_human_review" ? "فقط برای بررسی انسانی" : "در حال حاضر پیشنهاد نمی‌شود"}</span></article>)}</div><small>{decision.limitation}</small></section>;
}

function Readiness({ quality }: { quality: Summary["quality"] }) {
  return <><div className="section-title"><div><p className="eyebrow">DATA READINESS</p><h2>آمادگی داده</h2><p>قبل از تحلیل، کیفیت و ساختار فایل بررسی شده است.</p></div><span className="large-status ready">● {quality.valid ? "داده قابل استفاده است" : "داده نیازمند اصلاح است"}</span></div><div className="readiness-grid"><Metric title="تعداد ردیف" value={faNumber(quality.rows)} hint="ردیف هفتگی فروش" /><Metric title="سری کالا و فروشگاه" value={faNumber(quality.series)} hint="ترکیب‌های قابل تحلیل" /><Metric title="ردیف‌های پروموشن" value={faNumber(quality.promotion_rows)} hint="پرچم پروموشن ثبت شده" /><Metric title="تکرار در دانه داده" value={faNumber(quality.duplicate_grain_rows)} hint="باید صفر باشد" good={quality.duplicate_grain_rows === 0} /></div><article className="panel checklist"><h3>نتیجه کنترل‌های اصلی</h3><div className="check-row"><span className="check good">✓</span><div><strong>دانه داده یکتا است</strong><p>هر ردیف برای یک هفته، فروشگاه و کالا ثبت شده است.</p></div><b>{faNumber(quality.duplicate_grain_rows)} تکرار</b></div><div className="check-row"><span className="check good">✓</span><div><strong>بازه زمانی مشخص است</strong><p>{quality.date_min} تا {quality.date_max}</p></div><b>تأیید شد</b></div></article></>;
}

function Metric({ title, value, hint, good = false }: { title: string; value: string; hint: string; good?: boolean }) { return <article className="metric-card"><span>{title}</span><strong>{value}</strong><em className={good ? "positive" : "neutral"}>{hint}</em></article>; }

function Promotion({ audit, trend, onDownload }: { audit: Summary["audit"]; trend: Array<TrendPoint & { label: string }>; onDownload: () => void }) {
  return <>
    <div className="section-title"><div><h2>ممیزی پروموشن</h2><p>فروشگاه {audit.store_id} · کالا {audit.upc} · {audit.start_date} تا {audit.end_date}</p></div><span className="large-status amber">{recommendationLabel(audit.recommendation)}</span></div>
    <section className="audit-layout"><article className="panel"><h3>فروش این رویداد</h3><div className="audit-numbers"><Metric title="فروش مشاهده‌شده" value={faNumber(audit.observed_units)} hint="واحد" /><Metric title="خط مبنا" value={faNumber(audit.baseline_units.point)} hint={`بازه ${faNumber(audit.baseline_units.lower)} تا ${faNumber(audit.baseline_units.upper)}`} /><Metric title="تفاوت" value={faNumber(audit.estimated_units_difference_vs_baseline.point)} hint="واحد نسبت به مبنا" /></div><p className="explanation">{rationaleLabel(audit.recommendation)}</p>
      <h3>پیش از کمپین، هنگام اجرا و پس از آن</h3><div className="table-scroll"><table><thead><tr><th>دوره</th><th>هفته موجود / لازم</th><th>کل فروش</th><th>میانگین هفتگی</th></tr></thead><tbody>{([["قبل", audit.pre_window], ["حین", audit.during_window], ["بعد", audit.post_window]] as [string, WindowSummary][]).map(([label, window]) => <tr key={label}><td>{label}</td><td>{faNumber(window.observed_weeks)} / {faNumber(window.requested_weeks)}</td><td>{faNumber(window.total_units)}</td><td>{window.mean_units === null ? "نامشخص" : faNumber(window.mean_units, 1)}</td></tr>)}</tbody></table></div>
    </article><aside className="panel"><h3>هشدارها و محدودیت‌ها</h3>{audit.warnings.map((warning) => <div className="warning-row" key={warning.code}><div><strong>{warningLabel(warning.code)}</strong><p>{warningDetail(warning.code)}</p></div></div>)}<button className="primary full" onClick={onDownload}>دریافت PDF گزارش</button></aside></section>
    <section className="panel"><h3>کالاهای هم‌دسته</h3><p>{audit.cannibalization.eligible_neighbor_count === 0 ? "کالای هم‌دستهٔ واجد شرایط برای مقایسه پیدا نشد." : `${faNumber(audit.cannibalization.eligible_neighbor_count)} کالای هم‌دسته بررسی شد.`}</p>{audit.cannibalization.candidates.length === 0 ? <p>نشانه‌ای مطابق آستانهٔ این غربالگری پیدا نشد؛ این نتیجه نبود هم‌خوری فروش را اثبات نمی‌کند.</p> : <div className="table-scroll"><table><thead><tr><th>کالای کمپین</th><th>کالای هم‌دسته</th><th>تغییر هفتگی کمپین</th><th>تغییر هفتگی هم‌دسته</th><th>سطح شواهد</th></tr></thead><tbody>{audit.cannibalization.candidates.map((candidate) => <tr key={candidate.upc}><td>{audit.upc}</td><td>{candidate.upc}</td><td>{candidate.focal_units_change_per_week === null ? "نامشخص" : faNumber(candidate.focal_units_change_per_week, 1)}</td><td>{faNumber(candidate.observed_units_change_per_week, 1)}</td><td>مشاهده‌ای؛ رابطهٔ علّی اثبات نشده</td></tr>)}</tbody></table></div>}</section>
    <section className="panel"><h3>فروش هفتگی قابل بررسی</h3><div className="raw-table"><div className="raw-header"><span>هفته</span><span>فروش</span><span>وضعیت</span></div>{trend.map((point) => <div className="raw-row" key={point.week_end_date}><span>{point.week_end_date}</span><strong>{faNumber(point.units)}</strong><span>{point.promotion_flag ? "پروموشن" : "عادی"}</span></div>)}</div></section>
  </>;
}
