# جزوه فاز ۱: پایه‌گذاری با داده واقعی و کنترل کیفیت

وضعیت: تکمیل‌شده  
تاریخ: ۳۰ اوت ۲۰۲۶ / ۸ شهریور ۱۴۰۵  
پروژه: PromoGuard Retail Intelligence

## هدف فاز

در این فاز هنوز مدل Machine Learning یا تحلیل علی نمی‌سازیم. هدف این است که بفهمیم داده دقیقاً چه
ساختاری دارد و قبل از ورود به مدل، خطاها و محدودیت‌هایش را آشکار کنیم.

مسیر فاز ۱:

```text
Excel عمومی → خواندن sheetها → اعتبارسنجی → اتصال lookupها
→ پنل استاندارد هفتگی → quality report + provenance + تست
```

## منبع داده

منبع `dunnhumby Breakfast at the Frat` است:

```text
https://www.dunnhumby.com/source-files/
```

فایل در این مسیر قرار دارد:

```text
C:\Users\Reza\Desktop\promoguard-ai\data\raw\breakfast-at-the-frat\
```

محتوای ZIP:

- `dunnhumby - Breakfast at the Frat.xlsx`
- `dunnhumby - Breakfast at the Frat User Guide.pdf`

این داده عمومی و پژوهشی است، اما raw production data قابل شناسایی از یک شرکت نیست. برای reproducible
engineering و research مناسب است، ولی اثر واقعی روی یک شرکت ایرانی را اثبات نمی‌کند.

## ساختار workbook

فایل Excel چهار sheet دارد:

- `Glossary`: تعریف متغیرها؛
- `dh Store Lookup`: شهر، ایالت، segment، مساحت فروش و میانگین سبد؛
- `dh Products Lookup`: UPC، manufacturer، category، subcategory و اندازه؛
- `dh Transaction Data`: جدول اصلی فروش.

در sheet تراکنش، header واقعی در ردیف دوم است؛ بنابراین loader از `header=1` استفاده می‌کند.

ستون‌های اصلی:

```text
WEEK_END_DATE, STORE_NUM, UPC, UNITS, VISITS, HHS,
SPEND, PRICE, BASE_PRICE, FEATURE, DISPLAY, TPR_ONLY
```

## Grain داده

هر ردیف نماینده‌ی یک هفته، یک فروشگاه و یک محصول است:

```text
WEEK_END_DATE × STORE_NUM × UPC
```

داده daily نیست؛ weekly است. آن را به daily تبدیل نکردیم، چون چنین تبدیلی اطلاعاتی را که در منبع
وجود ندارد جعل می‌کند. مدل آینده باید با فرکانس هفتگی کار کند.

## تغییرات اصلی

### `src/promoguard/data/dunnhumby.py`

- پیدا کردن workbook از فایل یا پوشه؛
- خواندن workbook خام و پوشه‌ی processed؛
- بررسی ستون‌های ضروری، تاریخ، عدد، مقدار منفی و duplicate grain؛
- بررسی promotion flagهای ۰/۱ و تناقض `TPR_ONLY` با `FEATURE/DISPLAY`؛
- تولید `promotion_flag`؛
- تولید `discount_depth` فقط وقتی discount قابل تعریف باشد؛
- ثبت قیمت‌های خالی و مشکوک به‌عنوان warning؛
- merge امن lookupهای محصول و فروشگاه؛
- ساخت `weekly_panel.csv`؛
- ساخت `quality_report.json` و `provenance.json`.

### چرا merge معمولی کافی نبود؟

در lookup فروشگاه، دو فروشگاه برای یک کلید، دو segment متفاوت داشتند. merge عادی می‌توانست تعداد
ردیف‌های فروش را زیاد و فروش را دوباره‌شماری کند. بنابراین کلیدهای lookup تکراری شناسایی شدند و
metadata متعارض به شکل چندمقداری مانند `MAINSTREAM | UPSCALE` نگه داشته شد.

### `src/promoguard/data/contracts.py`

مدل `DunnhumbyWeeklyRecord` قرارداد یک مشاهده‌ی هفتگی را تعریف می‌کند. مدل `PromotionRecord` نیز
تاریخ معکوس را رد می‌کند.

### `src/promoguard/cli.py`

دستورهای زیر اضافه شدند:

```powershell
promoguard ingest --input data/raw/breakfast-at-the-frat --output data/processed/breakfast-at-the-frat
promoguard validate --input data/processed/breakfast-at-the-frat
promoguard health
```

### `pyproject.toml`

وابستگی `openpyxl` اضافه شد تا workbookهای `.xlsx` خوانده شوند.

## خروجی‌ها

```text
C:\Users\Reza\Desktop\promoguard-ai\data\processed\breakfast-at-the-frat\
```

- `transactions.csv`: تراکنش‌های خام با header استاندارد؛
- `stores.csv` و `products.csv`: lookupها؛
- `weekly_panel.csv`: پنل استاندارد؛
- `quality_report.json`: گزارش ماشین‌خوان؛
- `provenance.json`: URL، hash، grain و تعداد ردیف‌ها.

## نتیجه واقعی

```text
rows                         = 524,950
canonical panel columns      = 27
promotion rows               = 149,386
duplicate grain rows         = 0
date parse errors            = 0
numeric parse errors         = 0
negative values              = 0
missing PRICE                = 23
missing BASE_PRICE           = 185
zero-price sales rows        = 1
price above base price       = 6,047
duplicate store lookup rows  = 4
missing product metadata     = 0
missing store metadata       = 0
```

هشدارها حذف نشده‌اند؛ به مدل‌های بعدی منتقل می‌شوند تا در صورت نیاز مدل abstain کند.

## چرا missing value را پر نکردیم؟

اگر price خالی باشد و ما میانگین را جایگزین کنیم، قیمت واقعی آن هفته را جعل کرده‌ایم. در این فاز
مقدار خالی حفظ و تعدادش گزارش می‌شود. مرحله‌ی بعد باید تصمیم بگیرد که چنین ردیفی حذف شود، وزن بگیرد
یا از نتیجه کنار گذاشته شود.

## چرا profit محاسبه نمی‌کنیم؟

`SPEND` در داده وجود دارد، اما product cost و margin وجود ندارد. بنابراین revenue قابل بررسی است،
ولی این رابطه قابل ادعا نیست:

```text
profit = spend - cost
```

هزینه باید از design partner یا منبع دارای مجوز بیاید؛ margin ساختگی وارد پروژه نمی‌کنیم.

## چرا causal claim نداریم؟

این منبع observational است. بالا رفتن فروش هنگام promotion ممکن است از seasonality یا عوامل دیگری
آمده باشد. فعلاً فقط audit estimate یا association قابل گزارش است، نه جمله‌ی «promotion باعث شد».

## تست‌های فاز

۱۹ تست موفق داریم. موارد مهم:

- ستون ضروری گمشده؛
- units منفی؛
- تاریخ نامعتبر؛
- duplicate grain؛
- price غیرعددی؛
- promotion flag نامعتبر؛
- تناقض TPR-only؛
- missing price به‌عنوان warning؛
- قیمت صفر؛
- loader پوشه‌ی processed؛
- discount منفی تولید نشدن؛
- lookup تکراری بدون تکثیر ردیف‌ها.

## بازتولید

```powershell
Set-Location "C:\Users\Reza\Desktop\promoguard-ai"
.\.venv\Scripts\Activate.ps1

python -m ruff check .
python -m pytest -q
python -m compileall -q src apps
python -m promoguard.cli health

promoguard ingest `
  --input data/raw/breakfast-at-the-frat `
  --output data/processed/breakfast-at-the-frat

promoguard validate --input data/processed/breakfast-at-the-frat
```

نتیجه ثبت‌شده: Ruff موفق، ۱۹ تست موفق، compile موفق، health موفق و ingest واقعی موفق.

## سوال‌های مصاحبه

### چرا داده را daily نکردی؟

چون منبع weekly است و تبدیل weekly به daily اطلاعات واقعی ایجاد نمی‌کند؛ frequency داده و مدل باید
هماهنگ باشند.

### آیا promotion باعث افزایش فروش شده است؟

هنوز نه؛ داده observational است و بدون identification strategy نمی‌توان causal claim داد.

### چرا duplicate lookup مهم است؟

چون join اشتباه فروش را دوبار می‌شمارد و metricها را خراب می‌کند.

### آیا ۵۲۴٬۹۵۰ ردیف یعنی production-ready؟

خیر. فقط ingestion و data-quality foundation آماده است؛ forecasting، uncertainty، causal diagnostics،
monitoring و deployment هنوز باقی مانده‌اند.

## چیزهایی که باید یاد بگیری

- grain و cardinality در join؛
- تفاوت missing، invalid و warning؛
- تفاوت price، base price، spend و margin؛
- تفاوت association و causality؛
- Pydantic data contracts؛
- failure-mode testing؛
- reproducibility و file hash؛
- اصل «هیچ business value را جعل نکن».

## گام بعدی

فاز ۲ با همین پنل واقعی اجرا می‌شود:

```text
seasonal-naive baseline
        ↓
rolling-origin backtest
        ↓
WAPE / MASE / Bias
        ↓
forecast بدون leakage
```

خروجی فاز ۲ تخمینی از فروش عادی خواهد بود و در فاز ۳ به‌عنوان baseline promotion audit استفاده می‌شود.

