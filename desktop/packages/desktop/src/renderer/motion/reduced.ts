/**
 * MOTION.md §7 — reduced motion follows the Windows (OS) setting only (D-78: no in-app switch). The
 * library checks the media query itself because it does not use CSS transitions.
 */
import { useSyncExternalStore } from 'react';

const QUERY = '(prefers-reduced-motion: reduce)';
let override: boolean | null = null;
const listeners = new Set<() => void>();

const media = (): MediaQueryList | null =>
  typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia(QUERY) : null;

export const isReducedMotion = (): boolean => {
  if (override !== null) return override;
  return Boolean(media()?.matches);
};

/** Tests only: force reduced motion on or off (null follows the OS again). */
export const setReducedMotionOverride = (value: boolean | null): void => {
  override = value;
  listeners.forEach((listener) => listener());
};

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  const mq = media();
  mq?.addEventListener?.('change', listener);
  return () => {
    listeners.delete(listener);
    mq?.removeEventListener?.('change', listener);
  };
};

export const useReducedMotion = (): boolean => useSyncExternalStore(subscribe, isReducedMotion, () => false);
