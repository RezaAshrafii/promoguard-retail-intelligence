# گزارش اجرای واقعی PromoGuard — ۱۶ سپتامبر ۲۰۲۶

## وضعیت گیت

**Share with caveats** — pipeline روی دادهٔ واقعی/نمایندهٔ واقعی با موفقیت اجرا شد، اما این منبع
برای causal lift، سود، موجودی یا بازار ایران کافی نیست. خروجی باید به‌عنوان engineering/observational
benchmark و نمونهٔ محصول خوانده شود.

## منبع و بازتولید

- منبع: dunnhumby Breakfast at the Frat
- صفحهٔ ناشر: <https://www.dunnhumby.com/source-files/>
- workbook: `dunnhumby - Breakfast at the Frat.xlsx`
- workbook SHA-256: `61b1d77dd6d9298fed204cc231f2b853a4c7f79376cfc30231646e1e51d0daba`
- grain: `week_end_date × store_num × upc`
- خروجی processed: `data/processed/breakfast-at-the-frat/`

دستورهای اجرا:

```powershell
python -m pip install -e ".[dev,dashboard]"
promoguard ingest --input data/raw/breakfast-at-the-frat --output data/processed/breakfast-at-the-frat
promoguard validate --input data/processed/breakfast-at-the-frat
promoguard forecast-evaluate --input data/processed/breakfast-at-the-frat --output reports/live-2026-09-16/forecast
promoguard promotion-audit --input data/processed/breakfast-at-the-frat --output reports/live-2026-09-16/promotion-audit
```

در محیط فعلی که package هنوز editable نصب نشده بود، اجرای مستقیم module با
`$env:PYTHONPATH='src'` نیز برای بازتولید استفاده شد. README اکنون نصب editable را قبل از command
های CLI نشان می‌دهد تا خطای `ModuleNotFoundError: promoguard` برای عضو جدید رخ ندهد.

## ۱. ingest و کیفیت داده

| کنترل | نتیجه | تفسیر |
|---|---:|---|
| ردیف‌ها | ۵۲۴٬۹۵۰ | حجم واقعی panel واردشده |
| ستون ضروری گمشده | ۰ | قرارداد ورودی کامل است |
| خطای parse تاریخ | ۰ | تاریخ‌ها قابل‌خواندن‌اند |
| تاریخ خالی | ۰ | کلید زمانی کامل است |
| gap تقویم هفتگی | ۰ | تقویم global شکاف ندارد |
| parse خطای عددی | ۰ | ستون‌های عددی قابل تبدیل‌اند |
| شناسهٔ store/UPC گمشده | ۰ | کلیدهای grain کامل‌اند |
| duplicate در grain | ۰ | join اصلی چندبرابر نشده است |
| پرچم promotion نامعتبر | ۰ | مقدارها در دامنهٔ مجازند |
| conflict بین TPR و feature/display | ۰ | قانون cross-field پاس شد |
| ردیف promotion | ۱۴۹٬۳۸۶ | حدود ۲۸٫۴٪ از panel |

### هشدارهای واقعی

- ۲۳ مقدار `PRICE` گمشده است؛ مقدارگذاری خودکار انجام نشد.
- ۱۸۵ مقدار `BASE_PRICE` گمشده است؛ تخفیف برای آن‌ها نباید قطعی تفسیر شود.
- ۶٬۰۴۷ قیمت مشاهده‌شده از base price بالاتر است؛ این موارد discount مثبت محسوب نمی‌شوند.
- یک ردیف zero-price با units مثبت وجود دارد؛ به‌عنوان مورد review باقی ماند.
- چهار ردیف duplicate در lookup فروشگاه وجود داشت؛ lookup با ثبت warning collapse شد و ردیف‌های
  تراکنش چندبرابر نشدند.

**شدت کلی:** داده برای forecast و observational audit قابل‌استفاده است؛ برای economics کامل و
تفسیر تخفیف در همهٔ ردیف‌ها، محدودیت دارد.

## ۲. ارزیابی forecast

- test rows غیرپروموشن: ۵۸٬۱۳۱
- paired rows که هر دو مدل برای آن‌ها خروجی داشتند: ۴۱٬۵۱۶
- paired coverage: ۷۱٫۴۲٪
- folds: ۶
- حداقل history: ۱۰۴ هفته
- horizon: چهار هفته

| مدل | WAPE | MASE | Bias | پوشش interval |
|---|---:|---:|---:|---:|
| seasonal naive 52 | 0.40046 | 1.21410 | -0.01822 | 0.88108 |
| recursive naive 1 | 0.34828 | 1.10888 | 0.03114 | — |

نتیجه: seasonal-naive در این اجرای واقعی از baseline سادهٔ recursive-naive بهتر نشد. بنابراین
recursive-naive baseline نگه داشته می‌شود و ادعای برتری مدل فصلی حذف می‌شود. این نتیجه ضعف pipeline
نیست؛ یک نتیجهٔ معتبر و مهم برای انتخاب baseline است.

## ۳. promotion audit واقعی

نمونهٔ انتخاب‌شده توسط قانون deterministic:

- store: `23345`
- UPC: `2840004768`
- شروع: `2010-01-13`
- پایان: `2010-02-10`
- طول: ۵ هفته
- history غیرپروموشن: ۵۲ هفته

| شاخص | مقدار |
|---|---:|
| observed units در دوره | ۱۲۸ |
| baseline point | ۱۸۵ |
| اختلاف observed - baseline | -۵۷ |
| بازهٔ اختلاف | [-۱۲۷, ۱۳] |
| post/pre ratio | ۰٫۷۲۵ |

نتیجهٔ policy:

```text
recommendation = needs_more_evidence
```

علت blocking:

```text
FORWARD_BUY_RISK
```

یعنی بعد از پروموشن، فروش به کمتر از آستانهٔ ۰٫۸ نسبت به قبل رسیده است. این یک هشدار screening
است، نه اثبات قطعی خرید جلوتر از موعد. موجودی، stockout، margin و گروه کنترل در منبع وجود ندارند.

## ۴. اصلاح correctness در این اجرای واقعی

پیش از این اجرا، `evidence_refs` در audit به‌صورت ثابت به گزارش قدیمی Phase 2 اشاره می‌کرد. این
برای اجرای جدید از نظر provenance کافی نبود. اکنون:

- تابع audit می‌تواند `evidence_refs` مخصوص run دریافت کند؛
- CLI اگر گزارش forecast هم‌مسیر وجود داشته باشد، همان را در audit reference می‌کند؛
- اجرای فعلی به `reports/live-2026-09-16/forecast/forecast-evaluation.json` اشاره می‌کند؛
- API و تست‌های قبلی همچنان default reference مستند خود را حفظ می‌کنند؛
- برای این مسیر یک regression test اضافه شد.

این تغییر کوچک است، اما در محصول قابل‌اعتماد مهم است: گزارش نباید به سندی اشاره کند که در همان
اجرا تولید نشده یا قابل تشخیص نیست.

## ۵. تصمیم گیت فعلی

### مجاز

- نمایش Demo Mode؛
- ارائهٔ روش و محدودیت‌ها؛
- استفاده به‌عنوان engineering benchmark؛
- شروع discovery با مشتری؛
- درخواست sample دادهٔ ناشناس؛
- پیشنهاد Data Readiness & Promotion Audit با review انسانی.

### غیرمجاز

- ادعای causal lift؛
- ادعای promotion profit؛
- ادعای stockout یا latent demand؛
- ادعای اثر روی بازار ایران؛
- اجرای خودکار کمپین؛
- استفاده از این گزارش به‌عنوان نتیجهٔ مشتری؛
- فعال‌کردن `promotion_allowed`.

## فایل‌های خروجی ماشین‌خوان

- `forecast/forecast-evaluation.json`
- `forecast/forecast-evaluation.csv`
- `forecast/forecast-eligibility.csv`
- `forecast/forecast-segment-metrics.csv`
- `promotion-audit/promotion-audit.json`
- `promotion-audit/promotion-audit-windows.csv`

## گام بعدی فنی

۱. اجرای quality checks روی schema پیشنهادی مشتری؛

۲. ساخت یک `customer-intake` fixture بدون دادهٔ شخصی؛

۳. اضافه‌کردن تست برای missing margin/inventory و downgrade به `limited_observational_report`؛

۴. آماده‌کردن export مدیریتی با claim boundary؛

۵. بعد از دریافت دادهٔ واقعی مجاز از design partner، اجرای همین pipeline بدون commit دادهٔ خام.
