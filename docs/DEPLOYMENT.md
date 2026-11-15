# دليل النشر

> **حالة التحقق:** الخطوات مبنية على الوثائق الرسمية لكل أداة، وجُرّب منها محليًا تشغيل الخادم والاختبارات فقط. لم تُنفَّذ على كل مزوّد استضافة. إن اختلف شيء عندك فراجع الوثائق الرسمية المرتبطة.

## المتطلبات

- **خادم** يعمل دائمًا (VPS بنظام Ubuntu مثلًا) أو استضافة Python. الموقع خفيف جدًا، وأصغر حجم متاح يكفي.
- **نطاق (دومين)** موجَّه إلى الخادم. **HTTPS شرط** لتثبيت التطبيق على الجوال وللإشعارات.
- Python 3.10 أو أحدث.

## 1. تجهيز الخادم والنطاق

1. أنشئ خادمًا بنظام Ubuntu، واحتفظ بعنوان IP.
2. من لوحة النطاق أضف سجل **DNS** من النوع `A`: الاسم `@` والقيمة عنوان IP. انتظر انتشاره.
3. اتصل بالخادم: `ssh root@عنوان-الخادم`. (على Windows يتوفر OpenSSH: [دليل Microsoft](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_overview)).

## 2. تثبيت التطبيق

```bash
apt update && apt install -y python3-venv sqlite3 unzip git ufw
git clone <رابط-المستودع> /opt/tltd            # أو ارفع الملفات إلى /opt/tltd
cd /opt/tltd && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

ثبّت **Caddy** (يجلب شهادة HTTPS تلقائيًا) من الدليل الرسمي: <https://caddyserver.com/docs/install>

## 3. الإعدادات والحساب

```bash
install -d -o www-data -g www-data -m 700 /var/lib/tltd
cp /opt/tltd/.env.example /etc/tltd.env
chown root:www-data /etc/tltd.env && chmod 640 /etc/tltd.env
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(32))')|" /etc/tltd.env

sudo -u www-data bash -c 'set -a; . /etc/tltd.env; set +a; cd /opt/tltd && .venv/bin/flask --app app create-user'
```

يطلب الأمر الاسم واسم المستخدم وكلمة المرور (10 أحرف على الأقل)، ثم يعرض **رمز الاستعادة مرة واحدة فقط**. دوّنه في مكان آمن؛ إن ضاع مع كلمة المرور فلا استعادة للحساب.

## 4. التشغيل

```bash
cp /opt/tltd/deploy/tltd.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now tltd

cp /opt/tltd/deploy/Caddyfile /etc/caddy/Caddyfile
nano /etc/caddy/Caddyfile            # بدّل your-domain.example بنطاقك
systemctl restart caddy

ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

افتح `https://نطاقك`، وستظهر صفحة الدخول.

> تعمل الخدمة بعملية واحدة بعدة خيوط عمدًا (`-w 1 --threads 4`) لأن حدّ محاولات الدخول محفوظ في ذاكرة العملية.

## 5. مكتبات الحركة (اختياري)

```bash
bash /opt/tltd/scripts/vendor.sh && systemctl restart tltd
```

ينزّل GSAP وLenis إلى `static/vendor/` ليخدمهما خادمك نفسه. وبدونهما يعمل الموقع بحركات CSS أبسط. لا تحمّلهما من CDN: تمنع ذلك سياسة CSP وتضر بالخصوصية.

## 6. الإشعارات (Web Push)

```bash
.venv/bin/pip install -r requirements.txt
sudo -u www-data bash -c 'set -a; . /etc/tltd.env; set +a; cd /opt/tltd && .venv/bin/flask --app app vapid-gen --out /var/lib/tltd/vapid_private.pem'
```

يطبع الأمر سطرَي `VAPID_PUBLIC=` و`VAPID_PRIVATE_FILE=`. أضفهما إلى `/etc/tltd.env` مع `VAPID_SUBJECT=mailto:بريدك`، ثم:

```bash
cp deploy/tltd-push.service deploy/tltd-push.timer /etc/systemd/system/
systemctl daemon-reload && systemctl restart tltd && systemctl enable --now tltd-push.timer
```

ثم من التطبيق: **الإعدادات ← تفعيل الإشعارات على هذا الجهاز ← إشعار تجريبي**.

**قواعد الإرسال** (يفحصها المؤقّت كل 15 دقيقة):
- **تنبيه الهدف الأسبوعي:** مرة واحدة في الأسبوع لكل هدف لم يتقدّم حتى نهاية يوم الاثنين (بعد السادسة مساءً)، ولا يشمل الأهداف المضافة بعد الاثنين.
- **التذكير المسائي:** في الساعة المحددة، إن بقيت مهام اليوم غير محسومة.
- **وضع الراحة:** لا إشعارات بين التاريخين المحددين.
- لا إرسال قبل التاسعة صباحًا ولا بعد الحادية عشرة مساءً، ونصوص الإشعارات عامة بلا أسماء مهام.

**قيود:** على iPhone يلزم iOS 16.4 أو أحدث **وإضافة الموقع إلى الشاشة الرئيسية** ثم فتحه منها ([تفصيل Apple](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers)). ولا يوجد ضمان لوصول الإشعار في اللحظة نفسها.

## 7. إضافة التطبيق إلى الجوال

- **iPhone (Safari):** افتح الرابط ← زر المشاركة ← «إضافة إلى الشاشة الرئيسية» ([شرح Apple](https://support.apple.com/en-gb/guide/iphone/iph42ab2f3a7/ios)).
- **Android (Chrome):** قائمة النقاط الثلاث ← «تثبيت التطبيق».
- **حفظ التقرير الشهري صورةً:** قسم «التقارير» ← «حفظ التقرير كصورة» ← «حفظ الصورة» من قائمة المشاركة.

## 8. النسخ الاحتياطي

```bash
apt install -y sqlite3
sudo -u www-data sqlite3 /var/lib/tltd/tltd.db ".backup /var/lib/tltd/backup-$(date +%F).db"
```

انسخ الملف الناتج خارج الخادم. البيانات في ملف واحد، وغير مشفّرة داخله.

## 9. التحديث

```bash
cd /opt/tltd && git pull && .venv/bin/pip install -r requirements.txt
systemctl restart tltd
```

ترقية قاعدة البيانات تلقائية عند التشغيل (إضافة الأعمدة الجديدة فقط). ويُنصح بنسخة احتياطية قبل كل تحديث.

## خيار مجاني: PythonAnywhere (بلا إشعارات)

حساب «Beginner» المجاني لا يطلب بطاقة ويعطي عنوانًا `USERNAME.pythonanywhere.com` مع HTTPS. **القيود:** لا إشعارات Web Push (لا مهام مجدولة كل 15 دقيقة، والاتصال الخارجي مقيَّد)، وتلزم زيارة تبويب Web دوريًا لتمديد التطبيق. التفاصيل الحالية في [مدونة PythonAnywhere](https://blog.pythonanywhere.com/221/).

1. ارفع الأرشيف من تبويب Files، ثم من Bash console: `unzip tltd.zip -d ~ && mkdir -p ~/tltd-data && pip3.10 install --user -U "Flask>=3.0,<4"`.
2. تبويب Web ← Add a new web app ← **Manual configuration** ← Python 3.10 أو أحدث. المجلد: `/home/USERNAME/tltd`. الملفات الثابتة: الرابط `/static/` والمجلد `/home/USERNAME/tltd/static`.
3. ضع محتوى `deploy/pythonanywhere_wsgi.py` في ملف WSGI بعد تبديل `USERNAME` والمفتاح السري.
4. أنشئ الحساب: `cd ~/tltd && export SECRET_KEY=... DB_PATH=$HOME/tltd-data/tltd.db && python3.10 -m flask --app app create-user`.
5. اضغط Reload وافتح الرابط. (دليل Flask الرسمي لديهم: <https://help.pythonanywhere.com/pages/Flask/>)

## استكشاف الأخطاء

```bash
systemctl status tltd
journalctl -u tltd -n 50 --no-pager
systemctl status caddy
```

| العرَض | السبب المرجَّح |
|---|---|
| لا يفتح الموقع | النطاق لم ينتشر بعد، أو المنفذان 80 و443 مغلقان، أو خطأ في النطاق داخل `Caddyfile` |
| تسجيل الدخول لا يثبت | الوصول عبر HTTP بدل HTTPS (الكوكي `Secure`)، أو `INSECURE_DEV` مفعّل خطأً/غير مفعّل محليًا |
| «محاولات كثيرة» | حدّ محاولات الدخول (5 محاولات فاشلة لكل 15 دقيقة)؛ أعد تشغيل الخدمة أو انتظر |
| الإشعارات «غير مضبوطة» | `VAPID_PUBLIC` أو `VAPID_PRIVATE_FILE` غير مضبوطين أو الملف غير موجود |
| تظهر نسخة قديمة من الواجهة | ارفع رقم الإصدار في `static/sw.js` عند تغيير ملفات `static/` |
