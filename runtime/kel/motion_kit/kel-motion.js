/* Kel motion core (prototype). The Stage 2 renderer library is meant to grow out of this file.
   Everything is closed-form: a spring's value at time t comes from a formula, never from state
   stepped frame by frame. Interruptions re-seed a new spring from the current position and velocity. */
(function (global) {
  'use strict';
  const TAU = Math.PI * 2;

  /* Presets. duration = perceptual period (s); bounce = 1 - damping ratio. Every preset overshoots
     by 1.5% or less. stiffness/damping are for mass 1 (see MOTION.md). */
  const PRESETS = {
    micro:  { duration: 0.22, bounce: 0.10 }, // press, hover, ticks, icon swaps
    snappy: { duration: 0.34, bounce: 0.18 }, // indicators, chips, menus, rows
    morph:  { duration: 0.48, bounce: 0.15 }, // shared-element morphs (card <-> panel)
    gentle: { duration: 0.62, bounce: 0.10 }, // large travel: hand-off flight, sidebar list shifts
  };

  function params(p) {
    const P = typeof p === 'string' ? PRESETS[p] : p;
    const w = TAU / P.duration;
    const z = Math.min(0.999, Math.max(0.05, 1 - P.bounce));
    return { w, z, a: z * w, wd: w * Math.sqrt(1 - z * z), k: w * w, c: 2 * z * w, P };
  }

  /* Displacement and velocity t seconds after release from displacement x0 with velocity v0. */
  function solve(sp, x0, v0, t) {
    const e = Math.exp(-sp.a * t);
    const A = x0, B = (v0 + sp.a * x0) / sp.wd;
    const c = Math.cos(sp.wd * t), s = Math.sin(sp.wd * t);
    return [e * (A * c + B * s), e * ((B * sp.wd - sp.a * A) * c - (A * sp.wd + sp.a * B) * s)];
  }

  /* Time for a unit step to settle within eps (default 0.1%). */
  function settle(p, eps = 0.001) {
    const sp = params(p);
    let t = 0;
    for (; t < 5; t += 1 / 240) {
      const [x, v] = solve(sp, 1, 0, t);
      if (Math.abs(x) < eps && Math.abs(v) < eps * sp.w) {
        // confirm it stays settled for 50 ms
        let ok = true;
        for (let u = t; u < t + 0.05; u += 1 / 240) { if (Math.abs(solve(sp, 1, 0, u)[0]) > eps) { ok = false; break; } }
        if (ok) return t;
      }
    }
    return t;
  }

  /* CSS linear() easing that reproduces the preset from rest (for CSS transitions / WAAPI). */
  function linearEasing(p, points = 36) {
    const d = settle(p, 0.002);
    const sp = params(p);
    const out = [];
    for (let i = 0; i <= points; i++) {
      const t = (i / points) * d;
      const v = i === points ? 1 : 1 - solve(sp, 1, 0, t)[0];
      out.push(i === 0 || i === points ? v.toFixed(4) : `${v.toFixed(4)} ${((i / points) * 100).toFixed(1)}%`);
    }
    return { easing: `linear(${out.join(', ')})`, duration: Math.round(d * 1000) };
  }

  function overshoot(p) {
    const sp = params(p);
    return Math.exp(-Math.PI * sp.z / Math.sqrt(1 - sp.z * sp.z));
  }

  /* ---------- clock ---------- */
  const clock = { t: 0, scale: 1, manual: false, last: null };
  const tasks = new Set();
  function tick() {
    for (const task of Array.from(tasks)) {
      let done = false;
      try { done = task.step(clock.t); } catch (e) { console.error(e); done = true; }
      if (done) { tasks.delete(task); task.resolve && task.resolve(); }
    }
  }
  function frame(ts) {
    if (!clock.manual) {
      const dt = clock.last == null ? 16.67 : Math.min(50, ts - clock.last);
      clock.last = ts;
      clock.t += dt * clock.scale;
      tick();
    } else clock.last = ts;
    global.requestAnimationFrame(frame);
  }
  global.requestAnimationFrame(frame);

  function addTask(step) {
    let resolve;
    const finished = new Promise((r) => { resolve = r; });
    const task = { step, resolve };
    tasks.add(task);
    task.finished = finished;
    return task;
  }

  const M = {
    PRESETS, params, solve, settle, linearEasing, overshoot, clock,
    reduced: false,
    now: () => clock.t,
    /* Manual clock control for deterministic capture. */
    manual(on) { clock.manual = !!on; },
    /* Deterministic capture: step the clock in frame-sized slices and let promise chains run between them. */
    async advance(ms) {
      const steps = Math.max(1, Math.ceil(ms / 16.667));
      for (let i = 0; i < steps; i++) { clock.t += ms / steps; tick(); await new Promise((r) => setTimeout(r, 0)); await new Promise((r) => setTimeout(r, 0)); }
    },
    setScale(s) { clock.scale = s; },

    wait(ms) {
      if (ms <= 0) return Promise.resolve();
      const end = clock.t + ms;
      return addTask((now) => now >= end).finished;
    },

    /* One spring value. Returns a handle that can be retargeted mid-flight (velocity is kept). */
    spring(from, to, preset, onUpdate, opts = {}) {
      const h = { value: from, target: to, velocity: opts.velocity || 0, done: false };
      if (M.reduced && !opts.always) {
        h.value = to; onUpdate(to, h); h.done = true; h.finished = Promise.resolve(); h.retarget = (nt) => { h.target = nt; h.value = nt; onUpdate(nt, h); }; h.stop = () => {};
        return h;
      }
      let sp = params(preset);
      let t0 = clock.t + (opts.delay || 0), x0 = from - to, v0 = h.velocity;
      const eps = opts.eps || 0.01;
      const task = addTask((now) => {
        if (now < t0) return false;
        const [x, v] = solve(sp, x0, v0, (now - t0) / 1000);
        h.value = h.target + x; h.velocity = v;
        if (Math.abs(x) < eps && Math.abs(v) < eps * 10) { h.value = h.target; h.velocity = 0; onUpdate(h.value, h); h.done = true; return true; }
        onUpdate(h.value, h);
        return false;
      });
      h.finished = task.finished;
      h.retarget = (nt, np) => {
        if (np) sp = params(np);
        const now = Math.max(clock.t, t0);
        x0 = h.value - nt; v0 = h.velocity; t0 = now; h.target = nt;
        if (h.done) { h.done = false; tasks.add(task); }
      };
      h.stop = () => { tasks.delete(task); task.resolve(); };
      return h;
    },

    /* Several named values sharing one preset; onUpdate gets the whole object. */
    springs(from, to, preset, onUpdate, opts = {}) {
      const cur = Object.assign({}, from);
      const keys = Object.keys(to);
      let pending = keys.length;
      const handles = {};
      let res;
      const finished = new Promise((r) => { res = r; });
      let scheduled = false;
      const flush = () => { scheduled = false; onUpdate(cur); };
      keys.forEach((k) => {
        const pk = (opts.presets && opts.presets[k]) || preset;
        handles[k] = M.spring(from[k], to[k], pk, (v) => { cur[k] = v; if (!scheduled) { scheduled = true; queueMicrotask(flush); } }, Object.assign({}, opts, { delay: (opts.delays && opts.delays[k]) || opts.delay || 0 }));
        handles[k].finished.then(() => { if (--pending === 0) { onUpdate(cur); res(); } });
      });
      return { handles, finished, value: cur,
        retarget(nt, np) { for (const k of Object.keys(nt)) handles[k] && handles[k].retarget(nt[k], np); } };
    },

    /* Plain timed tween (fades). ease: 'out' | 'in' | 'inout' | 'linear'. */
    tween(from, to, ms, ease, onUpdate, opts = {}) {
      const E = { out: (x) => 1 - Math.pow(1 - x, 3), in: (x) => x * x * x, inout: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2), linear: (x) => x }[ease || 'out'];
      const start = clock.t + (opts.delay || 0);
      onUpdate(from);
      return addTask((now) => {
        if (now < start) return false;
        const p = Math.min(1, (now - start) / Math.max(1, ms));
        onUpdate(from + (to - from) * E(p));
        return p >= 1;
      }).finished;
    },
  };

  /* ---------- DOM helpers ---------- */
  const setFx = (el, o, blur, y, s) => {
    el.style.opacity = o.toFixed(3);
    el.style.filter = blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : '';
    const tf = [];
    if (y) tf.push(`translateY(${y.toFixed(2)}px)`);
    if (s != null && s !== 1) tf.push(`scale(${s.toFixed(4)})`);
    el.style.transform = tf.join(' ');
  };
  M.setFx = setFx;

  /* Content enters after its container has started to move: opacity up, blur and offset away. */
  M.enter = (el, opts = {}) => {
    if (!el) return Promise.resolve();
    const els = Array.isArray(el) || el instanceof NodeList ? Array.from(el) : [el];
    const y = opts.y ?? 6, blur = opts.blur ?? 6, ms = opts.ms ?? 220, gap = opts.stagger ?? 0, delay = opts.delay || 0, s0 = opts.scale;
    const all = els.map((e, i) => {
      if (M.reduced) { setFx(e, 0, 0, 0); return M.tween(0, 1, 140, 'linear', (v) => setFx(e, v, 0, 0), { delay: delay + Math.min(i * gap, 90) * 0.5 }); }
      setFx(e, 0, blur, y, s0);
      return M.tween(0, 1, ms, 'out', (v) => setFx(e, v, blur * (1 - v), y * (1 - v), s0 != null ? s0 + (1 - s0) * v : null), { delay: delay + Math.min(i * gap, 200) });
    });
    return Promise.all(all).then(() => els.forEach((e) => { e.style.filter = ''; e.style.transform = ''; e.style.opacity = ''; }));
  };
  /* Content leaves before the next morph: quick fade with a little blur. */
  M.exit = (el, opts = {}) => {
    if (!el) return Promise.resolve();
    const els = Array.isArray(el) || el instanceof NodeList ? Array.from(el) : [el];
    const y = opts.y ?? -4, blur = opts.blur ?? 4, ms = opts.ms ?? 120, delay = opts.delay || 0, s1 = opts.scale;
    return Promise.all(els.map((e) => {
      const o0 = e.style.opacity === '' ? 1 : +e.style.opacity;
      if (M.reduced) return M.tween(o0, 0, 100, 'linear', (v) => setFx(e, v, 0, 0), { delay });
      return M.tween(0, 1, ms, 'in', (p) => setFx(e, o0 * (1 - p), blur * p, y * p, s1 != null ? 1 + (s1 - 1) * p : null), { delay });
    }));
  };

  /* An indicator whose two edges ride separate springs: the leading edge is quicker, so it stretches
     toward the target and the trailing edge catches up. Drawn with clip-path (paint only, no layout). */
  M.edgeIndicator = (el, opts = {}) => {
    const st = { l: opts.l || 0, r: opts.r || 0, t: opts.t || 0, b: opts.b || 0, hl: null, hr: null, ht: null, hb: null };
    const axis = opts.axis || 'x';
    const radius = opts.radius ?? 6;
    const render = () => {
      const W = el.offsetParent ? el.clientWidth : 0; // read once per render call only when needed
      const box = el._box || (el._box = { w: el.clientWidth, h: el.clientHeight });
      if (axis === 'x') el.style.clipPath = `inset(0 ${Math.max(0, box.w - st.r).toFixed(2)}px 0 ${st.l.toFixed(2)}px round ${radius}px)`;
      else el.style.clipPath = `inset(${st.t.toFixed(2)}px 0 ${Math.max(0, box.h - st.b).toFixed(2)}px 0 round ${radius}px)`;
      void W;
    };
    const api = {
      state: st,
      set(a, b) { if (axis === 'x') { st.l = a; st.r = b; } else { st.t = a; st.b = b; } render(); },
      measure() { el._box = { w: el.clientWidth, h: el.clientHeight }; render(); },
      to(a, b, o = {}) {
        const lead = o.lead || 'micro', trail = o.trail || 'morph';
        const [k0, k1] = axis === 'x' ? ['l', 'r'] : ['t', 'b'];
        const forward = axis === 'x' ? b >= st.r : b >= st.b;
        const p0 = forward ? trail : lead, p1 = forward ? lead : trail;
        const d1 = o.trailDelay ?? 30;
        const h0 = axis === 'x' ? 'hl' : 'ht', h1 = axis === 'x' ? 'hr' : 'hb';
        if (M.reduced) { st[k0] = a; st[k1] = b; render(); return Promise.resolve(); }
        if (st[h0] && !st[h0].done) st[h0].retarget(a, p0); else st[h0] = M.spring(st[k0], a, p0, (v) => { st[k0] = v; render(); }, { delay: forward ? d1 : 0, eps: 0.05 });
        if (st[h1] && !st[h1].done) st[h1].retarget(b, p1); else st[h1] = M.spring(st[k1], b, p1, (v) => { st[k1] = v; render(); }, { delay: forward ? 0 : d1, eps: 0.05 });
        return Promise.all([st[h0].finished, st[h1].finished]);
      },
    };
    render();
    return api;
  };

  /* Shared-element morph surface. One element changes position, size, radius and colour; content
     layers inside it are anchored at their final size (so they never reflow) and swap on the way.
     The surface is out of flow with contain: strict, so writing its geometry lays out nothing else. */
  M.surface = (layer, cls) => {
    const el = document.createElement('div');
    el.className = 'km-surface ' + (cls || '');
    layer.appendChild(el);
    const st = { x: 0, y: 0, w: 0, h: 0, r: 10, bg: [0, 0, 0, 0], bd: [0, 0, 0, 0], bw: 1, sh: 0 };
    const col = (c) => `rgba(${c[0].toFixed(1)},${c[1].toFixed(1)},${c[2].toFixed(1)},${c[3].toFixed(3)})`;
    const render = () => {
      el.style.transform = `translate(${st.x.toFixed(2)}px, ${st.y.toFixed(2)}px)`;
      el.style.width = `${Math.max(0, st.w).toFixed(2)}px`;
      el.style.height = `${Math.max(0, st.h).toFixed(2)}px`;
      el.style.borderRadius = `${Math.max(0, st.r).toFixed(2)}px`;
      el.style.background = col(st.bg);
      el.style.borderColor = col(st.bd);
      el.style.borderWidth = `${st.bw}px`;
      el.style.boxShadow = st.sh > 0 ? `0 20px 48px -16px rgba(0,0,0,${(0.35 * st.sh).toFixed(3)}), inset 0 1px 0 rgba(191,216,255,${(0.18 * st.sh).toFixed(3)})` : '';
    };
    const api = {
      el, st,
      set(o) { Object.assign(st, o); render(); },
      /* Animate to a rect/style. Each edge can ride its own preset (o.edges) for a stretchy morph. */
      to(o, preset = 'morph', opts = {}) {
        const jobs = [];
        const geo = ['x', 'y', 'w', 'h', 'r'].filter((k) => o[k] != null);
        if (M.reduced) { Object.assign(st, o); render(); return Promise.resolve(); }
        for (const k of geo) {
          const pk = (opts.presets && opts.presets[k]) || preset;
          jobs.push(M.spring(st[k], o[k], pk, (v) => { st[k] = v; render(); }, { delay: (opts.delays && opts.delays[k]) || 0, eps: 0.3 }).finished);
        }
        for (const k of ['bg', 'bd']) {
          if (!o[k]) continue;
          const a = st[k].slice(), b = o[k];
          jobs.push(M.tween(0, 1, opts.colorMs || 260, 'out', (p) => { st[k] = a.map((v, i) => v + (b[i] - v) * p); render(); }, { delay: opts.colorDelay || 0 }));
        }
        if (o.sh != null) { const a = st.sh; jobs.push(M.tween(0, 1, 220, 'out', (p) => { st.sh = a + (o.sh - a) * p; render(); })); }
        if (o.bw != null) st.bw = o.bw;
        return Promise.all(jobs);
      },
      remove() { el.remove(); },
    };
    render();
    return api;
  };

  /* FLIP for in-flow siblings: record rects, mutate the DOM, then spring each element from its old
     place to its new place with transform only. */
  M.flip = (els, mutate, preset = 'snappy', opts = {}) => {
    const list = Array.from(els);
    const before = new Map(list.map((e) => [e, e.getBoundingClientRect()]));
    mutate();
    const scale = opts.scale || 1;
    const jobs = [];
    for (const e of list) {
      if (!e.isConnected) continue;
      const a = before.get(e), b = e.getBoundingClientRect();
      const dx = (a.left - b.left) / scale, dy = (a.top - b.top) / scale;
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) continue;
      if (M.reduced) continue;
      e.style.transform = `translate(${dx}px, ${dy}px)`;
      const s = { x: dx, y: dy };
      jobs.push(M.springs(s, { x: 0, y: 0 }, preset, (v) => { e.style.transform = Math.abs(v.x) < 0.01 && Math.abs(v.y) < 0.01 ? '' : `translate(${v.x.toFixed(2)}px, ${v.y.toFixed(2)}px)`; }, { delay: opts.delay || 0 }).finished);
    }
    return Promise.all(jobs);
  };

  /* A check mark that draws on (stroke-dashoffset on an SVG path). */
  M.drawOn = (path, ms = 260, delay = 0) => {
    const len = path.getTotalLength();
    path.style.strokeDasharray = `${len}`;
    if (M.reduced) { path.style.strokeDashoffset = '0'; return Promise.resolve(); }
    return M.tween(len, 0, ms, 'out', (v) => { path.style.strokeDashoffset = `${v}`; }, { delay });
  };

  global.KelMotion = M;
})(window);

/* D-88 (WRITER_ANIMATOR_ROLES.md §3.7): the house spring core for standalone pages, copied from Kel's
   motion prototype (Tools\motion\src\kel-motion.js). Reduced motion follows the OS setting, and the
   seekable clock is exposed as window.__motion so Kel's motion checks capture exact frames:
     window.__motion.manual(true); await window.__motion.advance(16.7);
   A page registers each moment it animates:
     window.__motion.moments['cards-enter'] = { run: () => enterCards(), targets: ['.card'] };  */
(function (global) {
  'use strict';
  const M = global.KelMotion;
  if (!M) return;
  const query = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)') : null;
  if (query) {
    M.reduced = query.matches;
    if (query.addEventListener) query.addEventListener('change', (e) => { M.reduced = e.matches; });
  }
  const hook = global.__motion || {};
  hook.manual = (on) => M.manual(on);
  hook.advance = (ms) => M.advance(ms);
  hook.moments = hook.moments || {};
  global.__motion = hook;
})(window);
