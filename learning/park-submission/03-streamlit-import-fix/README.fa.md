# رفع خطای اجرای Streamlit و پیدا نشدن `apps`

## مشکل چه بود؟

وقتی دستور زیر اجرا می‌شود، Streamlit فایل را به‌عنوان یک script مستقیم اجرا می‌کند:

```powershell
streamlit run apps/dashboard/app.py -- --demo
```

در این حالت پایتون همیشه ریشهٔ پروژه یعنی `C:\Users\Reza\Desktop\promoguard-ai` را در مسیر import
خود قرار نمی‌دهد. در نتیجه این import:

```python
from apps.dashboard.presentation import ...
```

ممکن است با خطای زیر متوقف شود:

```text
ModuleNotFoundError: No module named 'apps'
```

این خطا به معنی خراب‌بودن `presentation.py` یا داده‌ها نیست؛ فقط پایتون نمی‌دانسته package محلی
`apps` را از کجا پیدا کند.

## اصلاح انجام‌شده

در ابتدای `apps/dashboard/app.py`، قبل از import کردن `apps.dashboard.presentation`، مسیر ریشهٔ
مخزن از خود محل فایل محاسبه و در `sys.path` اضافه شد:

```python
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
```

`parents[2]` از مسیر `apps/dashboard/app.py` به ریشهٔ مخزن می‌رسد. شرط `if` هم مانع اضافه‌شدن
تکراری مسیر در صورت import دوباره می‌شود.

## چرا این روش مناسب است؟

- اجرای مستقیم Streamlit را پشتیبانی می‌کند؛
- به نصب package اضافی یا تغییر محیط کاربر وابسته نیست؛
- importهای تست و API را خراب نمی‌کند؛
- مسیر absolute شخصی را hard-code نمی‌کند و روی clone دیگر نیز کار می‌کند؛
- منطق تحلیلی، قرارداد داده و خروجی عددی را تغییر نمی‌دهد.

## چگونه صحت اصلاح بررسی شد؟

سه کنترل انجام شد:

1. اجرای مستقیم اپ با پورت جداگانه:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run apps/dashboard/app.py `
     --server.headless true --server.port 8502 -- --demo
   ```

2. درخواست HTTP به `http://localhost:8502/` با پاسخ `200`؛
3. اجرای Ruff و کل suite تست: `73 passed`.

یک warning مربوط به مرز dependency بین Starlette و httpx همچنان وجود دارد و ربطی به این اصلاح
ندارد؛ آن warning در گزارش‌های پروژه عمداً پنهان نشده است.

## اگر دوباره خطا دیدم چه کنم؟

ابتدا مطمئن شو از ریشهٔ پروژه اجرا می‌کنی:

```powershell
Set-Location C:\Users\Reza\Desktop\promoguard-ai
```

سپس از Python محیط مجازی استفاده کن:

```powershell
.\.venv\Scripts\python.exe -m streamlit run apps/dashboard/app.py -- --demo
```

اگر پورت ۸۵۰۱ اشغال بود، Streamlit خودش پورت دیگری اعلام می‌کند. همان URL نمایش‌داده‌شده در
ترمینال را باز کن.

## مرز این اصلاح

این تغییر فقط مشکل import و راه‌اندازی را حل می‌کند. آنچه هنوز خارج از این بخش است:

- اتصال به cloud یا deploy عمومی؛
- authentication؛
- تغییر مدل آماری؛
- اضافه‌کردن LLM یا API شخص ثالث؛
- جایگزین‌کردن دادهٔ واقعی با دادهٔ مصنوعی.

پس بعد از اصلاح، همان Demo Mode واقعی و deterministic قبلی اجرا می‌شود و هیچ ادعای جدیدی دربارهٔ
اثر علّی، سود یا آمادگی production ایجاد نمی‌شود.
