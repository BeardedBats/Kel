/**
 * MOTION.md §2 — the timed (non-spring) parts, as tokens. Opacity and blur are tweens, never springs.
 */
export const MOTION = {
  /** Content exit: ease-in, all at once. */
  exitMs: 120,
  /** Content enter: ease-out, staggered. */
  enterMs: 200,
  /** Stagger between siblings, capped at 200 ms in total. */
  staggerMs: 35,
  staggerCapMs: 200,
  /** Surface colour change during a morph, starting 30 ms after the move. */
  surfaceColorMs: 240,
  surfaceColorDelayMs: 30,
  /** Backdrop in / out (out starts 80 ms late). */
  backdropMs: 200,
  backdropOutDelayMs: 80,
  /** Toasts. */
  toastStayMs: 2600,
  toastExitMs: 140,
  /** Reduced motion cross-fade. */
  reducedOutMs: 100,
  reducedInMs: 150,
  /** A label swap (roll). */
  rollMs: 200,
  /** A check drawing on. */
  drawMs: 260,
  /**
   * The settling fade (Nick, 2026-09-29): a state change that is the resting end of a chain and stays
   * on screen for more than ~5 s fades in slower — opacity plus a small blur-to-sharp, eased out.
   */
  settleMs: 520,
  settleBlurPx: 3,
  /** Reduced motion keeps a gentle cross-fade for settling states (never an instant swap). */
  settleReducedMs: 360,
  /** The hand-off flight waits this long after the line appears (D-78). */
  handoffBeatMs: 400,
} as const;

/** Blur radii (§5). */
export const BLUR = { enter: 6, exit: 4, roll: 3, stream: 3, popover: 4 } as const;
