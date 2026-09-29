/**
 * MOTION.md §9 — no motion on first paint. Entrances are for things that arrive while Nick watches,
 * so a component that mounts as part of opening a page or a chat shows at once. A "scene" starts when
 * the app loads and whenever a chat or page opens; anything mounting within SCENE_QUIET_MS of that is
 * part of the first paint.
 */
import { useRef } from 'react';

export const SCENE_QUIET_MS = 900;

let sceneAt = typeof performance !== 'undefined' ? performance.now() : 0;

const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

/** A chat or page just opened: what mounts next is first paint, not an arrival. */
export const markScene = (): void => {
  sceneAt = now();
};

/** True when something mounting now would be arriving while Nick watches. */
export const isArrivalTime = (): boolean => now() - sceneAt > SCENE_QUIET_MS;

/** Tests: pretend the scene opened long ago (true) or just now (false). */
export const setSceneSettledForTests = (settled: boolean): void => {
  sceneAt = settled ? now() - SCENE_QUIET_MS * 10 : now();
};

/** Whether this component mounted as an arrival (fixed at its first render). */
export const useArrival = (): boolean => {
  const arrived = useRef<boolean | null>(null);
  if (arrived.current === null) arrived.current = isArrivalTime();
  return arrived.current;
};

/**
 * Call from the app layout with the route: a new page or chat starts a scene. It is marked during
 * render (the layout renders before the page's own components decide whether they are arrivals).
 */
export const useMotionScene = (key: string): void => {
  const last = useRef<string | null>(null);
  if (last.current !== key) {
    last.current = key;
    markScene();
  }
};
