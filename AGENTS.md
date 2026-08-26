# قوانین همکاری در repository هواچ

- نام محصول همیشه «هواچ» است؛ از «هاواچ» استفاده نکن.
- زبان محصول فارسی و layout آن RTL است.
- فونت مرجع محصول Vazirmatn است.
- هویت بصری فعلی نباید redesign یا با یک زبان بصری جدید جایگزین شود.
- تصاویر `design/screens` قرارداد بصری هستند و باید کنار implementation version شوند.
- هر تغییر برای mobile و desktop باید جداگانه بررسی شود.
- overflow افقی در کل صفحه ممنوع است؛ مخصوصاً در کارت‌های مقصد، روزها، مسیرها و داده‌های ساعتی.
- frontend نباید مستقیماً به provider هواشناسی یا database وصل شود؛ فقط از API داخلی استفاده کند.
- قبل از implementation، README، مستندات مرتبط و screenshotهای مرجع خوانده شوند.
- هر milestone باید محدود، قابل تست و قابل مقایسه با تصاویر باشد.
- compatibility نسخه‌های Django و DRF با Python 3.14 باید قبل از bump کردن version بررسی شود.
- Login در این milestone پیاده نمی‌شود؛ فایل‌های design و مستندات Login را دست‌نخورده نگه دار.
- تصاویر اصلی را resize، compress، re-encode یا حذف نکن.
