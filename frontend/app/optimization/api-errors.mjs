const fieldLabels = {
  body: "درخواست",
  optimization: "تنظیمات کمپین",
  request_id: "شناسهٔ درخواست",
  currency: "واحد پول",
  total_trade_spend_budget: "سقف هزینهٔ کمپین",
  minimum_unit_contribution: "حداقل سهم هر واحد",
  maximum_discount_rate: "بیشترین نرخ تخفیف",
  inventory_reserve_units: "ذخیرهٔ موجودی",
  scenarios: "سناریوها",
  scenario_id: "شناسهٔ سناریو",
  store_id: "شناسهٔ فروشگاه",
  sku_id: "شناسهٔ کالا",
  start_date: "تاریخ شروع",
  end_date: "تاریخ پایان",
  regular_unit_price: "قیمت عادی هر واحد",
  promotion_unit_price: "قیمت کمپین هر واحد",
  unit_cost: "بهای هر واحد",
  supplier_funding_per_unit: "حمایت تأمین‌کننده برای هر واحد",
  fixed_trade_spend: "هزینهٔ ثابت کمپین",
  variable_trade_spend_per_unit: "هزینهٔ متغیر هر واحد",
  available_inventory_units: "موجودی در دسترس",
  baseline_demand_units: "تقاضای مبنا",
  projected_demand_units: "تقاضای برآوردی",
  lower: "حد پایین",
  point: "برآورد میانی",
  upper: "حد بالا",
  evidence: "مدارک پشتیبان",
  field_name: "فیلد مستندشده",
  kind: "نوع مدرک",
  reference: "مرجع مدرک",
  as_of_date: "تاریخ مدرک",
  approved_by: "ثبت‌شده به نام",
  human_approval_required: "لزوم بررسی انسانی",
  automatic_execution_allowed: "اجازهٔ اجرای خودکار",
  policy: "سیاست حداقل سود",
  minimum_incremental_profit: "حداقل سود افزوده",
  human: "نام تأییدکننده",
};

const errorMessages = {
  missing: "این فیلد وارد نشده است.",
  decimal_parsing: "این مقدار باید عددی باشد.",
  int_parsing: "این مقدار باید عدد صحیح باشد.",
  int_type: "این مقدار باید عدد صحیح باشد.",
  float_parsing: "این مقدار باید عددی باشد.",
  greater_than: "مقدار از حداقل مجاز بیشتر باشد.",
  greater_than_equal: "مقدار کمتر از حداقل مجاز است.",
  less_than_equal: "مقدار از حداکثر مجاز بیشتر است.",
  string_too_short: "متن این فیلد کوتاه‌تر از حد مجاز است.",
  string_too_long: "متن این فیلد بلندتر از حد مجاز است.",
  string_pattern_mismatch: "قالب این مقدار درست نیست؛ واحد پول باید کد سه‌حرفی مانند USD باشد.",
  date_from_datetime_parsing: "تاریخ معتبر نیست؛ قالب YYYY-MM-DD را وارد کن.",
  date_parsing: "تاریخ معتبر نیست؛ قالب YYYY-MM-DD را وارد کن.",
  enum: "یکی از گزینه‌های مجاز انتخاب نشده است.",
  literal_error: "این گزینه باید مطابق مقدار ثابت‌شده در قرارداد باشد.",
  extra_forbidden: "این فیلد در قرارداد درخواست تعریف نشده است؛ نام فیلد را بررسی کن.",
  value_error: "این مقدار با قواعد کسب‌وکار یا شواهد ثبت‌شده سازگار نیست.",
  model_type: "این بخش باید به شکل یک شیء JSON باشد.",
  dict_type: "این بخش باید به شکل یک شیء JSON باشد.",
  list_type: "این بخش باید به شکل یک فهرست باشد.",
};

function persianDigits(value) {
  const digits = "۰۱۲۳۴۵۶۷۸۹";
  return String(value).replace(/\d/g, (digit) => digits[Number(digit)]);
}

function labelPath(location) {
  return location
    .filter((part) => part !== "body")
    .map((part) => {
      if (typeof part === "number") return `سناریوی ${persianDigits(part + 1)}`;
      const key = String(part);
      return fieldLabels[key] ?? `فیلد «${key}»`;
    })
    .join(" ← ") || fieldLabels.body;
}

/** Turn FastAPI/Pydantic error details into short, field-specific Persian guidance. */
export function formatApiValidationErrors(detail, maxVisible = 8) {
  if (!Array.isArray(detail) || detail.length === 0) return [];
  const messages = detail.slice(0, maxVisible).map((issue) => {
    const location = Array.isArray(issue?.loc) ? issue.loc : [];
    const message = errorMessages[String(issue?.type)] ?? "این مقدار با قرارداد ورودی سازگار نیست.";
    return `${labelPath(location)}: ${message}`;
  });
  const remaining = detail.length - messages.length;
  if (remaining > 0) messages.push(`و ${persianDigits(remaining)} مورد دیگر؛ خطاها را از ابتدای فهرست اصلاح کن.`);
  return messages;
}
