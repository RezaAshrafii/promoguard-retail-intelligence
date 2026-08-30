# اصلاح پایه ۱: جداکردن تفاوت فروش از ادعای سود

وضعیت: تکمیل‌شده  
تاریخ: ۳۰ اوت ۲۰۲۶ / ۸ شهریور ۱۴۰۵  
تصمیم انسانی: تأییدشده در ADR-0002 و GitHub Issue #1

## چرا این اصلاح لازم بود؟

نسخه قبلی ابتدا این مقدار را حساب می‌کرد:

```text
فروش مشاهده‌شده در پروموشن - فروش مبنای پیش‌بینی‌شده
```

این بخش یک مقایسه مشاهده‌ای است. سپس اگر کاربر `unit_margin` می‌داد، اختلاف واحدها در آن ضرب
می‌شد. از نظر ضرب ریاضی اشکالی نداشت، اما اسم `MarginScenario` و تصمیم‌های
`approve/reject/experiment` می‌توانستند این برداشت اشتباه را ایجاد کنند که سیستم سود پروموشن یا
اثر علّی آن را فهمیده است.

## مثال خیلی ساده

فرض کن بدون تخفیف ۱۰۰ واحد کالا با حاشیه ۲۰ فروخته می‌شد:

```text
100 × 20 = 2000
```

در پروموشن ۱۴۰ واحد با حاشیه ۱۰ فروخته شده است:

```text
140 × 10 = 1400
```

فروش ۴۰ واحد بیشتر است، اما حاشیه کل ۶۰۰ کمتر شده است. محاسبه‌ی `40 × 10 = 400` فقط یک
sensitivity خطی برای واحدهای اضافه است؛ سود پروموشن نیست، چون کاهش حاشیه ۱۰۰ واحد مبنا، trade
spend، funding و هزینه‌های دیگر را مدل نمی‌کند.

## قرارداد جدید خروجی

فیلد زیر:

```text
incremental_units
```

به نام دقیق‌تر زیر تغییر کرد:

```text
estimated_units_difference_vs_baseline
```

معنی آن فقط این است:

> فروش ثبت‌شده در پنجره پروموشن نسبت به forecast baseline چقدر فرق داشته است؟

این فیلد نمی‌گوید پروموشن علت تفاوت بوده است.

## قرارداد جدید تحلیل حساسیت

اگر کاربر بخواهد یک فرض مالی بررسی کند، باید سه چیز را با هم بدهد:

```text
amount_per_incremental_unit
currency
source
```

مثال:

```json
{
  "amount_per_incremental_unit": 12500,
  "currency": "IRR",
  "source": "approved finance input for sensitivity review"
}
```

خروجی در `contribution_sensitivity` قرار می‌گیرد و همیشه این برچسب را دارد:

```text
sensitivity_only
```

کد ارز به حروف بزرگ نرمال می‌شود، منبع خالی رد می‌شود و مقدار می‌تواند مثبت یا منفی باشد. منفی
بودن مقدار برای آزمودن سناریوی هزینه‌زای هر واحد اضافه مفید است.

## چرا sensitivity روی recommendation اثر ندارد؟

چون assumption ورودی کاربر است، نه واقعیت اندازه‌گیری‌شده دیتاست. بنابراین تابع recommendation
فقط units difference، uncertainty و warningهای داده‌ای را می‌بیند؛ contribution assumption اصلاً
به آن داده نمی‌شود.

تست مستقلی نیز ساخته شد که یک assumption منفی بزرگ وارد می‌کند و ثابت می‌کند recommendation قبل
و بعد از آن یکسان باقی می‌ماند.

## توصیه‌های جدید

### `candidate_for_controlled_test`

کل بازه‌ی تفاوت بالای صفر است و blocker وجود ندارد. معنی ساده: فرضیه ارزش آزمایش کنترل‌شده دارد؛
نه اینکه rollout یا سود تأیید شده است.

### `deprioritize_and_investigate`

کل بازه زیر صفر است. معنی ساده: فعلاً بودجه بیشتری نده و ابتدا علت اختلاف، confounder و کیفیت داده
را بررسی کن. این هم شکست علّی قطعی نیست.

### `needs_more_evidence`

بازه صفر را قطع می‌کند یا warning مسدودکننده وجود دارد. معنی ساده: داده فعلی جهت را روشن نمی‌کند.

## warning مالی جدید

`MISSING_COST` حذف شد، چون نبود فرض مالی نباید یک توصیه آزمایشی را block کند. به‌جای آن warning
اطلاعاتی زیر همیشه صادقانه وضعیت را می‌گوید:

```text
ECONOMIC_IMPACT_UNAVAILABLE
```

حتی با contribution assumption نیز اقتصاد کامل پروموشن در دسترس نیست.

## تغییرات لایه‌به‌لایه

- Domain: مدل‌های `AuditRecommendation`، `ContributionAssumption` و
  `ContributionSensitivity` جای قرارداد قبلی را گرفتند.
- Recommendation: هیچ ورودی مالی دریافت نمی‌کند.
- API: بدنه `contribution_assumption` تایپ‌شده می‌پذیرد.
- CLI: سه آرگومان contribution باید همگی با هم ارسال شوند.
- Dashboard: wording مالی حذف و sensitivity همراه ارز و منبع نمایش داده می‌شود.
- Demo: نام فیلدهای JSON با قرارداد جدید هماهنگ شد.
- Tests: توصیه مثبت، منفی، blocker، نبود assumption، assumption منفی، API و claim language کنترل شدند.
- Evidence: گزارش واقعی Phase 3 و smoke Phase 4 دوباره تولید می‌شوند.

## دستور CLI برای sensitivity

```powershell
promoguard promotion-audit `
  --input data/processed/breakfast-at-the-frat `
  --output reports/my-audit `
  --assumed-contribution-per-incremental-unit 12500 `
  --contribution-currency IRR `
  --contribution-assumption-source "approved finance sensitivity input"
```

اگر یکی از سه آرگومان ارسال شود ولی دو تای دیگر نباشند، CLI اجرا را متوقف می‌کند؛ چون عدد بدون ارز
یا منبع قابل ممیزی نیست.

## چیزی که هنوز نداریم

برای محاسبه واقعی promotion economics باید حداقل این داده‌ها موجود باشند:

- قیمت عادی و قیمت پروموشن؛
- unit cost؛
- trade spend یا funding؛
- هزینه‌های متغیر مرتبط؛
- currency و زمان اعتبار ورودی‌ها؛
- counterfactual اقتصادی معتبر.

تا آن زمان پروژه فقط experiment prioritization انجام می‌دهد و هیچ financial approval صادر نمی‌کند.

## نتیجه‌ی verification این بخش

```text
Pytest: 49 passed
Ruff: passed
Compileall: passed
OpenAPI semantic contract: passed
Real Phase-3 audit regeneration: passed
Real Phase-4 API smoke: passed
Dashboard browser smoke: passed
```

تنها warning تست‌ها مربوط به deprecation فعلی `Starlette TestClient/httpx` است و شکست منطق پروژه
نیست؛ رفع آن در cleanup وابستگی‌ها پیگیری می‌شود.

## پاسخ کوتاه برای مصاحبه

اگر پرسیدند «چرا اسم incremental profit را حذف کردی؟» بگو:

> چون اختلاف فروش با forecast baseline نه causal lift است و نه سود. یک promotion می‌تواند units را
> افزایش دهد ولی به‌دلیل تخفیف و trade spend سود را کاهش دهد. من evidence، sensitivity و decision
> policy را در سه قرارداد جدا نگه داشتم تا assumption مالی نتواند خودش را به‌جای واقعیت جا بزند.
