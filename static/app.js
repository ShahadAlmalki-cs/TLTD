(function () {
'use strict';
var CS = document.querySelector('meta[name=csrf]').content;
var NS = 'http://www.w3.org/2000/svg';
var REDUCED = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
var DN = ['سبت', 'أحد', 'اثنين', 'ثلاثاء', 'أربعاء', 'خميس', 'جمعة'];
var DF = ['السبت', 'الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة'];
var CATS = {health: 'الصحة', personal: 'شخصي', work: 'عمل', study: 'دراسة', home: 'المنزل', other: 'أخرى'};
var VIEWS = ['home', 'tasks', 'habits', 'goals', 'calendar', 'reports', 'notes', 'settings'];
var MOOD = {happy: 'أُنجزت مهام اليوم كلها.', curious: 'يوم هادئ، ولا مهام فيه بعد.', sleepy: 'بعض المهام بانتظار الحسم.', tired: 'يوم متفاوت، وهذا لا بأس به.',
  oops: 'لم تُنجَز مهام هذا اليوم. وغدًا فرصة جديدة.', excited: 'اكتمل هدف هذا الأسبوع.'};
var HINTS = ['أسبوع جديد، فرصة جديدة.', 'خطوة صغيرة اليوم تكفي.', 'البدء بأسهل مهمة يكفي.', 'كل ما يُنجَز يُحتسب.', 'الراحة جزء من الخطة.', 'يومٌ على مهل، وهذا جميل.', 'لا بأس بأن يكون اليوم هادئًا.'];
var now0 = new Date(), TD = '', LIM = '';
var S = {y: now0.getFullYear(), m: now0.getMonth(), sel: null, tasks: [], near: [], goals: [], habits: [], notes: {}, set: null, idx: 0, gf: 'all', tf: 'today', stag: true, noteDay: null};
var MF = new Intl.DateTimeFormat('ar-u-ca-gregory-nu-arab', {month: 'long', year: 'numeric'});
var DFMT = new Intl.DateTimeFormat('ar-u-ca-gregory-nu-arab', {day: 'numeric', month: 'long'});
var FULL = new Intl.DateTimeFormat('ar-u-ca-gregory-nu-arab', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'});

/* ---------- أدوات ---------- */
function $(i) { return document.getElementById(i); }
function $$(q) { return Array.prototype.slice.call(document.querySelectorAll(q)); }
function ar(n) { return String(n).replace(/\d/g, function (d) { return '٠١٢٣٤٥٦٧٨٩'[d]; }); }
function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
function p2(n) { return (n < 10 ? '0' : '') + n; }
function iso(d) { return d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()); }
function ymKey(y, m) { return y + '-' + p2(m + 1); }
function key(d) { return ymKey(S.y, S.m) + '-' + p2(d); }
function dOf(s) { return new Date(s + 'T12:00:00'); }
function nextDay(s) { var d = dOf(s); d.setDate(d.getDate() + 1); return iso(d); }
function lead() { return (new Date(S.y, S.m, 1).getDay() + 1) % 7; }
function icon(n) { var s = document.createElementNS(NS, 'svg'), u = document.createElementNS(NS, 'use'); s.setAttribute('class', 'i'); s.setAttribute('aria-hidden', 'true'); u.setAttribute('href', '#i-' + n); s.appendChild(u); return s; }
function mascot(k) { return (window.TLTD_IMG || {})[k] || '/static/img/mascot-' + k + '.svg'; }
var tt;
function toast(m) { var t = $('toast'); t.textContent = m; t.hidden = false; clearTimeout(tt); tt = setTimeout(function () { t.hidden = true; }, 2600); }
function fail(m) { var e = $('err'); e.textContent = m; e.hidden = false; }
function api(m, u, b) {
  return fetch(u, {method: m, credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRF': CS}, body: b ? JSON.stringify(b) : undefined}).then(function (r) {
    if (r.status === 401) { location.href = '/login'; throw 0; }
    if (!r.ok) throw r.status;
    return r.status === 204 ? null : r.json();
  });
}
function tally(list) { var c = {d: 0, x: 0, p: 0, n: 0}; list.forEach(function (t) { c[t.status]++; c.n++; }); return c; }
function todayTasks() { return S.near.filter(function (t) { return t.day === TD; }); }
function todayMood() {
  var c = tally(todayTasks());
  if (S.goals.some(function (g) { return g.done >= g.target; })) return 'excited';
  return !c.n ? 'curious' : c.p ? 'sleepy' : !c.x ? 'happy' : !c.d ? 'oops' : 'tired';
}
function byDay() {
  var o = {};
  S.tasks.forEach(function (t) { var d = +t.day.slice(8), c = o[d] = o[d] || {d: 0, x: 0, p: 0, n: 0, l: []}; c[t.status]++; c.n++; c.l.push(t); });
  return o;
}
function kind(c) { if (!c || !c.n || c.p) return ''; if (!c.x) return 'g'; if (!c.d) return 'pk'; return 'bl'; }
function empty(mood, text) {
  var d = el('div', 'empty'), i = el('img'); i.src = mascot(mood); i.alt = ''; i.width = 72; i.height = 72;
  d.appendChild(i); d.appendChild(el('p', '', text)); return d;
}

/* ---------- تحميل البيانات ---------- */
function load() {
  var t0 = new Date(), t1 = new Date(); t1.setDate(t1.getDate() + 14); TD = iso(t0); LIM = iso(t1);
  var mk = ymKey(S.y, S.m), months = [ymKey(t0.getFullYear(), t0.getMonth())], m1 = ymKey(t1.getFullYear(), t1.getMonth());
  if (m1 !== months[0]) months.push(m1);
  var need = [mk].concat(months.filter(function (m) { return m !== mk; }));
  return Promise.all(need.map(function (m) { return api('GET', '/api/tasks?month=' + m); })).then(function (res) {
    var by = {}; need.forEach(function (m, i) { by[m] = res[i]; });
    S.tasks = by[mk]; S.near = [];
    months.forEach(function (m) { (by[m] || []).forEach(function (t) { if (t.day >= TD && t.day <= LIM) S.near.push(t); }); });
    return Promise.all([api('GET', '/api/goals'), api('GET', '/api/habits'), api('GET', '/api/notes?month=' + mk)]);
  }).then(function (r) {
    S.goals = r[0].goals; S.idx = r[0].idx; S.habits = r[1]; S.notes = r[2]; $('err').hidden = true;
    var dim = new Date(S.y, S.m + 1, 0).getDate();
    if (!S.sel || S.sel > dim) S.sel = ymKey(S.y, S.m) === TD.slice(0, 7) ? +TD.slice(8) : 1;
    renderAll();
  }).catch(function (e) { if (e !== 0) fail('تعذّر الاتصال بالخادم. يُرجى التحقق من الشبكة ثم إعادة المحاولة.'); });
}
function setSt(t, s) { return api('PATCH', '/api/tasks/' + t.id, {status: s}).then(load).catch(function () { fail('تعذّر تحديث المهمة.'); }); }
function delTask(t) { return api('DELETE', '/api/tasks/' + t.id).then(function () { toast('حُذفت المهمة.'); return load(); }).catch(function () { fail('تعذّر حذف المهمة.'); }); }

/* ---------- عناصر مشتركة ---------- */
function closeMenus() { $$('.menu').forEach(function (m) { m.hidden = true; }); $$('.menu-btn').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); }); }
function taskMenu(t) {
  var w = el('div', 'menu-wrap'), b = el('button', 'icon-btn sm menu-btn'), m = el('div', 'menu'), items = [];
  b.type = 'button'; b.setAttribute('aria-haspopup', 'true'); b.setAttribute('aria-expanded', 'false'); b.setAttribute('aria-label', 'خيارات المهمة: ' + t.title); b.appendChild(icon('more'));
  m.hidden = true; m.setAttribute('role', 'menu');
  items.push(['تعديل', function () { openDlg('task', {edit: t}); }]);
  items.push([t.status === 'x' ? 'استعادة المهمة' : 'إلغاء المهمة', function () { setSt(t, t.status === 'x' ? 'p' : 'x'); }]);
  if (t.status !== 'd') items.push(['ترحيل إلى اليوم التالي', function () { api('PATCH', '/api/tasks/' + t.id, {day: nextDay(t.day), status: 'p'}).then(function () { toast('رُحّلت المهمة.'); return load(); }); }]);
  items.push(['حذف', function () { delTask(t); }, 'danger']);
  items.forEach(function (it) { var x = el('button', it[2] || '', it[0]); x.type = 'button'; x.setAttribute('role', 'menuitem'); x.onclick = function () { closeMenus(); it[1](); }; m.appendChild(x); });
  b.onclick = function (e) { e.stopPropagation(); var open = m.hidden; closeMenus(); m.hidden = !open; b.setAttribute('aria-expanded', String(open)); };
  w.appendChild(b); w.appendChild(m); return w;
}
function taskRow(t, compact) {
  var li = el('li', 'trow s-' + t.status), ck = el('button', 'check'), b = el('div', 'tbody'), tg = el('em', 'tag', CATS[t.category] || CATS.other);
  ck.type = 'button'; ck.setAttribute('role', 'checkbox'); ck.setAttribute('aria-checked', String(t.status === 'd')); ck.setAttribute('aria-label', 'إنجاز: ' + t.title); ck.appendChild(icon('check'));
  ck.onclick = function () { setSt(t, t.status === 'd' ? 'p' : 'd'); };
  tg.dataset.cat = t.category; b.appendChild(el('span', 'ttitle', t.title)); b.appendChild(tg);
  if (t.habit_id) b.appendChild(el('em', 'tag tag-h', 'عادة'));
  li.appendChild(ck); li.appendChild(b); if (!compact) li.appendChild(taskMenu(t));
  return li;
}
function taskList(list, compact) { var u = el('ul', 'list'); list.forEach(function (t) { u.appendChild(taskRow(t, compact)); }); return u; }
function habitToday(h) { return S.near.filter(function (t) { return t.habit_id === h.id && t.day === TD; })[0]; }

/* ---------- الرئيسية ---------- */
function greet() {
  $('hi').textContent = (new Date().getHours() < 12 ? 'صباح الخير' : 'مساء الخير') + '، ' + $('main').dataset.name;
  $('hint').textContent = HINTS[(new Date().getDay() + 1) % 7];
  $('dchip').textContent = FULL.format(new Date());
}
function renderHome() {
  var md = todayMood(), tl = todayTasks(), c = tally(tl), L = $('hc-tasks');
  greet();
  $('hmood').src = mascot(md); $('hm').textContent = MOOD[md];
  $('hc-tasks-n').textContent = ar(c.d) + ' / ' + ar(c.n); L.textContent = '';
  if (!tl.length) L.appendChild(empty('curious', 'لا مهام لليوم بعد.')); else L.appendChild(taskList(tl.slice(0, 5), true));
  var G = $('hc-goals'), sd = 0, st = 0; G.textContent = '';
  S.goals.forEach(function (g) { sd += Math.min(g.done, g.target); st += g.target; });
  $('hc-goals-n').textContent = ar(sd) + ' / ' + ar(st);
  if (!S.goals.length) G.appendChild(empty('sleepy', 'لا أهداف بعد.'));
  else {
    var pg = el('div', 'progress'), pb = el('b'); pb.style.width = (st ? sd / st * 100 : 0) + '%'; pg.appendChild(pb); G.appendChild(pg);
    S.goals.slice(0, 4).forEach(function (g) {
      var r = el('div', 'mini-row'), t = el('span', 't'), ok = g.done >= g.target, ic = icon(ok ? 'check' : 'goals'); ic.setAttribute('class', 'i ' + (ok ? 'dot-ok' : 'dot-off'));
      t.appendChild(ic); t.appendChild(el('span', '', g.title)); r.appendChild(t); r.appendChild(el('span', 'count', ar(g.done) + '/' + ar(g.target))); G.appendChild(r);
    });
  }
  var H = $('hc-habits'), best = 0; H.textContent = '';
  S.habits.forEach(function (x) { best = Math.max(best, x.streak); });
  $('hc-habits-n').textContent = best ? 'أطول سلسلة: ' + ar(best) : '';
  if (!S.habits.length) H.appendChild(empty('happy', 'لا عادات بعد.'));
  else S.habits.slice(0, 5).forEach(function (x) { H.appendChild(habitLine(x)); });
}
function habitLine(h) {
  var r = el('div', 'mini-row'), t = el('span', 't'), ht = habitToday(h), ck = el('button', 'check');
  ck.type = 'button'; ck.appendChild(icon('check'));
  if (ht) { ck.setAttribute('role', 'checkbox'); ck.setAttribute('aria-checked', String(ht.status === 'd')); ck.setAttribute('aria-label', 'إنجاز اليوم: ' + h.title); ck.onclick = function () { setSt(ht, ht.status === 'd' ? 'p' : 'd'); }; if (ht.status === 'd') r.className += ' s-d'; }
  else { ck.disabled = true; ck.setAttribute('aria-label', h.title + ': ليست اليوم'); }
  t.appendChild(ck); t.appendChild(el('span', '', h.title)); r.appendChild(t); r.appendChild(el('span', 'streak', h.streak ? streakWord(h.streak) : (ht ? '' : 'ليست اليوم')));
  if (ht && ht.status === 'd') r.classList.add('s-d');
  return r;
}

/* ---------- المهام ---------- */
function renderTasks() {
  var L = $('tlist'); L.textContent = '';
  $$('[data-tf]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.tf === S.tf)); });
  if (S.tf === 'today') {
    var tl = todayTasks();
    if (!tl.length) L.appendChild(empty('curious', 'لا مهام لليوم. يوم هادئ، أو يمكن إضافة مهمة.')); else L.appendChild(taskList(tl));
    return;
  }
  var up = S.near.filter(function (t) { return t.day > TD; });
  if (!up.length) { L.appendChild(empty('sleepy', 'لا مهام قادمة خلال الأيام القليلة المقبلة.')); return; }
  var u = el('ul', 'list'), last = '';
  up.sort(function (a, b) { return a.day < b.day ? -1 : a.day > b.day ? 1 : a.id - b.id; });
  up.forEach(function (t) {
    if (t.day !== last) { last = t.day; u.appendChild(el('li', 'dayhead', FULL.format(dOf(t.day)))); }
    u.appendChild(taskRow(t));
  });
  L.appendChild(u);
}

/* ---------- العادات ---------- */
function renderHabits() {
  var L = $('hlist'); L.textContent = '';
  if (!S.habits.length) { var c0 = el('div', 'card'); c0.appendChild(empty('happy', 'لا عادات بعد. يمكن البدء بعادة صغيرة.')); L.appendChild(c0); return; }
  S.habits.forEach(function (h) {
    var c = el('div', 'card'), r = el('div', 'card-head'), tg = el('em', 'tag', CATS[h.category] || CATS.other), rm = el('button', 'btn btn-quiet', 'حذف العادة');
    tg.dataset.cat = h.category; r.appendChild(el('h3', '', h.title)); r.appendChild(tg); c.appendChild(r);
    c.appendChild(habitLine(h));
    c.appendChild(el('p', 'sub', h.days.length === 7 ? 'يوميًا' : h.days.split('').map(function (i) { return DF[+i]; }).join('، ')));
    rm.type = 'button'; rm.onclick = function () { api('DELETE', '/api/habits/' + h.id).then(function () { toast('حُذفت العادة.'); return load(); }); };
    c.appendChild(rm); L.appendChild(c);
  });
}

/* ---------- الأهداف ---------- */
function renderGoals() {
  var T = $('gtabs'), L = $('glist'); T.textContent = ''; L.textContent = '';
  [['all', 'الكل']].concat(Object.keys(CATS).map(function (k) { return [k, CATS[k]]; })).forEach(function (p) {
    var b = el('button', 'chipb', p[1]); b.type = 'button'; b.setAttribute('aria-pressed', String(S.gf === p[0])); b.onclick = function () { S.gf = p[0]; renderGoals(); }; T.appendChild(b);
  });
  var gl = S.goals.filter(function (g) { return S.gf === 'all' || g.category === S.gf; });
  if (!gl.length) { var c0 = el('div', 'card'); c0.appendChild(empty('sleepy', S.goals.length ? 'لا أهداف في هذه الفئة.' : 'لا أهداف بعد. يمكن إضافة الهدف الأول.')); L.appendChild(c0); return; }
  gl.forEach(function (g) {
    var c = el('div', 'card'), r = el('div', 'card-head'), tg = el('em', 'tag', CATS[g.category] || CATS.other), pg = el('div', 'progress'), pb = el('b'), rm = el('button', 'btn btn-quiet', 'حذف الهدف');
    tg.dataset.cat = g.category; r.appendChild(el('h3', '', g.title)); r.appendChild(el('span', 'count', ar(g.done) + ' من ' + ar(g.target))); c.appendChild(r);
    pb.style.width = Math.min(100, g.done / g.target * 100) + '%'; pg.appendChild(pb); c.appendChild(pg); c.appendChild(tg);
    if (S.idx >= 2 && g.done === 0) c.appendChild(el('p', 'warn', 'اقترب الأسبوع من نهايته، ولم يتقدّم هذا الهدف بعد.'));
    rm.type = 'button'; rm.onclick = function () { api('DELETE', '/api/goals/' + g.id).then(function () { toast('حُذف الهدف.'); return load(); }); };
    c.appendChild(rm); L.appendChild(c);
  });
}

/* ---------- التقويم ---------- */
function renderCal() {
  var D = byDay(), cal = $('cal'), dim = new Date(S.y, S.m + 1, 0).getDate(); cal.textContent = '';
  DN.forEach(function (n) { cal.appendChild(el('div', 'cal-h', n)); });
  for (var i = 0; i < lead(); i++) cal.appendChild(el('div', 'cell e'));
  for (var d = 1; d <= dim; d++) (function (d) {
    var c = D[d], b = el('button', 'cell ' + kind(c) + (key(d) === TD ? ' today' : '') + (d === S.sel ? ' sel' : '') + (S.notes[key(d)] ? ' hn' : ''), ar(d));
    b.type = 'button'; b.setAttribute('aria-label', FULL.format(new Date(S.y, S.m, d)) + (c ? '، ' + ar(c.n) + ' مهام' : '')); if (d === S.sel) b.setAttribute('aria-pressed', 'true');
    b.onclick = function () { S.sel = d; renderCal(); }; cal.appendChild(b);
  })(d);
  $('mt').textContent = MF.format(new Date(S.y, S.m, 1));
  if (S.stag && window.gsap && !REDUCED) gsap.from('#cal .cell:not(.e)', {opacity: 0, scale: .7, duration: .3, stagger: .01, ease: 'back.out(1.6)'});
  S.stag = false;
  var dt = new Date(S.y, S.m, S.sel), L = $('dlist'), c = D[S.sel], nl = $('dnoteline'), note = S.notes[key(S.sel)];
  $('pt').textContent = FULL.format(dt); L.textContent = '';
  if (!c) L.appendChild(empty('curious', 'لا مهام في هذا اليوم.')); else L.appendChild(taskList(c.l));
  nl.hidden = !note; nl.textContent = note || '';
}

/* ---------- الملاحظات ---------- */
function renderNotes() {
  var L = $('nlist'), days = Object.keys(S.notes).sort(); L.textContent = ''; $('nt').textContent = 'ملاحظات ' + MF.format(new Date(S.y, S.m, 1));
  if (!days.length) { L.appendChild(empty('sleepy', 'لا ملاحظات في هذا الشهر.')); return; }
  var u = el('ul', 'list');
  days.forEach(function (d) {
    var li = el('li', 'note-item'), r = el('div', 'card-head'), bt = el('div', 'btn-row'), ed = el('button', 'btn btn-outline', 'تعديل'), rm = el('button', 'btn btn-quiet', 'حذف');
    r.appendChild(el('h3', '', FULL.format(dOf(d)))); ed.type = 'button'; rm.type = 'button';
    ed.onclick = function () { openDlg('note', {day: d}); };
    rm.onclick = function () { api('PUT', '/api/notes/' + d, {text: ''}).then(function () { toast('حُذفت الملاحظة.'); return load(); }); };
    bt.appendChild(ed); bt.appendChild(rm); r.appendChild(bt); li.appendChild(r); li.appendChild(el('p', '', S.notes[d])); u.appendChild(li);
  });
  L.appendChild(u);
}

/* ---------- الحوار (إضافة وتعديل) ---------- */
var DLG = $('dlg'), dkind = null, dedit = null, TITLES = {task: 'مهمة جديدة', goal: 'هدف جديد', habit: 'عادة جديدة', note: 'ملاحظة'};
function noteText(day) { return day.slice(0, 7) === ymKey(S.y, S.m) ? Promise.resolve(S.notes[day] || '') : api('GET', '/api/notes?month=' + day.slice(0, 7)).then(function (o) { return o[day] || ''; }); }
function openDlg(kind, o) {
  o = o || {}; dkind = kind; dedit = o.edit || null; $('derr').hidden = true;
  var tokens = [kind]; if (kind === 'task' && !dedit) tokens.push('task-new');
  $('dt').textContent = dedit ? 'تعديل المهمة' : TITLES[kind];
  $$('#dform [data-for]').forEach(function (f) { f.hidden = !f.dataset.for.split(' ').some(function (k) { return tokens.indexOf(k) >= 0; }); });
  var day = o.day || (dedit ? dedit.day : TD);
  $('f-title').value = dedit ? dedit.title : ''; $('f-day').value = day; $('f-cat').value = dedit ? dedit.category : 'other'; $('f-target').value = 3; $('f-text').value = '';
  var gs = $('f-goal'); gs.textContent = ''; var o0 = el('option', '', 'بلا هدف'); o0.value = ''; gs.appendChild(o0);
  S.goals.forEach(function (g) { var q = el('option', '', g.title); q.value = g.id; gs.appendChild(q); });
  $$('#f-days input').forEach(function (c) { c.checked = true; });
  if (kind === 'note') noteText(day).then(function (t) { $('f-text').value = t; });
  DLG.showModal(); (kind === 'note' ? $('f-text') : $('f-title')).focus();
}
function busy(on) { var b = $('dsave'); b.disabled = on; b.setAttribute('aria-busy', String(on)); }
function derr(m) { var e = $('derr'); e.textContent = m; e.hidden = false; }
function initDialog() {
  var cs = $('f-cat'); Object.keys(CATS).forEach(function (k) { var o = el('option', '', CATS[k]); o.value = k; cs.appendChild(o); });
  var dv = $('f-days'); DF.forEach(function (n, i) { var l = el('label', 'chip'), c = el('input'); c.type = 'checkbox'; c.value = i; c.checked = true; l.appendChild(c); l.appendChild(document.createTextNode(n)); dv.appendChild(l); });
  $('f-day').onchange = function () { if (dkind === 'note' && this.value) noteText(this.value).then(function (t) { $('f-text').value = t; }); };
  $('dx').onclick = $('dcancel').onclick = function () { DLG.close(); };
  DLG.addEventListener('click', function (e) { if (e.target === DLG) DLG.close(); });
  $('dform').onsubmit = function (e) {
    e.preventDefault();
    var title = $('f-title').value.trim(), day = $('f-day').value, cat = $('f-cat').value, p;
    if (dkind !== 'note' && !title) return derr('العنوان مطلوب.');
    if ((dkind === 'task' || dkind === 'note') && !day) return derr('التاريخ مطلوب.');
    if (dkind === 'task') p = dedit ? api('PATCH', '/api/tasks/' + dedit.id, {title: title, category: cat, day: day})
      : api('POST', '/api/tasks', {day: day, title: title, category: cat, goal_id: $('f-goal').value ? +$('f-goal').value : null});
    else if (dkind === 'goal') p = api('POST', '/api/goals', {title: title, target: +$('f-target').value, category: cat});
    else if (dkind === 'habit') {
      var days = $$('#f-days input').filter(function (c) { return c.checked; }).map(function (c) { return c.value; }).join('');
      if (!days) return derr('يلزم اختيار يوم واحد على الأقل.');
      p = api('POST', '/api/habits', {title: title, category: cat, days: days});
    } else p = api('PUT', '/api/notes/' + day, {text: $('f-text').value.trim()});
    busy(true);
    p.then(function () { DLG.close(); toast('تم الحفظ.'); return load(); }).catch(function () { derr('تعذّر الحفظ. يُرجى التحقق من البيانات وإعادة المحاولة.'); }).then(function () { busy(false); });
  };
  $$('[data-new]').forEach(function (b) { b.onclick = function () { openDlg(b.dataset.new, b.dataset.sel ? {day: key(S.sel)} : {}); }; });
  $('dnote').onclick = function () { openDlg('note', {day: key(S.sel)}); };
}

/* ---------- التقرير (رسوم وصورة محفوظة) ---------- */
function renderRep() { var D = byDay(); $('rt').textContent = 'تقرير ' + MF.format(new Date(S.y, S.m, 1)); drawRep(D); }

/* ---------- التنقل ---------- */
var lastFocus = null;
function openSide(on) {
  var s = $('side'), was = s.classList.contains('open'); s.classList.toggle('open', on); $('scrim').hidden = !on; $('more').setAttribute('aria-expanded', String(on));
  if (on) { lastFocus = document.activeElement; var a = s.querySelector('a'); if (a) a.focus(); } else if (was && lastFocus) lastFocus.focus();
}
function route() {
  var v = (location.hash || '#home').slice(1); if (VIEWS.indexOf(v) < 0) v = 'home';
  VIEWS.forEach(function (k) { $('v-' + k).classList.toggle('on', k === v); });
  $$('[data-v]').forEach(function (a) { if (a.dataset.v === v) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  openSide(false); closeMenus(); document.title = 'TLTD';
  if (window.LN) LN.scrollTo(0, {immediate: true}); else window.scrollTo(0, 0);
  if (v === 'reports') animateReport();
}
function renderAll() { renderHome(); renderTasks(); renderHabits(); renderGoals(); renderCal(); renderNotes(); renderRep(); }

/* ---------- من الإصدار السابق: الرسوم والصورة المحفوظة والإشعارات ---------- */
function svg(w, h, s) { return '<svg class="chart" viewBox="0 0 ' + w + ' ' + h + '" role="img">' + s + '</svg>'; }
function stack(items) {
  var W = 360, base = 135, top = 14, mx = 1, s = '', cl = ['fg', 'fp', 'fl'];
  items.forEach(function (i) { mx = Math.max(mx, i.v[0] + i.v[1] + i.v[2]); });
  var gap = (W - 20) / items.length, bw = Math.min(34, gap - 8);
  items.forEach(function (it, i) {
    var x = 10 + i * gap + (gap - bw) / 2, y = base;
    it.v.forEach(function (v, k) {
      if (!v) return; var h = v / mx * (base - top); y -= h;
      s += '<rect class="' + cl[k] + '" x="' + x + '" y="' + y + '" width="' + bw + '" height="' + h + '" rx="4"/>';
    });
    s += '<text x="' + (x + bw / 2) + '" y="' + (base + 18) + '" font-size="12" text-anchor="middle">' + it.l + '</text>';
  });
  return svg(W, 170, s + '<line class="ax" x1="6" x2="354" y1="' + base + '" y2="' + base + '"/>') +
    '<div class="lg"><span><i class="sw lg-g"></i>منجزة</span><span><i class="sw lg-p"></i>ملغاة</span><span><i class="sw lg-l"></i>معلّقة</span></div>';
}
function drawRep(D) {
  var Dn = 0, X = 0, days = {g: 0, bl: 0, pk: 0}, wk = {}, nd = 0;
  Object.keys(D).forEach(function (k) {
    var c = D[k], kd = kind(c); Dn += c.d; X += c.x; nd++; if (kd) days[kd]++;
    var w = Math.floor((+k - 1 + lead()) / 7); wk[w] = wk[w] || [0, 0, 0];
    wk[w][0] += c.d; wk[w][1] += c.x; wk[w][2] += c.p;
  });
  var tot = Dn + X, pc = tot ? Math.round(Dn / tot * 100) : 0;
  $('sent').textContent = Dn ? 'المهام المنجزة هذا الشهر: ' + ar(Dn) + '.' : 'لم تُنجَز مهام هذا الشهر بعد.';
  $('stats').innerHTML = '<div><strong>' + ar(nd) + '</strong>يومًا فيها مهام</div><div><strong>' + ar(Dn) +
    '</strong>مهمة منجزة</div><div><strong>' + ar(X) + '</strong>مهمة ملغاة</div>';
  var r = 52, C = 2 * Math.PI * r;
  $('donut').innerHTML = '<div class="dn">' + svg(180, 180, '<g transform="rotate(-90 90 90)"><circle class="sp" cx="90" cy="90" r="' + r +
    '" stroke-width="22"/><circle class="sg" cx="90" cy="90" r="' + r + '" stroke-width="22" stroke-dasharray="' + (tot ? C * Dn / tot : 0) + ' ' + C +
    '"/></g><text x="90" y="88" font-size="30" font-weight="700" text-anchor="middle">' + ar(pc) + '٪</text><text x="90" y="110" font-size="13" text-anchor="middle">منجز</text>') + '</div>';
  var wl = Object.keys(wk).sort(function (a, b) { return a - b; }).map(function (w) { return {l: 'أسبوع ' + ar(+w + 1), v: wk[w]}; });
  S.rep = {Dn: Dn, X: X, nd: nd, pc: pc, days: days, wk: wl};
  $('mchart').innerHTML = stack(wl);
  var rows = [['كل المهام منجزة', 'g', 'fg'], ['حالة بين ذلك', 'bl', 'fb'], ['لا مهمة منجزة', 'pk', 'fp']], mx = 1, t = '';
  rows.forEach(function (q) { mx = Math.max(mx, days[q[1]]); });
  rows.forEach(function (q, i) {
    var y = 10 + i * 40;
    t += '<text x="352" y="' + (y + 18) + '" font-size="14" text-anchor="end">' + q[0] + '</text><rect class="' + q[2] + '" x="70" y="' + y +
      '" width="' + (days[q[1]] / mx * 170) + '" height="26" rx="6"/><text x="60" y="' + (y + 19) + '" font-size="14" text-anchor="end">' + ar(days[q[1]]) + '</text>';
  });
  $('dchart').innerHTML = svg(360, 130, t);
  var cc = {}; S.tasks.forEach(function (q) { if (q.status === 'd') cc[q.category] = (cc[q.category] || 0) + 1; });
  var cr = Object.keys(cc).sort(function (p, q) { return cc[q] - cc[p]; }), cm = 1, ct = '';
  cr.forEach(function (k) { cm = Math.max(cm, cc[k]); });
  cr.forEach(function (k, i) {
    var y = 10 + i * 40;
    ct += '<text x="352" y="' + (y + 18) + '" font-size="14" text-anchor="end">' + (CATS[k] || CATS.other) + '</text><rect class="fg" x="70" y="' + y + '" width="' + (cc[k] / cm * 170) + '" height="26" rx="6"/><text x="60" y="' + (y + 19) + '" font-size="14" text-anchor="end">' + ar(cc[k]) + '</text>';
  });
  S.rep.cats = cr.map(function (k) { return [CATS[k] || CATS.other, cc[k]]; });
  $('cchart').innerHTML = cr.length ? svg(360, 20 + cr.length * 40, ct) : '<p class="sub">لا مهام منجزة بعد.</p>';
}
function saveImage() {
  var r = S.rep; if (!r) return;
  var W = 1080, H = 1740 + (r.cats && r.cats.length ? 150 + r.cats.length * 54 : 0), cv = document.createElement('canvas'); cv.width = W; cv.height = H;
  var x = cv.getContext('2d'), F = 'Tajawal, "Segoe UI", Tahoma, sans-serif', FS = 'Amiri, "Times New Roman", serif';
  var C = {bg: '#F2F0E6', card: '#FBFAF5', ink: '#2E3A34', soft: '#66736C', line: '#DCE1D2', btn: '#526A58', g: '#B8D2BC', bl: '#BFD5E3', pk: '#F0D2D4'};
  x.direction = 'rtl';
  function T(s, px, py, size, col, al, font, wt) { x.font = (wt || 400) + ' ' + size + 'px ' + (font || F); x.fillStyle = col; x.textAlign = al || 'center'; x.fillText(s, px, py); }
  function R(px, py, w, h, rad, col) {
    x.fillStyle = col; x.beginPath(); x.moveTo(px + rad, py); x.arcTo(px + w, py, px + w, py + h, rad); x.arcTo(px + w, py + h, px, py + h, rad);
    x.arcTo(px, py + h, px, py, rad); x.arcTo(px, py, px + w, py, rad); x.closePath(); x.fill();
  }
  R(0, 0, W, H, 0, C.bg);
  T('TLTD', 540, 95, 40, C.soft, 'center', FS, 700);
  T($('rt').textContent, 540, 175, 58, C.ink, 'center', FS, 700);
  T($('sent').textContent, 540, 245, 34, C.soft);
  [[r.nd, 'يومًا فيها مهام'], [r.Dn, 'مهمة منجزة'], [r.X, 'مهمة ملغاة']].forEach(function (s, i) {
    var px = W - 60 - 306 - i * 327;
    R(px, 290, 306, 170, 24, C.card); T(ar(s[0]), px + 153, 380, 66, C.ink, 'center', FS, 700); T(s[1], px + 153, 435, 28, C.soft);
  });
  R(60, 490, 960, 430, 28, C.card); T('المنجزة والملغاة', 1020, 555, 36, C.ink, 'right', FS, 700);
  x.lineWidth = 44; x.strokeStyle = r.Dn + r.X ? C.pk : C.line; x.beginPath(); x.arc(540, 735, 100, 0, 2 * Math.PI); x.stroke();
  if (r.Dn + r.X) { x.strokeStyle = C.g; x.beginPath(); x.arc(540, 735, 100, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * r.Dn / (r.Dn + r.X)); x.stroke(); }
  T(ar(r.pc) + '٪', 540, 745, 60, C.ink, 'center', FS, 700); T('منجز', 540, 785, 26, C.soft);
  R(60, 950, 960, 460, 28, C.card); T('الأسابيع', 1020, 1015, 36, C.ink, 'right', FS, 700);
  var mx = 1, n = r.wk.length, gap = 900 / Math.max(n, 1), bw = Math.min(80, gap - 20), base = 1300, cols = [C.g, C.pk, C.line];
  r.wk.forEach(function (w) { mx = Math.max(mx, w.v[0] + w.v[1] + w.v[2]); });
  r.wk.forEach(function (w, i) {
    var px = W - 90 - (i + 1) * gap + (gap - bw) / 2, y = base;
    w.v.forEach(function (v, k) { if (!v) return; var h = v / mx * 220; y -= h; R(px, y, bw, h, 10, cols[k]); });
    T(w.l, px + bw / 2, base + 40, 24, C.soft);
  });
  [['منجزة', C.g], ['ملغاة', C.pk], ['معلّقة', C.line]].forEach(function (l, i) {
    var px = 1020 - i * 190; R(px - 26, 1368, 26, 26, 6, l[1]); T(l[0], px - 36, 1390, 26, C.soft, 'right');
  });
  R(60, 1440, 960, 260, 28, C.card); T('ألوان الأيام', 1020, 1500, 36, C.ink, 'right', FS, 700);
  var dm = Math.max(1, r.days.g, r.days.bl, r.days.pk);
  [['أخضر', r.days.g, C.g], ['أزرق', r.days.bl, C.bl], ['وردي', r.days.pk, C.pk]].forEach(function (d, i) {
    var y = 1525 + i * 54, w = d[1] / dm * 520;
    T(d[0], 1020, y + 33, 28, C.ink, 'right'); if (w) R(870 - w, y, w, 38, 10, d[2]); T(ar(d[1]), 870 - w - 16, y + 31, 28, C.ink, 'right');
  });
  if (r.cats && r.cats.length) {
    var cy = 1720, cmx = Math.max.apply(null, r.cats.map(function (q) { return q[1]; }));
    R(60, cy, 960, 110 + r.cats.length * 54, 28, C.card); T('المنجز بحسب الفئة', 1020, cy + 60, 36, C.ink, 'right', FS, 700);
    r.cats.forEach(function (q, i) {
      var y = cy + 85 + i * 54, w = q[1] / cmx * 520;
      T(q[0], 1020, y + 33, 28, C.ink, 'right'); R(870 - w, y, w, 38, 10, C.g); T(ar(q[1]), 870 - w - 16, y + 31, 28, C.ink, 'right');
    });
  }
  var name = 'TLTD-' + S.y + '-' + p2(S.m + 1) + '.png';
  cv.toBlob(function (b) {
    if (!b) return;
    var f = new File([b], name, {type: 'image/png'});
    if (navigator.canShare && navigator.canShare({files: [f]})) { navigator.share({files: [f], title: 'TLTD'}).catch(function () {}); return; }
    var a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
  }, 'image/png');
}
function streakWord(n) { return n === 1 ? 'يوم واحد متتالٍ' : n === 2 ? 'يومان متتاليان' : n <= 10 ? ar(n) + ' أيام متتالية' : ar(n) + ' يومًا متتاليًا'; }
function theme(v) {
  try { if (v === 'auto') localStorage.removeItem('th'); else localStorage.setItem('th', v); } catch (e) {}
  if (v === 'auto') document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', v);
  document.querySelectorAll('[data-th]').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.th === v); });
}
function animateReport() {
  if (!window.gsap || REDUCED) return;
  document.querySelectorAll('#stats strong').forEach(function (e) {
    var v = +e.textContent.replace(/[٠-٩]/g, function (d) { return '٠١٢٣٤٥٦٧٨٩'.indexOf(d); }), o = {n: 0};
    gsap.to(o, {n: v, duration: .9, ease: 'power2.out', onUpdate: function () { e.textContent = ar(Math.round(o.n)); }});
  });
  gsap.from('#dchart rect, #cchart rect', {attr: {width: 0}, duration: .8, stagger: .08, ease: 'power3.out'});
  gsap.from('#mchart rect', {scaleY: 0, transformOrigin: '50% 100%', duration: .7, stagger: .03, ease: 'power3.out'});
}
function b64u(s) { var p = '='.repeat((4 - s.length % 4) % 4), r = atob((s + p).replace(/-/g, '+').replace(/_/g, '/')), o = new Uint8Array(r.length); for (var i = 0; i < r.length; i++) o[i] = r.charCodeAt(i); return o; }
function pushState() {
  var m = $('pst'), on = $('pon'), off = $('poff');
  function say(t) { m.textContent = t; on.disabled = true; return Promise.resolve(); }
  if (!S.set || !S.set.push_ready) return say('الإشعارات غير مضبوطة على الخادم بعد (مفاتيح VAPID).');
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return say('هذا المتصفح لا يدعم الإشعارات. على iPhone يلزم إضافة الموقع إلى الشاشة الرئيسية أولًا (iOS 16.4 فأحدث).');
  if (Notification.permission === 'denied') return say('الإشعارات محظورة لهذا الموقع في إعدادات المتصفح.');
  return navigator.serviceWorker.ready.then(function (r) { return r.pushManager.getSubscription(); }).then(function (sub) {
    m.textContent = sub ? 'الإشعارات مفعّلة على هذا الجهاز.' : 'الإشعارات غير مفعّلة على هذا الجهاز.'; on.disabled = false; on.hidden = !!sub; off.hidden = !sub;
  });
}
function loadSet() {
  return api('GET', '/api/settings').then(function (s) {
    S.set = s; $('sg').checked = s.push_goals; $('se').checked = s.push_evening; $('stime').value = s.evening_time; $('rfrom').value = s.rest_from; $('rto').value = s.rest_to;
    return pushState();
  }).catch(function () {});
}

/* ---------- الإعدادات ---------- */
function initSettings() {
  $('pon').onclick = function () {
    Notification.requestPermission().then(function (p) {
      if (p !== 'granted') return;
      return navigator.serviceWorker.ready.then(function (r) {
        return api('GET', '/api/push/key').then(function (k) { return r.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: b64u(k.key)}); });
      }).then(function (sub) { return api('POST', '/api/push/subscribe', sub.toJSON()); });
    }).then(pushState).catch(function () { $('pst').textContent = 'تعذّر تفعيل الإشعارات.'; });
  };
  $('poff').onclick = function () {
    navigator.serviceWorker.ready.then(function (r) { return r.pushManager.getSubscription(); }).then(function (sub) {
      if (!sub) return; var ep = sub.endpoint;
      return sub.unsubscribe().then(function () { return api('POST', '/api/push/unsubscribe', {endpoint: ep}); });
    }).then(pushState);
  };
  $('ssave').onclick = function () {
    api('PUT', '/api/settings', {push_goals: $('sg').checked, push_evening: $('se').checked, evening_time: $('stime').value || '21:00', rest_from: $('rfrom').value, rest_to: $('rto').value})
      .then(function () { $('smsg').textContent = 'حُفظت الإعدادات.'; }).catch(function () { $('smsg').textContent = 'تعذّر الحفظ. يُرجى التحقق من التواريخ.'; });
  };
  $('ptest').onclick = function () {
    api('POST', '/api/push/test').then(function () { $('smsg').textContent = 'أُرسل إشعار تجريبي.'; }).catch(function () { $('smsg').textContent = 'تعذّر الإرسال: يلزم تفعيل الإشعارات على هذا الجهاز أولًا.'; });
  };
  $('pf').onsubmit = function (e) {
    e.preventDefault();
    api('POST', '/api/password', {current: $('pc').value, new: $('pn').value}).then(function () { $('pc').value = ''; $('pn').value = ''; $('pmsg').textContent = 'تم تغيير كلمة المرور.'; })
      .catch(function (c) { $('pmsg').textContent = c === 403 ? 'كلمة المرور الحالية غير صحيحة.' : c === 429 ? 'محاولات كثيرة، يُرجى المحاولة بعد قليل.' : 'الجديدة 10 أحرف على الأقل.'; });
  };
  $('exp').onclick = function () {
    fetch('/api/export.csv', {credentials: 'same-origin'}).then(function (r) { if (!r.ok) throw 0; return r.blob(); }).then(function (b) {
      var a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'tltd-export.csv'; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
    }).catch(function () { fail('تعذّر تصدير البيانات.'); });
  };
  $('wf').onsubmit = function (e) {
    e.preventDefault();
    api('POST', '/api/wipe', {confirm: $('wc').value.trim()}).then(function () { $('wc').value = ''; $('wmsg').textContent = 'حُذفت كل البيانات.'; return load(); })
      .catch(function () { $('wmsg').textContent = 'للتأكيد تلزم كتابة كلمة «حذف» كما هي.'; });
  };
  $$('[data-th]').forEach(function (b) { b.onclick = function () { theme(b.dataset.th); }; });
  var sv = 'auto'; try { sv = localStorage.getItem('th') || 'auto'; } catch (e) {} theme(sv);
}

/* ---------- التشغيل ---------- */
function init() {
  initDialog(); initSettings();
  $$('[data-mnav]').forEach(function (b) {
    b.onclick = function () { S.m += +b.dataset.mnav; if (S.m < 0) { S.m = 11; S.y--; } if (S.m > 11) { S.m = 0; S.y++; } S.sel = null; S.stag = true; load(); };
  });
  $$('[data-tf]').forEach(function (b) { b.onclick = function () { S.tf = b.dataset.tf; renderTasks(); }; });
  $('more').onclick = function () { openSide(true); };
  $('sclose').onclick = $('scrim').onclick = function () { openSide(false); };
  document.addEventListener('click', closeMenus);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { closeMenus(); if ($('side').classList.contains('open')) openSide(false); } });
  $('saveimg').onclick = saveImage;
  window.addEventListener('hashchange', route);
  if (window.Lenis && !REDUCED) { window.LN = new Lenis({lerp: 0.1}); (function raf(t) { LN.raf(t); requestAnimationFrame(raf); })(0); }
  greet(); route(); load(); loadSet();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');
}
init();
})();
