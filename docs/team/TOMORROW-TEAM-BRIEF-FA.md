# برگهٔ جلسهٔ فردا: تسک‌های قابل‌تحویل تیم PromoGuard

تاریخ آماده‌سازی: ۱۶ سپتامبر ۲۰۲۶

هدف جلسه: هر نفر بداند چه خروجی‌ای تا هفت روز آینده تحویل می‌دهد. «کمک می‌کنم» تسک نیست؛ owner،
artifact و معیار پذیرش لازم است.

برای تقسیم کامل کار بین Codex، رضا و اعضا به
`docs/team/ASSISTANT-VS-TEAM-WORKSPLIT-FA.md` مراجعه کنید.

## تصمیم محصول

AIIF/bootcamp فعلاً از scope فعال خارج است. همهٔ کارها حول یک خروجی تجاری محدود می‌چرخد:

> Data Readiness & Promotion Audit برای یک شرکت FMCG/پخش/خرده‌فروشی با فایل ناشناس فروش و قیمت.

## تسک‌های رضا — Founder, Technical Lead و Data Engineer

### T-REV-01 — آماده‌سازی مسیر first paid offer

- owner: رضا
- خروجی: قرارداد ورودی، quality report، چک‌لیست تحویل و اجرای کامل روی dataset عمومی
- معیار قبولی: خروجی قابل بازتولید، بدون دادهٔ خصوصی، با limitation و provenance

### T-REV-02 — آماده‌سازی sample intake

- owner: رضا
- خروجی: یک فایل نمونهٔ schema و دستور `validate`
- معیار قبولی: missing column، duplicate grain، date error، قیمت نامعتبر و promotion ناسازگار
  باید reject یا flag شوند.

### T-REV-03 — تجاری‌سازی کنترل‌شده

- owner: رضا
- خروجی: تعریف Pilot در `docs/business/GO-TO-MARKET-SERVICE-PLAN-FA.md`
- معیار قبولی: scope، deadline، مبلغ آزمایشی، خروجی و چیزهای خارج از scope مشخص باشند.

## تسک‌های محمد مهدی — Product Discovery

### P-REV-01 — مصاحبهٔ مسئله

- حداقل ۵ گفت‌وگو با مدیر فروش، trade marketing یا برنامه‌ریزی؛
- برای هر گفت‌وگو: تصمیم فعلی، فایل فعلی، درد، هزینهٔ خطا و KPI؛
- خروجی: `docs/business/customer-discovery/` خارج از دادهٔ هویتی؛
- معیار قبولی: هیچ جمله‌ای مثل «همه نیاز دارند» بدون نقل‌قول یا شاهد ثبت نشود.

## تسک‌های محمد شاهین‌فر — Data & Statistical Analysis

### D-REV-01 — data dictionary مشتری‌پذیر

- mapping ستون‌های عمومی به schema پیشنهادی؛
- سه نمونهٔ خطای رایج در export فروش؛
- سه خطر leakage یا اشتباه در تفسیر promotion؛
- خروجی: data dictionary و quality checklist؛
- معیار قبولی: هر KPI numerator، denominator، grain و limitation داشته باشد.

## تسک‌های خواهر رضا — Business Development & Marketing

### B-REV-01 — فهرست مشتری بالقوه و پیام تماس

- ۲۰ سازمان هدف در دستهٔ FMCG/پخش/خرده‌فروشی متوسط؛
- نام نقش تصمیم‌گیر، نه الزاماً نام شخص؛
- ۱۰ معرفی گرم یا مسیر تماس مجاز؛
- پیام ۵ خطی بر اساس first paid offer؛
- وضعیت هر lead فقط یکی از `identified/contacted/replied/interviewed/pilot_candidate` باشد.

### B-REV-02 — آماده‌سازی جلسهٔ مدیر فروش

- یک فرم یک‌صفحه‌ای برای فهم درد؛
- بدون ادعای درصد سود یا اثر causal؛
- هدف جلسه: گرفتن sample ناشناس یا اجازهٔ گفت‌وگوی دوم، نه فروش feature.

## قوانین merge و انتشار

- هیچ فایل مشتری در GitHub؛
- هر تغییر فنی با branch/PR کوچک؛
- هر تغییر metric، threshold یا claim با review رضا؛
- هر گزارش تجاری باید بگوید public benchmark است یا customer evidence؛
- قیمت آزمایشی تا قبل از دو proposal واقعی «فرضیه» نامیده شود.

## خروجی جلسهٔ هفت‌روزه

در پایان هفته باید این پنج مورد موجود باشد:

1. یک problem brief؛
2. یک data dictionary؛
3. یک quality report بازتولیدشده؛
4. حداقل پنج تماس/گفت‌وگو با وضعیت واقعی؛
5. یک proposal محدود برای pilot.
