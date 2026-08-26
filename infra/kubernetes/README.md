# Kubernetes (آینده)

در این milestone هیچ manifest دیپلوی Kubernetes ساخته نمی‌شود.

آمادگی فعلی برای مهاجرت بعدی:

- web و api stateless هستند
- تنظیمات از environment variable خوانده می‌شوند
- state اپلیکیشن روی filesystem کانتینر ذخیره نمی‌شود
- postgres با volume جداست
- health: `/api/v1/health/live/` و `/api/v1/health/ready/`
- gunicorn با graceful timeout خاموش می‌شود

قدم بعدی می‌تواند Deployment/Service برای web و api، و یک دیتابیس مدیریت‌شده PostGIS باشد.
