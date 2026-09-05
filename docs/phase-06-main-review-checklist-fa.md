# چک‌لیست بازبینی اصلی Phase 6 — نسخهٔ 0.6.0

این سند نقطهٔ توقف نسخهٔ اصلاح‌شده برای بازبینی سطح بالا است. خروجی فعلی یک benchmark مهندسی و
آماری روی آزمایش تبلیغاتی Criteo است؛ اثبات ارزش تجاری PromoGuard یا اثر promotion فروشگاهی نیست.

## اصلاحات بسته‌شده

- split تناوبی وابسته به شمارهٔ ردیف با hash پایدار ویژگی‌های پیش‌درمان جایگزین شد.
- نمونه‌گیری وابسته به `visit` حذف شد؛ train sampling دیگر treatment یا outcome را نمی‌بیند.
- ضریب یک‌دوم trapezoid اصلاح شد و raw AUQC از Qini coefficient تفکیک شد.
- gate فقط مدل انتخاب‌شده روی validation را در test بررسی می‌کند.
- LogisticRegression بعد از StandardScaler اجرا و iteration واقعی ثبت می‌شود.
- ۵۰ Poisson multiplier bootstrap برای uncertainty رتبه‌بندی قفل‌شده اجرا می‌شود.
- SMD، propensity AUC و common support به گزارش اضافه شدند.
- یک S-Learner غیرخطی HistGradientBoosting با تنظیمات ثابت اضافه شد.

## نتیجهٔ واقعی

| شاخص | مقدار |
|---|---:|
| ردیف‌های test | 2,097,295 |
| S-Learner خطی Qini coefficient | 5,852.89 |
| T-Learner خطی Qini coefficient | 6,711.38 |
| S-Learner غیرخطی Qini coefficient | 6,553.73 |
| مدل منتخب روی validation | `s_learner_hist_gb` |
| فاصلهٔ اطمینان ۹۵٪ مدل منتخب | [5,953.79, 7,153.86] |
| random baseline Qini coefficient | -0.45 |
| propensity test ROC-AUC | 0.5086 |
| common support | 100% |
| بیشترین absolute SMD در test | 0.0481 |

T-Learner در test عدد بالاتری دارد، اما روی validation برنده نشده است؛ بنابراین انتخاب post-hoc آن
ممنوع است. مدل غیرخطی تمام بودجهٔ ۱۰۰ iteration را مصرف کرده و «همگرا» نامیده نمی‌شود.

## gateهای عبورکرده

- قرارداد داده، checksum و ممنوعیت `exposure`؛
- split مستقل از ترتیب ردیف و sampling مستقل از outcome؛
- فرمول Qini با تست دستی؛
- finite metrics و convergence مدل‌های logistic؛
- کران پایین bootstrap بالاتر از صفر؛
- balance، propensity AUC و common support؛
- انتخاب مدل فقط براساس validation؛
- ۹۰ تست، Ruff، compileall و diff check.

## محدودیت‌های باز

1. test در طول توسعه چند بار مشاهده شده و برای مقاله نباید final untouched holdout نامیده شود.
2. bootstrap فعلی ranking را ثابت نگه می‌دارد و uncertainty ناشی از refit مدل را اندازه نمی‌گیرد.
3. پنج random permutation برای sanity check است، نه فاصلهٔ اطمینان baseline.
4. تنظیمات boosting فقط یک configuration ثابت است و tuning گسترده انجام نشده است.
5. معیار Qini نرمال‌شده با perfect curve گزارش نشده؛ convention دقیق فعلی داخل artifact ثبت شده است.
6. دیتاست به بازار ایران، SKU، قیمت، هزینه یا موجودی مربوط نیست.

## پرسش‌های بازبین سطح بالا

1. آیا برای نسخهٔ پژوهشی باید nested cross-fitting جایگزین split فعلی شود؟
2. آیا model-refit bootstrap یا repeated split برای uncertainty لازم است؟
3. آیا Qini coefficient فعلی باید در کنار normalized Qini و policy value گزارش شود؟
4. آیا برای مقاله باید یک final audit holdout یا دیتاست مستقل جدید تعریف شود؟
5. آیا X/R/DR-Learner ارزش افزودهٔ روش‌شناختی کافی نسبت به baselineها دارد؟

## خط قرمز

`promotion_allowed=false` باقی می‌ماند. این نسخه اجازهٔ targeting خودکار، خرج بودجه، ادعای سود،
تعمیم به مشتری ایرانی یا ادعای اثر علّی promotion فروشگاهی نمی‌دهد.
