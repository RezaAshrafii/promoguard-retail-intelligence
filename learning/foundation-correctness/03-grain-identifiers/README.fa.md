# اصلاح پایه ۳: هیچ سری بدون شناسه معتبر ساخته نمی‌شود

وضعیت: تکمیل‌شده  
تاریخ: ۳۰ اوت ۲۰۲۶ / ۸ شهریور ۱۴۰۵  
تصمیم انسانی: تأییدشده در ADR-0002 و GitHub Issue #1

## grain یعنی چه؟

هر ردیف پنل PromoGuard باید دقیقاً یک ترکیب را معرفی کند:

```text
یک هفته × یک فروشگاه × یک کالا
```

پس کلید هر ردیف این است:

```text
week_end_date × store_id × upc
```

اگر `store_id` یا `upc` خالی باشد، سیستم نمی‌داند فروش متعلق به کدام سری است.

## مشکل نسخه قبلی

نسخه قبلی وجود ستون را بررسی می‌کرد؛ مثلاً مطمئن می‌شد ستونی به نام `store_id` وجود دارد. اما
ممکن بود مقدار داخل آن ستون در یک ردیف `null`، رشته خالی یا فقط چند فاصله باشد.

وجود ظرف کافی نیست؛ محتوای ظرف نیز باید معتبر باشد.

این مشکل می‌توانست باعث شود:

- groupby بعضی ردیف‌ها را حذف یا جدا کند؛
- تعداد سری‌ها اشتباه شود؛
- event هویت قابل اعتماد نداشته باشد؛
- duplicate پنهان بماند؛
- validation بگوید داده معتبر است ولی مرحله بعد شکست بخورد.

## سیاست مشترک جدید

یک ماژول مرکزی در `promoguard.data.grain` ساخته شد. تعریف invalid در همه‌جا یکسان است:

```text
null
""
"   "
```

شناسه معتبر به nullable string تبدیل و دو طرفش trim می‌شود. هیچ مقدار missing ساخته یا با مقدار
فرضی پر نمی‌شود.

## چرا duplicate بعد از normalization بررسی می‌شود؟

این دو مقدار برای انسان یک فروشگاه هستند:

```text
"1"
" 1 "
```

اگر قبل از trim duplicate را بررسی کنیم، ممکن است دو سری مصنوعی ساخته شوند. اکنون ابتدا normalize
و سپس grain duplicate بررسی می‌شود.

## کدام بخش‌ها از این سیاست استفاده می‌کنند؟

### Source ingestion

در داده خام dunnhumby، `STORE_NUM` و `UPC` هم از نظر missing بودن و هم numeric بودن کنترل می‌شوند.
بنابراین quality report دیگر نمی‌تواند داده را valid اعلام کند و بعد هنگام تبدیل identifier شکست
بخورد.

### Canonical panel

گزارش دو شمارنده صریح دارد:

```text
missing_store_id_rows
missing_upc_rows
```

هر مقدار بزرگ‌تر از صفر `valid=false` می‌سازد.

### Forecast و Audit

حتی اگر کسی API را دور بزند و تابع Python را مستقیم صدا بزند، domain دوباره همان policy را اعمال
می‌کند و قبل از مدل یا event detection متوقف می‌شود.

### API و Dashboard

API همان quality report را reuse می‌کند و با وضعیت ۴۲۲ تحلیل را متوقف می‌کند. Dashboard تعداد
شناسه‌های خراب را با متن فارسی نشان می‌دهد و اجازه ممیزی نمی‌دهد.

## تست‌های اضافه‌شده

- missing `store_id`؛
- blank و whitespace-only `store_id`؛
- missing `upc`؛
- blank و whitespace-only `upc`؛
- تاریخ نامعتبر؛
- duplicate پس از trim؛
- رد مستقیم در forecasting؛
- رد مستقیم در promotion audit؛
- رد در raw dunnhumby contract؛
- پاسخ ۴۲۲ API با تعداد دقیق ردیف خراب.

## نتیجه روی داده واقعی

پنل واقعی دوباره اعتبارسنجی و ingest شد:

```text
Source rows: 524,950
Canonical rows: 524,950
Missing STORE_NUM: 0
Missing UPC: 0
Missing store_id: 0
Missing upc: 0
Duplicate normalized grain: 0
Canonical series: 3,909
Valid: true
```

این نتیجه به معنی کامل بودن کل داده نیست؛ فقط نشان می‌دهد کلید grain این dataset از گیت جدید عبور
کرده است.

## فایل‌های اصلی تغییرکرده

- `src/promoguard/data/grain.py`: policy مشترک؛
- `src/promoguard/data/panel.py`: شمارنده‌ها و fatal gate؛
- `src/promoguard/data/dunnhumby.py`: کنترل شناسه‌های source؛
- `src/promoguard/forecasting/evaluation.py`: enforcement مستقیم domain؛
- `src/promoguard/insights/promotion_audit.py`: enforcement مستقیم domain؛
- `apps/api/contracts.py`: response contract جدید؛
- `apps/dashboard/app.py`: نمایش فارسی خطاها؛
- `reports/foundation-correctness/identifier-validation-evidence.json`: شواهد واقعی.

## نتیجه verification

```text
Pytest: 63 passed
Ruff: passed
Compileall: passed
Real-data re-ingestion: passed
Real source identifier counts: all zero
Real canonical identifier counts: all zero
API invalid-grain response: 422 with exact count
```

warning باقی‌مانده pytest مربوط به deprecation در dependency خارجی `Starlette TestClient/httpx`
است و failure قرارداد شناسه نیست.

## پاسخ کوتاه برای مصاحبه

اگر پرسیدند «چرا فقط API validation کافی نبود؟» بگو:

> چون CLI یا یک سرویس داخلی می‌تواند domain function را مستقیم صدا بزند. validation فقط در UI یا
> API یک دفاع شکننده است. من policy شناسه را در یک ماژول مشترک تعریف کردم و آن را هم در ingestion
> و هم در domain boundary اجرا کردم تا هر مسیر ورود، رفتار یکسان داشته باشد.
