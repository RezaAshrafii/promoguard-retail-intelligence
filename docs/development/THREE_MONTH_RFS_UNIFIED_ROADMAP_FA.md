# نقشهٔ راه سه‌ماههٔ PromoGuard برای RFS 005 و دامنهٔ FMCG/RFS 65

## هدف این سند

این سند نقشهٔ اجرای فنی و بازبینی یکپارچهٔ PromoGuard را از نسخهٔ فعلی تا یک تصمیم‌یار پروموشن و Revenue Growth Management تعریف می‌کند.

هدف سه‌ماهه این نیست که از روز اول ادعا کنیم سود هر کمپین را دقیق می‌دانیم. هدف به‌صورت مرحله‌ای این است:

```text
دادهٔ عمومی و benchmark
        ↓
ممیزی شواهد پروموشن
        ↓
برآورد اقتصادی مشروط
        ↓
دادهٔ مجاز چندکمپینی
        ↓
بازبینی مدیر فروش
        ↓
تحلیل contribution و سود با provenance
        ↓
سناریوهای بودجه و محدودیت
        ↓
بهینه‌سازی کنترل‌شدهٔ Revenue Growth Management
```

در این مسیر، RFS 005 مسیر رسمی و قابل‌ارائهٔ فعلی است. صفحهٔ RFS 005 فعال است و مسئلهٔ تحلیل اثر تخفیف، پروموشن و هم‌خوری محصولات را تعریف می‌کند:

<https://aiif.ai/100rfs/rfs/005/>

صفحهٔ RFS 65 در زمان تنظیم این سند پاسخ «این RFS پیدا نشد» می‌دهد. بنابراین RFS 65 در این برنامه به‌عنوان دامنهٔ تخصصی FMCG و چشم‌انداز اقتصادی نگه داشته می‌شود و تا دریافت تأیید رسمی نباید به‌عنوان RFS فعال و قطعی معرفی شود:

<https://aiif.ai/100rfs/rfs/065/>

این دو مسیر یک پلتفرم مشترک دارند، اما در ارائهٔ رسمی باید RFS 005 را مسیر اصلی و FMCG/RFS 65 را vertical تخصصی و مسیر توسعهٔ اقتصادی معرفی کرد.

## وضعیت شروع

نسخهٔ فعلی توانایی‌های زیر را دارد:

- قرارداد ورود داده و بررسی کیفیت فایل؛
- ثبت dataset ID و report ID؛
- تشخیص رویدادهای متوالی پروموشن؛
- baseline زمانی و مقایسهٔ فروش مشاهده‌شده با baseline؛
- پنجره‌های قبل، هنگام و بعد از کمپین؛
- بازهٔ عدم‌قطعیت برای اختلاف فروش؛
- هشدار Forward Buying؛
- غربالگری توصیفی هم‌خوری با محدودیت صریح؛
- تشخیص نبود cost، margin و inventory؛
- تصمیم‌یار با گزینه‌های repeat، modify، more testing و deprioritize؛
- job پس‌زمینه، cache، SQLite metadata store و retry؛
- API، داشبورد Next.js، مسیر Streamlit و PDF؛
- تست‌های واحد و integration؛
- اجرای benchmark روی دادهٔ عمومی واقعی.

نسخهٔ فعلی هنوز این ادعاها را پشتیبانی نمی‌کند:

- سود واقعی شرکت؛
- اثر علّی قطعی پروموشن؛
- فروش افزایشی علّی بدون کنترل معتبر؛
- رتبه‌بندی قطعی کمپین‌ها بر اساس سود؛
- بهینه‌سازی خودکار بودجه؛
- اجرای خودکار کمپین؛
- تعمیم benchmark عمومی به بازار ایران؛
- محصول چندسازمانی production-ready.

## تعریف خروجی‌های سه‌ماهه

در پایان سه ماه باید سه سطح خروجی از یک هستهٔ مشترک داشته باشیم:

### سطح اول: Promotion Evidence Audit

برای هر کمپین مشخص می‌کند:

- فایل و دانهٔ داده معتبر است یا نه؛
- فروش در دورهٔ کمپین چقدر بوده؛
- baseline چقدر بوده؛
- اختلاف فروش در چه بازه‌ای قرار دارد؛
- بعد از کمپین چه اتفاقی افتاده؛
- هم‌خوری قابل‌بررسی هست یا نه؛
- cost، margin و inventory موجود هست یا نه؛
- قدم بعدی repeat، modify، more testing یا deprioritize است.

### سطح دوم: Conditional Economics Report

وقتی شرکت cost، margin، trade spend و funding را با منبع و تاریخ ارائه کند، گزارش می‌تواند این موارد را محاسبه کند:

- contribution ناخالص؛
- هزینهٔ ثابت و متغیر کمپین؛
- contribution خالص مشروط؛
- بازهٔ contribution در سناریوی بدبینانه، میانی و خوش‌بینانه؛
- حساسیت نتیجه به margin و هزینه؛
- وضعیت economics readiness؛
- تصمیم پیشنهادی برای بررسی انسانی.

این خروجی تا زمانی که دادهٔ اقتصادی از شرکت نیاید «سود واقعی» نامیده نمی‌شود.

### سطح سوم: Budget and Revenue Growth Decision Support

بعد از چند کمپین مجاز و بازبینی مدیر فروش، سیستم می‌تواند سناریوهای مختلف را مقایسه کند:

- کدام کمپین ارزش بررسی دارد؛
- کدام ترکیب SKU ریسک هم‌خوری دارد؛
- کدام سناریو از سقف بودجه عبور می‌کند؛
- کدام سناریو موجودی کافی ندارد؛
- کدام سناریو contribution واحدی پایین‌تر از floor است؛
- بودجه چگونه بین کمپین‌های قابل‌اجرا توزیع شود.

این بخش ابتدا باید recommendation انسانی تولید کند. اجرای خودکار و تغییر واقعی قیمت یا بودجه در محدودهٔ این نقشه نیست.

## معماری هدف

```text
                 Partner/Public Input
                         │
       ┌─────────────────┴─────────────────┐
       │                                   │
   Data Contract                     Promotion Contract
       │                                   │
       └─────────────────┬─────────────────┘
                         │
                  Quality Gate
                         │
                 Canonical Panel
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
  Baseline Audit   Basket/Cannibal.   Economics
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
               Uncertainty + Provenance
                         │
             Decision Support / Abstention
                         │
          API + Dashboard + PDF + Report ID
                         │
                Manager Review Feedback
                         │
                Budget/RGM Scenario Layer
```

قواعد معماری:

- محاسبات در `src/promoguard` می‌مانند.
- API و dashboard فقط adapter هستند.
- دادهٔ خام و دادهٔ پردازش‌شده وارد Git نمی‌شوند.
- هر عدد اقتصادی باید منبع، تاریخ و نوع evidence داشته باشد.
- LLM تا قبل از تثبیت خروجی deterministic وارد محاسبه نمی‌شود.
- اگر دادهٔ لازم وجود نداشته باشد، سیستم `not_ready` یا `insufficient_evidence` تولید می‌کند.
- هیچ خروجی متنی حق تغییر عدد محاسبه‌شده را ندارد.

## نقشهٔ راه زمانی

### هفتهٔ اول: تثبیت هستهٔ چندکمپینی و بازبینی فعلی

هدف هفتهٔ اول این است که PromoGuard به‌جای نمایش عمیق یک کمپین، تمام کمپین‌های قابل‌تحلیل را پردازش و مقایسه کند.

#### کارهای فنی

1. ساخت `CampaignAuditBatchRequest` و `CampaignAuditBatchResult`.
2. اجرای audit برای همهٔ promotion episodeهای واجد شرایط.
3. نگه‌داشتن یک report ID برای batch و report ID جدا برای هر event.
4. ثبت وضعیت هر event:
   - `ready_for_screening`؛
   - `needs_more_evidence`؛
   - `invalid_window`؛
   - `economics_not_ready`.
5. ساخت جدول مقایسهٔ کمپین‌ها در API و dashboard.
6. اضافه‌کردن فیلتر بر اساس SKU، store، category و تاریخ در صورت وجود این ستون‌ها.
7. ثبت rule انتخاب event قبل از مشاهدهٔ نتیجه.

#### خروجی هفتهٔ اول

- یک JSON batch report؛
- جدول مقایسهٔ تمام eventها؛
- یک PDF چندکمپینی؛
- نمودار کمپین منتخب؛
- جدول هشدارها و محدودیت‌ها؛
- گزارش کیفیت داده؛
- test برای انتخاب همهٔ eventها و جلوگیری از cherry-picking.

#### معیار عبور

- همهٔ eventهای واجد شرایط پردازش شوند.
- event نامعتبر وارد نتیجهٔ مدیریتی نشود.
- selection rule در report ثبت شود.
- هیچ کمپینی فقط به‌خاطر مثبت‌بودن اختلاف انتخاب نشود.
- خروجی روی دادهٔ عمومی فعلی بازتولید شود.

### هفتهٔ دوم: برآورد اقتصادی مشروط

هدف هفتهٔ دوم این است که اگر cost، margin و trade spend وجود داشته باشد، سیستم بتواند contribution را با بازه و حساسیت محاسبه کند؛ و اگر وجود نداشته باشد، آشکارا توقف کند.

#### قرارداد ورودی اقتصادی

فیلدهای لازم:

```text
regular_unit_price
promotion_unit_price
unit_cost
contribution_margin
fixed_trade_spend
variable_trade_spend_per_unit
supplier_funding_per_unit
available_inventory_units
baseline_demand_units
projected_demand_units
currency
as_of_date
approved_by
evidence_reference
```

#### فرمول‌های نسخهٔ اول

```text
incremental_units
    = observed_units - baseline_units
```

```text
gross_contribution
    = incremental_units × unit_margin
```

```text
net_contribution
    = gross_contribution
    - fixed_trade_spend
    - variable_trade_spend
    + supplier_funding
```

برای بازه:

```text
contribution_lower
    = incremental_units_lower × unit_margin - costs

contribution_point
    = incremental_units_point × unit_margin - costs

contribution_upper
    = incremental_units_upper × unit_margin - costs
```

#### قانون مهم قیمت

اگر price و cost وجود داشته باشد اما margin ثبت نشده باشد، سیستم می‌تواند margin را از price و cost محاسبه کند؛ اما باید آن را در provenance ثبت کند.

اگر cost وجود نداشته باشد:

```text
economics_ready = false
```

و نباید contribution یا profit تولید شود.

اگر margin فقط به‌صورت فرض مورد تأیید شرکت وارد شود، خروجی باید این برچسب را داشته باشد:

```text
sensitivity_only
```

#### خروجی هفتهٔ دوم

- economics readiness report؛
- conditional contribution report؛
- تحلیل حساسیت برای margin و trade spend؛
- وضعیت `economics_not_available` برای دادهٔ عمومی بدون cost؛
- PDF با تفکیک فروش، contribution و هزینه؛
- تست واحد برای واحد پولی، bounds و provenance؛
- یک نمونهٔ گزارش قابل ارائه به مدیر فروش.

#### معیار عبور

- هیچ cost یا margin فرضی بدون برچسب وارد محاسبه نشود.
- مقدار lower هرگز از upper بیشتر نباشد.
- contribution با Decimal محاسبه شود.
- currency مخلوط نشود.
- cost و trade spend دوبار کم نشوند.
- گزارش مشخص کند عدد مشاهده‌شده است، model output است یا approved assumption.

### هفتهٔ سوم: بستهٔ partner data و دریافت چند کمپین

در شروع هفتهٔ سوم باید از دادهٔ عمومی به فایل شرکت منتقل شویم. هدف این هفته دریافت «یک فایل بزرگ و مبهم» نیست؛ هدف دریافت یک export محدود و قابل‌کنترل است.

#### درخواست دادهٔ اولیه از شرکت

حداقل:

- ۶ تا ۱۲ ماه فروش هفتگی یا روزانه؛
- چند SKU از یک دسته؛
- شناسهٔ فروشگاه یا منطقه؛
- تاریخ و شناسهٔ کمپین؛
- regular price و promotion price؛
- promotion type و discount depth؛
- در صورت امکان inventory و distribution.

برای economics:

- unit cost یا contribution margin؛
- fixed trade spend؛
- variable trade spend؛
- supplier funding؛
- واحد پول؛
- تاریخ اعتبار اعداد؛
- فرد تأییدکننده.

#### الزامات privacy

- customer-level identifier لازم نیست.
- شماره تلفن، نام، ایمیل و شناسهٔ شخصی پذیرفته نمی‌شود.
- فایل باید anonymized و aggregate باشد.
- نام شرکت یا برند می‌تواند در صورت درخواست حذف یا hash شود.
- hash فایل اصلی ثبت شود.
- retention و حذف فایل از ابتدا مشخص شود.
- مقصد ذخیره و افراد دارای دسترسی ثبت شوند.

#### معیار عبور

- data contract با شرکت امضا یا تأیید شود.
- source owner مشخص باشد.
- مجوز استفاده از داده برای pilot ثبت شود.
- mapping ستون‌ها تأیید شود.
- حداقل سه کمپین قابل‌تشخیص باشد.
- حداقل دو پنجرهٔ post-promotion کامل باشد.

### هفتهٔ چهارم: مقایسهٔ چندکمپینی و بازبینی مدیر فروش

در این هفته هدف فقط اجرای کد نیست. باید ببینیم مدیر فروش با گزارش چه می‌کند.

#### جلسهٔ بازبینی

برای هر کمپین از مدیر فروش بپرس:

1. آیا این کمپین را از نظر عملی درست شناسایی کرده‌ایم؟
2. آیا خط مبنا برای این کالا معقول است؟
3. کدام هشدار برای شما مفید بود؟
4. آیا این خروجی تصمیمی را تغییر می‌دهد؟
5. آیا margin و cost استفاده‌شده را قبول دارید؟
6. کدام کالا را جایگزین یا هم‌خوار می‌دانید؟
7. چه عامل مهمی در فایل نیست؟
8. گزارش بعدی باید چه چیزی را نشان دهد؟

#### خروجی

- manager feedback record؛
- جدول insight پذیرفته‌شده و ردشده؛
- اصلاح محدودیت‌ها و متن داشبورد؛
- گزارش before/after برای یک تصمیم واقعی؛
- تصمیم اینکه کدام قابلیت به محصول اصلی برگردد.

### هفتهٔ پنجم: سبد محصول و Cannibalization

هدف این هفته ساخت یک جدول سبدی است، نه ادعای causal cannibalization.

#### سطح اول: screening توصیفی

برای هر کمپین:

- SKU کمپین؛
- SKUهای هم‌دسته؛
- فروش قبل و هنگام؛
- نسبت during به pre؛
- تغییر فروش؛
- هم‌زمانی کمپین؛
- evidence level؛
- limitation.

#### سطح دوم: کنترل‌های لازم

- حذف یا علامت‌گذاری SKUهایی که هم‌زمان پروموشن داشته‌اند؛
- جداکردن store و region؛
- کنترل فصل و هفته؛
- بررسی تغییر distribution؛
- بررسی موجودی؛
- بررسی promotionهای رقیب در صورت وجود داده.

#### معیار عبور

- خروجی هرگز «اثبات هم‌خوری» نگوید مگر طراحی شناسایی مناسب وجود داشته باشد.
- کالاهای بدون category به‌عنوان `not_assessed` ثبت شوند.
- افت فروش یک SKU به‌تنهایی به معنی جایگزینی تلقی نشود.

### هفتهٔ ششم: contribution سبد و سناریوهای اقتصادی

در این مرحله contribution محصول اصلی و هزینهٔ کمپین با تغییرات سبد کنار هم قرار می‌گیرند.

```text
net_basket_contribution
    = focal_contribution
    - estimated_lost_contribution_of_neighbors
    - trade_spend
    + supplier_funding
```

اگر contribution کالاهای جایگزین قابل‌محاسبه نباشد، خروجی باید به sensitivity یا `not_assessed` تنزل کند.

سناریوهای اول:

- تکرار کمپین با همان سطح تخفیف؛
- تکرار با تخفیف کمتر؛
- عدم تکرار؛
- اجرای controlled test؛
- تغییر ترکیب کالا؛
- توقف تا تکمیل داده.

هیچ سناریویی در این مرحله به سیستم اجازهٔ اجرای خودکار نمی‌دهد.

### هفتهٔ هفتم: لایهٔ سناریوی بودجه

ورودی:

- کل بودجهٔ Trade Marketing؛
- حداقل contribution هر واحد؛
- maximum discount؛
- reserve موجودی؛
- سقف spend هر کمپین؛
- interval تقاضا؛
- اولویت دسته یا منطقه.

خروجی اولیه:

- feasible؛
- infeasible؛
- دلایل ردشدن؛
- budget used؛
- projected contribution؛
- risk flags.

در این هفته هنوز optimizer کامل نمی‌سازیم. ابتدا feasibility را ثابت می‌کنیم؛ سپس ranking و allocation را اضافه می‌کنیم.

### هفتهٔ هشتم: allocation محدود و قابل‌توضیح

فقط وقتی هفتهٔ هفتم بدون خطا عبور کرد:

- چند سناریوی feasible را مقایسه کن؛
- تابع هدف را صریح ثبت کن؛
- تعارض بین revenue و contribution را نمایش بده؛
- محدودیت موجودی و budget را اعمال کن؛
- tie و عدم‌قطعیت را گزارش کن؛
- اگر چند سناریو نزدیک هستند، خروجی را `indeterminate` کن.

تابع هدف نسخهٔ اول باید توسط کاربر یا مدیر تأیید شود، مثلاً:

```text
maximize expected net contribution
subject to:
  total trade spend <= approved budget
  projected demand <= sellable inventory
  discount <= approved maximum
  unit contribution >= approved floor
```

### هفتهٔ نهم: Revenue Growth Management اولیه

در این مرحله RGM را به‌عنوان یک dashboard تصمیم‌یار محدود می‌سازیم، نه سیستم کامل سازمانی.

ماژول‌ها:

- promotion effectiveness؛
- price and discount ladder؛
- portfolio mix؛
- cannibalization screen؛
- budget scenario؛
- regional/store comparison؛
- evidence and uncertainty panel؛
- manager decision log.

خروجی مدیریتی:

- کدام کمپین ارزش تکرار دارد؟
- کدام کمپین نیازمند اصلاح است؟
- کدام کالاها نباید هم‌زمان پروموشن شوند؟
- کدام سناریو budget را نقض می‌کند؟
- کجا داده برای تصمیم کافی نیست؟

## تقویم یکپارچهٔ بازبینی

در پایان هر مرحله، این پنج لایه باید با هم بازبینی شوند:

### بازبینی داده

- source و hash ثبت شده؟
- grain واضح است؟
- ستون‌های ضروری وجود دارند؟
- missing و duplicate گزارش شده‌اند؟
- units و currency مشخص‌اند؟

### بازبینی مدل

- leakage وجود دارد؟
- baseline قبل از event ساخته شده؟
- post-window کامل است؟
- همهٔ eventهای واجد شرایط دیده شده‌اند؟
- intervalها finite و مرتب‌اند؟

### بازبینی اقتصادی

- cost منبع دارد؟
- margin با currency درست ثبت شده؟
- trade spend دوبار کسر نشده؟
- سناریو با upper demand budget را می‌سنجد؟
- sensitivity از profit واقعی جدا شده؟

### بازبینی محصول

- مدیر بدون خواندن کد متوجه نتیجه می‌شود؟
- recommendation دلیل دارد؟
- limitation کنار عدد است؟
- report ID قابل‌بازیابی است؟
- PDF با dashboard هم‌خوان است؟

### بازبینی ادعا

- آیا عبارت profit بدون cost نمایش داده شده؟
- آیا عبارت causal بدون control نوشته شده؟
- آیا public data به بازار ایران تعمیم داده شده؟
- آیا insight مشاهده‌ای به‌عنوان fact کسب‌وکار آمده؟
- آیا LLM می‌تواند عدد را تغییر دهد؟

## تست‌های لازم

### تست‌های داده

- missing required columns؛
- duplicate grain؛
- date parse error؛
- negative units؛
- invalid promotion flag؛
- missing SKU/store؛
- inconsistent currency؛
- mixed units؛
- invalid campaign bounds؛
- incomplete post-window؛
- concurrent promotion contamination.

### تست‌های audit

- اختلاف مثبت؛
- اختلاف منفی؛
- baseline بدون leakage؛
- Forward Buying؛
- نبود inventory؛
- نبود category؛
- نبود cost؛
- چند event؛
- eventهای ردشده؛
- انتخاب event مستقل از نتیجه.

### تست‌های اقتصادی

- lower <= point <= upper؛
- Decimal money calculation؛
- currency normalization؛
- fixed spend؛
- variable spend؛
- supplier funding؛
- inventory reserve؛
- projected demand upper bound؛
- minimum contribution؛
- budget infeasibility؛
- evidence approval؛
- missing economics gate.

### تست‌های محصول

- upload → dataset ID؛
- dataset → event list؛
- event → report ID؛
- queued → running → ready؛
- interrupted report → failed؛
- retry → new report ID؛
- cache hit؛
- cache invalidation after source change؛
- PDF download؛
- report URL restore؛
- dashboard data and PDF equality.

## دادهٔ عمومی و دادهٔ شرکت چه نقشی دارند؟

دادهٔ عمومی فعلی برای این موارد کافی است:

- تست ingestion؛
- تست quality gate؛
- تست event detection؛
- تست baseline؛
- تست قبل/هنگام/بعد؛
- تست Forward Buying؛
- تست multi-campaign؛
- تست غربالگری توصیفی هم‌خوری؛
- تست report و PDF؛
- تست رفتار abstention.

دادهٔ عمومی فعلی برای این موارد کافی نیست:

- سود واقعی شرکت؛
- margin معتبر یک برند ایرانی؛
- trade spend واقعی؛
- allocation واقعی بودجه؛
- اثر competitor؛
- تصمیم نهایی تکرار کمپین؛
- اثبات willingness to pay.

برای دادهٔ شرکت باید از ابتدا این سه نسخه را نگه داریم:

```text
source file
    ↓ hash
immutable snapshot
    ↓ mapping
canonical panel
    ↓ analysis
report + evidence references
```

## مدل ادعا در سه ماه

### ماه اول

عبارت مجاز:

> PromoGuard شواهد مشاهده‌ای عملکرد کمپین را بررسی می‌کند و نقاط نیازمند بررسی بیشتر را مشخص می‌کند.

عبارت غیرمجاز:

> PromoGuard سود کمپین را ثابت می‌کند.

### ماه دوم

عبارت مجاز:

> با دادهٔ cost، margin و trade spend تأییدشده، PromoGuard contribution مشروط و تحلیل حساسیت تولید می‌کند.

عبارت غیرمجاز:

> این عدد سود قطعی شرکت است.

### ماه سوم

عبارت مجاز:

> PromoGuard چند سناریوی پروموشن را تحت محدودیت بودجه، موجودی و contribution مقایسه می‌کند و تصمیم قابل‌بازبینی پیشنهاد می‌دهد.

عبارت غیرمجاز:

> سیستم بدون تأیید مدیر بهترین بودجه را اجرا می‌کند.

## شاخص‌های موفقیت

### شاخص‌های فنی

- حداقل ۹۵٪ فایل‌های نمونهٔ مجاز از quality gate عبور یا با علت مشخص رد شوند.
- ۱۰۰٪ گزارش‌ها report ID و evidence reference داشته باشند.
- zero silent fallback برای cost، margin و currency.
- تمام اعداد PDF و dashboard برابر باشند.
- تمام تست‌های اقتصادی و lifecycle پاس شوند.

### شاخص‌های داده

- حداقل سه کمپین قابل تحلیل در partner export؛
- حداقل دو post-window کامل؛
- حداقل دو SKU هم‌دسته؛
- cost و margin تأییدشده برای بخش اقتصادی؛
- inventory یا ثبت رسمی نبود آن؛
- promotion semantics تأییدشده توسط صاحب داده.

### شاخص‌های مدیر فروش

- مدیر فروش بتواند در کمتر از ۱۰ دقیقه نتیجه را توضیح دهد.
- حداقل یک insight باعث تغییر سؤال یا تصمیم بعدی شود.
- مدیر بتواند محدودیت گزارش را بازگو کند.
- مدیر با تعریف cost، margin و promotion موافق باشد.
- مدیر یک کمپین مناسب برای آزمون بعدی انتخاب کند.

### شاخص‌های تجاری

- یک partner برای اجرای pilot؛
- یک export مجاز؛
- یک جلسهٔ بازبینی؛
- یک گزارش تأییدشده؛
- یک پیشنهاد قیمت برای تکرار خدمت؛
- بدون ادعای مشتری یا درآمد تا وقتی سند وجود نداشته باشد.

## ریسک‌های اصلی و پاسخ

| ریسک | اثر | پاسخ |
|---|---|---|
| نبود cost و margin | سود قابل محاسبه نیست | economics readiness و درخواست دادهٔ مشخص |
| نبود کنترل | اثر علّی ضعیف است | controlled pilot یا زبان observational |
| هم‌خوری نامشخص | سود بیش‌برآورد می‌شود | basket screen و سطح شواهد |
| موجودی ناقص | فروش کمتر از تقاضا دیده می‌شود | stockout warning و عدم‌قطعیت |
| دادهٔ چند کمپینی نامنظم | مقایسه ناعادلانه می‌شود | event contract و selection rule |
| overfitting به یک کمپین | تعمیم غلط | گزارش همهٔ eventها و time split |
| مشکل privacy | عدم پذیرش partner | aggregate export و hash و retention |
| داشبورد زیبا بدون تصمیم | عدم استفاده | manager feedback و decision log |
| LLM hallucination | عدد و ادعا تغییر می‌کند | JSON source of truth و golden tests |
| scope زیاد | تأخیر و انحراف | یک active gate و توقف قابلیت‌های کم‌ارزش |

## بازبینی اصلی در پایان ماه اول

در پایان ماه اول باید تصمیم بگیریم آیا ادامهٔ اقتصادی ارزش دارد یا نه.

### ادامه بده اگر

- چند کمپین واقعی یا عمومی با pipeline واحد پردازش شدند؛
- quality gate قابل‌اعتماد است؛
- مدیر فروش حداقل یک insight را مفید دانست؛
- cost و margin از partner قابل دریافت است؛
- گزارش قابل تکرار و قابل توضیح است.

### دامنه را کم کن اگر

- فقط یک SKU قابل تحلیل است؛
- category و basket در دسترس نیست؛
- مدیر فروش خروجی را به تصمیم وصل نمی‌کند؛
- costها اختلاف جدی دارند؛
- دادهٔ کمپین‌ها تعریف مشترک ندارد.

### متوقف کن اگر

- مجوز داده وجود ندارد؛
- هدف تصمیمی مشخص نیست؛
- source owner حاضر به تأیید semantics نیست؛
- هزینه و margin دائماً غیرقابل‌اعتماد است؛
- نتیجه فقط برای ساخت demo و بدون کاربر واقعی استفاده می‌شود.

## بازبینی اصلی در پایان ماه دوم

در پایان ماه دوم باید بررسی کنیم:

- آیا contribution مشروط با اعداد مدیر فروش سازگار است؟
- آیا نتایج بین چند کمپین پایدار است؟
- آیا هم‌خوری واقعی در سبد قابل بررسی است؟
- آیا post-window به‌اندازهٔ کافی وجود دارد؟
- آیا budget constraints به‌درستی اعمال می‌شوند؟
- آیا مدیر به خروجی اعتماد عملی دارد؟
- آیا یک تصمیم واقعاً بر اساس گزارش تغییر کرده است؟

اگر پاسخ این سؤال‌ها منفی باشد، وارد optimizer کامل نمی‌شویم و به data contract و partner validation برمی‌گردیم.

## دروازهٔ نهایی ماه سوم

برای اعلام «آماده برای pilot تجاری تکرارپذیر» همهٔ موارد زیر لازم است:

- حداقل یک partner مجاز؛
- چند کمپین در یک فایل یا چند فایل هم‌معنا؛
- تعریف تأییدشدهٔ units و promotion؛
- cost و margin با تاریخ و تأییدکننده؛
- inventory یا ثبت محدودیت آن؛
- report ID و provenance؛
- contribution interval؛
- manager review؛
- PDF و dashboard هم‌خوان؛
- test suite کامل؛
- بدون ادعای causal یا profit فراتر از evidence؛
- تصمیم بعدی مشخص و ثبت‌شده.

## تقسیم کار اجرایی پیشنهادی

### مسئول فنی و محصول

- هستهٔ calculation؛
- قراردادها؛
- API؛
- dashboard؛
- تست‌ها؛
- release و evidence.

### مسئول تحلیل و داده

- mapping فایل partner؛
- بررسی grain و semantics؛
- کنترل campaign windows؛
- بررسی category و basket؛
- بازبینی uncertainty.

### مسئول کسب‌وکار و ارتباط

- تعیین مدیر فروش مناسب؛
- ثبت نیاز تصمیمی؛
- گرفتن مجوز داده؛
- هماهنگی جلسهٔ بازبینی؛
- ثبت feedback و willingness to repeat.

اگر فقط یک نفر فعال باشد، نقش سوم را نمی‌توان با متن مصنوعی جایگزین کرد؛ باید ارتباط انسانی، مجوز و تأیید مدیر واقعاً انجام شود.

## ترتیب commit و release

هر vertical باید در یک commit قابل بازبینی بسته شود:

```text
feat(phase-08): add multi-campaign audit batch
feat(phase-08): add conditional economics report
feat(phase-08): add partner basket screening
feat(phase-08): add budget feasibility decision support
docs(phase-08): add manager review and evidence packet
```

هر commit باید این موارد را داشته باشد:

- تغییر کد؛
- تست؛
- گزارش فارسی در learning؛
- limitation؛
- evidence artifact؛
- دستور بازتولید؛
- نتیجهٔ review.

دادهٔ خام، فایل partner، credential و خروجی محرمانه وارد GitHub نمی‌شود.

## نتیجهٔ برنامه

در پایان دو هفته، هدف قابل‌دستیابی این است که PromoGuard یک برآورد اقتصادی مشروط و قابل‌ارائه تولید کند؛ یعنی اگر cost، margin و trade spend وجود داشته باشد contribution را با interval حساب کند و اگر وجود نداشته باشد با دلیل روشن متوقف شود.

در پایان شش هفته، هدف دریافت و اجرای چند کمپین مجاز، بازبینی با مدیر فروش و ثبت insightهای واقعاً مفید است.

در پایان سه ماه، هدف یک decision-support اولیه برای Revenue Growth Management است که کمپین‌ها و سناریوهای بودجه را تحت محدودیت‌های واقعی مقایسه می‌کند. این سیستم هنوز اجراکنندهٔ خودکار تصمیم نیست؛ تصمیم نهایی باید انسانی، قابل‌بازبینی و متکی به دادهٔ صاحب کسب‌وکار باقی بماند.

جملهٔ اصلی برای ارائه:

> PromoGuard از یک ممیزی شفاف شواهد پروموشن شروع می‌کند، در صورت وجود دادهٔ اقتصادی به contribution مشروط می‌رسد و پس از اعتبارسنجی چند کمپین و بازبینی مدیر فروش، سناریوهای بودجه و Revenue Growth Management را تحت محدودیت‌های واقعی مقایسه می‌کند.
