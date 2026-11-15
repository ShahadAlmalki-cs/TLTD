import datetime as dt, os, tempfile, unittest
os.environ.update(SECRET_KEY="t" * 32, INSECURE_DEV="1", DB_PATH=os.path.join(tempfile.mkdtemp(), "t.db"))
import app as A
from werkzeug.security import generate_password_hash as H


class Smoke(unittest.TestCase):
    def setUp(self):
        self.c = A.app.test_client()
        with A.app.app_context():
            for t in ("tasks", "habits", "notes", "goals", "users", "push_subs", "push_log", "settings"):
                A.db().execute("delete from " + t)
            A.db().execute("insert into users(name,username,pw,rec) values('سارة','s',?,?)", (H("a" * 10), H("ABCD")))
            A.db().commit()

    def login(self):
        self.c.get("/login")
        with self.c.session_transaction() as s: tok = s["csrf"]
        r = self.c.post("/login", data={"username": "s", "password": "a" * 10, "csrf": tok})
        self.assertEqual(r.status_code, 302)
        with self.c.session_transaction() as s: return s["csrf"]

    def test_requires_login(self):
        self.assertEqual(self.c.get("/api/goals").status_code, 401)

    def test_wrong_password(self):
        self.c.get("/login")
        with self.c.session_transaction() as s: tok = s["csrf"]
        r = self.c.post("/login", data={"username": "s", "password": "x", "csrf": tok})
        self.assertEqual(r.status_code, 200)

    def test_csrf_blocks(self):
        self.login()
        self.assertEqual(self.c.post("/api/tasks", json={"day": "2026-10-17", "title": "x"}).status_code, 400)

    def test_flow(self):
        h = {"X-CSRF": self.login()}
        g = self.c.post("/api/goals", json={"title": "رياضة", "target": 3}, headers=h).get_json()["id"]
        i = self.c.post("/api/tasks", json={"day": A.today().isoformat(), "title": "مشي", "goal_id": g}, headers=h).get_json()["id"]
        self.assertEqual(self.c.patch("/api/tasks/%d" % i, json={"status": "d"}, headers=h).status_code, 204)
        self.assertEqual(self.c.get("/api/goals").get_json()["goals"][0]["done"], 1)
        self.assertEqual(self.c.patch("/api/tasks/%d" % i, json={"status": "z"}, headers=h).status_code, 400)
        self.assertEqual(self.c.post("/api/tasks", json={"day": "2026-13-45", "title": "x"}, headers=h).status_code, 400)

    def test_category_and_postpone(self):
        h = {"X-CSRF": self.login()}
        self.assertEqual(self.c.post("/api/tasks", json={"day": "2026-10-17", "title": "x", "category": "zzz"}, headers=h).status_code, 400)
        i = self.c.post("/api/tasks", json={"day": "2026-10-17", "title": "x", "category": "work"}, headers=h).get_json()["id"]
        self.assertEqual(self.c.patch("/api/tasks/%d" % i, json={"day": "2026-10-18", "status": "p"}, headers=h).status_code, 204)
        t = self.c.get("/api/tasks?month=2026-10").get_json()[0]
        self.assertEqual((t["day"], t["category"]), ("2026-10-18", "work"))
        self.assertEqual(self.c.patch("/api/tasks/%d" % i, json={}, headers=h).status_code, 400)

    def test_export_and_wipe(self):
        h = {"X-CSRF": self.login()}
        self.c.post("/api/tasks", json={"day": "2026-10-17", "title": "=cmd()"}, headers=h)
        self.assertIn("'=cmd()", self.c.get("/api/export.csv").get_data(as_text=True))
        self.assertEqual(self.c.post("/api/wipe", json={"confirm": "no"}, headers=h).status_code, 400)
        self.assertEqual(self.c.post("/api/wipe", json={"confirm": "حذف"}, headers=h).status_code, 204)
        self.assertEqual(self.c.get("/api/tasks?month=2026-10").get_json(), [])

    def test_habit_and_password(self):
        h = {"X-CSRF": self.login()}; mo = A.today().isoformat()[:7]
        self.assertEqual(self.c.post("/api/habits", json={"title": "ماء", "days": "9"}, headers=h).status_code, 400)
        self.assertEqual(self.c.post("/api/habits", json={"title": "ماء", "days": "0123456"}, headers=h).status_code, 201)
        ts = self.c.get("/api/tasks?month=" + mo).get_json()
        self.assertEqual(len(ts), 1)
        self.c.patch("/api/tasks/%d" % ts[0]["id"], json={"status": "d"}, headers=h)
        self.assertEqual(self.c.get("/api/habits").get_json()[0]["streak"], 1)
        self.assertEqual(len(self.c.get("/api/tasks?month=" + mo).get_json()), 1)
        self.assertEqual(self.c.post("/api/password", json={"current": "bad", "new": "b" * 10}, headers=h).status_code, 403)
        self.assertEqual(self.c.post("/api/password", json={"current": "a" * 10, "new": "short"}, headers=h).status_code, 400)
        self.assertEqual(self.c.post("/api/password", json={"current": "a" * 10, "new": "b" * 10}, headers=h).status_code, 204)

    def test_notes_and_goal_category(self):
        h = {"X-CSRF": self.login()}
        self.assertEqual(self.c.put("/api/notes/2026-10-17", json={"text": "ملاحظة"}, headers=h).status_code, 204)
        self.assertEqual(self.c.get("/api/notes?month=2026-10").get_json(), {"2026-10-17": "ملاحظة"})
        self.c.put("/api/notes/2026-10-17", json={"text": ""}, headers=h)
        self.assertEqual(self.c.get("/api/notes?month=2026-10").get_json(), {})
        self.assertEqual(self.c.put("/api/notes/bad", json={"text": "x"}, headers=h).status_code, 400)
        self.assertEqual(self.c.put("/api/notes/2026-10-17", json={"text": "x"}).status_code, 400)
        self.assertEqual(self.c.post("/api/goals", json={"title": "ز", "target": 2, "category": "zzz"}, headers=h).status_code, 400)
        self.c.post("/api/goals", json={"title": "ز", "target": 2, "category": "study"}, headers=h)
        self.assertEqual(self.c.get("/api/goals").get_json()["goals"][0]["category"], "study")

    def push_setup(self):
        h = {"X-CSRF": self.login()}
        self.assertEqual(self.c.post("/api/push/subscribe", json={"endpoint": "https://push.example/1", "keys": {"p256dh": "a", "auth": "b"}}, headers=h).status_code, 204)
        self.sent = []; A.DELIVER = lambda sub, text, url="/": self.sent.append(text) or True
        return h

    def test_push_validation(self):
        h = {"X-CSRF": self.login()}
        self.assertEqual(self.c.put("/api/settings", json={"evening_time": "25:00"}, headers=h).status_code, 400)
        self.assertEqual(self.c.put("/api/settings", json={"rest_from": "2026-10-20", "rest_to": "2026-10-10"}, headers=h).status_code, 400)
        self.assertEqual(self.c.post("/api/push/subscribe", json={"endpoint": "http://x", "keys": {"p256dh": "a", "auth": "b"}}, headers=h).status_code, 400)
        self.assertEqual(self.c.get("/api/settings").get_json()["push_goals"], True)

    def test_push_goal_rule_and_rest_mode(self):
        h = self.push_setup(); tz = A.TZ
        with A.app.app_context():
            A.db().execute("insert into goals(title,target) values('رياضة',3)"); A.db().commit()
        sat, mon_noon, mon_eve, tue = (dt.datetime(2026, 10, d, hh, tzinfo=tz) for d, hh in ((17, 12), (19, 12), (19, 19), (20, 12)))
        self.c.put("/api/settings", json={"rest_from": "2026-10-20", "rest_to": "2026-10-22"}, headers=h)
        with A.app.app_context():
            self.assertEqual(A.push_check(tue), [])            # وضع الراحة
        self.c.put("/api/settings", json={"rest_from": "", "rest_to": ""}, headers=h)
        with A.app.app_context():
            self.assertEqual(A.push_check(sat), [])
            self.assertEqual(A.push_check(mon_noon), [])       # قبل مساء الاثنين
            self.assertEqual(len(A.push_check(mon_eve)), 1)
            self.assertEqual(A.push_check(tue), [])            # لا تكرار في الأسبوع نفسه

    def test_push_progress_suppresses_alert_and_evening(self):
        h = self.push_setup(); tz = A.TZ
        with A.app.app_context():
            A.db().execute("insert into goals(title,target) values('قراءة',3)"); A.db().commit()
        gid = self.c.get("/api/goals").get_json()["goals"][0]["id"]
        i = self.c.post("/api/tasks", json={"day": "2026-10-17", "title": "x", "goal_id": gid}, headers=h).get_json()["id"]
        self.c.patch("/api/tasks/%d" % i, json={"status": "d"}, headers=h)
        self.c.post("/api/tasks", json={"day": "2026-10-20", "title": "y"}, headers=h)
        self.c.put("/api/settings", json={"push_evening": True, "evening_time": "20:00"}, headers=h)
        with A.app.app_context():
            self.assertEqual(A.push_check(dt.datetime(2026, 10, 20, 12, tzinfo=tz)), [])       # الهدف تقدّم، ولا تذكير قبل الثامنة
            out = A.push_check(dt.datetime(2026, 10, 20, 21, tzinfo=tz))
            self.assertEqual(out, ["هناك مهام لم تُحسَم بعد اليوم."])
            self.assertEqual(A.push_check(dt.datetime(2026, 10, 20, 22, tzinfo=tz)), [])

    def test_edit_task_title_and_category(self):
        h = {"X-CSRF": self.login()}
        i = self.c.post("/api/tasks", json={"day": "2026-10-17", "title": "قديم"}, headers=h).get_json()["id"]
        self.assertEqual(self.c.patch("/api/tasks/%d" % i, json={"title": "جديد", "category": "study"}, headers=h).status_code, 204)
        t = self.c.get("/api/tasks?month=2026-10").get_json()[0]
        self.assertEqual((t["title"], t["category"]), ("جديد", "study"))
        self.assertEqual(self.c.patch("/api/tasks/%d" % i, json={"title": "  "}, headers=h).status_code, 400)
        self.assertEqual(self.c.patch("/api/tasks/%d" % i, json={"category": "zzz"}, headers=h).status_code, 400)


if __name__ == "__main__":
    unittest.main()
