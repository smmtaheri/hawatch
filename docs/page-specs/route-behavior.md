# رفتار Route

## ورودی

نمونهٔ اصلی `/routes/touchal-darband` است. route باید parent destination، origin، destination و نقاط مرتب‌شده داشته باشد.

## planner

- date، period، start time و speed پارامترهای تصمیم‌اند.
- تغییر هر پارامتر باید point arrival، weather mapping و decision card را هماهنگ update کند.
- mobile ساعت و speed را در یک row جمع‌وجور نشان می‌دهد.
- فقط یک period control مشترک برای timeline و cards وجود دارد.

## تصمیم و اشتراک

decision card باید risk point و زمان آن را برجسته کند و امکان کپی/اشتراک را نشان دهد. در این milestone این actionها فقط در سطح design contract هستند و integration واقعی ندارند.

## محور و overflow

نقاط مسیر و کارت هوا روی یک محور معناشناختی قرار می‌گیرند. اگر عرض کم است، container خود محور می‌تواند scroll شود؛ root صفحه هرگز overflow افقی نگیرد.

