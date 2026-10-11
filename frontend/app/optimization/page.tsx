"use client";

import { ChangeEvent, useRef, useState } from "react";
import { BrandLogo } from "../components/BrandLogo";
import { formatApiValidationErrors } from "./api-errors.mjs";
import { formatPersianDecimal } from "./format.mjs";
import { ScenarioRequestBuilder } from "./ScenarioRequestBuilder";
import styles from "./optimization.module.css";

type Assessment = {
  scenario_id: string;
  feasibility_status: "eligible" | "infeasible";
  blocking_reasons: string[];
  decision: "blocked_by_constraints" | "candidate_for_human_review" | "below_manager_hurdle" | "hurdle_not_resolved";
  hurdle_amount: string | number;
  currency: string;
  incremental_profit_lower: string | number;
  incremental_profit_point: string | number;
  incremental_profit_upper: string | number;
  conditional_economics: {
    baseline_profit: string | number;
    promoted_profit: { lower: string | number; point: string | number; upper: string | number; currency: string };
    incremental_profit: { lower: string | number; point: string | number; upper: string | number; currency: string };
    baseline_profit_basis: string;
    promoted_profit_basis: string;
    limitation: string;
  };
  economic_sensitivity: {
    cases: Array<{ case: "downside" | "expected" | "upside"; projected_demand_units: string | number; promoted_profit: string | number; incremental_profit: string | number; currency: string }>;
    limitation: string;
  };
  discount_rate: string | number;
  projected_unit_contribution: string | number;
  projected_trade_spend: string | number;
  sellable_inventory_units: number;
  explanation: string;
};

type Comparison = {
  request_id: string;
  policy: { minimum_incremental_profit: string | number; currency: string; reference: string; approved_by: string; as_of_date: string };
  assessments: Assessment[];
  budget_scope: string;
  selection_status: string;
  selected_scenario_id: null;
  limitation: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const number = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 2 });
const decisionLabels: Record<Assessment["decision"], string> = {
  blocked_by_constraints: "رد شده در بررسی محدودیت‌ها",
  candidate_for_human_review: "نامزد بررسی مدیر",
  below_manager_hurdle: "پایین‌تر از حداقل هدف مدیر",
  hurdle_not_resolved: "برای قضاوت کافی نیست",
};
const reasonLabels: Record<string, string> = {
  promotion_price_above_regular: "قیمت کمپین از قیمت عادی بیشتر است",
  discount_limit_exceeded: "تخفیف از سقف تعیین‌شده عبور کرده",
  inventory_reserve_not_met: "ذخیرهٔ حداقلی موجودی تأمین نشده",
  projected_demand_exceeds_sellable_inventory: "تقاضای برآوردی از موجودی قابل فروش بیشتر است",
  unit_contribution_below_floor: "سهم هر واحد از حداقل تعیین‌شده کمتر است",
  trade_spend_budget_exceeded: "هزینهٔ اجرای کمپین از بودجه بیشتر است",
};

function shownNumber(value: string | number, currency: string) {
  return `${formatPersianDecimal(value)} ${currency}`;
}

function shownPercent(value: string | number) {
  return `${formatPersianDecimal(value, 2)}٪`;
}

const demandCaseLabels = { downside: "تقاضای پایین", expected: "تقاضای میانی", upside: "تقاضای بالا" };

export default function OptimizationPage() {
  const [requestText, setRequestText] = useState("");
  const [fileName, setFileName] = useState("");
  const [result, setResult] = useState<Comparison | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [inputMode, setInputMode] = useState<"guided" | "json">("guided");
  const requestVersion = useRef(0);
  const operationVersion = useRef(0);

  async function readFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const operation = ++operationVersion.current;
    const submittedVersion = ++requestVersion.current;
    setError("");
    setResult(null);
    setBusy(true);
    try {
      const text = await file.text();
      if (requestVersion.current === submittedVersion) {
        setFileName(file.name);
        setRequestText(text);
      }
    } catch {
      if (requestVersion.current === submittedVersion) {
        setError("خواندن فایل انجام نشد. فایل JSON را دوباره انتخاب کن.");
      }
    } finally {
      if (operationVersion.current === operation) setBusy(false);
    }
  }

  async function compare() {
    const operation = ++operationVersion.current;
    const submittedVersion = requestVersion.current;
    const submittedText = requestText;
    setError("");
    setResult(null);
    let body: unknown;
    try {
      body = JSON.parse(submittedText);
      if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error();
    } catch {
      setError("متن واردشده JSON معتبر نیست. فایل یا متن درخواست را بررسی کن.");
      return;
    }

    setBusy(true);
    try {
      const response = await fetch(`${API_BASE}/v1/optimization/comparisons`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Send the validated source text: parsing and serializing through JS Number would round large values.
        body: submittedText,
      });
      const payload = await response.json();
      if (!response.ok) {
        const detail = payload.detail;
        const validationMessages = formatApiValidationErrors(detail);
        const message = typeof detail === "string"
          ? detail
          : validationMessages.length > 0
            ? validationMessages.join("\n")
            : "ساختار یا مقادیر درخواست با قرارداد تحلیل سازگار نیست.";
        throw new Error(message);
      }
      if (requestVersion.current === submittedVersion) setResult(payload as Comparison);
    } catch (caught) {
      if (requestVersion.current === submittedVersion) {
        setError(caught instanceof Error ? caught.message : "ارتباط با سرویس تحلیل برقرار نشد.");
      }
    } finally {
      if (operationVersion.current === operation) setBusy(false);
    }
  }

  return (
    <main className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}><BrandLogo size={43} /></div>
        <p className={styles.navCaption}>محصول</p>
        <nav aria-label="مسیرهای اصلی">
          <a className={styles.navItem} href="/?section=overview">⌂ <span>نمای کلی</span></a>
          <a className={styles.navItem} href="/?section=readiness">▣ <span>آمادگی داده</span></a>
          <a className={styles.navItem} href="/?section=promotion">▥ <span>ممیزی پروموشن</span></a>
          <a className={styles.navItem} href="/experiments">◉ <span>ارزیابی با گروه کنترل</span></a>
          <a className={`${styles.navItem} ${styles.active}`} href="/optimization" aria-current="page">↗ <span>بررسی سناریوها</span></a>
        </nav>
        <div className={styles.sidebarFooter}>محیط محلی بررسی<br />بدون اجرای خودکار کمپین</div>
      </aside>

      <section className={styles.content}>
        <header className={styles.topbar}><span>PromoGuard / تصمیم‌یار</span><span className={styles.localBadge}><i /> سرویس محلی</span></header>

        <div className={styles.heading}>
          <div><p className={styles.eyebrow}>PROMOTION SCENARIO REVIEW</p><h1>بررسی سناریوهای کمپین</h1><p>برآورد اقتصادی مشروط را با محدودیت‌ها و حداقل هدفی که مدیر تعیین کرده کنار هم ببین.</p></div>
          <span className={styles.version}>نسخهٔ بررسی · نیازمند دادهٔ مستند</span>
        </div>

        <section className={styles.notice} aria-label="محدودیت استفاده">
          <span className={styles.noticeIcon}>!</span>
          <div><strong>این صفحه کمپین را اجرا یا تأیید نمی‌کند</strong><p>نتیجه برآوردی مشروط به اعداد واردشده است. بازهٔ تقاضا «سناریو» است، نه فاصلهٔ اطمینان یا اثر علّی؛ تأیید نهایی و تخصیص بودجه با انسان است.</p></div>
        </section>

        <div className={styles.workspace}>
          <section className={styles.panel}>
            <div className={styles.panelHeading}><div><span className={styles.step}>۰۱</span><div><h2>ورودی مستندشده</h2><p>درخواست JSON ساخته‌شده از داده و مفروضات تأییدشده را بارگذاری یا اینجا جای‌گذاری کن.</p></div></div><a className={styles.templateLink} href="/templates/manager-scenario-comparison.template.json" download>دریافت قالب خالی</a></div>
            <div className={styles.inputMode} aria-label="روش ورود اطلاعات">
              <button type="button" disabled={busy} aria-pressed={inputMode === "guided"} className={inputMode === "guided" ? styles.inputModeActive : styles.inputModeButton} onClick={() => setInputMode("guided")}>فرم مرحله‌ای</button>
              <button type="button" disabled={busy} aria-pressed={inputMode === "json"} className={inputMode === "json" ? styles.inputModeActive : styles.inputModeButton} onClick={() => setInputMode("json")}>ورود JSON</button>
            </div>
            <div hidden={inputMode !== "guided"}><ScenarioRequestBuilder onBuild={(json) => {
              requestVersion.current += 1;
              setRequestText(json);
              setFileName("");
              setResult(null);
              setError("");
              setInputMode("json");
            }} /></div>
            <div hidden={inputMode !== "json"}>
            <label className={styles.filePicker}>
              <input type="file" accept=".json,application/json" disabled={busy} onChange={(event) => void readFile(event)} />
              <span className={styles.uploadIcon}>↑</span><span><strong>انتخاب فایل JSON</strong><small>{fileName || "فایل فقط در همین مرورگر خوانده می‌شود و به API محلی فرستاده می‌شود."}</small></span>
              <span className={styles.fileButton}>انتخاب فایل</span>
            </label>
            <label className={styles.editorLabel} htmlFor="scenario-request">متن درخواست</label>
            <textarea id="scenario-request" className={styles.editor} dir="ltr" spellCheck={false} disabled={busy} value={requestText} onChange={(event) => { requestVersion.current += 1; setRequestText(event.target.value); setFileName(""); setResult(null); setError(""); }} placeholder={'درخواست JSON را اینجا جای‌گذاری کن…\n\nفیلدهای سناریو، محدودیت‌ها، آستانهٔ مدیر و منبع هر عدد لازم است.'} aria-describedby="contract-help" />
            <div className={styles.contractHelp} id="contract-help">
              <strong>قبل از ارسال، این داده‌ها باید آماده باشند</strong>
              <p>برای هر سناریو: قیمت عادی و کمپین، بهای واحد، حمایت تأمین‌کننده، هزینه‌های ثابت و متغیر، موجودی، تقاضای مبنا و بازهٔ تقاضای برآوردی. برای هر ۹ مورد، نوع و مرجع مدرک، تاریخ و نام تأییدکننده ثبت شود. همچنین سقف بودجه، ذخیرهٔ موجودی، سقف تخفیف و حداقل سود هدف لازم است.</p>
            </div>
            <button className={styles.primary} type="button" disabled={busy || !requestText.trim()} onClick={() => void compare()}>{busy ? <><span className={styles.spinner} /> در حال بررسی…</> : "مقایسهٔ سناریوها"}</button>
            <p className={styles.privacyNote}>این صفحه درخواست را به API محلی تنظیم‌شده می‌فرستد؛ اطلاعات محرمانه را فقط در محیط مجاز خود وارد کن. این سرویس هنوز احراز هویت یا سطح دسترسی سازمانی ندارد.</p>
            </div>
          </section>

          <aside className={`${styles.panel} ${styles.guide}`}>
            <span className={styles.guideLabel}>روش خواندن نتیجه</span>
            <h2>چه چیزی را می‌سنجد؟</h2>
            <ol>
              <li><b>محدودیت‌ها</b><span>موجودی، بودجه، سقف تخفیف و حداقل سهم هر واحد بررسی می‌شود.</span></li>
              <li><b>اقتصاد مشروط</b><span>سود مبنا با سود کمپین در بازهٔ تقاضای واردشده مقایسه می‌شود.</span></li>
              <li><b>حداقل هدف مدیر</b><span>بازه با آستانهٔ ثبت‌شده سنجیده می‌شود؛ سیستم بین گزینه‌ها رتبه‌بندی نمی‌کند.</span></li>
            </ol>
            <div className={styles.guideFoot}><span>!</span><p>نام تأییدکننده و مرجع مدرک فعلاً متن ورودی‌اند؛ هویت یا اصالت سند به‌طور مستقل احراز نمی‌شود.</p></div>
          </aside>
        </div>

        {error && <section className={styles.error} role="alert"><strong>بررسی انجام نشد</strong><p>{error}</p><small>اگر فیلد مشخصی نام برده شده، همان را در درخواست اصلاح کن. در خطای ارتباطی، سرویس محلی را بررسی کن.</small></section>}

        {result && <section className={styles.results} aria-live="polite">
          <div className={styles.resultHeader}><div><p className={styles.eyebrow}>COMPARISON RESULT</p><h2>خلاصهٔ بررسی</h2><p>درخواست: <bdi>{result.request_id}</bdi></p></div><span className={styles.manualBadge}>تصمیم نهایی با مدیر</span></div>
          <div className={styles.policyStrip}><span>حداقل سود هدف</span><strong>{shownNumber(result.policy.minimum_incremental_profit, result.policy.currency)}</strong><span>مرجع: {result.policy.reference}</span><span>ثبت‌شده به نام: {result.policy.approved_by}</span><span>تاریخ: {result.policy.as_of_date}</span></div>

          <div className={styles.tableWrap}><table><thead><tr><th>سناریو</th><th>وضعیت</th><th>سود افزودهٔ پایین</th><th>برآورد میانی</th><th>سود افزودهٔ بالا</th></tr></thead><tbody>
            {result.assessments.map((item) => <tr key={item.scenario_id}>
              <th scope="row"><bdi>{item.scenario_id}</bdi></th>
              <td><span className={`${styles.decision} ${styles[item.decision]}`}>{decisionLabels[item.decision]}</span></td>
              <td>{shownNumber(item.incremental_profit_lower, item.currency)}</td><td><strong>{shownNumber(item.incremental_profit_point, item.currency)}</strong></td><td>{shownNumber(item.incremental_profit_upper, item.currency)}</td>
            </tr>)}
          </tbody></table></div>

          <div className={styles.assessmentGrid}>{result.assessments.map((item) => <article className={styles.assessmentCard} key={`${item.scenario_id}-why`}>
            <div><h3><bdi>{item.scenario_id}</bdi></h3><span className={item.feasibility_status === "eligible" ? styles.eligible : styles.blocked}>{item.feasibility_status === "eligible" ? "محدودیت‌های ثبت‌شده را گذرانده" : "دارای مانع"}</span></div>
            <p>{item.explanation}</p>
            {item.blocking_reasons.length > 0 && <ul>{item.blocking_reasons.map((reason) => <li key={reason}>{reasonLabels[reason] ?? reason}</li>)}</ul>}
            <details className={styles.economicDetails}>
              <summary>جزئیات عدد و سه حالت تقاضا</summary>
              <div className={styles.breakdownGrid}>
                <div><span>سود در حالت عادی</span><strong>{shownNumber(item.conditional_economics.baseline_profit, item.currency)}</strong></div>
                <div><span>سود کمپین · بازه</span><strong>{shownNumber(item.conditional_economics.promoted_profit.lower, item.currency)} تا {shownNumber(item.conditional_economics.promoted_profit.upper, item.currency)}</strong></div>
                <div><span>تخفیف واردشده</span><strong>{shownPercent(item.discount_rate)}</strong></div>
                <div><span>سهم هر واحد پس از هزینهٔ متغیر</span><strong>{shownNumber(item.projected_unit_contribution, item.currency)}</strong></div>
                <div><span>هزینهٔ معاملاتی · بر پایهٔ تقاضای بالای برآوردی</span><strong>{shownNumber(item.projected_trade_spend, item.currency)}</strong></div>
                <div><span>موجودی پس از ذخیره</span><strong>{formatPersianDecimal(item.sellable_inventory_units, 0, 0)} واحد</strong></div>
              </div>
              <p className={styles.formulaNote}>مبنای عادی: {item.conditional_economics.baseline_profit_basis}. مبنای کمپین: {item.conditional_economics.promoted_profit_basis}.</p>
              <div className={styles.tableWrap}><table><thead><tr><th>حالت تقاضا</th><th>تقاضای واردشده</th><th>سود کمپین</th><th>تفاوت با حالت عادی</th></tr></thead><tbody>
                {item.economic_sensitivity.cases.map((caseItem) => <tr key={caseItem.case}><th scope="row">{demandCaseLabels[caseItem.case]}</th><td>{formatPersianDecimal(caseItem.projected_demand_units, 0, 2)} واحد</td><td>{shownNumber(caseItem.promoted_profit, caseItem.currency)}</td><td><strong>{shownNumber(caseItem.incremental_profit, caseItem.currency)}</strong></td></tr>)}
              </tbody></table></div>
              <p className={styles.sensitivityLimit}>{item.economic_sensitivity.limitation} این صفحه مرجع‌ها و اعداد را با منبع اصلی تطبیق نمی‌دهد.</p>
            </details>
          </article>)}</div>

          <div className={styles.resultLimit}><strong>مرز تفسیر</strong><p>{result.limitation}</p><p>عبور از آستانه فقط «نامزد بررسی انسانی» می‌سازد؛ دادهٔ تقاضا، مبنا و هزینه‌ها باید پیش از هر تصمیم بازبینی شوند.</p></div>
          <div className={styles.resultFooter}><span>وضعیت: بررسی دستی لازم است</span><span>بودجه: غربال جداگانه برای هر سناریو؛ تخصیص سبد انجام نشده</span><span>گزینهٔ منتخب: ندارد</span></div>
        </section>}
      </section>
    </main>
  );
}
