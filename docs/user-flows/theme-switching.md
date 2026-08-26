# Flow: تغییر theme

```text
هر صفحه
  → theme toggle
  → light یا dark
  → حفظ page context و انتخاب‌های کاربر
```

theme باید در کل shell یکدست تغییر کند. transition می‌تواند نرم باشد، اما نباید باعث پرش layout یا کاهش خوانایی شود. ترجیح کاربر می‌تواند در آینده persist شود؛ storage و اولویت system preference هنوز تصمیم باز است.

## معیار

- هیچ متن یا status مهمی فقط به‌دلیل تغییر theme ناپدید نشود.
- teal، amber و coral در هر دو theme semantic یکسان داشته باشند.
- screenshotهای چهارگانه مرجع مستقل بررسی شوند.

