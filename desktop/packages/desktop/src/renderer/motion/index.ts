/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

/** Kel's motion language (docs/v2/design/MOTION.md). */

export { SPRINGS, Spring, solveSpring, springFromDuration, springOvershoot, springSettleTime } from './spring';
export type { SpringName, SpringPreset, SpringState } from './spring';
export { TWEEN, cssSprings, installSpringProperties, springToCss, staggerDelay } from './easing';
export { enter, exit, rollLabel } from './choreography';
export { prefersReducedMotion, useReducedMotion } from './reducedMotion';
export { useFlip } from './flip';
export { EdgeIndicator, edgeClipPath } from './EdgeIndicator';
export { createMorph, morph } from './morph';
export type { MorphHandle, MorphOptions, MorphPresets } from './morph';
export { useSharedMorph } from './useSharedMorph';
