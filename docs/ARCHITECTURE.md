# البنية التقنية

## نظرة عامة

```
المتصفح (PWA)                         الخادم (Flask)                      التخزين
┌────────────────────┐   /api/*    ┌──────────────────────────┐     ┌────────────┐
│ index.html         │  JSON+CSRF  │ app.py                   │     │ SQLite     │
│ app.js (حالة+رسم)  │ ──────────► │ • المصادقة والجلسات      │ ──► │ tltd.db    │
│ style.css          │ ◄────────── │ • واجهة API              │     └────────────┘
│ sw.js (SW)         │             │ • أوامر CLI              │
└────────────────────┘             └──────────────────────────┘
        ▲  Web Push ◄───────── flask push-check (مؤقّت systemd كل 15 دقيقة)
```

- صفحة واحدة تتنقل بين ثمانية أقسام بالروابط `#القسم`، وتستدعي `/api/*` من النطاق نفسه فقط.
- الخادم يخدم القوالب والملفات الثابتة وواجهة JSON. لا ORM ولا خطوة بناء.
- ألوان الأيام وإحصاءات التقرير **تُحسب في المتصفح** من مهام الشهر، والخادم يحسب تقدّم الأهداف وسلاسل العادات.

## نموذج البيانات (SQLite)

| الجدول | الأعمدة الرئيسية |
|---|---|
| `users` | `name`, `username` (فريد), `pw` (hash), `rec` (hash رمز الاستعادة) |
| `tasks` | `day` (YYYY-MM-DD), `title`, `status` (`p` معلّقة · `d` منجزة · `x` ملغاة), `category`, `goal_id`, `habit_id` |
| `goals` | `title`, `target` (1–7 أيام/أسبوع), `category`, `created` |
| `habits` | `title`, `category`, `days` (سلسلة أرقام 0–6، 0 = السبت)، `start` |
| `notes` | `day` (مفتاح), `body` |
| `settings` | `k`, `v` (إعدادات الإشعارات ووضع الراحة) |
| `push_subs` / `push_log` | اشتراكات الإشعارات وسجل عدم التكرار |

الترقية تلقائية عند الاستيراد (`alter table ... add column` عند غياب العمود). الفئات: `health, personal, work, study, home, other`.

## قواعد العمل

- **الأسبوع يبدأ السبت.** الفهرس = `(weekday + 2) % 7`.
- **لون اليوم** (في المتصفح): بلا لون إن لم تكن فيه مهام أو بقيت مهمة معلّقة. وإلا: أخضر = كل المهام منجزة، وردي = لا مهمة منجزة، أزرق = أي حالة بين ذلك.
- **تقدّم الهدف:** عدد **الأيام المميزة** التي أُنجزت فيها مهمة مرتبطة بالهدف خلال الأسبوع.
- **العادات:** عند طلب مهام شهر (`GET /api/tasks`) تُنشأ مهام العادات من تاريخ بدايتها حتى اليوم (بلا تكرار بفهرس فريد). السلسلة: أيام مجدولة متتالية منجزة حتى اليوم، واليوم المعلّق لا يقطعها.
- **الإشعارات:** انظر [DEPLOYMENT.md](DEPLOYMENT.md#6-الإشعارات-web-push). المنطق في `push_check()` ويقبل `now` ليسهل اختباره.

## واجهة API

كل المسارات تتطلب جلسة مسجَّلة (وإلا `401`)، وكل طلب كتابة (`POST/PUT/PATCH/DELETE`) يتطلب ترويسة `X-CSRF` (أو حقل `csrf` في النماذج).

| الطريقة | المسار | الوصف |
|---|---|---|
| GET | `/api/tasks?month=YYYY-MM` | مهام الشهر (وتولّد مهام العادات) |
| POST | `/api/tasks` | إضافة `{day, title, category?, goal_id?}` |
| PATCH | `/api/tasks/<id>` | تعديل `status` و/أو `day` و/أو `title` و/أو `category` |
| DELETE | `/api/tasks/<id>` | حذف مهمة |
| GET/POST | `/api/goals` | الأهداف مع تقدّم الأسبوع / إضافة `{title, target, category?}` |
| DELETE | `/api/goals/<id>` | حذف هدف |
| GET/POST | `/api/habits` | العادات مع السلسلة / إضافة `{title, days, category?}` |
| DELETE | `/api/habits/<id>` | حذف عادة |
| GET | `/api/notes?month=YYYY-MM` | ملاحظات الشهر `{day: text}` |
| PUT | `/api/notes/<day>` | حفظ ملاحظة `{text}` (نص فارغ = حذف) |
| GET/PUT | `/api/settings` | إعدادات الإشعارات ووضع الراحة |
| GET | `/api/push/key` | المفتاح العام VAPID |
| POST | `/api/push/subscribe` · `/unsubscribe` · `/test` | إدارة الاشتراكات وإرسال تجريبي |
| POST | `/api/password` | تغيير كلمة المرور `{current, new}` |
| GET | `/api/export.csv` | تصدير المهام (مع حماية من حقن الصيغ) |
| POST | `/api/wipe` | حذف كل البيانات `{confirm: "حذف"}` |
| GET/POST | `/login` · `/recover` · POST `/logout` | الدخول والاستعادة والخروج |

## الواجهة الأمامية

`static/app.js` وحدة واحدة (IIFE) مقسّمة بتعليقات: أدوات ← تحميل البيانات (`load`) ← عناصر مشتركة (صف المهمة وقائمة «⋯») ← رسم كل قسم (`renderHome` … `renderNotes`) ← حوار الإضافة والتعديل ← التقرير والصورة المحفوظة (Canvas) ← التنقل ← الإعدادات والإشعارات. الحالة في كائن `S`، وكل تعديل يعيد `load()` ثم `renderAll()`.

## الأمان

- **CSP:** `default-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`.
- **الجلسة:** `HttpOnly` و`Secure` و`SameSite=Strict`، وتنتهي بعد 30 يومًا.
- **ترويسات:** `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, و`Cache-Control: no-store` لغير الملفات الثابتة.
- **محاولات الدخول:** 5 محاولات فاشلة لكل 15 دقيقة لكل عنوان (في الذاكرة).
- **حقن SQL:** كل الاستعلامات بمعاملات `?`.

## Service Worker

يخزّن `style.css` و`app.js` فقط ويعتمد الشبكة أولًا، ولا يخزّن أي استجابة API. ويستقبل أحداث `push` و`notificationclick`. **ارفع رقم إصدار الذاكرة في `sw.js` عند كل تغيير في `static/`.**
