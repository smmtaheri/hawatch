# چک‌لیست visual QA

## آماده‌سازی

- [ ] صفحه، theme و device درست انتخاب شده است.
- [ ] تصویر مرجع از `design/screens` استفاده شده است.
- [ ] viewport با reference مقایسه شده است: mobile 576px، web 1905px.
- [ ] font Vazirmatn و direction RTL فعال است.

## layout

- [ ] header، hero، cardها و footer جایگاه درست دارند.
- [ ] ترتیب sectionها با page spec یکی است.
- [ ] هیچ overflow افقی در root وجود ندارد.
- [ ] در mobile، containerهای scroll فقط داخل ناحیهٔ خودشان scroll می‌شوند.
- [ ] radius، border و shadow از tokenها پیروی می‌کنند.

## محتوا و interaction

- [ ] نام محصول «هواچ» است.
- [ ] مقصد، مسیر، روز و period انتخاب‌شده قابل تشخیص‌اند.
- [ ] وضعیت normal/change/critical هم متن دارد و هم نشانهٔ بصری.
- [ ] loading، ready، empty، error، stale و partial-data فضای معتبر دارند.
- [ ] focus و keyboard order قابل استفاده‌اند.

## صفحه‌های ویژه

- [ ] Home: search input و button overlap ندارند.
- [ ] Destination mobile: dayها قبل از controls، routeها دو ستونه و عنوان «مسیرها» است.
- [ ] Route mobile: controls هم‌ارتفاع، ساعت و سرعت هم‌ردیف، خط عمودی حذف و period مشترک است.
- [ ] Login به‌عنوان reference باقی مانده و implementation ندارد.

