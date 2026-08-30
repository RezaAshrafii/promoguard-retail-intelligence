# اصلاح پایه ۲: MASE فقط با هفته‌های واقعاً متوالی

وضعیت: تکمیل‌شده  
تاریخ: ۳۰ اوت ۲۰۲۶ / ۸ شهریور ۱۴۰۵  
تصمیم انسانی: تأییدشده در ADR-0002 و GitHub Issue #1

## MASE خیلی ساده چیست؟

MASE خطای مدل را بر نوسان معمول همان سری تقسیم می‌کند. ایده‌اش این است:

```text
خطای مدل / تغییر عادی فروش از یک هفته به هفته بعد
```

اگر مخرج درست نباشد، عدد MASE نیز معنای دقیقی ندارد؛ حتی اگر predictionهای مدل هیچ تغییری نکرده
باشند.

## اشکال نسخه قبلی

در training history، ردیف‌های promotion عمداً حذف می‌شوند. نسخه قبلی بعد از حذف، فقط ردیف قبلی
باقی‌مانده را با `shift(1)` پیدا می‌کرد.

مثال:

```text
هفته ۱: non-promotion، فروش 10
هفته ۲: promotion، فروش 999
هفته ۳: non-promotion، فروش 20
هفته ۴: non-promotion، فروش 22
```

بعد از حذف هفته ۲، داده ظاهراً این‌طور می‌شد:

```text
هفته ۱: 10
هفته ۳: 20
هفته ۴: 22
```

کد قبلی اختلاف ۱۰ تا ۲۰ را یک تغییر یک‌هفته‌ای حساب می‌کرد؛ اما این دو مشاهده ۱۴ روز فاصله دارند.
اختلاف معتبر یک‌هفته‌ای در این مثال فقط `|22 - 20| = 2` است.

## اصلاح کد

اکنون برای هر store و UPC هم مقدار قبلی و هم تاریخ قبلی محاسبه می‌شود. اختلاف فقط وقتی نگه داشته
می‌شود که:

```text
current_week_end_date - previous_week_end_date == 7 days
```

این شرط هم روی scale هر سری و هم روی global fallback اثر می‌گذارد، چون هر دو از همان مجموعه
`naive_diffs` معتبر ساخته می‌شوند.

## تستی که جلوی بازگشت باگ را می‌گیرد

تست دقیقاً مثال بالا را می‌سازد. انتظار داریم MASE scale برابر ۲ باشد، نه میانگین اختلاف‌های ۱۰ و
۲. اگر کسی در آینده شرط تاریخ را حذف کند، تست شکست می‌خورد.

## اثر واقعی روی گزارش dunnhumby

| مدل | MASE قدیم | MASE اصلاح‌شده | تغییر نسبی |
|---|---:|---:|---:|
| seasonal-naive-52 | 1.20059 | 1.21410 | +1.12% |
| recursive-naive-1 | 1.09469 | 1.10888 | +1.30% |

MASE کمی افزایش یافت؛ یعنی scale قبلی خطا را اندکی خوش‌بینانه‌تر نشان می‌داد. این نتیجه پنهان نشد.

## چه چیزهایی تغییر نکردند؟

- predictionها تغییر نکردند؛
- WAPE مدل فصلی همچنان `0.40046` است؛
- WAPE مدل naive همچنان `0.34828` است؛
- Bias تغییر نکرد؛
- interval coverage تغییر نکرد؛
- تعداد ردیف‌های paired همچنان `41,516` است؛
- نتیجه انتخاب مدل تغییر نکرد: recursive-naive بر اساس WAPE بهتر باقی ماند.

بنابراین کل Forecast خراب نبود؛ فقط تعریف scale مربوط به MASE اصلاح شد.

## فایل‌های تغییرکرده

- `src/promoguard/forecasting/evaluation.py`: شرط فاصله دقیق هفت‌روزه و metadata گزارش؛
- `tests/unit/test_forecasting.py`: تست gap پروموشن؛
- `docs/evaluation-protocol.md`: تعریف دقیق scale؛
- `learning/02-forecasting-baseline/README.fa.md`: عددهای جدید و توضیح اصلاح؛
- `reports/phase-02/forecast-evaluation.*`: بازتولید از داده واقعی؛
- `reports/phase-02/mase-correction-comparison.json`: مقایسه قابل‌ممیزی قبل و بعد.

## نتیجه verification

```text
Focused forecasting tests: passed
Full Pytest suite: 50 passed
Ruff and Compileall: passed
Real Phase-2 report regeneration: passed
WAPE/Bias/Coverage invariance: verified
MASE old/new comparison: recorded
```

## پاسخ کوتاه برای مصاحبه

اگر پرسیدند «چرا promotion rows را حذف کردی ولی بعد MASE مشکل پیدا کرد؟» بگو:

> حذف promotion برای جلوگیری از آلوده‌شدن baseline درست بود، اما حذف ردیف می‌تواند gap تقویمی
> بسازد. من علاوه بر group identity، فاصله زمانی را هم وارد قرارداد metric کردم تا فقط جفت‌هفته‌های
> واقعاً متوالی مخرج MASE را بسازند. سپس گزارش واقعی را بازتولید کردم و نشان دادم فقط MASE تغییر
> کرده، نه prediction یا نتیجه انتخاب مدل.
