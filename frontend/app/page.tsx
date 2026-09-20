"use client";

import { useEffect, useMemo, useState } from "react";
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
type Summary = {
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
    during_window: { observed_weeks: number; total_units: number; mean_units: number | null };
  };
  trend: TrendPoint[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const DATASET_PATH = process.env.NEXT_PUBLIC_DATASET_PATH ?? "";

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [reportId, setReportId] = useState<string | null>(null);
  const [active, setActive] = useState("overview");

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    setProgress(5);
    try {
      let datasetId = reportId ? null : null;
      if (selectedFile) {
        const form = new FormData();
        form.append("file", selectedFile);
        const upload = await fetch(`${API_BASE}/v1/datasets`, { method: "POST", body: form });
        if (!upload.ok) throw new Error(await upload.text());
        const dataset = await upload.json();
        if (dataset.status !== "ready") throw new Error("دادهٔ ارسالی از کنترل‌های کیفیت عبور نکرد.");
        datasetId = dataset.dataset_id;
        setProgress(30);
      }
      if (datasetId) {
        const create = await fetch(`${API_BASE}/v1/reports`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ dataset_id: datasetId }) });
        if (!create.ok) throw new Error(await create.text());
        const created = await create.json();
        setReportId(created.report_id);
        for (let attempt = 0; attempt < 90; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          const status = await fetch(`${API_BASE}/v1/reports/${created.report_id}`);
          const report = await status.json();
          setProgress(report.progress ?? Math.min(95, 30 + attempt));
          if (report.status === "ready") { setSummary(report.result); setProgress(100); break; }
          if (report.status === "failed") throw new Error(report.error ?? "تحلیل گزارش ناموفق بود.");
        }
      } else if (DATASET_PATH) {
        const response = await fetch(`${API_BASE}/v1/dashboard/summary`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ input_path: DATASET_PATH }) });
        if (!response.ok) throw new Error(await response.text());
        setSummary(await response.json());
        setProgress(100);
      } else {
        throw new Error("ابتدا فایل دادهٔ فروش را انتخاب کنید.");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "ارتباط با سرویس تحلیل برقرار نشد");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
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
  const change = audit ? (audit.estimated_units_difference_vs_baseline.point / audit.baseline_units.point) * 100 : 0;

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">P</span><div><strong>PromoGuard</strong><small>Retail intelligence</small></div></div>
        <nav aria-label="مسیرهای اصلی">
          <button className={active === "overview" ? "nav-item active" : "nav-item"} onClick={() => setActive("overview")}>⌂ <span>نمای کلی</span></button>
          <button className={active === "readiness" ? "nav-item active" : "nav-item"} onClick={() => setActive("readiness")}>▣ <span>آمادگی داده</span></button>
          <button className={active === "promotion" ? "nav-item active" : "nav-item"} onClick={() => setActive("promotion")}>▥ <span>ممیزی پروموشن</span></button>
          <button className={active === "manual" ? "nav-item active" : "nav-item"} onClick={() => setActive("manual")}>▤ <span>تحلیل دستی</span></button>
        </nav>
        <div className="sidebar-footer"><span>راهنما</span><span>تنظیمات</span><small>محیط تحلیل سازمانی</small></div>
      </aside>

      <section className="content">
        <header className="topbar"><div className="search">⌕ <span>جست‌وجو در محصولات، فروشگاه‌ها یا گزارش‌ها</span></div><div className="top-actions"><span>آخرین بررسی: امروز</span><button className="primary" onClick={() => void loadDashboard()}>↻ به‌روزرسانی</button></div></header>
        <div className="page-heading"><div><p className="eyebrow">EVIDENCE-AWARE RETAIL INTELLIGENCE</p><h1>نمای کلی عملکرد پروموشن</h1><p className="subtitle">تصمیم‌گیری درباره پروموشن با داده واقعی و شواهد قابل بررسی</p></div><div className="scope-badge">غربالگری مشاهده‌ای</div></div>

        {loading && !summary && <div className="state-card"><div className="spinner" />در حال آماده‌سازی گزارش مدیریتی...<div className="progress-track"><span style={{ width: `${progress}%` }} /></div><small>{progress}% · فایل شما ابتدا از نظر ساختار و کیفیت بررسی می‌شود</small></div>}
        {error && <div className="state-card error"><strong>گزارش آماده نشد</strong><p>{error}</p><button className="primary" onClick={() => void loadDashboard()}>تلاش دوباره</button></div>}

        {!summary && !loading && <section className="upload-card"><div className="upload-icon">↑</div><h2>شروع بررسی داده</h2><p>فایل CSV فروش هفتگی را انتخاب کنید تا کیفیت داده بررسی و گزارش عملکرد پروموشن ساخته شود.</p><label className="file-picker"><input type="file" accept=".csv,text/csv" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} /><span>{selectedFile ? selectedFile.name : "انتخاب فایل CSV"}</span></label><button className="primary upload-action" disabled={!selectedFile} onClick={() => void loadDashboard()}>ساخت گزارش</button><small>فایل در این محیط برای تحلیل نگهداری می‌شود و قبل از گزارش از نظر دانه داده، تاریخ، فروش و پرچم پروموشن کنترل می‌شود.</small></section>}

        {summary && audit && active === "overview" && (
          <>
            <div className="notice"><span className="notice-icon">i</span><div><strong>این گزارش برای تصمیم‌سازی اولیه است</strong><p>مقایسه فروش قبل و هنگام پروموشن، اثر علّی یا سود خالص را ثابت نمی‌کند.</p></div><button className="link-button">راهنمای تفسیر ←</button></div>
            <section className="kpi-grid">
              <article className="kpi"><span className="kpi-icon blue">▥</span><div><span>فروش در دوره پروموشن</span><strong>{faNumber(audit.observed_units)} <small>واحد</small></strong><em className="neutral">ثبت‌شده در داده</em></div></article>
              <article className="kpi"><span className="kpi-icon slate">⌁</span><div><span>خط مبنای برآوردی</span><strong>{faNumber(audit.baseline_units.point)} <small>واحد</small></strong><em className="neutral">بازه {faNumber(audit.baseline_units.lower)} تا {faNumber(audit.baseline_units.upper)}</em></div></article>
              <article className="kpi"><span className="kpi-icon amber">%</span><div><span>تفاوت با خط مبنا</span><strong className={change >= 0 ? "positive" : "negative"}>{pct(change)}</strong><em className={change >= 0 ? "positive" : "negative"}>{faNumber(audit.estimated_units_difference_vs_baseline.point)} واحد</em></div></article>
              <article className="kpi"><span className="kpi-icon gold">!</span><div><span>وضعیت تصمیم</span><strong className="status-text">{recommendationLabel(audit.recommendation)}</strong><em className="neutral">نیازمند بررسی انسانی</em></div></article>
            </section>
            <section className="dashboard-grid">
              <article className="panel trend-panel"><div className="panel-heading"><div><h2>روند فروش رویداد منتخب</h2><p>فروش هفتگی همان کالا و فروشگاه در اطراف پروموشن</p></div><span className="legend"><i className="legend-dot blue-dot" /> فروش ثبت‌شده <i className="legend-dot gray-dot" /> بازه مرجع</span></div><div className="chart-wrap"><ResponsiveContainer width="100%" height={280}><LineChart data={chartData} margin={{ top: 14, right: 12, left: 0, bottom: 6 }}><CartesianGrid stroke="#e8edf5" vertical={false} /><XAxis dataKey="label" tick={{ fill: "#77839a", fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" /><YAxis tick={{ fill: "#77839a", fontSize: 11 }} axisLine={false} tickLine={false} width={45} /><Tooltip formatter={(value) => [faNumber(Number(value)), "واحد"]} labelFormatter={(label) => `هفته ${label}`} /><ReferenceArea x1={chartData.find((p) => p.promotion_flag === 1)?.label} x2={chartData.filter((p) => p.promotion_flag === 1).at(-1)?.label} fill="#315cde" fillOpacity={0.07} /><Line type="monotone" dataKey="units" stroke="#315cde" strokeWidth={3} dot={{ r: 3, fill: "#315cde", strokeWidth: 0 }} activeDot={{ r: 5 }} /></LineChart></ResponsiveContainer></div><div className="chart-caption"><span>پروموشن: {audit.start_date} تا {audit.end_date}</span><span>فروش مشاهده‌شده: {faNumber(audit.observed_units)} واحد</span></div></article>
              <article className="panel findings"><div className="panel-heading"><div><h2>شواهد و یافته‌ها</h2><p>چیزی که از داده می‌دانیم و چیزی که هنوز نمی‌دانیم</p></div><button className="link-button">مشاهده همه</button></div><div className="finding-list"><Finding tone="amber" title="فروش پایین‌تر از خط مبنا ثبت شده" text={`در این رویداد ${faNumber(Math.abs(audit.estimated_units_difference_vs_baseline.point))} واحد کمتر از برآورد مرجع دیده شده است.`} /><Finding tone="blue" title="این نتیجه اثر علّی را ثابت نمی‌کند" text="فصل، موجودی، قیمت و انتخاب فروشگاه می‌توانند بخشی از تفاوت را توضیح دهند." /><Finding tone="slate" title="وضعیت موجودی در این گزارش کامل نیست" text="قبل از تصمیم به توقف یا افزایش بودجه، موجودی و فروش پس از پروموشن بررسی شود." /></div><div className="next-action"><span className="action-icon">→</span><div><strong>پیشنهاد قدم بعدی</strong><p>موجودی و افت فروش پس از پروموشن را بررسی کنید و سپس یک آزمون کنترل‌شده طراحی کنید.</p></div><button className="secondary">باز کردن جزئیات</button></div></article>
            </section>
            <article className="panel event-strip"><div><span className="label">رویداد منتخب</span><strong>فروشگاه {audit.store_id} · کالای {audit.upc}</strong></div><div><span className="label">مدت</span><strong>{faNumber(audit.duration_weeks)} هفته</strong></div><div><span className="label">شناسه گزارش</span><strong className="mono">{audit.audit_id}</strong></div><div><span className="label">وضعیت داده</span><strong className="ready">● معتبر</strong></div></article>
          </>
        )}
        {summary && active === "readiness" && <Readiness quality={summary.quality} />}
        {summary && audit && active === "promotion" && <><div className="report-toolbar"><span>شناسه گزارش: {reportId ?? "گزارش محلی"}</span>{reportId && <button className="secondary" onClick={() => window.open(`${API_BASE}/v1/reports/${reportId}/pdf`, "_blank")}>دریافت PDF</button>}</div><Promotion audit={audit} trend={chartData} /></>}
        {active === "manual" && <div className="empty-page"><span className="empty-icon">⌁</span><h2>تحلیل دستی</h2><p>این بخش در نسخه بعدی برای انتخاب کالا، فروشگاه و بازه دلخواه فعال می‌شود.</p></div>}
      </section>
    </main>
  );
}

function Finding({ tone, title, text }: { tone: string; title: string; text: string }) {
  return <div className="finding"><span className={`finding-icon ${tone}`}>{tone === "amber" ? "!" : tone === "blue" ? "i" : "▣"}</span><div><strong>{title}</strong><p>{text}</p></div><span className={`severity ${tone}`}>{tone === "amber" ? "توجه" : tone === "blue" ? "محدودیت" : "بررسی"}</span></div>;
}

function Readiness({ quality }: { quality: Summary["quality"] }) {
  return <><div className="section-title"><div><p className="eyebrow">DATA READINESS</p><h2>آمادگی داده</h2><p>قبل از تحلیل، کیفیت و ساختار فایل بررسی شده است.</p></div><span className="large-status ready">● {quality.valid ? "داده قابل استفاده است" : "داده نیازمند اصلاح است"}</span></div><div className="readiness-grid"><Metric title="تعداد ردیف" value={faNumber(quality.rows)} hint="ردیف هفتگی فروش" /><Metric title="سری کالا و فروشگاه" value={faNumber(quality.series)} hint="ترکیب‌های قابل تحلیل" /><Metric title="ردیف‌های پروموشن" value={faNumber(quality.promotion_rows)} hint="پرچم پروموشن ثبت شده" /><Metric title="تکرار در دانه داده" value={faNumber(quality.duplicate_grain_rows)} hint="باید صفر باشد" good={quality.duplicate_grain_rows === 0} /></div><article className="panel checklist"><h3>نتیجه کنترل‌های اصلی</h3><div className="check-row"><span className="check good">✓</span><div><strong>دانه داده یکتا است</strong><p>هر ردیف برای یک هفته، فروشگاه و کالا ثبت شده است.</p></div><b>{faNumber(quality.duplicate_grain_rows)} تکرار</b></div><div className="check-row"><span className="check good">✓</span><div><strong>بازه زمانی مشخص است</strong><p>{quality.date_min} تا {quality.date_max}</p></div><b>تأیید شد</b></div></article></>;
}

function Metric({ title, value, hint, good = false }: { title: string; value: string; hint: string; good?: boolean }) { return <article className="metric-card"><span>{title}</span><strong>{value}</strong><em className={good ? "positive" : "neutral"}>{hint}</em></article>; }

function Promotion({ audit, trend }: { audit: Summary["audit"]; trend: Array<TrendPoint & { label: string }> }) {
  return <><div className="section-title"><div><p className="eyebrow">PROMOTION AUDIT</p><h2>ممیزی پروموشن</h2><p>بررسی قابل ردیابی یک رویداد، بدون ادعای سود یا اثر علّی.</p></div><span className="large-status amber">! {recommendationLabel(audit.recommendation)}</span></div><div className="audit-layout"><article className="panel audit-main"><div className="audit-hero"><span className="kpi-icon blue">▥</span><div><span>رویداد منتخب</span><h3>فروشگاه {audit.store_id} · کالای {audit.upc}</h3><p>{audit.start_date} تا {audit.end_date} · {faNumber(audit.duration_weeks)} هفته</p></div></div><div className="audit-numbers"><Metric title="فروش مشاهده‌شده" value={faNumber(audit.observed_units)} hint="واحد" /><Metric title="خط مبنا" value={faNumber(audit.baseline_units.point)} hint={`بازه ${faNumber(audit.baseline_units.lower)} تا ${faNumber(audit.baseline_units.upper)}`} /><Metric title="تفاوت" value={faNumber(audit.estimated_units_difference_vs_baseline.point)} hint="واحد نسبت به مبنا" /></div><div className="explanation"><h3>این عدد چه می‌گوید؟</h3><p>{rationaleLabel(audit.recommendation)}</p><small>این گزارش برای غربالگری است و اثر علّی، سود خالص یا تضمین فروش را ادعا نمی‌کند.</small></div></article><aside className="panel audit-side"><h3>کنترل ادعا</h3>{audit.warnings.map((warning) => <div className="warning-row" key={warning.code}><span className="finding-icon amber">!</span><div><strong>{warningLabel(warning.code)}</strong><p>{warningDetail(warning.code)}</p></div></div>)}<button className="primary full">دریافت گزارش قابل اشتراک</button></aside></div><article className="panel"><h3>روند خام قابل بررسی</h3><div className="raw-table"><div className="raw-header"><span>هفته</span><span>فروش</span><span>وضعیت</span></div>{trend.map((point) => <div className="raw-row" key={point.week_end_date}><span>{point.label}</span><strong>{faNumber(point.units)}</strong><span className={point.promotion_flag ? "tag promotion" : "tag"}>{point.promotion_flag ? "پروموشن" : "عادی"}</span></div>)}</div></article></>;
}
