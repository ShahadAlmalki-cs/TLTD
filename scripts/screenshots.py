"""يولّد لقطات الشاشة في docs/screenshots ببيانات تجريبية عامة (لا بيانات حقيقية).
الاستخدام:  pip install playwright && playwright install chromium
            python scripts/screenshots.py"""
import os, sys, tempfile, threading, datetime as dt
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
os.environ.update(SECRET_KEY="screens" * 6, INSECURE_DEV="1", DB_PATH=os.path.join(tempfile.mkdtemp(), "demo.db"))
import app as A
from werkzeug.security import generate_password_hash as H
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

OUT = os.path.join(ROOT, "docs", "screenshots"); os.makedirs(OUT, exist_ok=True)
today = A.today(); ws = A.wstart(today)
TITLES = [("مراجعة البريد", "work"), ("قراءة عشرين صفحة", "study"), ("نزهة قصيرة", "health"), ("ترتيب المكتب", "home"), ("مكالمة عائلية", "personal"), ("كتابة ملاحظات الاجتماع", "work")]
PATTERNS = ["dd", "dx", "xx", "ddd", "dxx", "dd", "dx", "x", "ddd", "dd", "ddxx", "dddd", "xx", "dd", "dx", "ddd", "dd", "dx", "ddd", "dd", "dxd"]
with A.app.app_context():
    db = A.db()
    db.execute("insert into users(name,username,pw,rec) values('ضيف','demo',?,?)", (H("demo-password-123"), H("ABCD")))
    goals = {}
    for t, n, c in [("ممارسة الرياضة", 3, "health"), ("القراءة", 4, "study"), ("تعلّم مهارة جديدة", 2, "personal")]:
        goals[t] = db.execute("insert into goals(title,target,category) values(?,?,?)", (t, n, c)).lastrowid
    hid = db.execute("insert into habits(title,category,days,start) values('شرب الماء','health','0123456',?)", ((today - dt.timedelta(days=5)).isoformat(),)).lastrowid
    for k, code in enumerate(PATTERNS):
        d = today - dt.timedelta(days=len(PATTERNS) - k)
        if d.month != today.month: continue
        for i, c in enumerate(code):
            ti, cat = TITLES[(k + i) % len(TITLES)]
            db.execute("insert into tasks(day,title,status,category) values(?,?,?,?)", (d.isoformat(), ti, c, cat))
    for i in range(1, 5):   # سلسلة عادة متتالية
        d = today - dt.timedelta(days=i)
        db.execute("insert or ignore into tasks(day,title,status,category,habit_id) values(?,?,?,?,?)", (d.isoformat(), "شرب الماء", "d", "health", hid))
    for t, st, cat, g in [("مراجعة خطة الأسبوع", "d", "work", None), ("قراءة عشرين صفحة", "d", "study", "القراءة"), ("نزهة قصيرة", "p", "health", "ممارسة الرياضة"), ("تحضير العشاء", "p", "home", None), ("مكالمة عائلية", "p", "personal", None)]:
        db.execute("insert into tasks(day,title,status,category,goal_id) values(?,?,?,?,?)", (today.isoformat(), t, st, cat, goals.get(g)))
    for d in (ws, ws + dt.timedelta(days=1)):
        if d <= today: db.execute("insert into tasks(day,title,status,category,goal_id) values(?,?,?,?,?)", (d.isoformat(), "جلسة رياضة", "d", "health", goals["ممارسة الرياضة"]))
    db.execute("insert into tasks(day,title,status,category) values(?,?,?,?)", ((today + dt.timedelta(days=2)).isoformat(), "موعد مراجعة الخطة", "p", "work"))
    db.execute("insert into notes(day,body) values(?,?)", (today.isoformat(), "يوم هادئ نسبيًا. أهم ما في اليوم: إنهاء المراجعة."))
    db.commit()
srv = make_server("127.0.0.1", 5099, A.app, threaded=True); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:5099"

with sync_playwright() as p:
    b = p.chromium.launch()
    def page(w, h, dark=False, dpr=1.5):
        c = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr, color_scheme="dark" if dark else "light", reduced_motion="reduce")
        pg = c.new_page(); pg.goto(URL + "/login")
        if "login" in pg.url and w == 1280 and not dark: pg.wait_for_timeout(300); pg.screenshot(path=os.path.join(OUT, "login.png"))
        pg.fill("[name=username]", "demo"); pg.fill("[name=password]", "demo-password-123"); pg.click("button.btn"); pg.wait_for_selector("#v-home.on"); pg.wait_for_timeout(700)
        return c, pg
    def snap(pg, view, name):
        pg.evaluate("location.hash='#%s'" % view); pg.wait_for_timeout(700); pg.screenshot(path=os.path.join(OUT, name + ".png"))
    c, pg = page(1280, 860)
    snap(pg, "home", "home"); snap(pg, "calendar", "calendar"); snap(pg, "reports", "reports"); snap(pg, "goals", "goals"); c.close()
    c, pg = page(390, 844, dpr=2); snap(pg, "home", "mobile-home"); snap(pg, "tasks", "mobile-tasks"); c.close()
    c, pg = page(390, 844, dark=True, dpr=2); snap(pg, "home", "mobile-home-dark"); snap(pg, "calendar", "mobile-calendar-dark"); c.close()
    b.close()
from PIL import Image
for f in os.listdir(OUT):
    pth = os.path.join(OUT, f); Image.open(pth).convert("RGB").quantize(colors=160, method=Image.Quantize.MEDIANCUT).save(pth, optimize=True)
print(sorted(os.listdir(OUT)))
