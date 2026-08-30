# جزوه فاز ۳: ممیزی صادقانه پروموشن

وضعیت: تکمیل‌شده  
تاریخ: ۳۰ اوت ۲۰۲۶ / ۸ شهریور ۱۴۰۵  
مدل توسعه: `gpt-5.6-sol` با reasoning سطح `xhigh`

## هدف این فاز چه بود؟

در فاز ۲ فهمیدیم baseline ساده‌ی یک‌هفته‌ای روی داده‌ی واقعی از seasonal-naive بهتر است. در این
فاز از همان baseline برای بررسی یک promotion استفاده کردیم:

```text
فروش واقعی هنگام promotion - فروش موردانتظار بدون promotion
```

خروجی این تفریق را «برآورد مشاهده‌ای incremental units» می‌نامیم. آن را causal lift نمی‌نامیم؛
چون فروش، قیمت و promotion در یک دیتاست observational ثبت شده‌اند و تخصیص promotion تصادفی نبوده
است.

## مدل انتخاب‌شده و دلیل آن

این فاز با `gpt-5.6-sol / xhigh` طراحی شد، چون اشتباه اصلی می‌توانست در syntax نباشد؛ خطر اصلی
ادعای آماری بیش از حد، leakage از دوره‌ی بعد از promotion، و تصمیم‌گیری بدون cost یا inventory بود.

## جریان کامل سیستم

```text
weekly_panel.csv
      ↓
اعتبارسنجی grain و ستون‌ها
      ↓
تشخیص promotion episodeهای متوالی
      ↓
انتخاب event یا دریافت store/UPC/start-date
      ↓
history فقط قبل از event و فقط non-promotion
      ↓
recursive-naive baseline + residual interval
      ↓
pre / during / post diagnostics
      ↓
warningها + margin scenario اختیاری
      ↓
typed JSON + approve/reject/experiment
```

## promotion episode چیست؟

اگر برای یک store و UPC، چند هفته‌ی پشت سر هم `promotion_flag=1` باشد، همه‌ی آن هفته‌ها یک episode
هستند. اگر بین دو هفته بیشتر از هفت روز فاصله باشد، episode جدید شروع می‌شود.

این تعریف مهم است، چون یک promotion پنج‌هفته‌ای نباید پنج رویداد مستقل شمرده شود.

## baseline چگونه ساخته می‌شود؟

برای هفته‌ی اول promotion، آخرین فروش non-promotion قبل از event گرفته می‌شود. همین مقدار برای
هفته‌های بعد episode به‌صورت recursive ادامه پیدا می‌کند.

مثال ساده:

```text
آخرین فروش عادی: 20 واحد
طول promotion: 3 هفته
baseline کل: 20 × 3 = 60 واحد
فروش مشاهده‌شده: 90 واحد
incremental estimate: 90 - 60 = 30 واحد
```

هیچ مقدار during یا post برای ساخت baseline استفاده نمی‌شود. بنابراین تغییر داده‌های آینده،
baseline و incremental estimate دوره‌ی promotion را تغییر نمی‌دهد.

## بازه‌ی عدم‌قطعیت

در history قبل از event، خطاهای یک‌هفته‌ای محاسبه می‌شوند:

```text
|units این هفته - units هفته قبل|
```

فقط جفت‌هفته‌های واقعاً متوالی و non-promotion استفاده می‌شوند. صدک ۹۰ این residualها عرض بازه را
می‌سازد. این بازه برای audit و screening است و confidence interval اثر causal نیست.

## پنجره‌های pre، during و post

- `pre`: چهار هفته قبل از شروع promotion؛
- `during`: تمام هفته‌های episode؛
- `post`: چهار هفته بعد از پایان episode.

این پنجره‌ها کمک می‌کنند بفهمیم رشد ظاهری فروش شاید از خرید زودتر مشتریان آمده باشد. اگر میانگین
post کمتر از ۸۰ درصد میانگین pre باشد، `FORWARD_BUY_RISK` فعال و تصمیم block می‌شود.

## warningهای پیاده‌سازی‌شده

| کد | معنی ساده | اثر بر تصمیم |
|---|---|---|
| `OBSERVATIONAL_ONLY` | این برآورد causal نیست | هشدار دائمی |
| `MISSING_COST` | unit margin نداریم | blocking |
| `SHORT_HISTORY` | history کافی نیست | blocking |
| `STOCKOUT_UNOBSERVABLE` | inventory در منبع نیست | هشدار |
| `STOCKOUT_RISK` | موجودی در promotion صفر شده | blocking |
| `INCOMPLETE_PRE_WINDOW` | پنجره‌ی قبل کامل نیست | هشدار |
| `INCOMPLETE_POST_WINDOW` | پنجره‌ی بعد کامل نیست | blocking |
| `POST_WINDOW_CONTAMINATED` | promotion دیگری در post دیده شده | هشدار |
| `SEVERE_SHIFT` | pre بیش از ۵۰٪ با history قبلی فرق دارد | blocking |
| `FORWARD_BUY_RISK` | post بیش از ۲۰٪ زیر pre است | blocking |

## منطق تصمیم

تصمیم‌ها برای screening هستند، نه اجرای خودکار کمپین:

- اگر warning blocking وجود داشته باشد: `experiment`؛
- اگر کل بازه‌ی incremental زیر صفر باشد: `reject`؛
- اگر کل بازه بالای صفر باشد، margin واقعی داده شده باشد و blocker نداشته باشیم: `approve`؛
- در بقیه‌ی حالت‌ها: `experiment`.

`approve` فقط یعنی شواهد برای یک pilot کنترل‌شده مناسب است؛ به معنی rollout یا اثبات causal نیست.

## profit چگونه برخورد شد؟

دیتای عمومی cost یا unit margin ندارد. بنابراین در اجرای واقعی:

```json
"margin_scenario": null
```

و warning `MISSING_COST` ثبت شد. اگر در آینده design partner مقدار واقعی unit margin را تأیید کند،
می‌توان آن را با `--unit-margin` وارد کرد. آن خروجی همچنان با برچسب `scenario_only` ذخیره می‌شود.

ما برای زیباتر شدن خروجی، cost مصنوعی اختراع نکردیم.

## انتخاب event واقعی

برای جلوگیری از cherry-picking، event با بهترین نتیجه انتخاب نشد. قانون از قبل مشخص بود:

1. episodeها بر اساس تاریخ مرتب شوند؛
2. حداقل ۵۲ ردیف non-promotion history داشته باشند؛
3. چهار هفته post کامل داشته باشند؛
4. اولین event واجد شرایط انتخاب شود.

event واقعی انتخاب‌شده:

```text
Store: 23345
UPC: 2840004768
Start: 2010-01-13
End: 2010-02-10
Duration: 5 weeks
History: 52 non-promotion rows
```

## نتیجه‌ی واقعی

```text
Observed units: 128
Baseline units: 185
Baseline interval: [115, 255]
Incremental estimate: -57
Incremental interval: [-127, 13]
Pre mean: 30
During mean: 25.6
Post mean: 21.75
Post / Pre ratio: 0.725
Decision: experiment
```

بازه‌ی incremental صفر را قطع می‌کند؛ یعنی نمی‌توانیم با این audit جهت اثر را قطعی بدانیم. علاوه
بر آن، cost وجود ندارد و نسبت post/pre برابر `0.725` است؛ بنابراین forward-buy risk فعال شده است.

## فایل‌های تغییرکرده

### کد

- `src/promoguard/insights/promotion_audit.py`
  - قراردادهای Pydantic؛
  - event detection؛
  - انتخاب event نماینده؛
  - baseline و interval؛
  - pre/during/post diagnostics؛
  - warningها، margin scenario و decision logic.
- `src/promoguard/insights/__init__.py`
  - public interfaceهای audit را export می‌کند.
- `src/promoguard/cli.py`
  - فرمان `promotion-audit` و خروجی JSON/CSV را اضافه می‌کند.

### تست

- `tests/unit/test_promotion_audit.py`
  - episode متوالی؛
  - positive و negative interval؛
  - margin scenario؛
  - missing cost؛
  - forward-buy؛
  - short history؛
  - severe shift؛
  - missing inventory؛
  - عدم استفاده از آینده؛
  - جلوگیری از wording علّی پشتیبانی‌نشده.

### گزارش و مستندات

- `reports/phase-03/promotion-audit.json`؛
- `reports/phase-03/promotion-audit-windows.csv`؛
- `docs/evaluation-protocol.md`؛
- `docs/limitations.md`؛
- `docs/model-card.md`؛
- `README.md`؛
- `ROADMAP.md`.

## دستور اجرا

انتخاب خودکار و بازتولید گزارش ثبت‌شده:

```powershell
.\.venv\Scripts\python.exe -m promoguard.cli promotion-audit `
  --input data\processed\breakfast-at-the-frat `
  --output reports\phase-03
```

انتخاب دستی یک event:

```powershell
.\.venv\Scripts\python.exe -m promoguard.cli promotion-audit `
  --input data\processed\breakfast-at-the-frat `
  --output reports\my-audit `
  --store-id 23345 `
  --upc 2840004768 `
  --start-date 2010-01-13
```

فقط با margin واقعی و تأییدشده:

```powershell
... --unit-margin 1.25
```

## نتیجه‌ی تست‌ها

```text
Ruff: passed
Pytest: 33 passed
Compileall: passed
Health CLI: passed
Real promotion audit: passed
```

warning فعلی pytest مربوط به deprecation در dependency خارجی Starlette/httpx است و failure تست
پروژه نیست.

## محدودیت‌ها

- assignment promotion تصادفی نیست؛
- cost و inventory نداریم؛
- interval، causal confidence interval نیست؛
- baseline ساده است و نتیجه‌ی همه‌ی SKUها را تضمین نمی‌کند؛
- cannibalization بین محصولات هنوز بررسی نشده؛
- تغییر distribution و assortment ممکن است پنهان باشد؛
- این نتیجه شواهد impact برای بازار ایران نیست.

## سؤال‌های مصاحبه

### چرا از post برای baseline استفاده نکردی؟

چون هنگام تصمیم‌گیری post هنوز وجود ندارد و استفاده از آن leakage است. post فقط diagnostic
forward-buy است.

### چرا نتیجه را causal lift نمی‌نامی؟

چون promotion به‌صورت تصادفی تخصیص نیافته و confounderهایی مثل تقاضا، زمان، distribution و
قیمت می‌توانند هم promotion و هم فروش را تغییر دهند.

### چرا event واقعی نتیجه‌ی منفی دارد؟

چون event بر اساس outcome انتخاب نشده است. اولین episode واجد شرایط انتخاب شد. بازه صفر را قطع
می‌کند، پس نتیجه‌ی درست `experiment` است، نه داستان‌سازی درباره‌ی موفقیت یا شکست قطعی.

### فرق interval این فاز با confidence interval چیست؟

این interval از residualهای تاریخی baseline ساخته شده و uncertainty پیش‌بینی را نشان می‌دهد؛
عدم‌قطعیت causal identification را پوشش نمی‌دهد.

### اگر cost نداشته باشیم چه می‌کنی؟

profit را unavailable اعلام می‌کنم. فقط با unit margin واقعی، یک scenario برچسب‌خورده محاسبه
می‌شود.

## فاز بعدی

فاز ۴، API و dashboard را روی همین typed JSON می‌سازد. محاسبات داخل UI قرار نمی‌گیرند؛ UI فقط
نتیجه، بازه، warningها، decision و شواهد را نمایش می‌دهد.
