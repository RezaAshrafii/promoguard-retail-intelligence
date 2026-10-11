"use client";

import { useState } from "react";
import { buildScenarioRequest } from "./request-builder.mjs";
import styles from "./optimization.module.css";

type Props = { onBuild: (json: string) => void };
type FormValues = Record<string, string>;

const evidenceFields = [
  ["regular_unit_price", "قیمت عادی هر واحد"],
  ["promotion_unit_price", "قیمت کمپین هر واحد"],
  ["unit_cost", "بهای تمام‌شدهٔ هر واحد"],
  ["supplier_funding_per_unit", "حمایت تأمین‌کننده برای هر واحد"],
  ["fixed_trade_spend", "هزینهٔ ثابت اجرای کمپین"],
  ["variable_trade_spend_per_unit", "هزینهٔ متغیر برای هر واحد"],
  ["available_inventory_units", "موجودی در دسترس"],
  ["baseline_demand_units", "تقاضای مبنا"],
  ["projected_demand_units", "بازهٔ تقاضای پیش‌بینی‌شده"],
] as const;

const errorLabels: Record<string, string> = {
  request_id: "شناسهٔ درخواست", scenario_id: "شناسهٔ سناریو", store_id: "شناسهٔ فروشگاه", sku_id: "شناسهٔ کالا",
  currency: "واحد پول درخواست", scenario_currency: "واحد پول سناریو", start_date: "تاریخ شروع", end_date: "تاریخ پایان",
  total_trade_spend_budget: "سقف هزینهٔ کمپین", minimum_unit_contribution: "حداقل سهم هر واحد", maximum_discount_rate: "سقف درصد تخفیف",
  inventory_reserve_units: "ذخیرهٔ موجودی", regular_unit_price: "قیمت عادی", promotion_unit_price: "قیمت کمپین", unit_cost: "بهای تمام‌شده",
  supplier_funding_per_unit: "حمایت تأمین‌کننده", fixed_trade_spend: "هزینهٔ ثابت", variable_trade_spend_per_unit: "هزینهٔ متغیر",
  available_inventory_units: "موجودی در دسترس", baseline_demand_units: "تقاضای مبنا", demand_lower: "حد پایین تقاضا",
  demand_point: "تقاضای میانی", demand_upper: "حد بالای تقاضا", policy_minimum_incremental_profit: "حداقل سود افزوده",
  policy_currency: "واحد پول آستانهٔ مدیر", policy_reference: "مرجع تأیید مدیر", policy_approved_by: "تأییدکنندهٔ آستانه",
  policy_as_of_date: "تاریخ آستانهٔ مدیر",
};

const stepTitles = ["مشخصات و محدودیت‌ها", "اعداد سناریو", "مدرک و آستانهٔ مدیر"];

function initialForm(): FormValues {
  const form: FormValues = {};
  const keys = [
    "request_id", "currency", "total_trade_spend_budget", "minimum_unit_contribution", "maximum_discount_rate", "inventory_reserve_units",
    "scenario_id", "store_id", "sku_id", "start_date", "end_date", "scenario_currency", "regular_unit_price", "promotion_unit_price",
    "unit_cost", "supplier_funding_per_unit", "fixed_trade_spend", "variable_trade_spend_per_unit", "available_inventory_units",
    "baseline_demand_units", "demand_lower", "demand_point", "demand_upper", "policy_minimum_incremental_profit", "policy_currency",
    "policy_reference", "policy_approved_by", "policy_as_of_date",
  ];
  keys.forEach((key) => { form[key] = ""; });
  evidenceFields.forEach((_, index) => {
    ["kind", "reference", "as_of_date", "approved_by"].forEach((part) => { form[`evidence_${index}_${part}`] = ""; });
  });
  return form;
}

function TextField({ form, name, label, hint, numeric = false, date = false, onChange }: {
  form: FormValues; name: string; label: string; hint?: string; numeric?: boolean; date?: boolean; onChange: (name: string, value: string) => void;
}) {
  return <label className={styles.builderField}>
    <span>{label}</span>
    <input
      value={form[name] ?? ""}
      onChange={(event) => onChange(name, event.target.value)}
      inputMode={numeric ? "decimal" : undefined}
      type={date ? "date" : "text"}
      dir={numeric || date ? "ltr" : undefined}
      placeholder={numeric ? "عدد را بدون جداکنندهٔ هزارگان وارد کنید" : hint}
      autoComplete="off"
    />
    {hint && <small>{hint}</small>}
  </label>;
}

export function ScenarioRequestBuilder({ onBuild }: Props) {
  const [form, setForm] = useState<FormValues>(initialForm);
  const [step, setStep] = useState(0);
  const [errors, setErrors] = useState<string[]>([]);

  function update(name: string, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
    setErrors([]);
  }

  function finish() {
    const result = buildScenarioRequest(form);
    if (!result.ok) {
      setErrors(result.errors.map((item) => {
        const [key, kind] = item.split(":");
        const evidenceMatch = key.match(/^evidence_(\d+)_(kind|reference|as_of_date|approved_by)$/);
        if (evidenceMatch) {
          const metric = evidenceFields[Number(evidenceMatch[1])]?.[1] ?? "شاخص";
          const partLabels: Record<string, string> = { kind: "نوع مدرک", reference: "مرجع مدرک", as_of_date: "تاریخ مدرک", approved_by: "تأییدکننده" };
          const part = partLabels[evidenceMatch[2]];
          return `${metric} · ${part}: ${kind === "date" ? "تاریخ نامعتبر است." : kind === "choice" ? "یک نوع مدرک معتبر انتخاب کن." : "این مورد را تکمیل کن."}`;
        }
        const label = errorLabels[key] ?? key;
        if (kind === "date") return `${label}: تاریخ معتبر با قالب میلادی YYYY-MM-DD وارد کن.`;
        if (kind === "currency") return `${label}: کد سه‌حرفی واحد پول مثل IRR را وارد کن.`;
        if (kind === "integer") return `${label}: عدد صحیحِ غیرمنفی و در محدودهٔ ایمن وارد کن.`;
        if (kind === "number") return `${label}: عدد را با نقطهٔ اعشار و بدون جداکنندهٔ هزارگان وارد کن.`;
        return `${label}: این مورد را تکمیل کن.`;
      }));
      const firstKey = result.errors[0]?.split(":")[0] ?? "";
      setStep(firstKey.startsWith("evidence_") || firstKey.startsWith("policy_") ? 2 :
        ["regular_unit_price", "promotion_unit_price", "unit_cost", "supplier_funding_per_unit", "fixed_trade_spend", "variable_trade_spend_per_unit", "available_inventory_units", "baseline_demand_units", "demand_lower", "demand_point", "demand_upper"].includes(firstKey) ? 1 : 0);
      return;
    }
    setErrors([]);
    onBuild(result.json);
  }

  return <section className={styles.builder} aria-label="ساخت درخواست بررسی سناریو">
    <div className={styles.builderHeader}>
      <div><span className={styles.guideLabel}>فرم ورود مرحله‌ای</span><h3>اطلاعات را از فایل یا تأیید مدیر بردار</h3><p>این فرم هیچ مقدار نمونه‌ای ندارد. اگر یک عدد یا مدرکش را نداری، قبل از تحلیل آن را از مسئول داده یا مدیر بگیر.</p></div>
      <span className={styles.builderProgress}>مرحلهٔ {step + 1} از 3</span>
    </div>
    <div className={styles.progressTrack} aria-label={`مرحلهٔ ${step + 1} از 3`}><span style={{ width: `${((step + 1) / 3) * 100}%` }} /></div>
    <div className={styles.stepTabs} aria-label="مراحل فرم">
      {stepTitles.map((title, index) => <button type="button" aria-current={step === index ? "step" : undefined} className={step === index ? styles.stepTabActive : styles.stepTab} key={title} onClick={() => setStep(index)}>{`${index + 1}. ${title}`}</button>)}
    </div>

    {step === 0 && <div className={styles.builderGrid}>
      <TextField form={form} name="request_id" label="شناسهٔ درخواست" hint="یک شناسهٔ داخلی برای این بررسی؛ نام شرکت یا اطلاعات شخصی لازم نیست." onChange={update} />
      <TextField form={form} name="currency" label="واحد پول کل درخواست" hint="کد سه‌حرفی مانند IRR؛ با واحد پول همهٔ سناریوها یکی باشد." onChange={update} />
      <TextField form={form} name="scenario_id" label="شناسهٔ سناریو" hint="مثلاً کد داخلی کمپین، نه توضیح تبلیغاتی." onChange={update} />
      <TextField form={form} name="store_id" label="شناسهٔ فروشگاه یا کانال" onChange={update} />
      <TextField form={form} name="sku_id" label="شناسهٔ کالا" onChange={update} />
      <TextField form={form} name="scenario_currency" label="واحد پول سناریو" hint="باید با واحد پول کل درخواست برابر باشد." onChange={update} />
      <TextField form={form} name="start_date" label="تاریخ شروع کمپین" date onChange={update} />
      <TextField form={form} name="end_date" label="تاریخ پایان کمپین" date onChange={update} />
      <TextField form={form} name="total_trade_spend_budget" label="سقف هزینهٔ مجاز کمپین" numeric hint="از بودجهٔ مصوب؛ بدون واحد پول در کادر." onChange={update} />
      <TextField form={form} name="minimum_unit_contribution" label="حداقل سهم قابل قبول هر واحد" numeric hint="آستانهٔ داخلی شرکت، نه عدد پیشنهادی PromoGuard." onChange={update} />
      <TextField form={form} name="maximum_discount_rate" label="حداکثر درصد تخفیف مجاز" numeric hint="به شکل نسبت وارد کن؛ برای ۲۰٪ عدد 0.20." onChange={update} />
      <TextField form={form} name="inventory_reserve_units" label="ذخیرهٔ حداقلی موجودی" numeric hint="تعداد واحدی که نباید برای کمپین مصرف شود." onChange={update} />
    </div>}

    {step === 1 && <div className={styles.builderGrid}>
      <TextField form={form} name="regular_unit_price" label="قیمت عادی هر واحد" numeric onChange={update} />
      <TextField form={form} name="promotion_unit_price" label="قیمت کمپین هر واحد" numeric onChange={update} />
      <TextField form={form} name="unit_cost" label="بهای تمام‌شدهٔ هر واحد" numeric onChange={update} />
      <TextField form={form} name="supplier_funding_per_unit" label="حمایت تأمین‌کننده برای هر واحد" numeric hint="اگر حمایت ندارید، بعد از تأیید مسئول می‌توان صفر ثبت کرد." onChange={update} />
      <TextField form={form} name="fixed_trade_spend" label="هزینهٔ ثابت کمپین" numeric onChange={update} />
      <TextField form={form} name="variable_trade_spend_per_unit" label="هزینهٔ متغیر برای هر واحد" numeric onChange={update} />
      <TextField form={form} name="available_inventory_units" label="موجودی در دسترس برای کمپین" numeric hint="عدد صحیح؛ موجودی کل منهای رزروهای دیگر." onChange={update} />
      <TextField form={form} name="baseline_demand_units" label="تقاضای مبنا در همین بازه" numeric hint="تقاضای مورد انتظار بدون این پروموشن؛ مبنایش را مستند کن." onChange={update} />
      <div className={styles.demandGroup}><strong>تقاضای پیش‌بینی‌شده در صورت اجرای کمپین</strong><p>سه سناریوی پایین، میانی و بالا هستند؛ این‌ها فاصلهٔ اطمینان آماری نیستند.</p><div>
        <TextField form={form} name="demand_lower" label="پایین" numeric onChange={update} />
        <TextField form={form} name="demand_point" label="میانی" numeric onChange={update} />
        <TextField form={form} name="demand_upper" label="بالا" numeric onChange={update} />
      </div></div>
    </div>}

    {step === 2 && <>
      <div className={styles.evidenceIntro}><strong>مدرک باید همان عدد را پشتیبانی کند</strong><p>برای هر ردیف، منبع، تاریخ داده و تأییدکننده را جداگانه ثبت کن. نوشتن اسم یا لینک به‌تنهایی اصالت مدرک را ثابت نمی‌کند.</p></div>
      <div className={styles.evidenceList}>{evidenceFields.map(([field, label], index) => <article className={styles.evidenceRow} key={field}>
        <h4>{label}</h4>
        <label className={styles.builderField}><span>نوع مدرک</span><select value={form[`evidence_${index}_kind`]} onChange={(event) => update(`evidence_${index}_kind`, event.target.value)}><option value="">انتخاب کن</option><option value="partner_export">خروجی دادهٔ شریک</option><option value="approved_contract">قرارداد یا فایل مصوب</option><option value="model_output">خروجی مدل</option><option value="approved_assumption">فرضیهٔ تأییدشده</option></select></label>
        <TextField form={form} name={`evidence_${index}_reference`} label="مرجع فایل/گزارش/مدل" hint="شناسه یا مسیر مجاز؛ دادهٔ محرمانه را اینجا کپی نکن." onChange={update} />
        <TextField form={form} name={`evidence_${index}_as_of_date`} label="تاریخ داده یا مدرک" date onChange={update} />
        <TextField form={form} name={`evidence_${index}_approved_by`} label="تأییدکنندهٔ منبع" onChange={update} />
      </article>)}</div>
      <div className={styles.policyBuilder}><h4>حداقل هدف تعیین‌شده توسط مدیر</h4><p>این حد را مدیر کسب‌وکار باید تعیین و تأیید کند؛ سیستم خودش هدف سود نمی‌سازد.</p><div className={styles.builderGrid}>
        <TextField form={form} name="policy_minimum_incremental_profit" label="حداقل سود افزودهٔ مورد انتظار" numeric onChange={update} />
        <TextField form={form} name="policy_currency" label="واحد پول آستانه" hint="باید با واحد پول سناریو یکی باشد." onChange={update} />
        <TextField form={form} name="policy_reference" label="مرجع تصمیم مدیر" hint="مثلاً شمارهٔ صورت‌جلسه یا سیاست مصوب." onChange={update} />
        <TextField form={form} name="policy_approved_by" label="نام/سمت تأییدکننده" onChange={update} />
        <TextField form={form} name="policy_as_of_date" label="تاریخ تأیید آستانه" date onChange={update} />
      </div></div>
    </>}

    {errors.length > 0 && <div className={styles.builderErrors} role="alert"><strong>درخواست هنوز کامل نیست</strong><ul>{errors.slice(0, 12).map((error) => <li key={error}>{error}</li>)}</ul>{errors.length > 12 && <small>{errors.length - 12} مورد دیگر هم باید تکمیل شود.</small>}</div>}
    <div className={styles.builderActions}>
      <button type="button" className={styles.secondaryAction} disabled={step === 0} onClick={() => setStep((current) => Math.max(0, current - 1))}>مرحلهٔ قبل</button>
      {step < 2
        ? <button type="button" className={styles.primaryAction} onClick={() => { setErrors([]); setStep((current) => Math.min(2, current + 1)); }}>مرحلهٔ بعد</button>
        : <button type="button" className={styles.primaryAction} onClick={finish}>ساخت درخواست و نمایش JSON</button>}
    </div>
  </section>;
}
