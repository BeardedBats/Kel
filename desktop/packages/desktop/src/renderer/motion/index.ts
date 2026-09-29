/**
 * Kel's motion library (D-78, docs/v2/design/MOTION.md §11). No dependency beyond React.
 */
export * from './spring';
export * from './easing';
export * from './reduced';
export * from './tokens';
export * from './fx';
export * from './flip';
export * from './morph';
export * from './indicator';
export * from './settling';
export * from './arrival';
export * from './popover';
export * from './layoutProbe';
export { EdgePill, RollText, SwapIn, ProgressFill, fillTone, useEntrance, type FillTone } from './components';
export { useStreamFade } from './streamFade';
export { useMessageArrival, THINKING_MARK } from './messageArrival';

import { installMotionTokens } from './easing';
import { motionClock } from './spring';
import { setReducedMotionOverride } from './reduced';

/** Install the CSS tokens and the capture hook (window.__kelMotion: clock control only). */
export const initMotion = (): void => {
  installMotionTokens();
  if (typeof window !== 'undefined') {
    (window as unknown as { __kelMotion?: unknown }).__kelMotion = {
      manual: (on: boolean) => motionClock.setManual(on),
      advance: (ms: number) => motionClock.advance(ms),
      advanceAsync: (ms: number) => motionClock.advanceAsync(ms),
      active: () => motionClock.active(),
      reduced: (value: boolean | null) => setReducedMotionOverride(value),
    };
  }
};
