# اصلاح پایه ۴: API فقط برای اجرای محلی

وضعیت: تکمیل‌شده  
تاریخ: ۳۰ اوت ۲۰۲۶ / ۸ شهریور ۱۴۰۵

## مشکل چه بود؟

API یک `input_path` از درخواست می‌گرفت و همان مسیر را روی کامپیوتر میزبان باز می‌کرد. این رفتار برای
demo محلی راحت است، اما اگر API مستقیماً روی اینترنت قرار بگیرد، caller می‌تواند مسیرهای مختلف
فایل‌سیستم سرور را امتحان کند.

حتی اگر محتوای کامل فایل برگردانده نشود، این طراحی می‌تواند به file probing، افشای metadata یا
مصرف منابع منجر شود.

## اصلاح انجام‌شده

API اکنون یک `LOCAL_DATA_ROOT` مشخص دارد که به‌صورت پیش‌فرض پوشه `data/` همین repository است.
مسیر ورودی ابتدا به مسیر absolute واقعی resolve می‌شود و سپس باید فرزند همین root باشد.

```text
data/processed/panel.csv     → مجاز
C:/Users/.../private.csv     → 403 Forbidden
../outside.csv               → بعد از resolve، 403 Forbidden
```

استفاده از `resolve` مهم است؛ چون فقط بررسی متن `../` کافی نیست.

## محدودیت deployment

OpenAPI و health اکنون صریحاً `local_demo_only` را اعلام می‌کنند. دستور اجرا نیز به loopback محدود
شده است:

```powershell
uvicorn apps.api.main:app --reload --host 127.0.0.1
```

این یعنی دستگاه‌های دیگر شبکه مستقیماً به آن دسترسی ندارند، مگر کاربر آگاهانه تنظیمات را تغییر دهد.

## چرا این هنوز production API نیست؟

نسخه اینترنتی باید به‌جای path دلخواه یکی از این دو مدل را داشته باشد:

- upload کنترل‌شده به storage امن؛
- `dataset_id` متعلق به server و دارای authorization.

همچنین authentication، rate limit، audit log و resource isolation لازم است.

## تست

تست integration یک CSV واقعی‌نما بیرون root مجاز می‌سازد و بررسی می‌کند API با وضعیت ۴۰۳ آن را رد
کند. تست‌های دیگر root را به پوشه موقت همان تست محدود می‌کنند تا isolation حفظ شود.

```text
Focused API tests: 10 passed
Real-data API smoke: passed
Ruff: passed
```

## پاسخ کوتاه مصاحبه

> API فعلی یک adapter محلی برای demo است. چون caller path می‌فرستد، من هم bind شبکه را روی loopback
> نگه داشتم و هم path را پس از resolve به data root محدود کردم. برای production، path contract را
> با authenticated dataset ID یا secure upload جایگزین می‌کنم.
