# اصلاح پایه ۶: AuditPolicy نسخه‌دار

وضعیت: تکمیل‌شده

تاریخ: ۳۱ اوت ۲۰۲۶ / ۹ شهریور ۱۴۰۵

مدل بازبینی: `gpt-5.6-sol` با reasoning سطح `xhigh`

## مسئله به زبان ساده

نسخه قبلی می‌گفت اگر فروش بعد از پروموشن کمتر از ۸۰٪ فروش قبل باشد، هشدار forward-buy صادر شود.
این قاعده در مستندات وجود داشت، اما عدد `0.8` داخل شرط کد نوشته شده بود. دو عدد `0.5` و `1.5`
برای تشخیص تغییر شدید قبل از رویداد نیز همین وضعیت را داشتند.

به چنین عددهایی «عدد جادویی» می‌گوییم، چون خروجی نام عدد و نسخه قاعده را نشان نمی‌دهد. اگر کسی
بعداً `0.8` را به `0.7` تغییر می‌داد، نتیجه تغییر می‌کرد ولی payload قدیمی و جدید قابل تشخیص نبودند.

## راه‌حل

یک مدل typed و immutable به نام `AuditPolicy` ساخته شد. این مدل تمام قواعد screening را با نام و
نسخه نگه می‌دارد و داخل هر نتیجه audit ذخیره می‌شود.

```text
policy_id: promoguard-observational-screening
version: 1.0.0
pre/post window: 4 weeks
shift range: 0.5 to 1.5
forward-buy threshold: 0.8
```

`extra="forbid"` یعنی اگر فایل config یک فیلد ناشناخته یا اشتباه املایی داشته باشد، سیستم آن را
رد می‌کند. `frozen=True` یعنی policy بعد از ساخته‌شدن در میانه run تغییر نمی‌کند.

## policy چه چیزهایی را تغییر می‌دهد؟

policy می‌تواند این موارد را تغییر دهد:

- حداقل تاریخچه؛
- طول پنجره قبل و بعد؛
- طول reference window؛
- مرز هشدار severe shift؛
- مرز هشدار forward-buy.

policy این موارد را تغییر نمی‌دهد:

- فروش مشاهده‌شده؛
- شناسه رویداد؛
- داده خام؛
- فرمول baseline؛
- ادعای observational بودن نتیجه؛
- ممنوعیت تصمیم rollout یا سود قطعی.

## تست کلیدی

یک نمونه با نسبت post/pre برابر `0.5` ساخته شد:

- policy پیش‌فرض با threshold `0.8` هشدار forward-buy می‌دهد؛
- policy آزمایشی با threshold `0.4` همان هشدار را نمی‌دهد؛
- observed units و baseline در هر دو اجرا دقیقاً برابر می‌مانند.

این تست نشان می‌دهد policy فقط قواعد screening را کنترل می‌کند و محاسبات مشاهده‌شده را بازنویسی
نمی‌کند.

تست دوم policy با lower=2 و upper=1 را رد می‌کند، چون بازه معکوس از نظر منطقی نامعتبر است.

## فایل‌های تغییرکرده

- `src/promoguard/insights/promotion_audit.py`: مدل policy و استفاده از آن؛
- `src/promoguard/cli.py`: بارگذاری اختیاری policy JSON؛
- `configs/audit-policy-v1.json`: نسخه قابل بازبینی policy؛
- `tests/unit/test_promotion_audit.py`: رفتار policy و validation؛
- `docs/evaluation-protocol.md`: تفسیر دقیق آستانه‌ها؛
- `docs/decisions/0003-versioned-observational-audit-policy.md`: دلیل معماری؛
- `reports/phase-03/promotion-audit.json`: payload واقعی همراه policy؛
- این فایل: آموزش فارسی کامل.

## اجرای واقعی

```powershell
python -m promoguard.cli promotion-audit `
  --input data/processed/breakfast-at-the-frat `
  --output reports/phase-03 `
  --audit-policy configs/audit-policy-v1.json
```

## پاسخ کوتاه برای مصاحبه

### چرا thresholdها را model training نکردی؟

داده عمومی outcome علّی، هزینه تصمیم و سیاست تجاری شریک را ندارد. یادگیری threshold از آن داده
ظاهر علمی ایجاد می‌کرد ولی هدف واقعی را optimize نمی‌کرد. بنابراین قواعد فعلی conservative،
versioned و صریح‌اند تا در pilot واقعی قابل کالیبره‌شدن باشند.

### چرا policy را داخل خروجی گذاشتی؟

برای reproducibility. recommendation بدون دانستن policy کامل نیست. ذخیره policy کنار نتیجه باعث
می‌شود بعداً بفهمیم هر warning دقیقاً با کدام نسخه قواعد ساخته شده است.

### آیا تغییر policy یعنی دستکاری نتیجه؟

اگر بدون نسخه و ثبت انجام شود، بله می‌تواند خطرناک باشد. در این معماری config معتبر، نسخه و تست
لازم است و observed data/baseline مستقل باقی می‌مانند.
