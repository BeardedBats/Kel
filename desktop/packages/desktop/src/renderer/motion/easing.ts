/**
 * MOTION.md §1 — the spring presets as CSS `linear()` easings sampled from the closed form, for the
 * places CSS must do the work (hover, :active, aria state). Generated, never typed by hand.
 */
import { PRESETS, settleTime, solveSpring, springParams, type PresetName, type SpringPreset } from './spring';

export type LinearEasing = { easing: string; duration: number };

export const linearEasing = (preset: PresetName | SpringPreset, points = 24): LinearEasing => {
  const d = settleTime(preset, 0.002);
  const sp = springParams(preset);
  const out: string[] = [];
  for (let i = 0; i <= points; i++) {
    const t = (i / points) * d;
    const v = i === points ? 1 : 1 - solveSpring(sp, 1, 0, t)[0];
    out.push(i === 0 || i === points ? v.toFixed(4).replace(/\.?0+$/, '') || '0' : `${v.toFixed(4)} ${((i / points) * 100).toFixed(1)}%`);
  }
  return { easing: `linear(${out.join(', ')})`, duration: Math.round(d * 1000) };
};

/** The custom properties Kel's CSS reads: --kel-spring-{name} and --kel-spring-{name}-ms. */
export const motionCustomProperties = (): Record<string, string> => {
  const props: Record<string, string> = {};
  for (const name of Object.keys(PRESETS) as PresetName[]) {
    const { easing, duration } = linearEasing(name);
    props[`--kel-spring-${name}`] = easing;
    props[`--kel-spring-${name}-ms`] = `${duration}ms`;
  }
  props['--kel-ease-out'] = 'cubic-bezier(0.215, 0.61, 0.355, 1)';
  props['--kel-ease-in'] = 'cubic-bezier(0.55, 0.055, 0.675, 0.19)';
  props['--kel-settle-ms'] = '520ms';
  return props;
};

let installed = false;

/** Write the spring custom properties once at startup (on :root). */
export const installMotionTokens = (root: HTMLElement | null = typeof document !== 'undefined' ? document.documentElement : null): void => {
  if (!root || installed) return;
  installed = true;
  for (const [name, value] of Object.entries(motionCustomProperties())) root.style.setProperty(name, value);
};
