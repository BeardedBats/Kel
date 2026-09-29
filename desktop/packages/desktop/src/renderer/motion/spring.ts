/**
 * D-78 / MOTION.md §1 — Kel's springs. Closed form: a value at time t comes from a formula, not from
 * state stepped frame by frame, so it is exact, frame-rate independent and interruptible. An
 * interrupted spring re-seeds from its current position and velocity, so retargeting never jolts.
 *
 * One requestAnimationFrame loop drives every spring and tween, and it only runs while something
 * moves. The loop never reads layout; callers measure once before they start (§8).
 */

export type PresetName = 'micro' | 'snappy' | 'morph' | 'gentle';
export type SpringPreset = { duration: number; bounce: number };

/** duration = perceptual period (s); bounce = 1 − damping ratio. Overshoot stays at or under ~1.1%. */
export const PRESETS: Record<PresetName, SpringPreset> = {
  micro: { duration: 0.22, bounce: 0.1 },
  snappy: { duration: 0.34, bounce: 0.18 },
  morph: { duration: 0.48, bounce: 0.15 },
  gentle: { duration: 0.62, bounce: 0.1 },
};

export type SpringParams = { w: number; z: number; a: number; wd: number; k: number; c: number };

const TAU = Math.PI * 2;

export const springParams = (preset: PresetName | SpringPreset): SpringParams => {
  const p = typeof preset === 'string' ? PRESETS[preset] : preset;
  const w = TAU / p.duration;
  const z = Math.min(0.999, Math.max(0.05, 1 - p.bounce));
  return { w, z, a: z * w, wd: w * Math.sqrt(1 - z * z), k: w * w, c: 2 * z * w };
};

/** Displacement and velocity t seconds after release from displacement x0 with velocity v0. */
export const solveSpring = (sp: SpringParams, x0: number, v0: number, t: number): [number, number] => {
  const e = Math.exp(-sp.a * t);
  const B = (v0 + sp.a * x0) / sp.wd;
  const c = Math.cos(sp.wd * t);
  const s = Math.sin(sp.wd * t);
  return [e * (x0 * c + B * s), e * ((B * sp.wd - sp.a * x0) * c - (x0 * sp.wd + sp.a * B) * s)];
};

/** Seconds for a unit step to settle within eps and stay there for 50 ms. */
export const settleTime = (preset: PresetName | SpringPreset, eps = 0.001): number => {
  const sp = springParams(preset);
  const dt = 1 / 240;
  for (let t = 0; t < 5; t += dt) {
    const [x, v] = solveSpring(sp, 1, 0, t);
    if (Math.abs(x) < eps && Math.abs(v) < eps * sp.w) {
      let ok = true;
      for (let u = t; u < t + 0.05; u += dt) {
        if (Math.abs(solveSpring(sp, 1, 0, u)[0]) > eps) {
          ok = false;
          break;
        }
      }
      if (ok) return t;
    }
  }
  return 5;
};

/** Peak overshoot of a unit step (fraction), e.g. 0.011 for snappy. */
export const overshoot = (preset: PresetName | SpringPreset): number => {
  const sp = springParams(preset);
  return Math.exp((-Math.PI * sp.z) / Math.sqrt(1 - sp.z * sp.z));
};

/* ──────────────────────────────── the loop and its clock ──────────────────────────────── */

type Task = { step: (now: number) => boolean; resolve: () => void; done: boolean };

const tasks = new Set<Task>();
const writes = new Map<unknown, () => void>();
let clockNow = 0;
let lastTs: number | null = null;
let manual = false;
let scheduled = false;
let inTick = false;

const raf = (cb: FrameRequestCallback): void => {
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(cb);
  else setTimeout(() => cb(Date.now()), 16);
};

const flushWrites = () => {
  if (!writes.size) return;
  const list = Array.from(writes.values());
  writes.clear();
  for (const write of list) write();
};

const tick = () => {
  inTick = true;
  for (const task of Array.from(tasks)) {
    let finished = false;
    try {
      finished = task.step(clockNow);
    } catch (error) {
      console.error('[motion]', error);
      finished = true;
    }
    if (finished) {
      tasks.delete(task);
      task.done = true;
      task.resolve();
    }
  }
  inTick = false;
  flushWrites();
};

const frame = (ts: number) => {
  scheduled = false;
  if (!manual) {
    const dt = lastTs === null ? 16.667 : Math.min(50, Math.max(0, ts - lastTs));
    lastTs = ts;
    clockNow += dt;
    tick();
  }
  if (tasks.size && !manual) schedule();
  else lastTs = null;
};

const schedule = () => {
  if (scheduled || manual) return;
  scheduled = true;
  raf(frame);
};

/**
 * Write to the DOM once per frame for this key (several springs driving one element render once).
 * Outside a frame the write happens at once.
 */
export const frameWrite = (key: unknown, write: () => void): void => {
  if (inTick) writes.set(key, write);
  else write();
};

export const addTask = (step: (now: number) => boolean): { finished: Promise<void>; cancel: () => void; task: Task } => {
  let resolve: () => void = () => undefined;
  const finished = new Promise<void>((r) => {
    resolve = r;
  });
  const task: Task = { step, resolve, done: false };
  tasks.add(task);
  schedule();
  return {
    finished,
    task,
    cancel: () => {
      if (task.done) return;
      tasks.delete(task);
      task.done = true;
      resolve();
    },
  };
};

/** The animation clock in ms (it only advances while something moves). */
export const motionNow = (): number => clockNow;

/** Deterministic capture and tests: freeze the loop and step it by hand. */
export const motionClock = {
  setManual(on: boolean): void {
    manual = on;
    lastTs = null;
    if (!on && tasks.size) schedule();
  },
  isManual: (): boolean => manual,
  /** Step the clock synchronously in frame-sized slices. */
  advance(ms: number, frameMs = 1000 / 60): void {
    const steps = Math.max(1, Math.ceil(ms / frameMs));
    for (let i = 0; i < steps; i++) {
      clockNow += ms / steps;
      tick();
    }
  },
  /** Step and let promise chains between steps run (for choreography that awaits). */
  async advanceAsync(ms: number, frameMs = 1000 / 60): Promise<void> {
    const steps = Math.max(1, Math.ceil(ms / frameMs));
    for (let i = 0; i < steps; i++) {
      clockNow += ms / steps;
      tick();
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    }
  },
  active: (): number => tasks.size,
  /** Stop everything (tests). */
  reset(): void {
    for (const task of Array.from(tasks)) {
      tasks.delete(task);
      task.done = true;
      task.resolve();
    }
    writes.clear();
  },
};

/** Resolves after ms of animation-clock time. */
export const waitMotion = (ms: number): Promise<void> => {
  if (ms <= 0) return Promise.resolve();
  const end = clockNow + ms;
  return addTask((now) => now >= end).finished;
};

/* ──────────────────────────────── springs and tweens ──────────────────────────────── */

export type SpringHandle = {
  value: number;
  velocity: number;
  target: number;
  readonly done: boolean;
  readonly finished: Promise<void>;
  /** Aim somewhere else mid-flight, keeping position and velocity. */
  retarget: (to: number, preset?: PresetName | SpringPreset) => void;
  stop: () => void;
};

export type SpringOptions = { velocity?: number; delay?: number; eps?: number };

export const spring = (
  from: number,
  to: number,
  preset: PresetName | SpringPreset,
  onUpdate: (value: number, handle: SpringHandle) => void,
  opts: SpringOptions = {}
): SpringHandle => {
  let sp = springParams(preset);
  let t0 = clockNow + (opts.delay ?? 0);
  let x0 = from - to;
  let v0 = opts.velocity ?? 0;
  const eps = opts.eps ?? 0.01;
  let job: ReturnType<typeof addTask> | null = null;
  let resolveAll: () => void = () => undefined;
  let finished = new Promise<void>((r) => {
    resolveAll = r;
  });

  const handle: SpringHandle = {
    value: from,
    velocity: v0,
    target: to,
    get done() {
      return job === null;
    },
    get finished() {
      return finished;
    },
    retarget(next, nextPreset) {
      if (nextPreset) sp = springParams(nextPreset);
      const at = Math.max(clockNow, t0);
      x0 = handle.value - next;
      v0 = handle.velocity;
      t0 = at;
      handle.target = next;
      if (!job) start();
    },
    stop() {
      if (!job) return;
      const j = job;
      job = null;
      j.cancel();
      resolveAll();
    },
  };

  let resolved = false;
  const settle = resolveAll;
  resolveAll = () => {
    resolved = true;
    settle();
  };
  const start = () => {
    if (resolved) {
      // A settled spring that is retargeted gets a fresh promise.
      resolved = false;
      finished = new Promise<void>((r) => {
        resolveAll = () => {
          resolved = true;
          r();
        };
      });
    }
    job = addTask((now) => {
      if (now < t0) return false;
      const [x, v] = solveSpring(sp, x0, v0, (now - t0) / 1000);
      handle.value = handle.target + x;
      handle.velocity = v;
      if (Math.abs(x) < eps && Math.abs(v) < eps * 10) {
        handle.value = handle.target;
        handle.velocity = 0;
        onUpdate(handle.value, handle);
        job = null;
        resolveAll();
        return true;
      }
      onUpdate(handle.value, handle);
      return false;
    });
  };

  start();
  return handle;
};

export type Ease = 'out' | 'in' | 'inout' | 'linear';
export const EASES: Record<Ease, (x: number) => number> = {
  out: (x) => 1 - Math.pow(1 - x, 3),
  in: (x) => x * x * x,
  inout: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
  linear: (x) => x,
};

export type TweenHandle = { finished: Promise<void>; stop: () => void; readonly progress: number };

/** A timed tween (fades cannot overshoot, so opacity and blur never ride springs). */
export const tween = (
  from: number,
  to: number,
  ms: number,
  ease: Ease,
  onUpdate: (value: number, progress: number) => void,
  opts: { delay?: number } = {}
): TweenHandle => {
  const start = clockNow + (opts.delay ?? 0);
  const fn = EASES[ease];
  let progress = 0;
  onUpdate(from, 0);
  const job = addTask((now) => {
    if (now < start) return false;
    progress = Math.min(1, (now - start) / Math.max(1, ms));
    onUpdate(from + (to - from) * fn(progress), progress);
    return progress >= 1;
  });
  return {
    finished: job.finished,
    stop: job.cancel,
    get progress() {
      return progress;
    },
  };
};
