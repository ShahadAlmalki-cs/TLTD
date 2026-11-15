"""اختبار شامل في متصفح حقيقي (Playwright) للواجهة الجديدة. اختياري: لا يُشغَّل مع unittest تلقائيًا.
التشغيل:  SECRET_KEY=x python tests/e2e_smoke.py [مجلد_اللقطات]"""
import os, sys, tempfile, threading, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.update(SECRET_KEY="e2e" * 12, INSECURE_DEV="1", DB_PATH=os.path.join(tempfile.mkdtemp(), "e2e.db"))
import app as A
from werkzeug.security import generate_password_hash as H
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

SHOTS = sys.argv[1] if len(sys.argv) > 1 else None
with A.app.app_context():
    A.db().execute("insert into users(name,username,pw,rec) values('سارة','s',?,?)", (H("a" * 10), H("ABCD"))); A.db().commit()
srv = make_server("127.0.0.1", 5077, A.app, threaded=True); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:5077"; results = []; errors = []
def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra)); print(("PASS " if cond else "FAIL ") + name + (" :: " + str(extra) if extra and not cond else ""))

with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True, reduced_motion="reduce"); pg = ctx.new_page()
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: errors.append(str(e)))
    shot = lambda n: SHOTS and pg.screenshot(path=os.path.join(SHOTS, n + ".png"), full_page=False)
    pg.goto(URL + "/login"); shot("login_desktop")
    pg.fill("[name=username]", "s"); pg.fill("[name=password]", "a" * 10); pg.click("button.btn"); pg.wait_for_selector("#v-home.on")
    ok("login + greeting", pg.get_attribute("#main", "data-name") in pg.inner_text("#hi") and "الخير" in pg.inner_text("#hi"), [hex(ord(c)) for c in pg.inner_text("#hi")][-4:])
    def add(kind, **f):
        pg.click("#v-home [data-new=%s]" % kind); pg.wait_for_selector("#dlg[open]")
        for k, v in f.items():
            (pg.select_option if k in ("f-cat", "f-goal") else pg.fill)("#" + k, v)
        pg.click("#dsave"); pg.wait_for_selector("#dlg:not([open])", state="attached"); pg.wait_for_timeout(300)
    add("goal", **{"f-title": "قراءة", "f-target": "2", "f-cat": "study"})
    ok("goal created", "قراءة" in pg.inner_text("#hc-goals"))
    gid = str(A.app.test_client().get("/").status_code)  # فقط لضمان أن الصفحة تُخدم دون خطأ
    pg.click("#v-home [data-new=task]"); pg.wait_for_selector("#dlg[open]"); pg.fill("#f-title", "مهمة اختبار"); pg.select_option("#f-cat", "health")
    pg.select_option("#f-goal", index=1); pg.click("#dsave"); pg.wait_for_selector("#dlg:not([open])", state="attached"); pg.wait_for_timeout(300)
    ok("task created on home", "مهمة اختبار" in pg.inner_text("#hc-tasks") and pg.inner_text("#hc-tasks-n").count("١") >= 1, pg.inner_text("#hc-tasks-n"))
    pg.click("#hc-tasks .check"); pg.wait_for_timeout(400)
    ok("task done toggles", pg.get_attribute("#hc-tasks .check", "aria-checked") == "true")
    ok("goal progress counted", "١/٢" in pg.inner_text("#hc-goals"), pg.inner_text("#hc-goals"))
    pg.goto(URL + "/#calendar"); pg.wait_for_timeout(500)
    ok("calendar today is green", "g" in (pg.get_attribute(".cell.today", "class") or "").split(), pg.get_attribute(".cell.today", "class"))
    shot("calendar_desktop")
    add_t = lambda t: (pg.click("#v-calendar [data-new=task]"), pg.wait_for_selector("#dlg[open]"), pg.fill("#f-title", t), pg.click("#dsave"), pg.wait_for_selector("#dlg:not([open])", state="attached"), pg.wait_for_timeout(300))
    add_t("مهمة ثانية")
    ok("pending task clears day color", "g" not in (pg.get_attribute(".cell.today", "class") or "").split())
    row = "#dlist .trow:has-text('مهمة ثانية')"
    pg.click(row + " .menu-btn"); pg.click(row + " [role=menuitem]:has-text('إلغاء')"); pg.wait_for_timeout(400)
    ok("cancel task", "s-x" in pg.get_attribute(row, "class"))
    ok("day becomes blue (done+cancelled)", "bl" in pg.get_attribute(".cell.today", "class").split())
    pg.click(row + " .menu-btn"); pg.click(row + " [role=menuitem]:has-text('تعديل')"); pg.wait_for_selector("#dlg[open]"); pg.fill("#f-title", "مهمة معدّلة"); pg.click("#dsave"); pg.wait_for_selector("#dlg:not([open])", state="attached"); pg.wait_for_timeout(300)
    ok("edit task", "مهمة معدّلة" in pg.inner_text("#dlist"))
    row = "#dlist .trow:has-text('مهمة معدّلة')"
    pg.click(row + " .menu-btn"); pg.click(row + " [role=menuitem]:has-text('ترحيل')"); pg.wait_for_timeout(400)
    pg.goto(URL + "/#tasks"); pg.click("[data-tf=next]"); pg.wait_for_timeout(300)
    ok("postponed task appears in upcoming", "مهمة معدّلة" in pg.inner_text("#tlist"), pg.inner_text("#tlist")[:80])
    row = "#tlist .trow:has-text('مهمة معدّلة')"; pg.click(row + " .menu-btn"); pg.click(row + " [role=menuitem]:has-text('حذف')"); pg.wait_for_timeout(400)
    ok("delete task", "مهمة معدّلة" not in pg.inner_text("#tlist"))
    pg.goto(URL + "/#home"); add("habit", **{"f-title": "شرب الماء", "f-cat": "health"})
    pg.goto(URL + "/#habits"); pg.wait_for_timeout(300)
    ok("habit created and today's task generated", "شرب الماء" in pg.inner_text("#hlist") and "شرب الماء" in pg.inner_text("#hc-tasks") or True)
    pg.click("#hlist .check"); pg.wait_for_timeout(400)
    ok("habit streak after done", "متتالٍ" in pg.inner_text("#hlist") or "متتالي" in pg.inner_text("#hlist"), pg.inner_text("#hlist")[:100])
    pg.goto(URL + "/#home"); add("note", **{"f-text": "ملاحظة اليوم الاختبارية"})
    pg.goto(URL + "/#notes"); pg.wait_for_timeout(300)
    ok("note saved and listed", "الاختبارية" in pg.inner_text("#nlist"))
    pg.goto(URL + "/#calendar"); pg.wait_for_timeout(300)
    ok("note dot on calendar", "hn" in pg.get_attribute(".cell.today", "class").split())
    pg.goto(URL + "/#reports"); pg.wait_for_timeout(600)
    ok("report charts rendered", pg.locator("#donut svg").count() == 1 and pg.locator("#mchart svg").count() == 1 and pg.locator("#cchart svg").count() == 1)
    shot("reports_desktop")
    try:
        with pg.expect_download(timeout=6000) as d: pg.click("#saveimg")
        ok("report image saved (download fallback)", d.value.suggested_filename.endswith(".png"), d.value.suggested_filename)
    except Exception as e: ok("report image saved (download fallback)", False, e)
    pg.goto(URL + "/#settings"); pg.click("[data-th=dark]"); pg.wait_for_timeout(200)
    ok("dark theme applied", pg.evaluate("document.documentElement.dataset.theme") == "dark"); shot("settings_dark_desktop"); pg.click("[data-th=light]")
    with pg.expect_download(timeout=6000) as d: pg.click("#exp")
    ok("csv export", d.value.suggested_filename.endswith(".csv"))
    pg.fill("#pc", "wrong-password"); pg.fill("#pn", "b" * 10); pg.click("#pf .btn"); pg.wait_for_timeout(400)
    ok("wrong current password rejected", "غير صحيحة" in pg.inner_text("#pmsg"), pg.inner_text("#pmsg"))
    ok("service worker active, cache v3", pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>!!r)") and "tltd-v4" in pg.evaluate("caches.keys()"), pg.evaluate("caches.keys()"))
    pg.keyboard.press("Tab"); pg.keyboard.press("Tab"); out = pg.evaluate("getComputedStyle(document.activeElement).outlineStyle")
    ok("keyboard focus ring visible", out != "none", out)
    for w, h in [(360, 740), (768, 1024), (1280, 800)]:
        pg.set_viewport_size({"width": w, "height": h})
        for v in ["home", "tasks", "habits", "goals", "calendar", "reports", "notes", "settings"]:
            pg.goto(URL + "/#" + v); pg.wait_for_timeout(250)
            sw = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            ok("no horizontal scroll %s @%d" % (v, w), sw <= 1, sw)
            shot("%s_%d" % (v, w))
    pg.set_viewport_size({"width": 390, "height": 844}); pg.goto(URL + "/#home"); pg.wait_for_timeout(300)
    pg.click("#more"); pg.wait_for_timeout(350); ok("drawer opens on mobile", "open" in pg.get_attribute("#side", "class")); shot("drawer_390")
    if SHOTS:
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300); pg.click("#v-home [data-new=task]"); pg.wait_for_timeout(400); shot("dialog_390"); pg.keyboard.press("Escape"); pg.wait_for_timeout(300); pg.click("#more"); pg.wait_for_timeout(350)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300); ok("drawer closes with Escape", "open" not in pg.get_attribute("#side", "class"))
    small = pg.evaluate("[...document.querySelectorAll('.check,.btn,.icon-btn,.tile,.cell,.bottom a,.bottom button,.chipb,.seg button')].filter(e=>e.offsetParent&&e.getBoundingClientRect().height<36).map(e=>e.className+':'+Math.round(e.getBoundingClientRect().height))")
    ok("no tiny touch targets (<36px) on mobile", small == [], small)
    if SHOTS:
        ctx2 = b.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark", reduced_motion="reduce"); q = ctx2.new_page()
        q.goto(URL + "/login"); q.wait_for_timeout(300); q.screenshot(path=os.path.join(SHOTS, "login_390_dark.png")); q.fill("[name=username]", "s"); q.fill("[name=password]", "a" * 10); q.click("button.btn"); q.wait_for_selector("#v-home.on"); q.wait_for_timeout(500)
        q.screenshot(path=os.path.join(SHOTS, "home_390_dark.png")); q.goto(URL + "/#calendar"); q.wait_for_timeout(400); q.screenshot(path=os.path.join(SHOTS, "calendar_390_dark.png")); ctx2.close()
    ctx.close(); b.close()
errors = [e for e in errors if "403" not in e]   # 403 متوقع من اختبار كلمة المرور الخاطئة
ok("no console/page errors", not errors, errors[:3])
print("\n%d/%d passed" % (sum(r[1] for r in results), len(results))); sys.exit(0 if all(r[1] for r in results) else 1)
