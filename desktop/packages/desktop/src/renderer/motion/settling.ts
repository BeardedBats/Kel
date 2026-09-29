/**
 * The settling-fade rule (Nick, 2026-09-29; MOTION.md §2.1). When something changes state in place
 * and the new state is BOTH the resting end of its chain AND will stay on screen for more than about
 * five seconds, it arrives with the longer settling fade (MOTION.settleMs). Intermediate states, and
 * anything gone within five seconds, keep the quicker enter.
 */
export type TransitionKind = 'settling' | 'quick';

/** How long a state must stay on screen to count as resting. */
export const SETTLE_MIN_STAY_MS = 5000;

export type TransitionFacts = {
  /** The new state is the final item of its chain (nothing follows it on its own). */
  final: boolean;
  /** How long it is expected to stay on screen (Infinity for "until Nick acts"). */
  staysMs: number;
};

export const classifyTransition = ({ final, staysMs }: TransitionFacts): TransitionKind =>
  final && staysMs > SETTLE_MIN_STAY_MS ? 'settling' : 'quick';

const FINISHED = new Set(['done', 'failed', 'stopped']);

/** A work card, detail header or in-thread line reaching Done, Failed or Stopped. */
export const cardStateTransition = (state: string | null | undefined): TransitionKind =>
  classifyTransition({ final: FINISHED.has(String(state ?? '')), staysMs: FINISHED.has(String(state ?? '')) ? Infinity : 4000 });

/** A step ticking: only the last step's tick is the resting end of the steps. */
export const stepTickTransition = (index: number, total: number): TransitionKind =>
  classifyTransition({ final: total > 0 && index === total - 1, staysMs: Infinity });

/**
 * Named moments and their kind (tests and MOTION.md keep this list honest). "quick" entries are
 * intermediate states or things that leave within five seconds.
 */
export const SETTLING_MOMENTS: Record<string, TransitionFacts> = {
  'card reaches done/failed/stopped': { final: true, staysMs: Infinity },
  'done check draws on': { final: true, staysMs: Infinity },
  'result card: Done and checked': { final: true, staysMs: Infinity },
  'You answered · Kel is continuing': { final: true, staysMs: Infinity },
  'scoping summary after Start': { final: true, staysMs: Infinity },
  'staff fallback note': { final: true, staysMs: Infinity },
  'last step ticked': { final: true, staysMs: Infinity },
  'needs you → answered': { final: true, staysMs: Infinity },
  'Undone: the earlier files are back': { final: true, staysMs: Infinity },
  'card working → in review': { final: false, staysMs: 60000 },
  'a middle step ticked': { final: false, staysMs: Infinity },
  'Thinking… row': { final: false, staysMs: 3000 },
  toast: { final: true, staysMs: 2600 },
  'menu opening': { final: false, staysMs: 3000 },
};
