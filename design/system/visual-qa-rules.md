# قواعد visual QA

## تطبیق با reference

- برای هر صفحه چهار حالت مستقل بررسی شود: light/mobile، dark/mobile، light/web و dark/web.
- تصویر مرجع همان page، theme و device از `design/screens` استفاده شود.
- ابتدا layout و ترتیب sectionها، سپس typography، رنگ، spacing، stateها و در پایان جزئیات icon بررسی شوند.
- تغییر در copy یا asset بدون ثبت تصمیم انجام نشود.

## mobile

- هیچ overflow افقی در root صفحه وجود نداشته باشد.
- Home: input و دکمهٔ جست‌وجو overlap نداشته باشند.
- Point: روزها قبل از weather controls، مسیرها دو ستونه و عنوان فقط «مسیرها» باشد.
- Route: کنترل‌ها کوچک و هم‌ارتفاع، ساعت و سرعت هم‌ردیف، خط جداکنندهٔ عمودی حذف‌شده و یک toggle چهارگزینه‌ای بامداد/صبح/ظهر/شب وجود داشته باشد.
- نقاط مسیر و کارت‌های هوا روی یک محور قابل فهم بمانند.
- «دیروز» از «امروز» کم‌رنگ‌تر باشد.

## web

- whitespace، max-width و hierarchy با screenshot هماهنگ باشد.
- layout چندستونه در Point و Route با تبدیل ناگهانی به overflow جایگزین نشود.
- hero و تصویر زمینه، جایگاه title و actionهای اصلی را نپوشانند.

## accessibility و رفتار

- focus، keyboard order، label و state semantic بررسی شوند.
- متن روی تصویر در هر دو theme خوانا باشد.
- هشدارها متن قابل فهم داشته باشند و فقط با رنگ تشخیص داده نشوند.
- تغییر theme نباید state صفحه یا انتخاب کاربر را از بین ببرد.
- loading/error/stale/partial-data جای کافی و layout پایدار داشته باشند.
