# سیاست انتخاب مدل برای توسعه PromoGuard

این سند مشخص می‌کند هر فاز با چه مدل و چه سطح reasoning اجرا شود. هدف این نیست که همیشه قوی‌ترین
مدل را بدون دلیل اجرا کنیم؛ هدف این است که در فازهای آماری و معماری، کیفیت تصمیم از هزینه و سرعت
مهم‌تر باشد و در کارهای تکراری منابع هدر نرود.

## تصمیم فوری

فاز فعال فعلی **Release Gate 5.1 — Foundation Correctness و آماده‌سازی ارسال پارک** است و Phase 6
تا عبور کامل این gate متوقف می‌ماند. برای coverage accounting، AuditPolicy، امنیت مرزها و audit
نهایی ادعاها استفاده کن:

```powershell
.\start-agent.ps1 -Model gpt-5.6-sol -Reasoning xhigh -RunMode phase
```

برای بازبینی نهایی thresholdها، leakage، سازگاری artifact و زبان abstention یک اجرای جداگانه با
Sol مناسب است:

```powershell
.\start-agent.ps1 -Model gpt-5.6-sol -Reasoning max -RunMode phase
```

برای نگارش فارسی بسته، roadmap و ویدیو از `gpt-5.6-terra` با `high` استفاده شود. اجرای review
جایگزین شاهد، تست و بررسی انسانی نیست؛ فقط برای consistency audit نهایی استفاده می‌شود.

## ماتریس پیشنهادی فازها

| فاز | موضوع | مدل اصلی | reasoning | مدل کمکی |
|---|---|---|---|---|
| ۳ | promotion audit و observational estimate | `gpt-5.6-sol` | `xhigh` | Sol `max` برای review نهایی |
| ۴ | FastAPI، dashboard و demo | `gpt-5.6-sol` | `high` | Terra `high` برای iteration |
| ۵ | بسته‌ی پارک و ارائه | `gpt-5.6-terra` | `high` | Sol `xhigh` برای consistency review |
| ۶ | benchmark causal و Criteo | `gpt-5.6-sol` | `xhigh` | Sol `max` برای estimator review |
| ۷ | cannibalization، forward-buy و uncertainty | `gpt-5.6-sol` | `xhigh` | Sol `max` برای abstention review |
| ۸ | constrained profit optimization | `gpt-5.6-sol` | `xhigh` | Terra `high` برای تست سناریوها |
| ۹ | production، monitoring و LLM guardrails | `gpt-5.6-sol` | `xhigh` | Terra `high` برای adapterها |
| ۱۰ | portfolio، AIIF و job packaging | `gpt-5.6-terra` | `high` | Sol `xhigh` برای final review |

## Luna چه زمانی مناسب است؟

`gpt-5.6-luna` را برای این کارها نگه می‌داریم:

- اصلاح فرمت Markdown؛
- تغییر نام یا refactor کوچک و کم‌ریسک؛
- اجرای تست‌های موجود و توضیح خروجی؛
- تولید چند نسخه‌ی متن پس از قطعی‌شدن محاسبات؛
- کارهای پرتعداد که تصمیم آماری یا معماری جدیدی ندارند.

Luna نباید مدل اصلی طراحی estimand، ارزیابی causal، leakage prevention، interval calibration،
یا معماری production باشد.

## Terra چه زمانی مناسب است؟

Terra انتخاب متعادل برای پیاده‌سازی‌هایی است که design آن‌ها قبلاً با Sol بررسی شده است؛ مثل
adapterهای API، endpointها، جدول‌های dashboard، documentation و iterationهای معمول. اگر هنگام
کار Terra به تصمیم جدید آماری، causal یا امنیتی رسیدیم، کار متوقف می‌شود و برای review به Sol
برمی‌گردد.

## قانون تغییر مدل وسط فاز

مدل را وسط یک task بدون ثبت دلیل عوض نمی‌کنیم. تغییر مدل فقط در این حالت‌ها انجام می‌شود:

1. مسئله از implementation ساده به تصمیم آماری/causal تبدیل شود؛
2. مدل فعلی دو بار در بررسی کد، تست یا جلوگیری از leakage شکست بخورد؛
3. خروجی عددی با artifact بازتولیدشده ناسازگار باشد؛
4. معماری جدیدی وارد scope شود؛
5. قبل از merge، یک review مستقل برای ادعاهای مهم لازم باشد.

در هر تغییر باید مدل، reasoning، دلیل تغییر، و نتیجه‌ی validation در گزارش همان فاز نوشته شود.

## روال ثابت قبل از هر فاز

در ابتدای هر اجرای agent این چهار خط باید مشخص باشد:

```text
Active phase: ...
Model: ...
Reasoning: ...
Why this model: ...
```

پس از پایان فاز، نتیجه‌ی مدل باید با تست، artifact و محدودیت‌های ثبت‌شده سنجیده شود؛ مدل قوی‌تر
هرگز مجوز ادعای قوی‌تر درباره‌ی business impact نیست.

## نکته درباره‌ی DeepSeek

DeepSeek V4 Pro می‌تواند به‌عنوان reviewer دوم یا برای مقایسه‌ی prompt استفاده شود، اما برای
فازهای causal و production من آن را مدل اصلی قرار نمی‌دهم مگر این‌که همان commitها، تست‌ها و
artifactها را مستقل و بدون اختلاف بازتولید کند. provider را وسط یک اجرای حساس عوض نمی‌کنیم تا
تفاوت نتیجه با تفاوت مدل اشتباه نشود.

## مرجع رسمی

راهنمای رسمی OpenAI می‌گوید Sol برای complex reasoning and coding، Terra برای تعادل intelligence
و cost، و Luna برای cost-sensitive/high-volume workload مناسب است:

- https://developers.openai.com/api/docs/models
- https://developers.openai.com/api/docs/guides/latest-model
