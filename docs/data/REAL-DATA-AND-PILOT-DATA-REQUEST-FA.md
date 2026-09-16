# نقشهٔ دادهٔ واقعی PromoGuard و فرم درخواست پایلوت

آخرین به‌روزرسانی: ۱۶ سپتامبر ۲۰۲۶

## ۱. اصل مهم

برای توسعهٔ فنی، از public datasetهای واقعی یا نزدیک به واقعیت استفاده می‌کنیم. برای درآمد و ادعای
تجاری، منبع اصلی باید **دادهٔ واقعی مشتری با اجازهٔ کتبی** باشد. هیچ dataset عمومی جای دادهٔ
فروش، هزینه، موجودی و فرایند واقعی یک شرکت ایرانی را نمی‌گیرد.

دادهٔ مصنوعی فقط برای unit test قراردادها مجاز است و business evidence محسوب نمی‌شود.

## ۲. اولویت منابع برای پروژه

| اولویت | منبع | کاربرد درست | محدودیت |
|---|---|---|---|
| ۱ | دادهٔ anonymized شریک تجاری | پایلوت و فهم مسئلهٔ واقعی | نیازمند اجازه، NDA و data contract |
| ۲ | dunnhumby Breakfast at the Frat | promotion audit، قیمت و sales هفتگی | representation/inspired real-world؛ هزینه، موجودی و RCT ندارد |
| ۳ | dunnhumby The Complete Journey | household transaction، coupon و direct marketing | دادهٔ آموزشی/نماینده؛ برای profit فروشگاه کافی نیست |
| ۴ | FreshRetailNet-50K | stockout، censored demand و forecast تازه‌فروشی | رetail چین و متغیرهای promotion آن با مسئلهٔ ما یکسان نیست |
| ۵ | Walmart M5 | forecast در مقیاس SKU/store/day و price feature | قیمت تغییرکرده الزاماً promotion نیست؛ رقابت Kaggle قواعد خود را دارد |
| ۶ | Criteo Uplift v2.1 | benchmark علّی/ uplift تبلیغات | SKU، قیمت، هزینه، margin و inventory ندارد؛ retail promotion نیست |
| ۷ | UCI Online Retail II | transaction و basket analysis | promotion، inventory و cost کامل ندارد |

## ۳. لینک‌های قابل استفاده

### ۳.۱ منبع اصلی فعلی

- صفحهٔ رسمی dunnhumby Source Files: <https://www.dunnhumby.com/source-files/>
- Breakfast at the Frat از همان صفحه: از دکمهٔ رسمی دانلود در بخش dataset استفاده شود؛ URL فایل
  ممکن است تغییر کند، پس صفحهٔ publisher مرجع پایدار است.
- The Complete Journey از همان صفحه: مناسب برای تحلیل coupon/direct marketing و household.
- راهنمای رسمی dataset بزرگ‌تر: <https://www.dunnhumby.com/wp-content/uploads/2023/08/Let_s-Get-Sort-of-Real-User-Guide-dunnhumby.pdf>

### ۳.۲ stockout و demand

- صفحهٔ رسمی/منبع داده در Hugging Face: <https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K>
- مقالهٔ dataset: <https://arxiv.org/abs/2505.16319>
- baseline رسمی پژوهش: <https://github.com/Dingdong-Inc/frn-50k-baseline>

این dataset در کارت عمومی خود ۵۰٬۰۰۰ سری store-product، دادهٔ فروش روزانه و وضعیت stockout
ساعتی را معرفی می‌کند. قبل از هر استفادهٔ تجاری، license صفحهٔ همان نسخه، attribution و مناسب‌بودن
برای استفادهٔ موردنظر دوباره بررسی شود.

### ۳.۳ forecasting در مقیاس بزرگ

- صفحهٔ رسمی رقابت M5 در Kaggle: <https://www.kaggle.com/competitions/m5-forecasting-accuracy/data>
- mirror قابل دریافت در Zenodo: <https://zenodo.org/records/12636070>

Mirror، جایگزین حقوقی خودکار برای قواعد Kaggle نیست. فایل، checksum، تاریخ دریافت و شرایط استفاده
در `docs/data-acquisition.md` ثبت شود. از آن برای forecast و price-response engineering استفاده
کنید، نه برای ادعای causal promotion lift.

### ۳.۴ causal marketing benchmark

- صفحهٔ رسمی Criteo: <https://ailab.criteo.com/criteo-uplift-prediction-dataset/>
- فهرست datasetهای Criteo: <https://ailab.criteo.com/ressources/>

Criteo برای مقایسهٔ uplift learner و ارزیابی RCT مناسب است. خروجی آن اثبات اثر تخفیف روی SKU یا
سود فروشگاه نیست.

### ۳.۵ تراکنش و basket

- UCI Online Retail II: <https://archive-beta.ics.uci.edu/dataset/502/online%2Bretail%2Bii/files>
- Instacart dataset page قدیمی: <https://www.instacart.com/datasets/grocery-shopping-2017>

Instacart برای basket/reorder جالب است، اما برای دسترسی فعلی و شرایط استفاده باید صفحهٔ منبع را
بررسی کرد. از repositoryهای شخصی به‌عنوان مرجع license استفاده نکنید.

## ۴. بهترین منبع برای اولین درآمد

بهترین داده برای اولین مشتری، دانلود اینترنتی نیست؛ یک export کوچک و ناشناس از خود مشتری است.
حداقل نمونهٔ قابل‌اجرا:

- ۶ تا ۱۲ ماه؛
- یک دسته یا ۵ تا ۲۰ SKU؛
- یک کانال یا حداکثر چند منطقه؛
- فروش روزانه یا هفتگی؛
- حداقل ۳ تا ۵ episode پروموشن؛
- تعریف روشن واحد و currency؛
- یک شخص در سازمان که تعریف ستون‌ها را تأیید کند.

اگر مشتری فقط فروش ماهانه دارد، آن را رد نکنید؛ اما محصول را به «گزارش trend و data readiness»
محدود کنید و وعدهٔ ارزیابی دقیق پروموشن ندهید.

## ۵. schema پیشنهادی برای مشتری

### جدول فروش

`date, store_or_channel_id, product_id, units, revenue, currency`

### جدول قیمت و پروموشن

`date, store_or_channel_id, product_id, regular_price, selling_price, promotion_id,
promotion_type, discount_rate`

### جدول موجودی

`date, store_or_channel_id, product_id, opening_stock, closing_stock, stockout_flag`

### جدول اقتصاد

`product_id, unit_cost, contribution_margin, supplier_funding, fixed_trade_spend,
variable_trade_spend, effective_from, currency`

### ابعاد

`product_id, category_id, brand_id, store_or_channel_id, region_id, channel_id`

برای MVP هیچ `customer_id`, phone, name, national_id یا متن آزاد شخصی لازم نیست. اگر مشتری چنین
ستونی دارد، قبل از دریافت حذف یا hash قراردادی شود. Hash یک جایگزین کامل برای مجوز و کنترل دسترسی
نیست.

## ۶. data contract و دروازهٔ پذیرش

برای اجرای اولیهٔ این دروازه، command زیر یک CSV مشتری را بدون اصلاح یا imputation بررسی می‌کند:

```powershell
promoguard customer-intake `
  --input path/to/partner-export.csv `
  --output reports/customer-intake
```

وضعیت خروجی یکی از این حالت‌هاست:

- `ready_for_observational_audit`
- `limited_observational_report`
- `blocked_data_quality`
- `blocked_privacy_review`

این command هنوز تحلیل causal یا profit انجام نمی‌دهد؛ فقط دروازهٔ پذیرش و سطح مجاز تحلیل را تعیین
می‌کند.

`ready_for_observational_audit` فقط یعنی فایل از کنترل‌های اولیهٔ قالب، واحد فروش، تاریخ،
شناسه، تکرار و نشانهٔ تخفیف عبور کرده است. این وضعیت نه کیفیت طراحی علّی را تأیید می‌کند،
نه کفایت تاریخچه/گروه کنترل را، نه اجازهٔ درآمد یا هدف‌گیری خودکار را. حتی اگر ستون هزینه و
حاشیهٔ سود وجود داشته باشد، `economics_ready=false` تا قرارداد شواهد سناریوی Phase 8
با صاحب داده و مالک تجاری تکمیل شود.

فایل مشتری فقط وقتی وارد pipeline می‌شود که این پرسش‌ها پاسخ داشته باشد:

1. grain چیست؟ یک ردیف فروش روزانهٔ SKU/فروشگاه است یا invoice line؟
2. صفر یعنی فروش صفر است یا دادهٔ گمشده؟
3. آیا stockout ثبت شده یا فروش کم را به‌جای آن داریم؟
4. قیمت regular و selling چگونه تعریف شده‌اند؟
5. promotion flag از کجا می‌آید و چه کسی آن را تأیید می‌کند؟
6. هزینه و margin قبل از چه تاریخی معتبر است؟
7. timezone، تقویم و تعطیلی چیست؟
8. آیا شناسه‌ها پایدارند یا در هر export تغییر می‌کنند؟
9. مالک داده چه کسی است و مدت نگهداری چقدر است؟
10. خروجی برای چه تصمیمی قرار است استفاده شود؟

اگر پاسخ کافی نیست، خروجی status باید `blocked_data_quality` یا `limited_observational_report`
باشد، نه `profit_approved`.

## ۷. امنیت و نگهداری

- دادهٔ خام شریک در `data/partner/` یا خارج از repo نگهداری شود و هرگز commit نشود.
- فقط schema نمونه و fixture کوچک بدون هویت در Git باشد.
- برای هر فایل hash، تاریخ دریافت، منبع و owner ثبت شود.
- دادهٔ خام و خروجی گزارش سطح دسترسی جدا داشته باشند.
- مدت نگهداری، حذف پس از تحویل و افراد مجاز در NDA/قرارداد نوشته شود.
- دادهٔ شخصی برای نسخهٔ اول حذف شود تا دامنهٔ ریسک و اعتماد ساده بماند.
- لاگ‌ها نباید row-level data یا شناسهٔ شخصی را چاپ کنند.

## ۸. برنامهٔ دادهٔ سه‌مسیره

### مسیر A — benchmark عمومی

هدف: regression test، مقایسهٔ مدل، reproducibility و رزومه. claim آن فقط دربارهٔ همان dataset است.

### مسیر B — design partner ناشناس

هدف: فهم schema واقعی، data quality و workflow مدیر فروش. نتیجه ابتدا confidential و بدون claim
بازاری است.

### مسیر C — پایلوت پولی

هدف: یک تصمیم محدود و قابل اندازه‌گیری با scope، deadline، مسئول و acceptance criteria روشن.

هیچ نتیجهٔ مسیر A به‌طور خودکار به مسیر C منتقل نمی‌شود.

## ۹. از مدیر فروش چه بخواهیم؟

متن ساده برای ارسال:

> برای شروع به اطلاعات هویتی مشتریان نیاز نداریم. یک خروجی ناشناس از فروش، قیمت، پروموشن و در
> صورت وجود موجودی برای یک دسته یا چند SKU کافی است. ابتدا فقط کیفیت و قابلیت تحلیل داده را بررسی
> می‌کنیم. اگر داده برای نتیجه‌گیری کافی نباشد، همان را گزارش می‌کنیم و عدد ساختگی تولید نمی‌شود.
> فایل خام در GitHub یا ارائهٔ عمومی قرار نمی‌گیرد و محدودهٔ دسترسی و حذف آن قبل از شروع مشخص می‌شود.

## ۱۰. ترتیب عملی دریافت داده

1. تماس discovery و تعیین یک تصمیم واقعی؛
2. امضای NDA یا حداقل اجازهٔ کتبی محدود؛
3. دریافت sample کوچک و ناشناس؛
4. اجرای validator و صدور Data Quality Report؛
5. جلسهٔ اصلاح تعریف ستون‌ها؛
6. دریافت بازهٔ کامل پایلوت؛
7. اجرای تحلیل با hash و provenance؛
8. تحویل گزارش و جلسهٔ توضیح؛
9. ثبت feedback و تصمیم برای monitoring.

## ۱۱. معیار توقف

اگر دادهٔ مشتری کمتر از ۳ episode پروموشن، بدون قیمت، بدون تعریف صفر، یا بدون شناسهٔ پایدار باشد،
پروژه متوقف نمی‌شود؛ خروجی به «آمادگی داده» downgrade می‌شود. این رفتار از نظر تجاری بهتر از آن
است که یک گزارش جذاب اما غیرقابل دفاع تحویل دهیم.
