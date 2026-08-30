# بخش ۹: Release Gate 5.1 و معنای «آماده انتشار»

## در این بخش چه اتفاقی افتاد؟

همه اصلاح‌های correctness جداگانه انجام شده بودند، اما تا وقتی کل زنجیره دوباره روی داده واقعی اجرا
نشود نمی‌توان گفت foundation بسته شده است. این بخش نقش کنترل نهایی را دارد: نسخه package و API یکی
شد، تمام تست‌ها اجرا شدند، داده واقعی validate شد، forecast و audit دوباره ساخته شدند و هش فایل‌های
شاهد ثبت شد.

## نتایج واقعی

- ۶۷ تست پاس شد و هیچ test failure نداشتیم.
- Ruff و compileall پاس شدند.
- package با نسخه 0.5.1 نصب شد و health endpoint همان نسخه را برگرداند.
- ۵۲۴٬۹۵۰ ردیف واقعی validate شد؛ grain تکراری و شناسه store/SKU گمشده صفر بود.
- از ۵۸٬۱۳۱ ردیف non-promotion، هر دو مدل برای ۴۱٬۵۱۶ ردیف prediction داشتند؛ یعنی coverage برابر
  ۷۱٫۴۲ درصد است.
- مدل seasonal-naive با WAPE حدود 0.4005 از recursive-naive با WAPE حدود 0.3483 بهتر نشد.
- audit واقعی ۱۲۸ واحد مشاهده‌شده را با baseline برابر ۱۸۵ مقایسه کرد؛ اختلاف -۵۷ و بازه
  [-۱۲۷، ۱۳] بود.
- به علت `FORWARD_BUY_RISK` خروجی `needs_more_evidence` باقی ماند.

## چرا hash ثبت کردیم؟

SHA-256 اثر انگشت فایل است. اگر حتی یک کاراکتر در گزارش forecast، audit یا smoke عوض شود hash هم
عوض می‌شود. بنابراین داور یا عامل بعدی می‌تواند بفهمد گزارشی که درباره‌اش حرف می‌زنیم همان فایل
بررسی‌شده است، نه یک خروجی تازه و ناشناخته.

## یک warning باقی مانده؛ یعنی شکست خورده‌ایم؟

خیر. warning از مرز نسخه‌های Starlette TestClient و httpx می‌آید، نه از محاسبات PromoGuard. آن را
پنهان نکردیم و در quality report ثبت کردیم. چون ۶۷ تست پاس‌اند و warning رفتار فعلی را خراب نمی‌کند،
blocker انتشار نیست؛ ولی در ارتقای dependency بعدی باید دوباره بررسی شود.

## چرا قبل از tag منتظر GitHub CI می‌مانیم؟

تست محلی فقط ماشین فعلی را ثابت می‌کند. CI همان commit را روی محیط تمیز Ubuntu و Python 3.11 نصب
و تست می‌کند. روند حرفه‌ای این است: candidate commit → push → CI سبز → final status → annotated
tag. اگر CI قرمز شود، tag ساخته نمی‌شود.

## فایل‌های این بخش

- `pyproject.toml` و `src/promoguard/__init__.py`: نسخه 0.5.1.
- `tests/unit/test_health.py`: تست هماهنگی health version.
- `reports/foundation-correctness/release-quality-report.json`: منبع عددی اصلی release.
- `docs/releases/v0.5.1-foundation-correctness.md`: release note قابل خواندن برای داور.
- `ROADMAP.md` و `PARK_SUBMISSION_AGENT_HANDOFF.md`: وضعیت دقیق برای عامل بعدی.

## پاسخ کوتاه مصاحبه‌ای

اگر پرسیدند «از کجا می‌فهمی پروژه آماده release بود؟» بگویید: «فقط unit test را نگاه نکردم؛ lint،
compile، نصب package، validation کامل داده واقعی، بازتولید forecast/audit، API smoke، hash artifact و
CI محیط تمیز را gate کردم. نتیجه منفی و warning dependency را هم حذف یا پنهان نکردم.»
