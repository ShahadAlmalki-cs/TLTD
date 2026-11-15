import csv, io, json, os, re, sqlite3, secrets, hmac, time, datetime as dt
from zoneinfo import ZoneInfo
from functools import wraps
import click
from flask import (Flask, g, request, session, jsonify, render_template,
                   redirect, url_for, abort, send_from_directory, Response)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.environ.get("INSECURE_DEV") != "1",
    PERMANENT_SESSION_LIFETIME=dt.timedelta(days=30),
    MAX_CONTENT_LENGTH=64 * 1024)
if os.environ.get("BEHIND_PROXY") == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

DB = os.environ.get("DB_PATH", "tltd.db")
TZ = ZoneInfo(os.environ.get("TZ_NAME", "Asia/Riyadh"))
CATS_AR = {"health": "الصحة", "personal": "شخصي", "work": "عمل", "study": "دراسة", "home": "المنزل", "other": "أخرى"}
CATS = tuple(CATS_AR)
VAPID_PUBLIC = os.environ.get("VAPID_PUBLIC", "")
VAPID_PRIVATE_FILE = os.environ.get("VAPID_PRIVATE_FILE", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@example.com")
SCHEMA = """
create table if not exists users(id integer primary key, name text, username text unique, pw text, rec text);
create table if not exists habits(id integer primary key, title text not null, category text not null default 'other', days text not null, start text not null);
create table if not exists notes(day text primary key, body text not null);
create table if not exists settings(k text primary key, v text not null);
create table if not exists push_subs(endpoint text primary key, p256dh text not null, auth text not null, created text not null);
create table if not exists push_log(kind text not null, ref text not null, period text not null, primary key(kind, ref, period));
create table if not exists goals(id integer primary key, title text not null, target integer not null check(target between 1 and 7), category text not null default 'other');
create table if not exists tasks(id integer primary key, day text not null, title text not null,
  status text not null default 'p' check(status in ('p','d','x')),
  category text not null default 'other',
  goal_id integer references goals(id) on delete set null);
create index if not exists ix_day on tasks(day);
"""
_c = sqlite3.connect(DB); _c.executescript(SCHEMA)
if "category" not in [r[1] for r in _c.execute("pragma table_info(tasks)")]:   # ترحيل قواعد البيانات القديمة
    _c.execute("alter table tasks add column category text not null default 'other'")
if "habit_id" not in [r[1] for r in _c.execute("pragma table_info(tasks)")]:
    _c.execute("alter table tasks add column habit_id integer references habits(id) on delete set null")
if "category" not in [r[1] for r in _c.execute("pragma table_info(goals)")]:
    _c.execute("alter table goals add column category text not null default 'other'")
if "created" not in [r[1] for r in _c.execute("pragma table_info(goals)")]:
    _c.execute("alter table goals add column created text not null default ''")
_c.execute("create unique index if not exists ix_habit_day on tasks(habit_id, day) where habit_id is not null")
_c.commit(); _c.close()

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
        g.db.execute("pragma foreign_keys=on")
    return g.db

@app.teardown_appcontext
def _close(_):
    d = g.pop("db", None)
    if d: d.close()

@app.before_request
def csrf_check():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = (request.headers.get("X-CSRF") or request.form.get("csrf") or "").encode()
        have = session.get("csrf", "").encode()
        if not have or not hmac.compare_digest(sent, have):
            abort(400)

@app.context_processor
def _ctx():
    return {"csrf": lambda: session.setdefault("csrf", secrets.token_hex(16))}

@app.after_request
def _hdr(r):
    r.headers["Content-Security-Policy"] = ("default-src 'self'; style-src 'self'; img-src 'self' data:; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "no-referrer"
    if not request.path.startswith("/static"):
        r.headers["Cache-Control"] = "no-store"
    return r

FAILS = {}
def limited(ip):
    now = time.time()
    FAILS[ip] = [t for t in FAILS.get(ip, []) if now - t < 900]
    return len(FAILS[ip]) >= 5

def norm(code): return re.sub(r"[^0-9A-Z]", "", code.upper())
def new_code(): return "-".join(secrets.token_hex(2).upper() for _ in range(5))

def auth(f):
    @wraps(f)
    def w(*a, **k):
        if "u" not in session:
            if request.path.startswith("/api"): abort(401)
            return redirect(url_for("login"))
        return f(*a, **k)
    return w

@app.cli.command("create-user")
@click.option("--name", prompt="الاسم الذي يظهر في التحية")
@click.option("--username", prompt="اسم المستخدم")
@click.password_option("--password", prompt="كلمة المرور (10 أحرف على الأقل)", confirmation_prompt=True)
def create_user(name, username, password):
    if db().execute("select 1 from users").fetchone():
        raise click.ClickException("يوجد حساب بالفعل. هذا الموقع لحساب واحد فقط.")
    if len(password) < 10:
        raise click.ClickException("كلمة المرور أقصر من 10 أحرف.")
    code = new_code()
    db().execute("insert into users(name,username,pw,rec) values(?,?,?,?)",
        (name.strip(), username.strip(), generate_password_hash(password), generate_password_hash(norm(code))))
    db().commit()
    click.echo("تم إنشاء الحساب.\nرمز الاستعادة (يظهر مرة واحدة، يُحفظ في مكان آمن): " + code)

@app.route("/login", methods=["GET", "POST"])
def login():
    err = None
    if request.method == "POST":
        ip = request.remote_addr
        if limited(ip):
            err = "محاولات كثيرة. يُرجى المحاولة بعد قليل."
        else:
            u = db().execute("select * from users where username=?", (request.form.get("username", "").strip(),)).fetchone()
            if u and check_password_hash(u["pw"], request.form.get("password", "")):
                session.clear(); session.permanent = True
                session["u"] = u["id"]; session["csrf"] = secrets.token_hex(16)
                return redirect(url_for("home"))
            FAILS.setdefault(ip, []).append(time.time())
            err = "بيانات الدخول غير صحيحة."
    return render_template("auth.html", mode="login", err=err)

@app.route("/recover", methods=["GET", "POST"])
def recover():
    err = None
    if request.method == "POST":
        ip = request.remote_addr
        pw = request.form.get("password", "")
        if limited(ip):
            err = "محاولات كثيرة. يُرجى المحاولة بعد قليل."
        else:
            u = db().execute("select * from users where username=?", (request.form.get("username", "").strip(),)).fetchone()
            if u and len(pw) >= 10 and check_password_hash(u["rec"], norm(request.form.get("code", ""))):
                code = new_code()
                db().execute("update users set pw=?, rec=? where id=?",
                    (generate_password_hash(pw), generate_password_hash(norm(code)), u["id"]))
                db().commit(); session.clear()
                return render_template("auth.html", mode="login", code=code)
            FAILS.setdefault(ip, []).append(time.time())
            err = "الرمز أو البيانات غير صحيحة. كلمة المرور الجديدة 10 أحرف على الأقل."
    return render_template("auth.html", mode="recover", err=err)

@app.post("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

@app.get("/")
@auth
def home():
    u = db().execute("select name from users where id=?", (session["u"],)).fetchone()
    vendor = os.path.exists(os.path.join(app.static_folder, "vendor", "gsap.min.js"))   # مكتبات الحركة اختيارية
    return render_template("index.html", name=u["name"], vendor=vendor)

@app.get("/sw.js")
def sw():
    r = send_from_directory(app.static_folder, "sw.js", mimetype="text/javascript")
    r.headers["Cache-Control"] = "no-cache"; return r

def today(): return dt.datetime.now(TZ).date()
def wstart(d): return d - dt.timedelta(days=(d.weekday() + 2) % 7)   # الأسبوع يبدأ السبت
def body(): return request.get_json(silent=True) or {}
def day_of(s):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s): abort(400)
    try: return dt.date.fromisoformat(s).isoformat()
    except ValueError: abort(400)

def day_idx(d): return str((d.weekday() + 2) % 7)   # 0 = السبت ... 6 = الجمعة

def materialize(month):
    """تُنشئ مهام العادات للأيام من بداية العادة حتى اليوم، ولا تكرر ما أُنشئ."""
    t = today(); first = dt.date.fromisoformat(month + "-01")
    for h in db().execute("select * from habits").fetchall():
        d = max(first, dt.date.fromisoformat(h["start"]))
        while d.isoformat()[:7] == month and d <= t:
            if day_idx(d) in h["days"]:
                db().execute("insert or ignore into tasks(day,title,category,habit_id) values(?,?,?,?)",
                             (d.isoformat(), h["title"], h["category"], h["id"]))
            d += dt.timedelta(days=1)
    db().commit()

def streak(h):
    t = today(); d = t; n = 0; start = dt.date.fromisoformat(h["start"])
    st = {r["day"]: r["status"] for r in db().execute("select day,status from tasks where habit_id=?", (h["id"],))}
    while d >= start:
        if day_idx(d) in h["days"]:
            s = st.get(d.isoformat())
            if s == "d": n += 1
            elif not (d == t and s in (None, "p")): break
        d -= dt.timedelta(days=1)
    return n

@app.get("/api/tasks")
@auth
def tasks_list():
    m = request.args.get("month", "")
    if not re.fullmatch(r"\d{4}-\d{2}", m): abort(400)
    materialize(m)
    rows = db().execute("select id,day,title,status,category,habit_id,goal_id from tasks where day like ? order by id", (m + "-%",)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/tasks")
@auth
def tasks_add():
    b = body(); title = str(b.get("title", "")).strip()[:200]
    if not title: abort(400)
    gid = b.get("goal_id")
    if gid is not None:
        try: gid = int(gid)
        except (TypeError, ValueError): abort(400)
        if not db().execute("select 1 from goals where id=?", (gid,)).fetchone(): abort(400)
    cat = b.get("category", "other")
    if cat not in CATS: abort(400)
    cur = db().execute("insert into tasks(day,title,category,goal_id) values(?,?,?,?)",
                       (day_of(str(b.get("day", ""))), title, cat, gid))
    db().commit(); return jsonify(id=cur.lastrowid), 201

@app.patch("/api/tasks/<int:i>")
@auth
def tasks_set(i):
    b = body(); sets, vals = [], []
    if "status" in b:
        if b["status"] not in ("p", "d", "x"): abort(400)
        sets.append("status=?"); vals.append(b["status"])
    if "day" in b:
        sets.append("day=?"); vals.append(day_of(str(b["day"])))
    if "title" in b:
        ti = str(b["title"]).strip()[:200]
        if not ti: abort(400)
        sets.append("title=?"); vals.append(ti)
    if "category" in b:
        if b["category"] not in CATS: abort(400)
        sets.append("category=?"); vals.append(b["category"])
    if not sets: abort(400)
    db().execute("update tasks set " + ",".join(sets) + " where id=?", vals + [i]); db().commit(); return "", 204

@app.delete("/api/tasks/<int:i>")
@auth
def tasks_del(i):
    db().execute("delete from tasks where id=?", (i,)); db().commit(); return "", 204

@app.get("/api/goals")
@auth
def goals_list():
    t = today(); ws = wstart(t); we = ws + dt.timedelta(days=6)
    rows = db().execute("""select g.id,g.title,g.target,g.category,
        (select count(distinct day) from tasks where goal_id=g.id and status='d' and day between ? and ?) as done
        from goals g order by g.id""", (ws.isoformat(), we.isoformat())).fetchall()
    return jsonify(today=t.isoformat(), idx=(t.weekday() + 2) % 7, goals=[dict(r) for r in rows])

@app.post("/api/goals")
@auth
def goals_add():
    b = body(); title = str(b.get("title", "")).strip()[:100]
    try: n = int(b.get("target"))
    except (TypeError, ValueError): abort(400)
    cat = b.get("category", "other")
    if not title or not 1 <= n <= 7 or cat not in CATS: abort(400)
    cur = db().execute("insert into goals(title,target,category,created) values(?,?,?,?)", (title, n, cat, today().isoformat())); db().commit()
    return jsonify(id=cur.lastrowid), 201

@app.delete("/api/goals/<int:i>")
@auth
def goals_del(i):
    db().execute("delete from goals where id=?", (i,)); db().commit(); return "", 204

def _safe(v):  # يمنع تنفيذ الصيغ عند فتح الملف في برامج الجداول
    v = str(v or "")
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v

@app.get("/api/export.csv")
@auth
def export_csv():
    st = {"p": "معلّقة", "d": "منجزة", "x": "ملغاة"}
    out = io.StringIO(); w = csv.writer(out); w.writerow(["التاريخ", "المهمة", "الحالة", "الفئة", "الهدف"])
    for r in db().execute("select t.day,t.title,t.status,t.category,g.title as goal from tasks t "
                          "left join goals g on g.id=t.goal_id order by t.day,t.id"):
        w.writerow([r["day"], _safe(r["title"]), st[r["status"]], CATS_AR.get(r["category"], ""), _safe(r["goal"])])
    return Response("\ufeff" + out.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="tltd-export.csv"'})

@app.post("/api/wipe")
@auth
def wipe():
    if body().get("confirm") != "حذف": abort(400)
    db().execute("delete from tasks"); db().execute("delete from habits"); db().execute("delete from notes"); db().execute("delete from goals"); db().commit(); return "", 204

@app.get("/api/habits")
@auth
def habits_list():
    rows = db().execute("select * from habits order by id").fetchall()
    return jsonify([dict(id=h["id"], title=h["title"], category=h["category"], days=h["days"], streak=streak(h)) for h in rows])

@app.post("/api/habits")
@auth
def habits_add():
    b = body(); title = str(b.get("title", "")).strip()[:100]; days = str(b.get("days", "")); cat = b.get("category", "other")
    if not title or cat not in CATS or not days or not set(days) <= set("0123456"): abort(400)
    days = "".join(sorted(set(days)))
    cur = db().execute("insert into habits(title,category,days,start) values(?,?,?,?)", (title, cat, days, today().isoformat()))
    db().commit(); return jsonify(id=cur.lastrowid), 201

@app.delete("/api/habits/<int:i>")
@auth
def habits_del(i):
    db().execute("delete from habits where id=?", (i,)); db().commit(); return "", 204

@app.post("/api/password")
@auth
def change_password():
    b = body(); ip = request.remote_addr
    if limited(ip): abort(429)
    u = db().execute("select * from users where id=?", (session["u"],)).fetchone()
    if not check_password_hash(u["pw"], str(b.get("current", ""))):
        FAILS.setdefault(ip, []).append(time.time()); abort(403)
    new = str(b.get("new", ""))
    if len(new) < 10: abort(400)
    db().execute("update users set pw=? where id=?", (generate_password_hash(new), u["id"])); db().commit()
    return "", 204

@app.get("/api/notes")
@auth
def notes_list():
    m = request.args.get("month", "")
    if not re.fullmatch(r"\d{4}-\d{2}", m): abort(400)
    rows = db().execute("select day,body from notes where day like ?", (m + "-%",)).fetchall()
    return jsonify({r["day"]: r["body"] for r in rows})

@app.put("/api/notes/<day>")
@auth
def notes_set(day):
    day = day_of(day); text = str(body().get("text", "")).strip()[:2000]
    if text: db().execute("insert into notes(day,body) values(?,?) on conflict(day) do update set body=excluded.body", (day, text))
    else: db().execute("delete from notes where day=?", (day,))
    db().commit(); return "", 204


# ---------------- الإشعارات (Web Push) ----------------
def push_ready(): return bool(VAPID_PUBLIC and VAPID_PRIVATE_FILE and os.path.exists(VAPID_PRIVATE_FILE))

def get_settings():
    s = {r["k"]: r["v"] for r in db().execute("select k,v from settings")}
    return {"push_goals": s.get("push_goals", "1") == "1", "push_evening": s.get("push_evening", "0") == "1",
            "evening_time": s.get("evening_time", "21:00"), "rest_from": s.get("rest_from", ""), "rest_to": s.get("rest_to", "")}

def deliver(sub, text, url="/"):
    """يرسل إشعارًا واحدًا. يُرجع False إذا انتهى الاشتراك."""
    from pywebpush import webpush, WebPushException
    try:
        webpush({"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
                data=json.dumps({"title": "TLTD", "body": text, "url": url}, ensure_ascii=False),
                vapid_private_key=VAPID_PRIVATE_FILE, vapid_claims={"sub": VAPID_SUBJECT}, timeout=10)
        return True
    except WebPushException as e:
        if getattr(e.response, "status_code", None) in (404, 410): return False
        raise

DELIVER = deliver   # قابلة للاستبدال في الاختبارات

def notify(text, url="/"):
    n = 0
    for s in db().execute("select * from push_subs").fetchall():
        try: ok = DELIVER(s, text, url)
        except Exception: continue
        if ok: n += 1
        else: db().execute("delete from push_subs where endpoint=?", (s["endpoint"],))
    db().commit(); return n

def logged(kind, ref, period):
    return db().execute("select 1 from push_log where kind=? and ref=? and period=?", (kind, ref, period)).fetchone() is not None

def log(kind, ref, period):
    db().execute("insert or ignore into push_log values(?,?,?)", (kind, ref, period)); db().commit()

def push_check(now=None):
    """تُستدعى كل 15 دقيقة. تُرجع نصوص الإشعارات التي أُرسلت."""
    now = now or dt.datetime.now(TZ); t = now.date(); st = get_settings(); sent = []
    if st["rest_from"] and st["rest_to"] and st["rest_from"] <= t.isoformat() <= st["rest_to"]: return sent   # وضع الراحة
    if not 9 <= now.hour < 23 or not db().execute("select 1 from push_subs").fetchone(): return sent
    idx = (t.weekday() + 2) % 7; ws = wstart(t)
    if st["push_goals"] and (idx > 2 or (idx == 2 and now.hour >= 18)):     # بعد انتهاء يوم الاثنين
        rows = db().execute("""select g.id,g.created,(select count(distinct day) from tasks where goal_id=g.id and status='d' and day between ? and ?) as done
            from goals g""", (ws.isoformat(), (ws + dt.timedelta(days=6)).isoformat())).fetchall()
        late = [g for g in rows if g["done"] == 0 and g["created"] <= (ws + dt.timedelta(days=2)).isoformat()
                and not logged("goal", str(g["id"]), ws.isoformat())]
        msg = "الأسبوع يقترب من نهايته، ولم يتقدّم أحد الأهداف بعد."
        if late and notify(msg, "/"):
            for g in late: log("goal", str(g["id"]), ws.isoformat())
            sent.append(msg)
    if st["push_evening"] and now.strftime("%H:%M") >= st["evening_time"] and not logged("evening", "", t.isoformat()):
        materialize(t.isoformat()[:7])
        pend = db().execute("select count(*) c from tasks where day=? and status='p'", (t.isoformat(),)).fetchone()["c"]
        msg = "هناك مهام لم تُحسَم بعد اليوم."
        if pend and notify(msg, "/"):
            log("evening", "", t.isoformat()); sent.append(msg)
    return sent

@app.cli.command("push-check")
def push_check_cmd():
    click.echo("أُرسل %d إشعار" % len(push_check()))

@app.cli.command("vapid-gen")
@click.option("--out", default="vapid_private.pem", help="مسار حفظ المفتاح الخاص")
def vapid_gen(out):
    import base64
    from py_vapid import Vapid
    from cryptography.hazmat.primitives import serialization
    v = Vapid(); v.generate_keys()
    pub = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f: f.write(v.private_pem())
    click.echo("تُضاف إلى /etc/tltd.env:\nVAPID_PUBLIC=" + base64.urlsafe_b64encode(pub).rstrip(b"=").decode() + "\nVAPID_PRIVATE_FILE=" + os.path.abspath(out))

@app.get("/api/push/key")
@auth
def push_key():
    if not push_ready(): abort(404)
    return jsonify(key=VAPID_PUBLIC)

@app.post("/api/push/subscribe")
@auth
def push_subscribe():
    b = body(); k = b.get("keys") or {}; ep = str(b.get("endpoint", ""))
    if not ep.startswith("https://") or len(ep) > 600 or not all(isinstance(k.get(x), str) and 0 < len(k[x]) < 200 for x in ("p256dh", "auth")): abort(400)
    db().execute("insert or replace into push_subs(endpoint,p256dh,auth,created) values(?,?,?,?)", (ep, k["p256dh"], k["auth"], today().isoformat()))
    db().commit(); return "", 204

@app.post("/api/push/unsubscribe")
@auth
def push_unsubscribe():
    db().execute("delete from push_subs where endpoint=?", (str(body().get("endpoint", "")),)); db().commit(); return "", 204

@app.post("/api/push/test")
@auth
def push_test():
    if not push_ready(): abort(503)
    if not notify("هذا إشعار تجريبي من TLTD."): abort(409)
    return "", 204

@app.get("/api/settings")
@auth
def settings_get():
    return jsonify(dict(get_settings(), push_ready=push_ready()))

@app.put("/api/settings")
@auth
def settings_put():
    b = body(); new = get_settings()
    for k in ("push_goals", "push_evening"):
        if k in b: new[k] = bool(b[k])
    if "evening_time" in b:
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(b["evening_time"])): abort(400)
        new["evening_time"] = b["evening_time"]
    for k in ("rest_from", "rest_to"):
        if k in b: new[k] = day_of(str(b[k])) if b[k] else ""
    if new["rest_from"] and new["rest_to"] and new["rest_from"] > new["rest_to"]: abort(400)
    for k, v in new.items():
        db().execute("insert or replace into settings(k,v) values(?,?)", (k, ("1" if v else "0") if isinstance(v, bool) else v))
    db().commit(); return "", 204
