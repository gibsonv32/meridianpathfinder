/* Frontline AI Readiness Lab: application logic.
   Plain JavaScript, no build step. State lives in memory and is mirrored to
   localStorage as a convenience so a reviewer can close the tab and resume. */
(function () {
  "use strict";

  const L = window.LAB;
  const view = document.getElementById("view");
  const tabsEl = document.getElementById("tabs");
  const boardEl = document.getElementById("board");
  const tipEl = document.getElementById("tip");
  const KEY = "fairl.session.v2";
  const VIEWS = ["overview", "diagnostic", "learn", "simulation", "results", "analytics", "blueprint"];
  const LETTERS = "ABCDEF";

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  /* Role-adapted content: {base, leader} or {agent, backoffice, leader} resolve to one variant. */
  const pick = (o, role) => (o && typeof o === "object" && !Array.isArray(o) && ("base" in o || role in o)) ? (role in o ? o[role] : o.base) : o;
  const comp = (id) => L.competencies.find((c) => c.id === id);
  const fmt = (sec) => String(Math.floor(sec / 60)).padStart(2, "0") + ":" + String(Math.floor(sec % 60)).padStart(2, "0");
  const level = (v) => (v >= 80 ? "Proficient" : v >= 50 ? "Practicing" : "Emerging");
  const levelCls = (v) => (v >= 80 ? "good" : v >= 50 ? "warn" : "crit");
  const lcFirst = (s) => s.charAt(0).toLowerCase() + s.slice(1);
  const mean = (a) => (a.length ? Math.round(a.reduce((t, v) => t + v, 0) / a.length) : 0);

  /* ---------------- State ---------------- */
  function blank() {
    return {
      profile: { role: "agent", exp: "some" },
      elapsed: 0,
      diag: { i: 0, answers: {}, conf: {}, done: false },
      path: null,
      learn: { i: 0, items: {}, done: false },
      sim: { i: 0, res: {}, drafts: {}, picks: {}, hints: {}, done: false },
      coach: { answers: {}, shown: 0 },
      filters: { site: "all", role: "all" }
    };
  }
  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const o = JSON.parse(raw);
        if (o && o.profile && o.diag && o.sim && o.learn) return Object.assign(blank(), o);
      }
    } catch (e) { /* storage unavailable: run in memory */ }
    return blank();
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* ignore */ } }
  let saveTimer = null;
  function saveSoon() { clearTimeout(saveTimer); saveTimer = setTimeout(save, 400); }
  let S = load();
  let current = "overview";
  let askReset = false;

  const started = () => Object.keys(S.diag.answers).length > 0;
  const activePath = (St) => (St.path || []).filter((p) => p.depth !== "queued");
  const queuedPath = (St) => (St.path || []).filter((p) => p.depth === "queued");
  const simFor = (role) => (role === "leader" ? L.sims.leader : L.sims.frontline);
  const roleName = (id) => L.roles.find((r) => r.id === id).name;
  const expName = (id) => L.experience.find((r) => r.id === id).name;

  /* ---------------- Live AI (optional) ----------------
     The tutor always works from prepared lesson notes. Where the viewer is signed in to
     Claude and allows it, the same panel answers live. Scores never depend on it. */
  const AI = { fn: null };
  const HIDE = ["not_granted", "sampling_disabled", "not_declared", "capability_disabled", "capability_removed"];
  const aiLabel = () => (AI.fn ? "Live AI" : "Guided");
  function aiSync() {
    document.body.setAttribute("data-ai", AI.fn ? "live" : "guided");
    document.querySelectorAll("[data-ai-label]").forEach((el) => { el.textContent = aiLabel(); });
  }
  function aiOff() { AI.fn = null; aiSync(); }
  try {
    if (window.claude && typeof window.claude.use === "function") {
      window.claude.use("sample").then((fn) => { if (typeof fn === "function") { AI.fn = fn; aiSync(); } }).catch(() => {});
    }
  } catch (e) { /* no runtime: guided mode */ }

  function aiComment(targetId, prompt) {
    const el = document.getElementById(targetId);
    if (!el || !AI.fn) return;
    el.hidden = false;
    el.textContent = "Thinking…";
    AI.fn(prompt, { modelTier: "quick", onText: (u) => { el.textContent = u.text; } })
      .then((r) => { el.textContent = r.text; })
      .catch((e) => {
        const code = e && e.code;
        if (HIDE.indexOf(code) >= 0) { aiOff(); el.hidden = true; }
        else if (code === "rate_limited") el.textContent = "The live tutor is busy. Try again in a minute.";
        else el.textContent = (e && e.text) || "The live answer was interrupted. Try again.";
      });
  }

  /* ---------------- Scoring ---------------- */
  function diagScore(St, q) {
    const a = St.diag.answers[q.id];
    return a == null ? null : pick(q.options, St.profile.role)[a].s;
  }
  function preScores(St) {
    const out = {};
    L.diagnostic.forEach((q) => { const s = diagScore(St, q); out[q.comp] = s == null ? null : Math.round(s * 100); });
    return out;
  }
  /* The adaptive rule set. Transparent on purpose: every placement has a stated reason. */
  function buildPath(St) {
    const role = St.profile.role;
    const w = L.roleWeights[role] || {};
    const items = L.diagnostic.map((q) => {
      const s = diagScore(St, q);
      const cf = St.diag.conf[q.id];
      let pri = 1 - s;
      let reason;
      if (s < 1 && cf === 2) { pri += 0.4; reason = "You were certain, and the answer missed. That gap is the one most likely to show up on live work, so it comes early."; }
      else if (s === 0) reason = "Missed in the diagnostic.";
      else if (s < 1) reason = "Partly right in the diagnostic.";
      else if (cf === 0) { pri += 0.3; reason = "Right, but you said you were guessing. A full lesson locks it in."; }
      else reason = "Solid in the diagnostic, so you get the harder version.";
      if (w[q.comp]) { pri += w[q.comp]; if (s < 1) reason += " Weighted up for your role."; }
      if (St.profile.exp === "new" && q.comp === "prompt") pri += 0.2;
      const depth = s === 1 && cf !== 0 ? "stretch" : "core";
      return { id: q.comp, pri: pri, reason: reason, depth: depth, minutes: depth === "core" ? 3 : 2 };
    }).sort((a, b) => b.pri - a.pri);
    let left = 9;
    items.forEach((it, k) => {
      if (it.minutes <= left || k < 2) left -= it.minutes;
      else { it.depth = "queued"; it.minutes = 0; it.reason += " Queued so this sprint stays inside 15 minutes."; }
    });
    return items;
  }
  function scoreExplain(text, ex) {
    const t = String(text || "").toLowerCase();
    const hits = ex.ideas.map((i) => new RegExp(i.re, "i").test(t));
    const words = t.trim().split(/\s+/).filter(Boolean).length;
    let score = hits.filter(Boolean).length / ex.ideas.length;
    if (words < 6) score = Math.min(score, 0.34);
    return { score: score, hits: hits, words: words };
  }
  function scorePrompt(text, st) {
    const raw = String(text || "");
    const t = raw.toLowerCase().replace(/\s+/g, " ");
    const crit = {};
    let n = 0;
    st.criteria.forEach((c) => { crit[c.id] = new RegExp(c.re, "i").test(t); if (crit[c.id]) n++; });
    const pii = /(?:\d[ -]?){13,19}/.test(raw) || /(cvv|cvc|security code|code)\D{0,6}\d{3,4}\b/i.test(raw) || /\b\d{3}-\d{2}-\d{4}\b/.test(raw);
    const named = new RegExp("\\b" + (st.nameCheck || "dana") + "\\b", "i").test(raw);
    return { type: "prompt", text: raw, crit: crit, pii: pii, named: named, s: n / st.criteria.length, final: true };
  }
  function scoreFlag(picked, st) {
    const bad = st.segments.map((g, k) => (g.bad ? k : -1)).filter((k) => k >= 0);
    const hits = picked.filter((k) => bad.indexOf(k) >= 0).length;
    const fp = picked.length - hits;
    return { type: "flag", picked: picked.slice(), hits: hits, fp: fp, s: Math.max(0, Math.min(1, (hits - 0.5 * fp) / bad.length)), final: true };
  }
  function stageDetail(st, r) {
    if (st.type === "choice") return st.options[r.choice].fb;
    if (st.type === "prompt") {
      const miss = st.criteria.filter((c) => !r.crit[c.id]).map((c) => c.label.toLowerCase());
      const n = st.criteria.length - miss.length;
      return n + " of " + st.criteria.length + " parts present" + (miss.length ? " (missing " + miss.join(", ") + ")." : ".") + (r.pii ? " The request included card or ID details." : "");
    }
    const nb = st.segments.filter((g) => g.bad).length;
    return "Caught " + r.hits + " of " + nb + " errors in the AI draft" + (r.fp ? ", and flagged " + r.fp + " sentence" + (r.fp > 1 ? "s" : "") + " that " + (r.fp > 1 ? "were" : "was") + " fine" : "") + ".";
  }
  /* Evidence model: every score is a weighted list of things the learner did. */
  function evidence(St) {
    const role = St.profile.role;
    const ev = {};
    L.competencies.forEach((c) => { ev[c.id] = []; });
    activePath(St).forEach((p) => {
      const it = St.learn.items[p.id];
      if (!it) return;
      const les = L.lessons[p.id];
      const chk = pick(p.depth === "stretch" ? les.stretch : les.check, role);
      if (it.check != null) {
        const o = chk.options[it.check];
        ev[p.id].push({ w: 1, s: o.ok ? 1 : 0, src: "lesson", label: p.depth === "stretch" ? "Stretch check" : "Lesson check", detail: o.ok ? "Answered correctly." : "You chose \u201c" + o.t.replace(/\.$/, "") + "\u201d. " + o.fb });
      }
      if (it.explainRes) {
        const k = it.explainRes.hits.filter(Boolean).length;
        ev[p.id].push({ w: 1, s: it.explainRes.score, src: "lesson", label: "Explain-back", detail: k + " of " + it.explainRes.hits.length + " key ideas present in your own words." });
      }
    });
    simFor(role).stages.forEach((st) => {
      const r = St.sim.res[st.id];
      if (!r || !r.final) return;
      Object.keys(st.comp).forEach((cid) => { ev[cid].push({ w: 2, s: r.s, src: "sim", label: "Simulation: " + st.label, detail: stageDetail(st, r) }); });
      if (st.type === "prompt") {
        if (r.pii) ev.protect.push({ w: 2, s: 0, src: "sim", label: "Simulation: " + st.label, detail: "The request you wrote included card or ID details." });
        else ev.protect.push({ w: 1, s: r.named ? 0.5 : 1, src: "sim", label: "Simulation: " + st.label, detail: r.named ? "No card details, but you named the person where a description would do." : "Kept identifying details out of the request you wrote." });
      }
    });
    L.diagnostic.forEach((q) => {
      if (!ev[q.comp].some((e) => e.src === "lesson")) {
        const s = diagScore(St, q);
        if (s != null) ev[q.comp].push({ w: 1, s: s, src: "diag", label: "Diagnostic", detail: "Carried forward. No lesson on this in the sprint." });
      }
    });
    return ev;
  }
  function postScores(ev) {
    const out = {};
    Object.keys(ev).forEach((k) => {
      const w = ev[k].reduce((t, e) => t + e.w, 0);
      out[k] = w ? Math.round(100 * ev[k].reduce((t, e) => t + e.w * e.s, 0) / w) : null;
    });
    return out;
  }

  /* A filled-in example so Results is never an empty shell. Clearly labelled where shown. */
  let SAMPLE = null;
  function sampleState() {
    if (SAMPLE) return SAMPLE;
    const St = blank();
    St.elapsed = 13 * 60 + 20;
    St.diag = { i: 4, done: true, answers: { "d-prompt": 2, "d-verify": 1, "d-protect": 2, "d-judge": 1, "d-improve": 0 }, conf: { "d-prompt": 1, "d-verify": 2, "d-protect": 2, "d-judge": 1, "d-improve": 0 } };
    St.path = buildPath(St);
    const okIdx = (id) => pick(L.lessons[id].check, "agent").options.findIndex((o) => o.ok);
    St.learn = { i: 2, done: true, items: {
      verify: { check: okIdx("verify"), explain: "", explainRes: { score: 1, hits: [true, true, true] }, skipped: false },
      judge: { check: okIdx("judge"), explain: "", explainRes: { score: 0.67, hits: [true, false, true] }, skipped: false },
      prompt: { check: okIdx("prompt"), explain: "", explainRes: null, skipped: true }
    } };
    St.sim = { i: 4, done: true, drafts: {}, picks: {}, hints: {}, res: {
      s1: { type: "choice", choice: 1, s: 1, final: true },
      s2: { type: "prompt", text: "", crit: { context: true, task: true, limits: false, format: true }, pii: false, named: false, s: 0.75, final: true },
      s3: { type: "flag", picked: [1, 5], hits: 2, fp: 0, s: 2 / 3, final: true },
      s4: { type: "choice", choice: 3, s: 0.5, final: true },
      s5: { type: "choice", choice: 1, s: 1, final: true }
    } };
    SAMPLE = St;
    return St;
  }

  /* ---------------- Shell ---------------- */
  function stepDone(v) {
    if (v === "diagnostic") return S.diag.done;
    if (v === "learn") return S.learn.done;
    if (v === "simulation" || v === "results") return S.sim.done;
    return false;
  }
  function renderTabs() {
    const items = [["overview", "Overview"], ["diagnostic", "Diagnostic", 1], ["learn", "Learn", 2], ["simulation", "Simulation", 3], ["results", "Results and coaching", 4], null, ["analytics", "Adoption analytics"], ["blueprint", "Deployment blueprint"]];
    tabsEl.innerHTML = items.map((it) => {
      if (!it) return '<span class="gap" aria-hidden="true"></span>';
      const done = stepDone(it[0]);
      const n = it[2] ? '<span class="n">' + (done && current !== it[0] ? "✓" : it[2]) + "</span>" : "";
      return '<a href="#' + it[0] + '" data-go="' + it[0] + '" class="' + (done ? "done" : "") + '"' + (current === it[0] ? ' aria-current="page"' : "") + ">" + n + it[1] + "</a>";
    }).join("");
    const cur = tabsEl.querySelector('[aria-current="page"]');
    const sc = tabsEl.parentElement;
    if (cur && sc && sc.scrollWidth > sc.clientWidth) sc.scrollLeft = Math.max(0, cur.offsetLeft - sc.offsetLeft - (sc.clientWidth - cur.offsetWidth) / 2);
  }
  function renderBoard() {
    const done = (S.diag.done ? 1 : 0) + (S.learn.done ? 1 : 0) + (S.sim.done ? 1 : 0);
    boardEl.innerHTML = '<div><span>Time</span><b id="clock">' + fmt(S.elapsed) + " / 15:00</b></div><div><span>Path</span><b>" + done + " of 3 done</b></div><div><span>Tutor</span><b data-ai-label>" + aiLabel() + "</b></div>";
  }
  function renderReset() {
    const slot = document.getElementById("reset-slot");
    if (!slot) return;
    slot.innerHTML = askReset
      ? '<span class="row"><span>Clear your answers and start again?</span><button class="btn sm" data-act="resetYes">Clear</button><button class="btn sm quiet" data-act="resetNo">Keep</button></span>'
      : (started() ? '<button class="btn sm quiet" data-act="resetAsk">Start over</button>' : "");
  }
  function render() {
    hideTip();
    renderTabs();
    renderBoard();
    renderReset();
    view.innerHTML = VIEW[current]();
    aiSync();
    if (current === "analytics") drawActive();
    const log = document.getElementById("tutor-log");
    if (log) log.scrollTop = log.scrollHeight;
  }
  function go(v) {
    if (VIEWS.indexOf(v) < 0) v = "overview";
    current = v;
    try { if (location.hash !== "#" + v) location.hash = v; } catch (e) { /* hash not available */ }
    render();
    window.scrollTo(0, 0);
  }
  function locked(msg, v, label) {
    return '<div class="panel stack" style="max-width:660px"><h2>One step first</h2><p class="muted">' + msg + '</p><div class="row"><a class="btn primary" href="#' + v + '" data-go="' + v + '">' + label + '</a><a class="btn" href="#results" data-go="results">See a sample learner’s results</a></div></div>';
  }
  function progress(i, n) {
    let h = '<div class="prog" aria-hidden="true">';
    for (let k = 0; k < n; k++) h += '<i class="' + (k <= i ? "on" : "") + '"></i>';
    return h + "</div>";
  }

  /* ---------------- Overview ---------------- */
  function profilePicker() {
    const lockedProfile = started();
    const cards = (list, key, act) => list.map((r) => '<button class="choice" data-act="' + act + '" data-arg="' + r.id + '" aria-pressed="' + (S.profile[key] === r.id) + '"' + (lockedProfile ? " disabled" : "") + "><b>" + esc(r.name) + "</b><span>" + esc(r.desc) + "</span></button>").join("");
    const next = !S.diag.done ? "diagnostic" : !S.learn.done ? "learn" : !S.sim.done ? "simulation" : "results";
    return '<section class="panel stack" aria-label="Set up your session">' +
      '<div class="stack-s"><h3>Who is learning today?</h3><p class="small muted">Your role changes the scenarios, the simulation and the coaching.</p></div>' +
      '<div class="cards rows" role="group" aria-label="Role">' + cards(L.roles, "role", "setRole") + "</div>" +
      '<div class="stack-s"><h3>How much have you used generative AI?</h3></div>' +
      '<div class="cards rows" role="group" aria-label="Experience">' + cards(L.experience, "exp", "setExp") + "</div>" +
      (lockedProfile
        ? '<div class="row"><a class="btn primary" href="#' + next + '" data-go="' + next + '">Continue where you left off</a><span class="small muted">Use Start over at the foot of the page to change role.</span></div>'
        : '<div class="row"><a class="btn primary" href="#diagnostic" data-go="diagnostic">Start the 2-minute diagnostic</a><span class="small muted">No sign-in. Nothing you type leaves this page unless you turn on the live tutor.</span></div>') +
      "</section>";
  }
  function vOverview() {
    const steps = [
      ["Diagnostic", "Five short scenarios. Your answers and your confidence decide what comes next.", "2 min"],
      ["Adaptive lessons", "Only the lessons you need, at the depth you need, with an AI tutor beside each one.", "8 min"],
      ["Simulation", "A realistic case: brief the AI, check its draft, make the judgment call.", "4 min"],
      ["Results and coaching", "A scorecard with the evidence behind it, and a plan for your next shift.", "1 min"]
    ];
    const caps = [
      ["Adaptive 15-minute learning", "Five answers and your confidence decide which lessons you get, how deep they go, and what waits for the next sprint.", "diagnostic", "Start the diagnostic"],
      ["Personalized AI tutoring", "A tutor beside every lesson. It answers from prepared lesson notes, and live through Claude when a signed-in viewer allows it.", "learn", "Open the lessons"],
      ["Realistic business simulation", "A live contact or a coaching day, with a prompt to write, an AI draft to check and a judgment call to make.", "simulation", "Open the simulation"],
      ["Competency assessment", "Five competencies scored before and after. Every score links to what the learner did to earn it.", "results", "See a scorecard"],
      ["Coaching", "A guided reflection, a commitment card, and a toolkit a team leader can use the same day.", "results", "See the coaching plan"],
      ["Adoption analytics", "A readiness dashboard for a 2,400-person rollout that pairs usage with quality and business results.", "analytics", "Open the dashboard"]
    ];
    return '<div class="stack-l">' +
      '<div class="hero">' +
        '<div class="stack">' +
          '<span class="eyebrow">Work sample · Manager, Learning &amp; Enablement Consultant for AI · R1004111</span>' +
          "<h1>Get a frontline team ready for AI in fifteen minutes at a time</h1>" +
          '<p class="lede">This is a working learning product. Take the path as an agent or a team leader, then see how the same data tells an operations executive whether the rollout is working.</p>' +
          '<ol class="steps">' + steps.map((s, k) => '<li><span class="n">0' + (k + 1) + '</span><span><span class="t">' + s[0] + '</span><br><span class="d">' + s[1] + '</span></span><span class="m">' + s[2] + "</span></li>").join("") + "</ol>" +
          '<p class="small muted">Short on time? <a href="#results" data-go="results">See a finished scorecard</a>, <a href="#analytics" data-go="analytics">the adoption dashboard</a> or <a href="#blueprint" data-go="blueprint">how this deploys</a>.</p>' +
        "</div>" +
        profilePicker() +
      "</div>" +
      '<hr class="rule">' +
      '<div class="stack"><h2>What you can evaluate here</h2>' +
        '<div class="grid-3">' + caps.map((c) => '<div class="panel cap stack-s"><h3>' + c[0] + "</h3><p>" + c[1] + '</p><a href="#' + c[2] + '" data-go="' + c[2] + '">' + c[3] + " →</a></div>").join("") + "</div>" +
      "</div>" +
      '<div class="band small muted">The setting is Northfield Card Services, a fictional card issuer rolling out a fictional agent-assist tool called Relay Assist to 2,400 associates. All customers, colleagues, policies and metrics are invented.</div>' +
    "</div>";
  }

  /* ---------------- Diagnostic ---------------- */
  function vDiagnostic() {
    if (S.diag.done) return pathScreen();
    const role = S.profile.role;
    const n = L.diagnostic.length;
    const q = L.diagnostic[S.diag.i];
    const opts = pick(q.options, role);
    const a = S.diag.answers[q.id];
    const cf = S.diag.conf[q.id];
    const last = S.diag.i === n - 1;
    return '<div class="stack-l" style="max-width:780px">' +
      '<div class="stack-s"><span class="eyebrow">Diagnostic · question ' + (S.diag.i + 1) + " of " + n + " · " + esc(roleName(role)) + "</span>" + progress(S.diag.i, n) + "</div>" +
      "<h2>" + esc(pick(q.stem, role)) + "</h2>" +
      '<div class="opts" role="group" aria-label="Answers">' + opts.map((o, k) => '<button class="opt" data-act="diagPick" data-arg="' + k + '" aria-pressed="' + (a === k) + '"><span class="key">' + LETTERS[k] + "</span><span>" + esc(o.t) + "</span></button>").join("") + "</div>" +
      '<div class="stack-s"><span class="small muted">How sure are you?</span><div><div class="seg" role="group" aria-label="Confidence">' + ["Guessing", "Fairly sure", "Certain"].map((t, k) => '<button data-act="diagConf" data-arg="' + k + '" aria-pressed="' + (cf === k) + '">' + t + "</button>").join("") + "</div></div></div>" +
      '<div class="row between"><span class="small muted">No feedback yet. That comes in the lessons.</span><button class="btn primary" data-act="diagNext"' + (a == null || cf == null ? " disabled" : "") + ">" + (last ? "Build my path" : "Next question") + "</button></div>" +
    "</div>";
  }
  const DEPTH = { core: ["Full lesson", "accent"], stretch: ["Stretch version", "signal"], queued: ["Next sprint", ""] };
  function pathScreen() {
    const act = activePath(S);
    const q = queuedPath(S);
    const mins = act.reduce((t, p) => t + p.minutes, 0);
    const row = (p, k) => '<div class="it"><span class="eyebrow">' + (p.depth === "queued" ? "–" : "0" + (k + 1)) + '</span><div class="stack-s"><div class="row"><b>' + esc(L.lessons[p.id].title) + '</b><span class="pill ' + DEPTH[p.depth][1] + '">' + DEPTH[p.depth][0] + '</span></div><span class="small muted">' + esc(comp(p.id).name) + ". " + esc(p.reason) + '</span></div><span class="eyebrow">' + (p.minutes ? p.minutes + " min" : "") + "</span></div>";
    return '<div class="stack-l" style="max-width:820px">' +
      '<div class="stack-s"><span class="eyebrow">Diagnostic complete</span><h2>Your path: ' + act.length + " lesson" + (act.length > 1 ? "s" : "") + ", " + mins + " minutes</h2>" +
      '<p class="muted measure">Built from your five answers, how sure you were, and your role. Lessons you already have are shortened or held back so the sprint fits in 15 minutes.</p></div>' +
      '<div class="panel pathlist">' + act.map(row).join("") + q.map(row).join("") + "</div>" +
      '<div class="row"><a class="btn primary" href="#learn" data-go="learn">' + (S.learn.done ? "Review lessons" : S.learn.i > 0 ? "Continue lessons" : "Start lesson 1") + '</a><span class="small muted">Then a ' + (S.profile.role === "leader" ? "coaching" : "live-contact") + " simulation, about 4 minutes.</span></div>" +
    "</div>";
  }

  /* ---------------- Learn ---------------- */
  const T = { key: null, msgs: [], busy: false, ctl: null, awaiting: false };
  function curLesson() { const p = activePath(S)[S.learn.i]; return p ? L.lessons[p.id] : null; }
  function tutorInit(p) {
    if (T.key === p.id) return;
    const x = { new: "new to generative AI, so I will skip the jargon", some: "an occasional user of generative AI", daily: "a daily user of generative AI, so I will move quickly" }[S.profile.exp];
    T.key = p.id;
    T.awaiting = false;
    T.msgs = [{ who: "tutor", text: "I am your tutor for this lesson. You are a " + roleName(S.profile.role).toLowerCase() + " and " + x + ". I will keep examples close to your work. Pick a question or ask your own." }];
  }
  const msgHtml = (m) => '<div class="msg ' + m.who + '"><span class="who">' + (m.who === "you" ? "You" : "Tutor") + "</span><span>" + esc(m.text) + "</span></div>";
  function tutorPanel(les) {
    return '<aside class="panel side tutor" aria-label="AI tutor">' +
      '<div class="row between"><h3>AI tutor</h3><span class="pill accent" data-ai-label>' + aiLabel() + "</span></div>" +
      '<div class="log" id="tutor-log" aria-live="polite">' + T.msgs.map(msgHtml).join("") + "</div>" +
      '<div class="chips">' + les.tutor.map((t, k) => '<button class="chip" data-act="askChip" data-arg="' + k + '">' + esc(t.q) + "</button>").join("") + "</div>" +
      '<div class="askrow"><input type="text" id="tutor-q" placeholder="Ask about this lesson" aria-label="Your question" autocomplete="off"><button class="btn primary sm" id="tutor-send" data-act="ask">Ask</button></div>' +
      '<p class="small muted" data-guided-only>Guided mode. Answers come from prepared lesson notes. Viewers signed in to Claude get live answers here.</p>' +
      '<p class="small muted" data-ai-only>Live mode. Claude answers from this lesson and your role. Your first question asks for permission.</p>' +
    "</aside>";
  }
  function drawLog() {
    const log = document.getElementById("tutor-log");
    if (log) { log.innerHTML = T.msgs.map(msgHtml).join(""); log.scrollTop = log.scrollHeight; }
    const b = document.getElementById("tutor-send");
    if (b) { b.textContent = T.busy ? "Stop" : "Ask"; b.setAttribute("data-act", T.busy ? "stopAsk" : "ask"); }
  }
  function overlap(text, q) {
    const words = q.replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter((w) => w.length > 3);
    if (!words.length) return 0;
    return words.filter((w) => text.indexOf(w) >= 0).length / words.length;
  }
  function guidedAnswer(text, les) {
    const t = text.toLowerCase();
    let best = null;
    let score = 0;
    les.tutor.forEach((qa) => { const sc = overlap(t, qa.q.toLowerCase()); if (sc > score) { score = sc; best = qa; } });
    if (score < 0.6) {
      let g = null;
      let gs = 0;
      L.tutorGeneral.forEach((x) => { const h = x.k.filter((k) => t.indexOf(k) >= 0).length; if (h > gs) { gs = h; g = x; } });
      if (g) { T.awaiting = false; return g.a; }
      if (score < 0.34) {
        if (T.awaiting && t.indexOf("?") < 0) { T.awaiting = false; return "Thanks. Hold on to that example. It is the kind of case the check in this lesson is about."; }
        return "In guided mode I answer from this lesson’s prepared notes, and I do not have a note that fits that question. Try one of the suggested questions, or ask about prompts, checking drafts, customer data, escalation or coaching.";
      }
    }
    T.awaiting = !!best.ask;
    return best.a + (best.ask ? "\n\n" + best.ask : "");
  }
  function tutorRules(les) {
    const role = S.profile.role;
    const x = L.experience.find((e) => e.id === S.profile.exp);
    return [
      "You are the tutor inside a 15-minute AI readiness lesson for staff at Northfield Card Services, a fictional card issuer. Their approved AI assistant is called Relay Assist, also fictional.",
      "Learner: " + roleName(role) + ". Experience with generative AI: " + x.name + " (" + x.desc + ")",
      "Lesson: " + les.title + ". Framework: " + pick(les.modelName, role) + ". Points: " + pick(les.model, role).map((m) => m[0] + ": " + m[1]).join(" | "),
      "Rules: plain text only, no markdown, at most 110 words. Use an example from the learner's own kind of work and match their experience level. If they ask for the answer to a quiz question, give a hint and not the answer. End with one short question that makes them apply the idea. If the question is unrelated to using AI at work, steer back to the lesson in one sentence. Never ask for real customer data."
    ].join("\n");
  }
  function tutorAsk(q) {
    const les = curLesson();
    if (!les || T.busy) return;
    T.msgs.push({ who: "you", text: q });
    if (!AI.fn) { T.msgs.push({ who: "tutor", text: guidedAnswer(q, les) }); drawLog(); return; }
    const turns = [{ role: "user", content: tutorRules(les) }];
    T.msgs.slice(1).forEach((m) => turns.push({ role: m.who === "you" ? "user" : "assistant", content: m.text }));
    const m = { who: "tutor", text: "Thinking…" };
    T.msgs.push(m);
    T.busy = true;
    T.ctl = new AbortController();
    drawLog();
    AI.fn(turns, {
      cache: false, modelTier: "quick", signal: T.ctl.signal,
      onText: (u) => {
        m.text = u.text;
        const log = document.getElementById("tutor-log");
        if (log && log.lastElementChild) { log.lastElementChild.lastElementChild.textContent = u.text; log.scrollTop = log.scrollHeight; }
      }
    }).then((r) => { m.text = r.text; }).catch((e) => {
      const code = e && e.code;
      if (code === "cancelled") m.text = (e && e.text) || "Stopped.";
      else if (HIDE.indexOf(code) >= 0) { aiOff(); m.text = guidedAnswer(q, les); }
      else if (code === "rate_limited") m.text = "The live tutor is busy right now. From the lesson notes:\n\n" + guidedAnswer(q, les);
      else m.text = "The live answer was interrupted. From the lesson notes:\n\n" + guidedAnswer(q, les);
    }).then(() => { T.busy = false; T.ctl = null; drawLog(); });
  }

  function lessonItem(p) {
    if (!S.learn.items[p.id]) S.learn.items[p.id] = { check: null, explain: "", explainRes: null, skipped: false };
    return S.learn.items[p.id];
  }
  function modelCard(les, role) {
    return '<div class="stack-s"><span class="eyebrow">' + esc(pick(les.modelName, role)) + '</span><div class="model">' + pick(les.model, role).map((m) => "<div><b>" + esc(m[0]) + "</b><span>" + esc(m[1]) + "</span></div>").join("") + "</div></div>";
  }
  function vLearn() {
    if (!S.diag.done) return locked("Your lessons are chosen from the diagnostic, so it comes first. It takes about two minutes.", "diagnostic", "Take the diagnostic");
    const role = S.profile.role;
    const act = activePath(S);
    if (S.learn.done) {
      return '<div class="stack-l"><div class="stack-s"><span class="eyebrow">Lessons complete</span><h2>Your reference cards</h2><p class="muted measure">Keep these open during the simulation if you like. That is how they are meant to be used on the floor.</p></div>' +
        '<div class="two">' + act.map((p) => '<div class="panel stack-s"><h3>' + esc(L.lessons[p.id].title) + "</h3>" + modelCard(L.lessons[p.id], role) + "</div>").join("") + "</div>" +
        '<div class="row"><a class="btn primary" href="#simulation" data-go="simulation">' + (S.sim.done ? "Review the simulation" : "Go to the simulation") + "</a></div></div>";
    }
    const p = act[S.learn.i];
    const les = L.lessons[p.id];
    const it = lessonItem(p);
    const stretch = p.depth === "stretch";
    const chk = pick(stretch ? les.stretch : les.check, role);
    const ex = pick(les.example, role);
    const explain = pick(les.explain, role);
    tutorInit(p);

    const rail = '<div class="pathrail" aria-label="Your path">' + act.map((x, k) => '<span class="p ' + (k < S.learn.i ? "done" : k === S.learn.i ? "now" : "") + '">' + (k < S.learn.i ? "✓ " : "") + esc(comp(x.id).short) + "</span>").join("") + queuedPath(S).map((x) => '<span class="p q" title="Queued for your next sprint">' + esc(comp(x.id).short) + " · next sprint</span>").join("") + "</div>";

    const exBody = '<div class="ba"><div><span class="eyebrow">Before</span><span class="quote">' + esc(ex.before) + '</span></div><div class="after"><span class="eyebrow">After</span><span class="quote">' + esc(ex.after) + '</span></div></div><p class="small muted">' + esc(ex.note) + "</p>";
    const example = S.profile.exp === "daily"
      ? '<details><summary class="small"><b>Worked example</b> · ' + esc(ex.label) + ' (collapsed for daily users)</summary><div class="stack-s" style="margin-top:10px">' + exBody + "</div></details>"
      : '<div class="stack-s"><h3>' + (S.profile.exp === "new" ? "Worked example: " : "") + esc(ex.label) + "</h3>" + exBody + "</div>";

    const answered = it.check != null;
    const right = chk.options.find((o) => o.ok);
    const chosen = answered ? chk.options[it.check] : null;
    const check = '<div class="stack"><h3>' + (stretch ? "Stretch check" : "Check your understanding") + "</h3><p>" + esc(chk.stem) + "</p>" +
      '<div class="opts">' + chk.options.map((o, k) => '<button class="opt ' + (answered ? (o.ok ? "right" : k === it.check ? "wrong" : "dim") : "") + '" data-act="lessonCheck" data-arg="' + k + '"' + (answered ? " disabled" : "") + '><span class="key">' + LETTERS[k] + "</span><span>" + esc(o.t) + "</span></button>").join("") + "</div>" +
      (answered ? '<div class="fb ' + (chosen.ok ? "good" : "crit") + '"><b>' + (chosen.ok ? "Correct." : "Not this one.") + "</b> " + esc(chosen.fb) + (chosen.ok ? "" : " <b>Stronger answer:</b> " + esc(right.t) + " " + esc(right.fb)) + "</div>" : "") + "</div>";

    let explainHtml = "";
    if (!stretch) {
      const res = it.explainRes;
      explainHtml = '<div class="stack"><div class="stack-s"><h3>Explain it back</h3><p>' + esc(explain.ask) + "</p></div>" +
        '<textarea id="explain-' + p.id + '" data-bind="learn.items.' + p.id + '.explain" placeholder="Two sentences is plenty." aria-label="Your explanation">' + esc(it.explain) + "</textarea>" +
        (res ? '<div class="fb ' + (res.score >= 0.99 ? "good" : res.score >= 0.5 ? "warn" : "crit") + ' stack-s"><div><b>' + res.hits.filter(Boolean).length + " of " + res.hits.length + " key ideas.</b>" + (res.words < 6 ? " Try a full sentence so there is something to assess." : "") + '</div><div class="rubric">' + explain.ideas.map((i, k) => '<div><span class="tick ' + (res.hits[k] ? "y" : "n") + '">' + (res.hits[k] ? "✓" : "✕") + "</span><span>" + (res.hits[k] ? "Present" : "Missing") + "</span><span>" + esc(i.label) + "</span></div>").join("") + "</div><div><b>A strong answer:</b> " + esc(explain.model) + "</div></div>" : "") +
        (it.skipped && !res ? '<p class="small muted">Skipped. It will not count for or against you.</p>' : "") +
        '<div class="row"><button class="btn" data-act="explainScore">' + (res ? "Check again" : "Check my explanation") + "</button>" + (!res && !it.skipped ? '<button class="btn quiet" data-act="explainSkip">Skip this</button>' : "") + '<button class="btn quiet" data-ai-only data-act="aiExplain">Ask the live tutor for feedback</button></div>' +
        '<div class="fb" id="ai-explain" hidden></div></div>';
    }
    const ready = answered && (stretch || it.explainRes || it.skipped);
    const last = S.learn.i === act.length - 1;

    return '<div class="stack-l">' +
      '<div class="stack"><div class="row between"><span class="eyebrow">Lesson ' + (S.learn.i + 1) + " of " + act.length + " · " + p.minutes + " min · " + DEPTH[p.depth][0] + "</span>" + rail + "</div>" +
      "<h2>" + esc(les.title) + '</h2><p class="small muted">Why this is on your path: ' + esc(p.reason) + "</p></div>" +
      '<div class="work"><section class="panel stack-l" aria-label="Lesson">' +
        '<p class="lede">' + esc(pick(les.hook, role)) + "</p>" +
        modelCard(les, role) +
        (stretch ? "" : example) +
        '<hr class="rule">' + check +
        (stretch ? "" : '<hr class="rule">' + explainHtml) +
        '<div class="row between"><span class="small muted">' + (ready ? "" : stretch ? "Answer the check to continue." : "Answer the check and the explain-back to continue.") + '</span><button class="btn primary" data-act="lessonNext"' + (ready ? "" : " disabled") + ">" + (last ? "Go to the simulation" : "Next lesson") + "</button></div>" +
      "</section>" + tutorPanel(les) + "</div></div>";
  }

  /* ---------------- Simulation ---------------- */
  function sceneMsg(m) {
    if (m.who === "note") return '<div class="msg note">' + esc(m.text) + "</div>";
    if (m.who === "assist") return '<div class="msg assist"><span class="who">Relay Assist suggests</span><span>' + esc(m.text) + "</span></div>";
    return '<div class="msg cust"><span class="who">' + esc(m.who) + "</span><span>" + esc(m.text) + "</span></div>";
  }
  function caseFile(sim, role) {
    const cf = sim.caseFile;
    return '<aside class="panel side stack" aria-label="' + esc(cf.heading) + '"><div class="stack-s"><span class="eyebrow">' + esc(cf.heading) + "</span><b>" + esc(pick(cf.customer, role)) + "</b></div>" +
      '<div class="facts">' + cf.facts.map((f) => "<div><span>" + esc(f[0]) + "</span><b>" + esc(f[1]) + "</b></div>").join("") + "</div>" +
      cf.articles.map((a) => '<div class="ka"><h4><code>' + esc(a.id) + "</code>" + esc(a.title) + "</h4><ul>" + a.lines.map((l) => "<li>" + esc(l) + "</li>").join("") + "</ul></div>").join("") +
    "</aside>";
  }
  function stageBody(st, r) {
    if (st.type === "choice") {
      const best = st.options.find((o) => o.s === 1);
      const ch = r ? st.options[r.choice] : null;
      return '<div class="opts">' + st.options.map((o, k) => {
        let cls = "";
        if (r) cls = k === r.choice ? (o.s === 1 ? "right" : o.s > 0 ? "part" : "wrong") : (o.s === 1 ? "right" : "dim");
        return '<button class="opt ' + cls + '" data-act="simChoice" data-arg="' + k + '"' + (r ? " disabled" : "") + '><span class="key">' + LETTERS[k] + "</span><span>" + esc(o.t) + "</span></button>";
      }).join("") + "</div>" +
      (r ? '<div class="fb ' + (ch.s === 1 ? "good" : ch.s > 0 ? "warn" : "crit") + '"><b>' + (ch.s === 1 ? "Met the standard." : ch.s > 0 ? "Partly there." : "Missed.") + "</b> " + esc(ch.fb) + (ch.s === 1 ? "" : " <b>Stronger move:</b> " + esc(best.t) + " " + esc(best.fb)) + "</div>" : "");
    }
    if (st.type === "prompt") {
      const draft = S.sim.drafts[st.id] || "";
      let out = '<textarea id="draft-' + st.id + '" data-bind="sim.drafts.' + st.id + '" placeholder="' + esc(st.placeholder) + '" aria-label="Your request to the assistant">' + esc(draft) + "</textarea>";
      if (r) {
        const n = st.criteria.filter((c) => r.crit[c.id]).length;
        out += '<div class="fb ' + (r.pii ? "crit" : n === st.criteria.length ? "good" : "warn") + ' stack-s"><div><b>' + n + " of " + st.criteria.length + ' parts present.</b></div><div class="rubric">' +
          st.criteria.map((c) => '<div><span class="tick ' + (r.crit[c.id] ? "y" : "n") + '">' + (r.crit[c.id] ? "✓" : "✕") + "</span><span><b>" + c.label + "</b></span><span>" + (r.crit[c.id] ? "Present." : esc(c.tip)) + "</span></div>").join("") +
          '<div><span class="tick ' + (r.pii ? "n" : "y") + '">' + (r.pii ? "✕" : "✓") + "</span><span><b>Data</b></span><span>" + (r.pii ? "Remove the card or ID details. The assistant does not need them." : r.named ? "No card details. You could also drop the name: a description works as well." : "No identifying details in the request.") + "</span></div></div></div>" +
          '<details><summary class="small"><b>See a model request</b></summary><p class="quote" style="margin-top:8px">' + esc(st.model) + "</p></details>";
      }
      out += '<div class="row"><button class="btn" data-act="simPrompt">' + (r ? "Score it again" : "Score my request") + '</button><button class="btn quiet" data-ai-only data-act="aiPrompt">Ask the live tutor to critique it</button></div><div class="fb" id="ai-prompt" hidden></div>';
      return out;
    }
    const picks = r ? r.picked : (S.sim.picks[st.id] || []);
    let h = '<div class="segs">' + st.segments.map((g, k) => {
      const on = picks.indexOf(k) >= 0;
      let cls = "";
      let note = "";
      if (r) {
        if (g.bad && on) { cls = "hit"; note = "Caught. " + g.why; }
        else if (g.bad) { cls = "miss"; note = "Missed. " + g.why; }
        else if (on) { cls = "false"; note = "This one was fine as written."; }
      }
      return '<button class="sg ' + cls + '" data-act="simSeg" data-arg="' + k + '" aria-pressed="' + on + '"' + (r ? " disabled" : "") + '><span class="box" aria-hidden="true">' + (on ? "✕" : "") + "</span><span>" + esc(g.t) + (note ? "<small>" + esc(note) + "</small>" : "") + "</span></button>";
    }).join("") + "</div>";
    if (r) h += '<div class="fb ' + (r.s >= 0.99 ? "good" : r.s >= 0.5 ? "warn" : "crit") + '"><b>' + esc(stageDetail(st, r)) + "</b> " + (r.s >= 0.99 ? "Nothing wrong would have reached the customer." : "Anything missed here would have been sent under your name.") + "</div>";
    else h += '<div class="row"><button class="btn" data-act="simFlag">Check my review</button><span class="small muted">' + picks.length + " selected</span></div>";
    return h;
  }
  function vSimulation() {
    if (!S.diag.done) return locked("The simulation is scored against your diagnostic, so that comes first. It takes about two minutes.", "diagnostic", "Take the diagnostic");
    const role = S.profile.role;
    const sim = simFor(role);
    if (S.sim.done) return simDebrief(sim, role);
    const n = sim.stages.length;
    const st = sim.stages[S.sim.i];
    const r = S.sim.res[st.id];
    const last = S.sim.i === n - 1;
    return '<div class="stack-l"><div class="stack-s"><span class="eyebrow">Simulation · ' + esc(roleName(role)) + "</span><h2>" + esc(pick(sim.title, role)) + '</h2><p class="muted measure">' + esc(pick(sim.intro, role)) + "</p>" +
      (S.learn.done ? "" : '<p class="small muted">You still have lessons open. They stay available under Learn.</p>') + "</div>" +
      '<div class="work sim">' + caseFile(sim, role) +
      '<section class="panel stack" aria-label="Current decision"><div class="stack-s"><span class="eyebrow">Decision ' + (S.sim.i + 1) + " of " + n + " · " + esc(st.label) + "</span>" + progress(S.sim.i, n) + "</div>" +
        '<div class="scene">' + st.scene.map(sceneMsg).join("") + "</div>" +
        "<h3>" + esc(st.ask) + "</h3>" + stageBody(st, r) +
        (S.sim.hints[st.id] ? '<div class="fb"><b>Tutor hint.</b> ' + esc(st.hint) + "</div>" : "") +
        '<div class="row between">' + (S.sim.hints[st.id] || (r && r.final) ? "<span></span>" : '<button class="btn quiet" data-act="simHint">Ask the tutor for a hint</button>') + '<button class="btn primary" data-act="simNext"' + (r && r.final ? "" : " disabled") + ">" + (last ? "Finish and debrief" : "Continue") + "</button></div>" +
      "</section></div></div>";
  }
  function simDebrief(sim, role) {
    const rows = sim.stages.map((st) => {
      const r = S.sim.res[st.id];
      const tag = r.s >= 0.99 ? ["good", "Met"] : r.s >= 0.5 ? ["warn", "Partly"] : ["crit", "Missed"];
      return "<tr><td><b>" + esc(st.label) + '</b><br><span class="small muted">' + esc(Object.keys(st.comp).map((c) => comp(c).name).join(", ")) + '</span></td><td><span class="pill ' + tag[0] + '">' + tag[1] + '</span></td><td class="muted">' + esc(stageDetail(st, r)) + "</td></tr>";
    }).join("");
    const met = sim.stages.filter((st) => S.sim.res[st.id].s >= 0.99).length;
    const hints = Object.keys(S.sim.hints).length;
    return '<div class="stack-l"><div class="stack-s"><span class="eyebrow">Simulation debrief</span><h2>' + met + " of " + sim.stages.length + ' decisions met the standard</h2><p class="muted measure">' + esc(pick(sim.title, role)) + ". " + (hints ? "You used " + hints + " hint" + (hints > 1 ? "s" : "") + ", which is what they are for." : "No hints used.") + "</p></div>" +
      '<div class="panel scroll-x"><table class="tbl"><thead><tr><th>Decision</th><th>Outcome</th><th>What happened</th></tr></thead><tbody>' + rows + "</tbody></table></div>" +
      '<div class="row"><a class="btn primary" href="#results" data-go="results">See my results and coaching plan</a><button class="btn" data-act="simRetry">Run the simulation again</button></div></div>';
  }

  /* ---------------- Results and coaching ---------------- */
  function dumbbell(rows, withAvg) {
    return '<div class="db">' + rows.map((r) => {
      const a = Math.min(r.pre, r.post);
      const b = Math.max(r.pre, r.post);
      return '<div class="db-row"><span class="db-name">' + esc(r.name) + '</span><div class="db-track" role="img" aria-label="' + esc(r.name) + ": " + r.pre + " before, " + r.post + ' after"><span class="db-link" style="left:' + a + "%;width:" + (b - a) + '%"></span><span class="db-dot pre" style="left:' + r.pre + '%" title="Diagnostic: ' + r.pre + '"></span>' + (withAvg ? '<span class="db-dot avg" style="left:' + r.avg + '%" title="Cohort average: ' + r.avg + '"></span>' : "") + '<span class="db-dot post" style="left:' + r.post + '%" title="After the sprint: ' + r.post + '"></span></div><span class="db-val">' + r.pre + " → " + r.post + "</span></div>";
    }).join("") + '<div class="db-axis"><span></span><div><span>0</span><span>50</span><span>100</span></div><span></span></div></div>';
  }
  function resultModel(St) {
    const pre = preScores(St);
    const ev = evidence(St);
    const post = postScores(ev);
    const rows = L.competencies.map((c) => ({ id: c.id, name: c.name, pre: pre[c.id] == null ? 0 : pre[c.id], post: post[c.id] == null ? 0 : post[c.id], ev: ev[c.id] }));
    const sorted = rows.slice().sort((a, b) => a.post - b.post);
    return { rows: rows, pre: mean(rows.map((r) => r.pre)), post: mean(rows.map((r) => r.post)), low: sorted[0], best: sorted[sorted.length - 1], top: sorted.slice().reverse().filter((r) => r.post >= 80).slice(0, 2), gain: rows.slice().sort((a, b) => (b.post - b.pre) - (a.post - a.pre))[0] };
  }
  function summaryText(St, M) {
    const lines = ["Frontline AI Readiness Lab: learner summary", "Role: " + roleName(St.profile.role) + " | Experience: " + expName(St.profile.exp), "Time used: " + fmt(St.elapsed) + " of 15:00", "Overall readiness: " + M.pre + " to " + M.post + " (" + level(M.post) + ")"];
    M.rows.forEach((r) => lines.push("  " + r.name + ": " + r.pre + " to " + r.post));
    lines.push("Priority next: " + M.low.name);
    lines.push("Practice: " + pick(L.practice[M.low.id].rep, St.profile.role));
    if (St === S && S.coach.shown >= 4) lines.push("Commitment: " + (S.coach.answers.options || "") + " | Check-in: " + (S.coach.answers.will || ""));
    lines.push("Fictional scenario. Scores are rule-based and linked to evidence in the app.");
    return lines.join("\n");
  }
  function vResults() {
    const mine = S.sim.done;
    const St = mine ? S : sampleState();
    const role = St.profile.role;
    const M = resultModel(St);
    const pr = L.practice[M.low.id];
    const over = L.diagnostic.filter((q) => St.diag.conf[q.id] === 2 && diagScore(St, q) < 1).map((q) => comp(q.comp));
    const under = L.diagnostic.filter((q) => St.diag.conf[q.id] === 0 && diagScore(St, q) === 1).map((q) => comp(q.comp));
    const post = {};
    M.rows.forEach((r) => { post[r.id] = r.post; });

    const strengths = M.top.length
      ? M.top.map((r) => { const e = r.ev.filter((x) => x.s >= 0.99).sort((a, b) => b.w - a.w)[0]; return "<li><b>" + esc(r.name) + ".</b> " + esc(e ? e.detail : "Consistent across the sprint.") + "</li>"; }).join("")
      : "<li>No competency reached 80 yet. That is normal for a first sprint. The plan below shows where to start.</li>";
    const worst = M.low.ev.slice().sort((a, b) => a.s - b.s)[0];
    const calib = (over.length ? "<p>You were certain about <b>" + esc(over.map((c) => lcFirst(c.name)).join(" and ")) + "</b> in the diagnostic and the answer missed. After the sprint: " + over.map((c) => post[c.id]).join(" and ") + ". Confident gaps are the ones that reach customers, which is why the path put them early.</p>" : "") +
      (under.length ? "<p>You guessed right on <b>" + esc(under.map((c) => lcFirst(c.name)).join(" and ")) + "</b>. The lesson was there to turn a guess into a habit.</p>" : "") +
      (!over.length && !under.length ? "<p>Your confidence matched your answers. You know what you know, which makes coaching easier.</p>" : "");

    const evidenceHtml = M.rows.map((r) => '<details class="ev"' + (r.id === M.low.id ? " open" : "") + '><summary><b>' + esc(r.name) + '</b><span class="pill ' + levelCls(r.post) + '">' + level(r.post) + '</span><span class="db-val">' + r.post + '</span></summary><div class="evlist">' +
      r.ev.map((e) => '<div><span class="pill ' + (e.s >= 0.99 ? "good" : e.s >= 0.5 ? "warn" : "crit") + '">' + (e.s >= 0.99 ? "Met" : e.s >= 0.5 ? "Partly" : "Missed") + "</span><span><b>" + esc(e.label) + ".</b> " + esc(e.detail) + "</span></div>").join("") + "</div></details>").join("");

    /* Coaching reflection (only for the reviewer's own session) */
    let coach;
    if (!mine) {
      coach = '<p class="muted">Finish the path and this becomes a four-question reflection that ends in a commitment card you can copy to your team leader.</p><div class="commit stack-s"><span class="eyebrow">Sample commitment card</span><p><b>I will try:</b> Before I send any AI draft with a customer-impacting decision in it, I will check KA-5102 for a trigger.</p><p><b>Check-in:</b> With my team leader at Thursday’s one-to-one.</p></div>';
    } else {
      const c = comp(M.low.id);
      coach = L.coachSteps.map((stp, k) => {
        if (k > S.coach.shown) return "";
        const val = S.coach.answers[stp.id] || "";
        return '<div class="stack-s"><label class="fld" for="coach-' + stp.id + '"><span class="eyebrow">' + stp.label + "</span>" + esc(stp.ask(c)) + '</label><textarea id="coach-' + stp.id + '" data-bind="coach.answers.' + stp.id + '" style="min-height:64px">' + esc(val) + "</textarea>" + (k < S.coach.shown ? '<p class="small muted">' + esc(stp.reflect) + "</p>" : "") + "</div>";
      }).join("");
      if (S.coach.shown < 4) coach += '<div class="row"><button class="btn" data-act="coachNext">' + (S.coach.shown === 3 ? "Make my commitment card" : "Next question") + '</button><span class="small muted" id="coach-msg"></span></div>';
      else coach += '<div class="commit stack-s"><span class="eyebrow">My commitment card</span><p><b>Goal:</b> ' + esc(S.coach.answers.goal) + "</p><p><b>What gets in the way:</b> " + esc(S.coach.answers.reality) + "</p><p><b>I will try:</b> " + esc(S.coach.answers.options) + "</p><p><b>Check-in:</b> " + esc(S.coach.answers.will) + '</p></div><div class="row"><button class="btn quiet" data-ai-only data-act="aiCoach">Ask the live coach to respond</button></div><div class="fb" id="ai-coach" hidden></div>';
    }
    const leader = role === "leader";
    const queued = queuedPath(St);

    return '<div class="stack-l">' +
      (mine ? "" : '<div class="notice"><span><b>Sample learner shown.</b> A contact center agent who uses AI now and then. Your own results replace this when you finish the simulation.</span><a class="btn sm" href="#' + (S.diag.done ? "simulation" : "diagnostic") + '" data-go="' + (S.diag.done ? "simulation" : "diagnostic") + '">' + (S.diag.done ? "Continue my path" : "Take the path") + "</a></div>") +
      '<div class="stack-s"><span class="eyebrow">Results · ' + esc(roleName(role)) + " · " + esc(expName(St.profile.exp)) + "</span><h2>" + (M.post >= 80 ? "Ready to use AI on live work, with one area to keep practicing" : M.post >= 50 ? "Practicing: the habits are forming, and one needs attention first" : "Emerging: a clear place to start") + "</h2></div>" +
      '<div class="panel score-hero">' +
        '<div class="stat"><div class="v num">' + M.pre + " <small>→</small> " + M.post + '</div><div class="l">Overall readiness, before and after</div></div>' +
        '<div class="stat"><div class="v">' + level(M.post) + '</div><div class="l">Level. Proficient is 80 or above.</div></div>' +
        '<div class="stat"><div class="v num">' + fmt(St.elapsed) + '</div><div class="l">Time used, of a 15:00 budget</div></div>' +
        (M.gain.post - M.gain.pre > 0
          ? '<div class="stat"><div class="v num">+' + (M.gain.post - M.gain.pre) + '</div><div class="l">Biggest gain: ' + esc(lcFirst(M.gain.name)) + "</div></div>"
          : '<div class="stat"><div class="v num">' + M.best.post + '</div><div class="l">Strongest area: ' + esc(lcFirst(M.best.name)) + "</div></div>") +
      "</div>" +
      '<div class="two">' +
        '<section class="panel stack"><div class="row between"><h3>Competency scorecard</h3><div class="legend"><span><i style="background:var(--ink-3)"></i>Diagnostic</span><span><i style="background:var(--s1)"></i>After the sprint</span></div></div>' + dumbbell(M.rows) + '<p class="small muted">Scores are 0 to 100. “After” rests on more evidence: lesson checks, explain-backs and simulation decisions. The diagnostic is one scenario per competency, so it places you roughly.</p></section>' +
        '<section class="panel stack-s"><h3>The evidence behind each score</h3>' + evidenceHtml + "</section>" +
      "</div>" +
      '<div class="two">' +
        '<section class="panel stack"><h3>What you did well</h3><ul class="list">' + strengths + "</ul><h3>Where to focus next</h3><p><b>" + esc(M.low.name) + ".</b> " + esc(worst ? worst.detail : "") + '</p><div class="band"><span class="eyebrow">Practice on your next shift</span><p style="margin-top:4px">' + esc(pick(pr.rep, role)) + "</p></div><h3>Confidence check</h3>" + '<div class="stack-s muted">' + calib + "</div></section>" +
        '<section class="panel stack"><div class="stack-s"><h3>Coaching: plan your next shift</h3><p class="small muted">Four questions, in the order a coach would ask them.</p></div>' + coach + "</section>" +
      "</div>" +
      '<div class="two">' +
        '<section class="panel stack"><h3>' + (leader ? "Toolkit for your team" : "For your team leader") + '</h3><div class="stack-s"><span class="eyebrow">' + (leader ? "Questions to ask your agents" : "Questions they can ask you") + '</span><ul class="list">' + pr.leaderAsk.map((q) => "<li>" + esc(q) + "</li>").join("") + '</ul></div><div class="stack-s"><span class="eyebrow">Five-minute huddle</span><p class="muted">' + esc(pr.huddle) + "</p></div></section>" +
        '<section class="panel stack"><h3>What happens next</h3><ul class="list">' +
          (queued.length ? "<li><b>Next sprint:</b> " + esc(queued.map((p) => L.lessons[p.id].title).join(", ")) + ".</li>" : "<li><b>Next sprint:</b> the stretch set for your strongest areas.</li>") +
          "<li><b>Day 7:</b> a two-question check on \u201c" + esc(lcFirst(M.low.name)) + "\u201d, and your team leader sees your commitment card.</li>" +
          "<li><b>Day 30:</b> the same competencies are checked on live work through QA sampling. One sitting shows learning. Behavior takes a month.</li></ul>" +
          '<div class="stack-s"><span class="eyebrow">Summary to share</span><div class="copybox" id="copybox">' + esc(summaryText(St, M)) + '</div><div class="row"><button class="btn sm" data-act="copy">Copy summary</button><a class="btn sm quiet" href="#analytics" data-go="analytics">See how this rolls up for leaders →</a></div></div></section>' +
      "</div></div>";
  }

  /* ---------------- Adoption analytics ---------------- */
  function agg(f) {
    const rows = L.cohorts.filter((c) => (f.site === "all" || c.site === f.site) && (f.role === "all" || c.role === f.role));
    const n = rows.reduce((t, c) => t + c.n, 0);
    const weeks = [];
    for (let w = 0; w < 12; w++) {
      const o = { activated: 0, completed: 0, active: 0, proficient: 0 };
      rows.forEach((c) => { Object.keys(o).forEach((k) => { o[k] += c.weeks[w][k]; }); });
      weeks.push(o);
    }
    const cm = {};
    L.competencies.forEach((c) => { cm[c.id] = Math.round(rows.reduce((t, r) => t + r.comp[c.id] * r.n, 0) / n); });
    return { rows: rows, n: n, weeks: weeks, comp: cm, days: Math.round(rows.reduce((t, r) => t + r.daysToProficient * r.n, 0) / n) };
  }
  const SERIES_COLOR = { agent: "var(--s1)", backoffice: "var(--s2)", leader: "var(--s3)" };
  function seriesFor(f) {
    return L.cohortRoles.filter((r) => f.role === "all" || r.id === f.role).map((r) => {
      const rows = L.cohorts.filter((c) => c.role === r.id && (f.site === "all" || c.site === f.site));
      const n = rows.reduce((t, c) => t + c.n, 0);
      const vals = [];
      for (let w = 0; w < 12; w++) vals.push(Math.round(100 * rows.reduce((t, c) => t + c.weeks[w].active, 0) / n));
      return { id: r.id, name: r.name, color: SERIES_COLOR[r.id], vals: vals };
    });
  }
  function hideTip() { tipEl.hidden = true; }
  function showTip(html, cx, cy) {
    tipEl.innerHTML = html;
    tipEl.hidden = false;
    const w = tipEl.offsetWidth;
    const h = tipEl.offsetHeight;
    let x = cx + 14;
    if (x + w > window.innerWidth - 8) x = Math.max(8, cx - w - 14);
    let y = cy + 14;
    if (y + h > window.innerHeight - 8) y = Math.max(8, cy - h - 14);
    tipEl.style.left = x + "px";
    tipEl.style.top = y + "px";
  }
  function drawActive() {
    const box = document.getElementById("chart-active");
    if (!box) return;
    const W = Math.max(280, Math.floor(box.clientWidth));
    const H = 270;
    const m = { l: 40, r: 46, t: 16, b: 42 };
    const ser = seriesFor(S.filters);
    const sx = (W - m.l - m.r) / 11;
    const x = (w) => m.l + (w - 1) * sx;
    const y = (v) => m.t + (100 - v) * (H - m.t - m.b) / 100;
    let g = "";
    [0, 25, 50, 75, 100].forEach((v) => {
      g += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="' + (v === 0 ? "var(--axis)" : "var(--grid)") + '" stroke-width="1"/><text x="' + (m.l - 8) + '" y="' + (y(v) + 4) + '" text-anchor="end" font-size="11" fill="var(--ink-3)">' + v + "%</text>";
    });
    const step = W < 420 ? 3 : W < 620 ? 2 : 1;
    for (let w = 1; w <= 12; w++) if ((w - 1) % step === 0) g += '<text x="' + x(w) + '" y="' + (H - m.b + 16) + '" text-anchor="middle" font-size="11" fill="var(--ink-3)">' + w + "</text>";
    g += '<text x="' + m.l + '" y="' + (H - 6) + '" font-size="11" fill="var(--ink-3)">Rollout week</text>';
    g += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y(70) + '" y2="' + y(70) + '" stroke="var(--ink-3)" stroke-width="1" stroke-dasharray="4 4"/><text x="' + (m.l + 6) + '" y="' + (y(70) - 6) + '" font-size="11" fill="var(--ink-2)">Target 70%</text>';
    ser.forEach((s) => {
      g += '<path d="' + s.vals.map((v, k) => (k ? "L" : "M") + x(k + 1).toFixed(1) + " " + y(v).toFixed(1)).join(" ") + '" fill="none" stroke="' + s.color + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
    });
    const ends = ser.map((s) => ({ s: s, y: y(s.vals[11]), ly: y(s.vals[11]) })).sort((a, b) => a.y - b.y);
    for (let i = 1; i < ends.length; i++) if (ends[i].ly - ends[i - 1].ly < 14) ends[i].ly = ends[i - 1].ly + 14;
    ends.forEach((e) => {
      g += '<circle cx="' + x(12) + '" cy="' + e.y + '" r="4.5" fill="' + e.s.color + '" stroke="var(--surface)" stroke-width="2"/><text x="' + (x(12) + 10) + '" y="' + (e.ly + 4) + '" font-size="12" font-weight="600" fill="var(--ink)">' + e.s.vals[11] + "%</text>";
    });
    box.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" width="' + W + '" height="' + H + '" role="img" tabindex="0" aria-label="Weekly use of Relay Assist on live work by role, weeks 1 to 12. Use the arrow keys to read each week.">' + g + '<g id="hov"></g></svg>';
    const svg = box.querySelector("svg");
    const hov = svg.querySelector("#hov");
    let cur = 12;
    const show = (w, cx, cy) => {
      cur = w;
      hov.innerHTML = '<line x1="' + x(w) + '" x2="' + x(w) + '" y1="' + m.t + '" y2="' + (H - m.b) + '" stroke="var(--axis)" stroke-width="1"/>' + ser.map((s) => '<circle cx="' + x(w) + '" cy="' + y(s.vals[w - 1]) + '" r="4.5" fill="' + s.color + '" stroke="var(--surface)" stroke-width="2"/>').join("");
      showTip("<h5>Week " + w + "</h5>" + ser.map((s) => '<div><i style="background:' + s.color + '"></i><span>' + esc(s.name) + "</span><b>" + s.vals[w - 1] + "%</b></div>").join(""), cx, cy);
    };
    const clear = () => { hov.innerHTML = ""; hideTip(); };
    svg.addEventListener("pointermove", (e) => {
      const r = svg.getBoundingClientRect();
      const px = (e.clientX - r.left) * (W / r.width);
      show(Math.max(1, Math.min(12, Math.round((px - m.l) / sx) + 1)), e.clientX, e.clientY);
    });
    svg.addEventListener("pointerleave", clear);
    svg.addEventListener("blur", clear);
    svg.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      const w = Math.max(1, Math.min(12, cur + (e.key === "ArrowRight" ? 1 : -1)));
      const r = svg.getBoundingClientRect();
      show(w, r.left + x(w) * (r.width / W), r.top + m.t + 10);
    });
  }
  function vAnalytics() {
    const f = S.filters;
    const A = agg(f);
    const pct = (v) => Math.round(100 * v / A.n);
    const w12 = A.weeks[11];
    const w8 = A.weeks[7];
    const kpi = (label, now, then, note) => '<div class="kpi"><div class="l">' + label + '</div><div class="v num">' + now + '%</div><div class="d"><b class="up-good">▲ ' + (now - then) + " pts</b> in 4 weeks" + (note ? " · " + note : "") + "</div></div>";
    const funnel = [["Invited", A.n], ["Activated the assistant", w12.activated], ["Completed a first sprint", w12.completed], ["Using it weekly on live work", w12.active], ["Proficient, 80 or above", w12.proficient]];
    const ser = seriesFor(f);
    const siteRows = L.sites.filter((s) => f.site === "all" || s.id === f.site).map((s) => {
      const rows = L.cohorts.filter((c) => c.site === s.id && (f.role === "all" || c.role === f.role));
      const n = rows.reduce((t, c) => t + c.n, 0);
      const vals = L.competencies.map((c) => Math.round(rows.reduce((t, r) => t + r.comp[c.id] * r.n, 0) / n));
      return { name: s.name, vals: vals, avg: mean(vals) };
    });
    const bin = (v) => (v < 68 ? 1 : v < 74 ? 2 : v < 80 ? 3 : v < 86 ? 4 : 5);
    const lowSite = siteRows.slice().sort((a, b) => a.avg - b.avg)[0];
    const lowComp = L.competencies.slice().sort((a, b) => A.comp[a.id] - A.comp[b.id])[0];
    const teamRows = L.teams.filter((t) => f.site === "all" || t.site === f.site);
    const St = S.sim.done ? S : sampleState();
    const M = resultModel(St);
    const you = M.rows.map((r) => ({ name: r.name, pre: r.pre, post: r.post, avg: A.comp[r.id] }));
    const opt = (list, key) => '<option value="all">All</option>' + list.map((o) => '<option value="' + o.id + '"' + (f[key] === o.id ? " selected" : "") + ">" + esc(o.name) + "</option>").join("");

    return '<div class="stack-l">' +
      '<div class="stack-s"><span class="eyebrow">Adoption analytics · week 12 of rollout · synthetic data</span><h2>Is the rollout working?</h2><p class="muted measure">The view an accountable executive and the readiness team would review each month. Usage is always shown beside quality, because one without the other misleads.</p></div>' +
      '<div class="filters"><label class="fld" for="f-site">Site<select id="f-site" data-filter="site">' + opt(L.sites, "site") + '</select></label><label class="fld" for="f-role">Role<select id="f-role" data-filter="role">' + opt(L.cohortRoles, "role") + '</select></label><span class="small muted num">' + A.n.toLocaleString("en-US") + " associates in view</span></div>" +
      '<div class="kpis">' + kpi("Activated", pct(w12.activated), pct(w8.activated)) + kpi("Completed a first sprint", pct(w12.completed), pct(w8.completed)) + kpi("Using it weekly on live work", pct(w12.active), pct(w8.active), "target 70%") + kpi("Proficient, 80 or above", pct(w12.proficient), pct(w8.proficient)) +
        '<div class="kpi"><div class="l">Median days to proficient</div><div class="v num">' + A.days + '</div><div class="d">From first sprint to 80 or above</div></div></div>' +
      '<div class="two">' +
        '<section class="panel stack"><div class="stack-s"><h3>Weekly use on live work, by role</h3><div class="legend">' + ser.map((s) => '<span><i class="line" style="background:' + s.color + '"></i>' + esc(s.name) + "</span>").join("") + '</div></div><div class="chart" id="chart-active"></div>' +
          '<details><summary class="small">View as table</summary><div class="scroll-x" style="margin-top:8px"><table class="tbl"><thead><tr><th>Week</th>' + ser.map((s) => '<th class="r">' + esc(s.name) + "</th>").join("") + "</tr></thead><tbody>" + [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((w) => "<tr><td>" + w + "</td>" + ser.map((s) => '<td class="r">' + s.vals[w - 1] + "%</td>").join("") + "</tr>").join("") + "</tbody></table></div></details></section>" +
        '<section class="panel stack"><h3>Adoption funnel</h3><div class="funnel">' + funnel.map((s) => '<div class="fn-row"><span class="fn-name">' + s[0] + '</span><div class="fn-bar" title="' + s[0] + ": " + s[1].toLocaleString("en-US") + '"><i style="width:' + (100 * s[1] / A.n).toFixed(1) + '%"></i></div><span class="fn-val">' + s[1].toLocaleString("en-US") + " · " + pct(s[1]) + "%</span></div>").join("") + '</div><p class="small muted">Share of invited associates at week 12. The widest drop is between completing a sprint and using the tool on live work, which is where leader coaching acts.</p></section>' +
      "</div>" +
      '<section class="panel stack"><div class="row between"><h3>Competency scores by site</h3><div class="hl"><span>Average post-assessment</span><span class="b1">under 68</span><span class="b2">68–73</span><span class="b3">74–79</span><span class="b4">80–85</span><span class="b5">86+</span></div></div>' +
        '<div class="scroll-x"><table class="tbl heat"><thead><tr><th>Site</th>' + L.competencies.map((c) => "<th>" + esc(c.short) + "</th>").join("") + "</tr></thead><tbody>" + siteRows.map((s) => "<tr><td>" + esc(s.name) + "</td>" + s.vals.map((v, k) => '<td class="c" title="' + esc(s.name) + ", " + esc(L.competencies[k].name) + ": " + v + '"><span class="b' + bin(v) + '">' + v + "</span></td>").join("") + "</tr>").join("") + "</tbody></table></div>" +
        '<div class="band"><span class="eyebrow">Reading this</span><p style="margin-top:4px">' + esc(lowSite.name) + " has the lowest average (" + lowSite.avg + "), and “" + esc(lcFirst(lowComp.name)) + "” is the weakest competency across this view (" + A.comp[lowComp.id] + "). Leader coaching starts there, before another content push.</p></div></section>" +
      '<div class="two">' +
        '<section class="panel stack"><h3>Business results: AI-ready cohort against comparison</h3><div class="scroll-x"><table class="tbl"><thead><tr><th>Measure</th><th class="r">Comparison</th><th class="r">AI-ready</th><th>Change</th></tr></thead><tbody>' +
          L.outcomes.map((o) => { const d = o.after - o.before; const good = (o.better === "up") === (d > 0); return "<tr><td>" + esc(o.metric) + '</td><td class="r">' + o.before.toFixed(o.dp) + o.suffix + '</td><td class="r">' + o.after.toFixed(o.dp) + o.suffix + '</td><td><span class="pill ' + (good ? "good" : "crit") + '">' + (d > 0 ? "▲" : "▼") + " " + Math.abs(d).toFixed(o.dp) + o.dUnit +" · " + (good ? "better" : "worse") + "</span></td></tr>"; }).join("") +
          '</tbody></table></div><p class="small muted">AI-ready means proficient and using the tool weekly. Cohorts are matched on tenure and contact mix, not randomized, so this shows association. A stepped rollout by site would be the way to estimate effect.</p></section>' +
        '<section class="panel stack"><h3>Your session against the cohort</h3><div class="legend"><span><i style="background:var(--ink-3)"></i>Diagnostic</span><span><i style="background:var(--s1)"></i>After the sprint</span><span><i class="sq" style="background:transparent;border:2px solid var(--signal);transform:rotate(45deg)"></i>Cohort average</span></div>' + dumbbell(you, true) + '<p class="small muted">' + (S.sim.done ? "Your results from this session, as " + esc(roleName(S.profile.role).toLowerCase()) + "." : "Showing the sample learner. Finish the path and your own results appear here.") + "</p></section>" +
      "</div>" +
      '<section class="panel stack"><h3>Teams that need support, and the play for each</h3><div class="scroll-x"><table class="tbl"><thead><tr><th>Team</th><th>Leader</th><th class="r">Weekly use</th><th class="r">QA accuracy</th><th>Signal</th><th>Recommended play</th></tr></thead><tbody>' +
        (teamRows.length ? teamRows.map((t) => "<tr><td><b>" + esc(t.team) + "</b></td><td>" + esc(t.lead) + '</td><td class="r">' + t.use + '%</td><td class="r">' + t.qa + '%</td><td><span class="pill ' + t.status + '">' + (t.status === "crit" ? "● Act now" : t.status === "warn" ? "▲ Watch" : "✓ Exemplar") + '</span><br><span class="small muted">' + esc(t.signal) + '</span></td><td class="muted" style="min-width:240px">' + esc(t.play) + "</td></tr>").join("") : '<tr><td colspan="6" class="muted">No teams flagged at this site.</td></tr>') +
        "</tbody></table></div></section>" +
      '<section class="stack"><h3>Experiment log</h3><div class="grid-3">' + L.experiments.map((x) => '<div class="panel stack-s"><h4>' + esc(x.name) + '</h4><p class="muted small">' + esc(x.n) + "</p><p>" + esc(x.result) + '</p><p class="small"><b>Decision:</b> ' + esc(x.decision) + "</p></div>").join("") + "</div></section>" +
    "</div>";
  }

  /* ---------------- Deployment blueprint ---------------- */
  function vBlueprint() {
    const layers = [
      ["Where people learn", ["Agent desktop", "Learning platform", "Team huddle"], false],
      ["Experience", ["Diagnostic", "Adaptive sprints", "Simulations", "Coaching toolkits"], true],
      ["Engines", ["Path rules, rule-based and auditable", "Approved LLM gateway for tutoring", "Scoring rubrics"], false],
      ["Content", ["Enterprise AI fluency assets", "Operations knowledge articles", "Role packs"], false],
      ["Data", ["Learning records (xAPI)", "QA and operations metrics", "Readiness scorecard"], true]
    ];
    const A = L.about;
    return '<div class="stack-l">' +
      '<div class="stack-s"><span class="eyebrow">Deployment blueprint</span><h2>From this prototype to an enterprise rollout</h2><p class="muted measure">How the pieces you just used map to the role, how they would be built and governed inside a large operation, and what the first 90 days look like.</p></div>' +
      '<section class="panel stack"><h3>What the role asks for, and where it shows up</h3><div class="scroll-x"><table class="tbl"><thead><tr><th>The role calls for</th><th>In this lab</th><th>At scale</th></tr></thead><tbody>' + L.traceability.map((t) => '<tr><td style="min-width:220px"><b>' + esc(t.need) + '</b></td><td style="min-width:200px">' + esc(t.here) + '</td><td class="muted" style="min-width:200px">' + esc(t.scale) + "</td></tr>").join("") + '</tbody></table></div><p class="small muted">Requirements are paraphrased from the public posting for R1004111.</p></section>' +
      '<div class="two">' +
        '<section class="panel stack"><h3>Reference architecture</h3><div class="arch">' + layers.map((l, k) => (k ? '<div class="flowmark" aria-hidden="true">↓</div>' : "") + '<div class="layer' + (l[2] ? " key" : "") + '"><span class="eyebrow">' + l[0] + '</span><div class="boxes">' + l[1].map((b) => "<span>" + b + "</span>").join("") + "</div></div>").join("") + '</div><p class="small muted">The adaptive rules and the scoring are deliberately rule-based. An approved language model adds tutoring and commentary, and can be switched off without breaking the learning path.</p></section>' +
        '<section class="panel stack"><h3>Governance for the rollout</h3><div class="dl">' + L.governance.map((g) => "<div><b>" + esc(g[0]) + "</b><span>" + esc(g[1]) + "</span></div>").join("") + "</div></section>" +
      "</div>" +
      '<section class="panel stack"><h3>How readiness is measured</h3><div class="scroll-x"><table class="tbl"><thead><tr><th>Level</th><th>Question</th><th>Measures</th></tr></thead><tbody>' + L.measures.map((r) => "<tr><td><b>" + esc(r[0]) + "</b></td><td>" + esc(r[1]) + '</td><td class="muted">' + esc(r[2]) + "</td></tr>").join("") + "</tbody></table></div></section>" +
      '<section class="stack"><h3>First 90 days</h3><div class="plan">' + L.plan.map((p) => '<div class="panel"><span class="eyebrow">' + esc(p.when) + '</span><h4 style="margin-top:4px">' + esc(p.title) + "</h4><ul>" + p.items.map((i) => "<li>" + esc(i) + "</li>").join("") + "</ul></div>").join("") + "</div></section>" +
      '<section class="panel tint stack"><div class="stack-s"><span class="eyebrow">Who built this</span><h3>' + esc(A.name) + '</h3><p class="muted">' + esc(A.line) + '</p></div><div class="dl">' + A.points.map((p) => "<div><b>" + esc(p[0]) + "</b><span>" + esc(p[1]) + "</span></div>").join("") + '</div><p class="small">LinkedIn: <a href="' + esc(A.linkedin) + '" target="_blank" rel="noopener">' + esc(A.linkedin.replace("https://www.", "")) + "</a></p></section>" +
    "</div>";
  }

  const VIEW = { overview: vOverview, diagnostic: vDiagnostic, learn: vLearn, simulation: vSimulation, results: vResults, analytics: vAnalytics, blueprint: vBlueprint };

  /* ---------------- Actions ---------------- */
  function setPath(obj, path, val) {
    const parts = path.split(".");
    let o = obj;
    for (let i = 0; i < parts.length - 1; i++) { if (!o[parts[i]] || typeof o[parts[i]] !== "object") o[parts[i]] = {}; o = o[parts[i]]; }
    o[parts[parts.length - 1]] = val;
  }
  function curStage() { return simFor(S.profile.role).stages[S.sim.i]; }
  function rerender() { const y = window.scrollY; save(); render(); window.scrollTo(0, y); }

  const ACT = {
    setRole: (v) => { if (!started()) { S.profile.role = v; rerender(); } },
    setExp: (v) => { if (!started()) { S.profile.exp = v; rerender(); } },
    diagPick: (v) => { S.diag.answers[L.diagnostic[S.diag.i].id] = +v; rerender(); },
    diagConf: (v) => { S.diag.conf[L.diagnostic[S.diag.i].id] = +v; rerender(); },
    diagNext: () => {
      if (S.diag.i < L.diagnostic.length - 1) { S.diag.i++; save(); render(); window.scrollTo(0, 0); return; }
      S.diag.done = true;
      S.path = buildPath(S);
      save(); render(); window.scrollTo(0, 0);
    },
    lessonCheck: (v) => { const p = activePath(S)[S.learn.i]; const it = lessonItem(p); if (it.check == null) { it.check = +v; rerender(); } },
    explainScore: () => {
      const p = activePath(S)[S.learn.i];
      const it = lessonItem(p);
      if (!String(it.explain || "").trim()) { const el = document.getElementById("explain-" + p.id); if (el) el.focus(); return; }
      it.explainRes = scoreExplain(it.explain, pick(L.lessons[p.id].explain, S.profile.role));
      it.skipped = false;
      rerender();
    },
    explainSkip: () => { lessonItem(activePath(S)[S.learn.i]).skipped = true; rerender(); },
    aiExplain: () => {
      const p = activePath(S)[S.learn.i];
      const it = lessonItem(p);
      const ex = pick(L.lessons[p.id].explain, S.profile.role);
      if (!String(it.explain || "").trim()) return;
      aiComment("ai-explain", "You are a tutor giving feedback to a " + roleName(S.profile.role).toLowerCase() + " in a short AI readiness lesson at a fictional card issuer. Question they were asked: " + ex.ask + "\nA strong answer covers: " + ex.ideas.map((i) => i.label).join("; ") + ".\nTheir answer: " + it.explain + "\nReply in plain text, at most 70 words: one thing they got right, one thing to add, and one follow-up question. No markdown.");
    },
    lessonNext: () => {
      const act = activePath(S);
      if (S.learn.i < act.length - 1) { S.learn.i++; save(); render(); window.scrollTo(0, 0); return; }
      S.learn.done = true;
      save();
      go("simulation");
    },
    ask: () => { const inp = document.getElementById("tutor-q"); const q = inp ? inp.value.trim() : ""; if (!q) return; inp.value = ""; tutorAsk(q); },
    askChip: (k) => { const les = curLesson(); if (les) tutorAsk(les.tutor[+k].q); },
    stopAsk: () => { if (T.ctl) T.ctl.abort(); },
    simChoice: (v) => { const st = curStage(); if (S.sim.res[st.id]) return; S.sim.res[st.id] = { type: "choice", choice: +v, s: st.options[+v].s, final: true }; rerender(); },
    simPrompt: () => {
      const st = curStage();
      const text = S.sim.drafts[st.id] || "";
      if (!text.trim()) { const el = document.getElementById("draft-" + st.id); if (el) el.focus(); return; }
      S.sim.res[st.id] = scorePrompt(text, st);
      rerender();
    },
    aiPrompt: () => {
      const st = curStage();
      const text = S.sim.drafts[st.id] || "";
      if (!text.trim()) return;
      aiComment("ai-prompt", "You coach contact center staff on writing requests to an AI assistant. A good request has four parts: context, task, limits, format, and contains no customer identifiers. Task they were given: " + st.ask + "\nTheir request: " + text + "\nReply in plain text, at most 80 words: what works, the single most useful improvement, and a rewritten first line. No markdown.");
    },
    simSeg: (v) => { const st = curStage(); if (S.sim.res[st.id]) return; const a = S.sim.picks[st.id] || (S.sim.picks[st.id] = []); const k = a.indexOf(+v); if (k >= 0) a.splice(k, 1); else a.push(+v); rerender(); },
    simFlag: () => { const st = curStage(); S.sim.res[st.id] = scoreFlag(S.sim.picks[st.id] || [], st); rerender(); },
    simHint: () => { S.sim.hints[curStage().id] = true; rerender(); },
    simNext: () => {
      const n = simFor(S.profile.role).stages.length;
      if (S.sim.i < n - 1) S.sim.i++; else S.sim.done = true;
      save(); render(); window.scrollTo(0, 0);
    },
    simRetry: () => { S.sim = blank().sim; S.coach = blank().coach; save(); render(); window.scrollTo(0, 0); },
    coachNext: () => {
      const stp = L.coachSteps[S.coach.shown];
      if (!String(S.coach.answers[stp.id] || "").trim()) { const el = document.getElementById("coach-" + stp.id); if (el) el.focus(); const msg = document.getElementById("coach-msg"); if (msg) msg.textContent = "Write a line first."; return; }
      S.coach.shown++;
      rerender();
      const nxt = L.coachSteps[S.coach.shown];
      if (nxt) { const el = document.getElementById("coach-" + nxt.id); if (el) el.focus(); }
    },
    aiCoach: () => {
      const M = resultModel(S);
      const a = S.coach.answers;
      aiComment("ai-coach", "You are a workplace coach responding to a " + roleName(S.profile.role).toLowerCase() + " who just finished an AI readiness sprint. Their priority area: " + M.low.name + ". Their plan. Goal: " + a.goal + " | Barrier: " + a.reality + " | Will try: " + a.options + " | Check-in: " + a.will + "\nReply in plain text, at most 80 words. Reflect back what is strong about the plan, ask one question that makes it more specific, and do not give advice they did not ask for. No markdown.");
    },
    copy: (v, btn) => {
      const box = document.getElementById("copybox");
      const text = box ? box.textContent : "";
      const fallback = () => { try { const r = document.createRange(); r.selectNodeContents(box); const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r); btn.textContent = "Selected. Press copy."; } catch (e) { /* ignore */ } };
      try { navigator.clipboard.writeText(text).then(() => { btn.textContent = "Copied"; }, fallback); } catch (e) { fallback(); }
    },
    resetAsk: () => { askReset = true; renderReset(); },
    resetNo: () => { askReset = false; renderReset(); },
    resetYes: () => { askReset = false; S = blank(); T.key = null; save(); go("overview"); }
  };

  document.addEventListener("click", (e) => {
    const g = e.target.closest("[data-go]");
    if (g) { e.preventDefault(); go(g.getAttribute("data-go")); return; }
    const a = e.target.closest("[data-act]");
    if (!a || a.disabled) return;
    const fn = ACT[a.getAttribute("data-act")];
    if (fn) fn(a.getAttribute("data-arg"), a, e);
  });
  document.addEventListener("input", (e) => {
    const b = e.target.getAttribute && e.target.getAttribute("data-bind");
    if (b) { setPath(S, b, e.target.value); saveSoon(); }
  });
  document.addEventListener("change", (e) => {
    const f = e.target.getAttribute && e.target.getAttribute("data-filter");
    if (!f) return;
    S.filters[f] = e.target.value;
    const id = e.target.id;
    rerender();
    const el = document.getElementById(id);
    if (el) el.focus();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.id === "tutor-q") { e.preventDefault(); if (!T.busy) ACT.ask(); }
  });
  window.addEventListener("hashchange", () => {
    const h = (location.hash || "").replace(/^#/, "");
    if (VIEWS.indexOf(h) >= 0 && h !== current) { current = h; render(); window.scrollTo(0, 0); }
  });
  let rz = null;
  window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => { if (current === "analytics") drawActive(); }, 150); });

  /* The 15-minute clock runs only while the learner is on a learning step. */
  setInterval(() => {
    if (document.hidden || S.sim.done) return;
    if (current === "diagnostic" ? S.diag.done : current === "learn" ? S.learn.done : current !== "simulation") return;
    S.elapsed += 1;
    const c = document.getElementById("clock");
    if (c) c.textContent = fmt(S.elapsed) + " / 15:00";
    if (S.elapsed % 5 === 0) save();
  }, 1000);

  const h0 = (location.hash || "").replace(/^#/, "");
  if (VIEWS.indexOf(h0) >= 0) current = h0;
  render();
})();
