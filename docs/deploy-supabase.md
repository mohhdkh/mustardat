# نشر مستردات مجانًا: Render + Supabase

المشروع يعمل محليًا باستخدام SQLite والتخزين المحلي. عند النشر، متغيرات البيئة
تنقله إلى PostgreSQL وSupabase Storage تلقائيًا، من دون تغيير الواجهة أو روابط الصور.

## 1. إنشاء مشروع Supabase

1. أنشئ مشروعًا جديدًا من لوحة Supabase واحتفظ بكلمة مرور قاعدة البيانات.
2. من **Connect** انسخ رابط **Session pooler** الذي يستخدم المنفذ `5432`.
3. من **Project Settings > API** انسخ:
   - `Project URL`
   - مفتاح `service_role` السري

لا تضع مفتاح `service_role` داخل ملفات الواجهة أو مستودع GitHub. يستخدمه الخادم فقط.

لا تحتاج لإنشاء الجداول أو حاوية الصور يدويًا؛ التطبيق ينشئ الجداول وحاوية
`mustardat-images` عند أول تشغيل.

## 2. النشر على Render

اربط مستودع GitHub بــ Render واستخدم ملف `render.yaml`. عند طلب القيم السرية أدخل:

| المتغير | القيمة |
|---|---|
| `DATABASE_URL` | رابط Session pooler من Supabase |
| `SUPABASE_URL` | Project URL من Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | مفتاح service_role السري |

بقية القيم مضبوطة مسبقًا في `render.yaml`. يولّد Render مفتاح JWT عشوائيًا، ويشغّل
الخدمة على الخطة المجانية، بينما تبقى الحسابات والبلاغات والصور في Supabase.

## 3. فحص ما بعد النشر

1. افتح `https://YOUR-DOMAIN/health` وتأكد من ظهور `"status": "healthy"`.
2. أنشئ حسابًا تجريبيًا.
3. أضف بلاغًا وارفع صورة.
4. أعد نشر الخدمة من Render ثم تأكد أن الحساب والبلاغ والصورة ما زالت موجودة.

## متغيرات اختيارية

- `SUPABASE_STORAGE_BUCKET`: اسم حاوية الصور، والافتراضي `mustardat-images`.
- `SUPABASE_STORAGE_PUBLIC`: القيمة الافتراضية `true` لأن صور البلاغات تظهر في
  صفحة التصفح. عند ضبطها إلى `false` يمر عرض الصور عبر خادم التطبيق.
- `STORAGE_BACKEND=local`: يعيد التخزين المحلي أثناء التطوير.

