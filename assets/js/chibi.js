/* Chibi Alvin: an animated guide for the portfolio.
   One sprite sheet (assets/img/alvin-sprite.webp, 9 columns x 11 rows of 384 px cells) drives:
   - the hero character (190 px; 140 px on phones) that follows the mouse, waves when you come close,
     points at the folder you hover, celebrates when you click one, and offers a 60-second tour;
   - a 96 px corner companion on wide screens that reacts to the section you are reading and to the
     tools you use (job fit check, inquiry form, résumé downloads, the item-analysis demo);
   - easter eggs: click him five times, or search "alvin";
   - a confused Alvin on the 404 page.
   Loads after the page has finished loading, so it never slows the first paint. Reduced motion
   shows still frames only. The corner companion can be hidden and stays hidden. */
(function () {
  "use strict";
  var script = document.currentScript;
  var PAGE = (script && script.dataset.page) || "home";
  var SHEET = new URL("../img/alvin-sprite.webp", script ? script.src : location.href).href;
  var COLS = 9, ROWS = 11;
  /* name: [row, frames, fps, loops] */
  var MOVES = {
    idle: [0, 8, 7, true], wave: [1, 8, 10, false], typing: [2, 8, 11, true], idea: [3, 8, 6, false],
    celebrate: [4, 8, 11, false], point: [5, 8, 9, false], thumbs: [6, 8, 9, false], worried: [7, 8, 9, false],
    resume: [8, 8, 8, false], confused: [9, 8, 7, true], look: [10, 9, 0, false]
  };
  /* frames of the "look" row, as a 3x3 grid: index = (dy+1)*3 + (dx+1) */
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = matchMedia("(hover: hover) and (pointer: fine)").matches;
  var store = { get: function (k) { try { return localStorage.getItem(k) } catch (e) { return null } },
                set: function (k, v) { try { localStorage.setItem(k, v) } catch (e) {} } };

  var CSS = [
    ".chibi{position:absolute;z-index:6;width:var(--s);height:var(--s);padding:0;border:0;background:none;cursor:pointer;opacity:0;transition:opacity 260ms ease,transform 200ms cubic-bezier(.23,1,.32,1);-webkit-tap-highlight-color:transparent}",
    ".chibi.on{opacity:1}",
    ".chibi .spr{position:absolute;inset:0;background-image:var(--sheet);background-repeat:no-repeat;background-size:calc(var(--s) * " + COLS + ") calc(var(--s) * " + ROWS + ");background-position:calc(var(--c,0) * var(--s) * -1) calc(var(--r,0) * var(--s) * -1);pointer-events:none}",
    ".chibi:focus-visible{outline:2px solid var(--amber,#F2A516);outline-offset:2px;border-radius:12px}",
    ".chibi-hero{--s:190px;right:-1%;bottom:-6px;transform-origin:50% 92%}",
    "@media (max-width:760px){.chibi-hero{--s:140px;right:0;bottom:-8px}}",
    ".chibi-bub{position:absolute;z-index:7;max-width:240px;padding:9px 13px;border-radius:14px;background:var(--paper,#fff);color:var(--paper-ink,#121927);font:600 13.5px/1.35 var(--body,system-ui,sans-serif);box-shadow:0 14px 30px -14px rgba(0,0,0,.55),0 0 0 1px rgba(18,25,39,.08);opacity:0;transform:translateY(6px) scale(.96);transform-origin:90% 100%;transition:opacity 180ms ease,transform 220ms cubic-bezier(.23,1,.32,1);pointer-events:none}",
    ".chibi-bub.on{opacity:1;transform:none;pointer-events:auto}",
    ".chibi-bub::after{content:\"\";position:absolute;right:26px;bottom:-6px;width:12px;height:12px;background:inherit;transform:rotate(45deg);box-shadow:3px 3px 0 0 rgba(18,25,39,.04)}",
    ".chibi-bub .cb-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}",
    ".chibi-bub button{min-height:34px;padding:0 12px;border-radius:999px;border:1px solid rgba(18,25,39,.2);background:none;color:inherit;font:600 13px var(--body,system-ui,sans-serif);cursor:pointer}",
    ".chibi-bub button.cb-go{background:var(--amber,#F2A516);border-color:var(--amber,#F2A516);color:var(--on-amber,#1B1203)}",
    ".chibi-hero-bub{right:calc(190px * .62);bottom:calc(190px * .72)}",
    "@media (max-width:760px){.chibi-hero-bub{right:calc(140px * .5);bottom:calc(140px * .78);max-width:170px;font-size:13px;padding:8px 11px}.chibi-hero-bub .cb-row button{min-height:30px;padding:0 10px}}",
    ".chibi-dock{position:fixed;z-index:50;right:calc(46px + env(safe-area-inset-right,0px));bottom:calc(10px + env(safe-area-inset-bottom,0px));width:96px;height:96px;opacity:0;transform:translateY(16px);transition:opacity 220ms ease,transform 260ms cubic-bezier(.23,1,.32,1);pointer-events:none}",
    ".chibi-dock.on{opacity:1;transform:none;pointer-events:auto}",
    ".chibi-dock .chibi{--s:96px;position:absolute;left:0;top:0;opacity:1}",
    ".chibi-dock .cb-x{position:absolute;z-index:9;right:-4px;top:-4px;width:24px;height:24px;border-radius:50%;border:1px solid var(--rule-2,rgba(0,0,0,.2));background:var(--sheet,var(--paper,#fff));color:var(--fg,#121927);font:600 14px/1 system-ui;display:grid;place-items:center;cursor:pointer;opacity:0;transition:opacity 160ms ease}",
    ".chibi-dock:hover .cb-x,.chibi-dock:focus-within .cb-x{opacity:1}",
    "@media (hover:none){.chibi-dock .cb-x{opacity:1}}",
    ".chibi-dock .chibi-bub{right:30px;bottom:100px;width:max-content;max-width:190px;transform-origin:90% 100%}",
    ".chibi-confetti{position:absolute;z-index:8;left:50%;top:40%;width:8px;height:12px;border-radius:2px;pointer-events:none;animation:chibi-pop 1100ms cubic-bezier(.2,.7,.3,1) forwards}",
    "@keyframes chibi-pop{0%{transform:translate(-50%,-50%) rotate(0);opacity:1}100%{transform:translate(calc(-50% + var(--dx)),calc(-50% + var(--dy))) rotate(var(--rot));opacity:0}}",
    ".chibi-tour-hl{outline:3px solid var(--amber,#F2A516)!important;outline-offset:6px;border-radius:6px;transition:outline-color 200ms ease}",
    ".chibi-tour{position:fixed;z-index:85;left:50%;bottom:calc(16px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);width:min(560px,calc(100% - 32px));display:grid;grid-template-columns:96px minmax(0,1fr);gap:12px;align-items:end;padding:14px 16px 14px 8px;border-radius:14px;background:var(--paper,#fff);color:var(--paper-ink,#121927);box-shadow:0 30px 60px -24px rgba(0,0,0,.6),0 0 0 1px rgba(18,25,39,.1)}",
    ".chibi-tour .chibi{--s:96px;position:relative;opacity:1;cursor:default}",
    ".chibi-tour .cb-say{margin:0;font:500 15px/1.45 var(--body,system-ui,sans-serif)}",
    ".chibi-tour .cb-k{font:500 11px var(--mono,monospace);letter-spacing:.07em;text-transform:uppercase;color:#4E586B;margin-bottom:4px}",
    ".chibi-tour .cb-acts{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}",
    ".chibi-tour[hidden]{display:none!important}",
    ".chibi-tour button[hidden]{display:none}",
    ".chibi-tour button{min-height:40px;padding:0 14px;border-radius:4px;border:1px solid rgba(18,25,39,.22);background:none;color:inherit;font:600 14px var(--body,system-ui,sans-serif);cursor:pointer}",
    ".chibi-tour button.cb-go{background:var(--amber,#F2A516);border-color:var(--amber,#F2A516);color:var(--on-amber,#1B1203)}",
    "@media (max-width:520px){.chibi-tour{grid-template-columns:72px minmax(0,1fr)}.chibi-tour .chibi{--s:72px}}",
    ".chibi-404{position:relative;--s:170px;display:block;margin:0 auto -18px;opacity:1}",
    "@media (hover:hover){.chibi-bub button:hover,.chibi-tour button:hover{border-color:var(--amber,#F2A516)}}",
    "@media (prefers-reduced-motion:reduce){.chibi,.chibi-bub,.chibi-dock{transition:none!important}}"
  ].join("\n");

  /* ---------- one animated character ---------- */
  function Sprite(el) {
    this.el = el; this.spr = el.querySelector(".spr"); this.timer = 0; this.name = ""; this.busy = false; this.done = null;
    this.el.style.setProperty("--sheet", 'url("' + SHEET + '")');
  }
  Sprite.prototype.frame = function (row, col) { this.spr.style.setProperty("--r", row); this.spr.style.setProperty("--c", col); };
  Sprite.prototype.play = function (name, opts) {
    opts = opts || {}; var m = MOVES[name]; if (!m) return; var self = this;
    clearTimeout(this.timer); this.name = name; this.busy = !m[3]; this.done = opts.then || null;
    var f = 0, times = opts.times || 1, loops = 0;
    if (reduce) {               /* still frame that reads well on its own */
      var still = { wave: 2, celebrate: 4, point: 4, thumbs: 5, idea: 6, resume: 3, worried: 2, confused: 0, typing: 0, idle: 0 }[name] || 0;
      this.frame(m[0], still);
      if (!m[3]) this.timer = setTimeout(function () { self.busy = false; var d = self.done; self.done = null; d ? d() : self.play("idle"); }, opts.hold || 1600);
      return;
    }
    (function tick() {
      self.frame(m[0], f);
      f++;
      if (f >= m[1]) { f = 0; loops++; if (!m[3] && loops >= times) { self.timer = setTimeout(function () { self.busy = false; var d = self.done; self.done = null; d ? d() : self.play("idle"); }, opts.hold || 120); return; } }
      self.timer = setTimeout(tick, 1000 / m[2]);
    })();
  };
  Sprite.prototype.look = function (dx, dy) {   /* dx, dy in -1..1 */
    if (this.busy) return;
    clearTimeout(this.timer); this.name = "look";
    this.frame(MOVES.look[0], (dy + 1) * 3 + (dx + 1));
  };

  function make(cls, label) {
    var el = document.createElement(label ? "button" : "div");
    if (label) { el.type = "button"; el.setAttribute("aria-label", label); }
    el.className = "chibi " + (cls || "");
    el.innerHTML = '<span class="spr" aria-hidden="true"></span>';
    return el;
  }
  function bubble(cls) { var b = document.createElement("div"); b.className = "chibi-bub " + (cls || ""); b.setAttribute("aria-hidden", "true"); return b; }
  function say(b, html, ms, interactive) {
    clearTimeout(b._t); b.innerHTML = html; b.classList.add("on");
    if (interactive) b.removeAttribute("aria-hidden"); else b.setAttribute("aria-hidden", "true");
    if (ms) b._t = setTimeout(function () { b.classList.remove("on"); b.setAttribute("aria-hidden", "true"); }, ms);
  }
  function hush(b) { clearTimeout(b._t); b.classList.remove("on"); b.setAttribute("aria-hidden", "true"); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function confetti(host) {
    if (reduce) return;
    var cols = ["#F2A516", "#5BE3FF", "#C8202B", "#43C08F", "#FFFFFF", "#2C4A7C"];
    for (var i = 0; i < 26; i++) {
      var c = document.createElement("i"), a = Math.random() * Math.PI * 2, r = 70 + Math.random() * 110;
      c.className = "chibi-confetti";
      c.style.cssText = "background:" + cols[i % cols.length] + ";--dx:" + Math.round(Math.cos(a) * r) + "px;--dy:" + Math.round(Math.sin(a) * r - 40) + "px;--rot:" + Math.round(Math.random() * 720 - 360) + "deg";
      host.appendChild(c);
      setTimeout(function (x) { return function () { x.remove(); }; }(c), 1200);
    }
  }

  /* ---------- the corner companion (wide screens) ---------- */
  var dock = null, dockSpr = null, dockBub = null;
  function gutterOk() {
    if (innerWidth < 1100) return false;
    var inner = document.querySelector("main .inner, .inner"); if (!inner) return false;
    var right = 0;
    document.querySelectorAll("main .inner").forEach(function (n) { var r = n.getBoundingClientRect(); if (r.bottom > 0 && r.top < innerHeight) right = Math.max(right, r.right); });
    if (!right) right = inner.getBoundingClientRect().right;
    return innerWidth - right - 46 >= 78;   /* 46 px = the index tabs; the cell's own padding covers the rest */
  }
  function buildDock() {
    if (dock) return;
    dock = document.createElement("div"); dock.className = "chibi-dock"; dock.setAttribute("role", "complementary"); dock.setAttribute("aria-label", "Chibi Alvin");
    var who = make("", "Chibi Alvin. Press to wave.");
    var x = document.createElement("button"); x.type = "button"; x.className = "cb-x"; x.setAttribute("aria-label", "Hide chibi Alvin"); x.textContent = "×";
    dockBub = bubble();
    dock.appendChild(dockBub); dock.appendChild(who); dock.appendChild(x);
    document.body.appendChild(dock);
    dockSpr = new Sprite(who); dockSpr.play("idle");
    who.addEventListener("click", function () { dockSpr.play("wave"); say(dockBub, "Kumusta! 👋", 2200); });
    x.addEventListener("click", function () { store.set("adm-chibi", "off"); dock.classList.remove("on"); hush(dockBub); });
  }
  var dockWanted = false;
  function updateDock(want) {
    if (want !== undefined) dockWanted = want;
    if (store.get("adm-chibi") === "off" || !dockWanted || !gutterOk() || tourOpen) { if (dock) dock.classList.remove("on"); return; }
    buildDock(); dock.classList.add("on");
  }
  function dockShown() { return dock && dock.classList.contains("on"); }

  /* react to something the visitor did: whichever Alvin is on screen plays it */
  var hero = null, heroSpr = null, heroBub = null;
  function heroVisible() { if (!hero) return false; var r = hero.getBoundingClientRect(); return r.bottom > 40 && r.top < innerHeight - 40; }
  function react(move, text, ms) {
    if (heroVisible()) { heroSpr.play(move, { hold: 900 }); if (text) say(heroBub, esc(text), ms || 2600); return; }
    if (!dockShown() && store.get("adm-chibi") !== "off") {
      if (gutterOk()) updateDock(true);
      else if (innerWidth >= 900 && !tourOpen) {   /* no free margin: pop in briefly, like a toast */
        buildDock(); dock.classList.add("on"); clearTimeout(dock._t);
        dock._t = setTimeout(function () { if (!(dockWanted && gutterOk())) { dock.classList.remove("on"); hush(dockBub); } }, (ms || 2800) + 400);
      }
    }
    if (dockShown()) { dockSpr.play(move, { hold: 900, then: function () { dockSpr.play(sectionMove || "idle"); } }); if (text) say(dockBub, esc(text), ms || 2800); }
  }
  window.addEventListener("chibi", function (e) { var d = e.detail || {}; react(d.move || "wave", d.say, d.ms); });

  /* ---------- section moods for the companion ---------- */
  var SECTIONS = PAGE === "case" ? {
    watch: ["typing", "This is the real app, recorded."], story: ["idea", "Scroll on. The picture follows."],
    "try": ["point", "Tap the answers. Try it!"], role: ["thumbs", "I decide, the AI drafts."]
  } : {
    projects: ["typing", "Flip through the files."], services: ["idea", "What can I build for you?"],
    cases: ["typing", "Real problems, real fixes."], about: ["wave", "Kumusta! That's me."],
    skills: ["thumbs", "Excel, AI, data, design."], experience: ["idea", "Teaching since 2017."],
    resume: ["resume", "Pick the version for your role."], contact: ["wave", "Let's talk!"]
  };
  var sectionMove = "idle", lastSec = "";
  function watchSections() {
    var targets = PAGE === "case" ? Object.keys(SECTIONS).map(function (id) { return document.getElementById(id); }).filter(Boolean)
                                  : [].slice.call(document.querySelectorAll("section[data-sec]"));
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (!en.isIntersecting) return;
        var key = PAGE === "case" ? en.target.id : en.target.getAttribute("data-sec");
        if (key === lastSec || !SECTIONS[key]) return; lastSec = key;
        var s = SECTIONS[key]; sectionMove = s[0] === "wave" || s[0] === "point" || s[0] === "thumbs" || s[0] === "resume" ? "idle" : s[0];
        updateDock(!heroVisible());
        if (dockShown()) { dockSpr.play(s[0], { then: function () { dockSpr.play(sectionMove); } }); say(dockBub, esc(s[1]), 3000); }
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    targets.forEach(function (t) { io.observe(t); });
  }

  /* ---------- tool reactions (watch the existing widgets, no changes to them needed) ---------- */
  function watchText(sel, fn) {
    var el = document.querySelector(sel); if (!el) return;
    var last = "";
    new MutationObserver(function () { var t = el.textContent || ""; if (t && t !== last) { last = t; fn(t); } }).observe(el, { childList: true, subtree: true, characterData: true });
  }
  function watchTools() {
    watchText("#jdOut", function (t) {
      var m = /(\d+)\s*\/\s*(\d+)/.exec(t); if (!m || +m[2] === 0) return; var r = +m[1] / +m[2];
      if (r >= .7) react("celebrate", "Strong match! Let's talk.");
      else if (r >= .4) react("idea", "Close fit. The gaps are listed honestly.");
      else react("worried", "Not my strongest fit, to be honest.");
    });
    watchText("#inqOut", function (t) {
      var l = t.toLowerCase();
      if (l.indexOf("please add") > -1) react("worried", "A few fields are still empty.");
      else if (l.indexOf("copied") > -1) react("thumbs", "Copied. Salamat!");
      else if (l.indexOf("email") > -1) react("wave", "Salamat! Talk soon.");
    });
    document.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest("#cvCard a, .cv-card a, a[href$='.pdf'], a[href$='.docx']");
      if (a) react("resume", "Good pick! That's the one.");
    });
    var pq = document.getElementById("pq");
    if (pq) pq.addEventListener("input", function () {
      if (pq.value.trim().toLowerCase() === "alvin") { react("celebrate", "You found me! 🎉"); var host = heroVisible() ? hero.parentNode : dock; if (host) confetti(heroVisible() ? hero : dock); }
    });
    watchText("#report", function (t) {   /* case page: item-analysis demo */
      if (t.indexOf("Every competency") > -1) react("celebrate", "All mastered! Galing!");
      else if ((t.match(/Re-teach /g) || []).length >= 2) react("worried", "Time for remediation.");
      else if (t.indexOf("Re-teach") > -1) react("idea", "One competency to re-teach.");
    });
  }

  /* ---------- the 60-second tour ---------- */
  var TOUR = [
    ["#reel", "point", "These are working systems, not mockups. Swipe through the files."],
    ["#excel", "typing", "Excel that does the reporting: SF9, attendance and item analysis."],
    ["#match", "idea", "Paste a job description and see how well I fit, gaps included."],
    ["#resume", "resume", "Grab the résumé written for your role. PDF or Word."]
  ];
  var tourOpen = false, tourEl = null, tourSpr = null, tourStep = 0, tourFrom = null;
  function tourShow(i) {
    tourStep = i; var st = TOUR[i], target = document.querySelector(st[0]);
    document.querySelectorAll(".chibi-tour-hl").forEach(function (n) { n.classList.remove("chibi-tour-hl"); });
    if (target) { var box = target.querySelector(".reel, .inner") || target; box.classList.add("chibi-tour-hl"); target.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }); }
    tourEl.querySelector(".cb-k").textContent = "Tour · " + (i + 1) + " of " + TOUR.length;
    tourEl.querySelector(".cb-say").textContent = st[2];
    tourEl.querySelector(".cb-prev").hidden = i === 0;
    tourEl.querySelector(".cb-next").textContent = i === TOUR.length - 1 ? "Finish" : "Next";
    tourSpr.play(st[1], { then: function () { tourSpr.play("idle"); } });
  }
  function tourClose() {
    tourOpen = false; document.querySelectorAll(".chibi-tour-hl").forEach(function (n) { n.classList.remove("chibi-tour-hl"); });
    if (tourEl) tourEl.hidden = true; updateDock(!heroVisible());
    if (tourFrom && document.contains(tourFrom)) tourFrom.focus();
  }
  function tourStart(from) {
    tourFrom = from || null;
    if (!tourEl) {
      tourEl = document.createElement("div"); tourEl.className = "chibi-tour"; tourEl.setAttribute("role", "dialog"); tourEl.setAttribute("aria-label", "60-second tour");
      tourEl.innerHTML = '<div class="chibi"><span class="spr" aria-hidden="true"></span></div><div><div class="cb-k"></div><p class="cb-say" aria-live="polite"></p>' +
        '<div class="cb-acts"><button type="button" class="cb-go cb-next">Next</button><button type="button" class="cb-prev">Back</button><button type="button" class="cb-skip">Skip tour</button></div></div>';
      document.body.appendChild(tourEl); tourSpr = new Sprite(tourEl.querySelector(".chibi"));
      tourEl.querySelector(".cb-next").addEventListener("click", function () {
        if (tourStep < TOUR.length - 1) tourShow(tourStep + 1);
        else { tourClose(); react("celebrate", "That's the tour. Salamat!"); }
      });
      tourEl.querySelector(".cb-prev").addEventListener("click", function () { tourShow(Math.max(0, tourStep - 1)); });
      tourEl.querySelector(".cb-skip").addEventListener("click", tourClose);
      tourEl.addEventListener("keydown", function (e) { if (e.key === "Escape") tourClose(); });
    }
    tourOpen = true; if (dock) dock.classList.remove("on"); tourEl.hidden = false;
    if (heroBub) hush(heroBub);
    tourShow(0); tourEl.querySelector(".cb-next").focus({ preventScroll: true });
  }

  /* ---------- home: the hero character ---------- */
  function buildHero() {
    var cab = document.getElementById("cab"); if (!cab) return;
    hero = make("chibi-hero", "Chibi Alvin. Press to say hi.");
    heroBub = bubble("chibi-hero-bub");
    cab.appendChild(hero); cab.appendChild(heroBub);
    heroSpr = new Sprite(hero);
    requestAnimationFrame(function () { hero.classList.add("on"); });
    var offered = false;
    heroSpr.play("wave", { then: function () {
      heroSpr.play("idle");
      if (!offered && !tourOpen) { offered = true; offerTour(); }
    } });
    say(heroBub, "Kumusta! I'm Alvin.", 2200);

    /* follow the mouse */
    var lastMove = 0, waved = 0, lean = 0;
    function face() { var r = hero.getBoundingClientRect(); return { x: r.left + r.width * .46, y: r.top + r.height * .36, r: r }; }
    if (fine) document.addEventListener("pointermove", function (e) {
      if (!heroVisible() || tourOpen) return;
      var f = face(), dx = e.clientX - f.x, dy = e.clientY - f.y, dist = Math.hypot(dx, dy);
      lastMove = Date.now();
      /* come close and he waves (at most every 6 s) */
      if (dist < f.r.width * .75 && Date.now() - waved > 6000 && !heroSpr.busy) { waved = Date.now(); heroSpr.play("wave"); say(heroBub, ["Kumusta!", "Hi there!", "Hello! 👋"][Math.floor(Math.random() * 3)], 1800); return; }
      if (heroSpr.busy) return;
      var gx = dist < 50 ? 0 : (dx < -dist * .38 ? -1 : dx > dist * .38 ? 1 : 0);
      var gy = dist < 50 ? 0 : (dy < -dist * .38 ? -1 : dy > dist * .38 ? 1 : 0);
      heroSpr.look(gx, gy);
      if (!reduce) { lean = Math.max(-5, Math.min(5, dx / 120)); hero.style.transform = "rotate(" + lean.toFixed(2) + "deg)"; }
    }, { passive: true });
    /* back to idle when the mouse rests */
    setInterval(function () {
      if (lastMove && Date.now() - lastMove > 2200 && heroSpr.name === "look") { heroSpr.play("idle"); hero.style.transform = ""; }
    }, 600);

    /* folders: point at the one you hover, cheer when you open it */
    document.querySelectorAll("#rig .folder").forEach(function (f) {
      var name = (f.querySelector(".front b") || {}).textContent || "this file";
      f.addEventListener("pointerenter", function () { if (!fine || tourOpen) return; heroSpr.busy = false; heroSpr.play("point", { hold: 1400 }); say(heroBub, "Open " + esc(name) + "?", 1800); });
      f.addEventListener("focus", function () { heroSpr.busy = false; heroSpr.play("point", { hold: 1400 }); say(heroBub, "Open " + esc(name) + "?", 1800); });
      f.addEventListener("click", function () { heroSpr.busy = false; heroSpr.play("celebrate"); say(heroBub, "Good choice!", 1500); });
    });

    /* click him: hi; five quick clicks: party */
    var clicks = [];
    hero.addEventListener("click", function () {
      var now = Date.now(); clicks = clicks.filter(function (t) { return now - t < 3000; }); clicks.push(now);
      heroSpr.busy = false;
      if (clicks.length >= 5) { clicks = []; heroSpr.play("celebrate", { times: 2 }); confetti(hero); say(heroBub, "Party mode! 🎉 You found the secret.", 2600); return; }
      if (store.get("adm-chibi") === "off") { store.set("adm-chibi", "on"); say(heroBub, "I'll walk with you again.", 2200); heroSpr.play("thumbs"); return; }
      offerTour(true);
      heroSpr.play("wave");
    });

    /* hero in view -> no corner companion */
    new IntersectionObserver(function (es) { updateDock(!es[0].isIntersecting); }).observe(hero);
  }
  function offerTour(force) {
    say(heroBub, 'Short on time?<div class="cb-row"><button type="button" class="cb-go" data-tour>Take the 60-second tour</button><button type="button" data-no>Later</button></div>', innerWidth < 760 ? 7000 : (force ? 9000 : 12000), true);
    heroBub.querySelector("[data-tour]").addEventListener("click", function (e) { tourStart(hero); });
    heroBub.querySelector("[data-no]").addEventListener("click", function () { hush(heroBub); heroSpr.play("thumbs"); });
  }

  /* ---------- 404 ---------- */
  function build404() {
    var main = document.querySelector("main .sheet") || document.querySelector("main"); if (!main) return;
    var c = make("chibi-404"); main.parentNode.insertBefore(c, main);
    var s = new Sprite(c); c.classList.add("on"); s.play("confused");
  }

  function start() {
    var st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    if (PAGE === "404") { build404(); return; }
    if (PAGE === "home") buildHero();
    watchSections(); watchTools();
    addEventListener("resize", function () { updateDock(); }, { passive: true });
    addEventListener("scroll", function () { if (dock && dockWanted) updateDock(); }, { passive: true });
    window.chibiAlvin = { react: react, tour: tourStart, hero: function () { return heroSpr; }, dock: function () { return dockSpr; } };
  }
  /* wait for the page to finish loading and the sheet to download, then appear */
  function boot() {
    var img = new Image(); img.decoding = "async";
    img.onload = start; img.onerror = function () {};
    img.src = SHEET;
  }
  function later() { (window.requestIdleCallback || function (f) { setTimeout(f, 300); })(boot, { timeout: 2000 }); }
  if (PAGE === "404") { document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", boot) : boot(); }
  else if (document.readyState === "complete") later(); else addEventListener("load", later);
})();
