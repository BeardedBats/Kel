/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import type { Theme } from '@/common/theme/types';
import { THEME_TOKENS } from '@/common/theme/tokenContract';
import { configService } from '@/common/config/configService';
import { ipcBridge } from '@/common';
import { resolveActiveTheme } from '@/common/theme/resolveTheme';
import { DARK_THEME_ID } from '@/common/theme/constants';
import { BUILTIN_THEMES } from '@renderer/theme/builtinThemes';
import { processCustomCss } from './customCssProcessor';
import { tokensToCss } from './tokensToCss';
import { getSystemPrefersDark } from './systemAppearance';

const TOKENS_STYLE_ID = 'theme-tokens';
const DECORATION_STYLE_ID = 'theme-decoration';

function upsertStyle(id: string, css: string | null, root: Document = document): void {
  const existing = root.getElementById(id);
  if (!css) {
    existing?.remove();
    return;
  }
  const el = (existing as HTMLStyleElement | null) ?? root.createElement('style');
  el.id = id;
  el.textContent = css;
  root.head.appendChild(el); // (re)append to keep it last in <head>
}

function isElectronRenderer(): boolean {
  return typeof window !== 'undefined' && Boolean((window as Window & { electronAPI?: unknown }).electronAPI);
}

async function publishThemeToElectron(theme: Theme): Promise<void> {
  if (!isElectronRenderer()) return;
  await ipcBridge.theme.setActive.invoke(theme);
}

/**
 * Write the two appearance attributes as one coupled unit:
 *  - `data-theme` on `<html>` drives our own design tokens
 *  - `arco-theme` on `<body>` drives Arco's color scales and the
 *    `body[arco-theme='dark']` overrides in arco-override.css
 *
 * Both must stay in sync or dark mode splits (our tokens go dark while Arco
 * stays light). `<html>` always exists; `<body>` can be null during early boot
 * (`readyState === 'loading'`). In that case we must NOT silently skip the
 * `arco-theme` write — defer it to DOMContentLoaded so the two attributes still
 * converge once the body is parsed.
 */
function applyAppearanceAttributes(root: Document, appearance: Theme['appearance']): void {
  root.documentElement.setAttribute('data-theme', appearance);
  if (root.body) {
    root.body.setAttribute('arco-theme', appearance);
    return;
  }
  root.addEventListener(
    'DOMContentLoaded',
    () => {
      root.body?.setAttribute('arco-theme', appearance);
    },
    { once: true }
  );
}

type ThemeOverrides = Record<string, Record<string, string>>;

/** Semantic color overrides the user saved for one theme (built-in defaults are untouched). */
export function themeOverrides(themeId: string): Record<string, string> {
  const all = (configService.get('theme.overrides') as ThemeOverrides | undefined) ?? {};
  return all[themeId] ?? {};
}

/** Apply a resolved theme to a document. Used by every app-chrome surface. */
export function applyTheme(theme: Theme, root: Document = document): void {
  applyAppearanceAttributes(root, theme.appearance);
  const overrides = themeOverrides(theme.id);
  // Inline user choices win against appearance-specific default selectors.
  // Remove only contract keys, leaving font settings and unrelated inline styles intact.
  for (const { key } of THEME_TOKENS) {
    if (overrides[key]) root.documentElement.style.setProperty(key, overrides[key]);
    else root.documentElement.style.removeProperty(key);
  }
  // Shell glass has several layers. Explicit color choices replace those layers as a unit.
  const shellColors: Record<string, string> = {
    '--bg-base': '--kel-shell-custom-canvas', '--bg-1': '--kel-shell-custom-panel',
    '--bg-2': '--kel-shell-custom-elevated', '--text-primary': '--kel-shell-custom-text',
    '--text-secondary': '--kel-shell-custom-secondary', '--border-base': '--kel-shell-custom-border',
    '--primary': '--kel-shell-custom-accent',
  };
  for (const [token, alias] of Object.entries(shellColors)) {
    if (overrides[token]) root.documentElement.style.setProperty(alias, overrides[token]);
    else root.documentElement.style.removeProperty(alias);
  }
  const hasOverrides = Object.keys(overrides).length > 0;
  const tokens = hasOverrides ? { ...(theme.tokens ?? {}), ...overrides } : theme.tokens;
  upsertStyle(TOKENS_STYLE_ID, tokensToCss(tokens as Theme['tokens']), root);
  upsertStyle(DECORATION_STYLE_ID, theme.css ? processCustomCss(theme.css) : null, root);
}

async function reapplyIfActive(themeId: string): Promise<Theme> {
  const userThemes = (configService.get('theme.userThemes') as Theme[] | undefined) ?? [];
  const activeId = (configService.get('theme.activeId') as string | undefined) || DARK_THEME_ID;
  const resolved = resolveActiveTheme(activeId, [...BUILTIN_THEMES, ...userThemes], getSystemPrefersDark());
  if (resolved.id === themeId) {
    applyTheme(resolved);
    await publishThemeToElectron(resolved);
  }
  return resolved;
}

/** Set or remove one semantic color override for a theme; applies live when that theme is active. */
export async function setThemeOverride(themeId: string, token: string, value: string | null): Promise<void> {
  const all = { ...((configService.get('theme.overrides') as ThemeOverrides | undefined) ?? {}) };
  const current = { ...(all[themeId] ?? {}) };
  if (value) {
    current[token] = value;
  } else {
    delete current[token];
  }
  if (Object.keys(current).length > 0) {
    all[themeId] = current;
  } else {
    delete all[themeId];
  }
  await configService.set('theme.overrides', all);
  await reapplyIfActive(themeId);
}

/** Restore every saved color for one theme. */
export async function clearThemeOverrides(themeId: string): Promise<void> {
  const all = { ...((configService.get('theme.overrides') as ThemeOverrides | undefined) ?? {}) };
  delete all[themeId];
  await configService.set('theme.overrides', all);
  await reapplyIfActive(themeId);
}

/** Resolve `activeId` locally, apply, persist, and publish to Electron for cross-window broadcast. */
export async function setActiveTheme(activeId: string): Promise<Theme> {
  const userThemes = (configService.get('theme.userThemes') as Theme[] | undefined) ?? [];
  const resolved = resolveActiveTheme(activeId, [...BUILTIN_THEMES, ...userThemes], getSystemPrefersDark());
  applyTheme(resolved);
  await configService.set('theme.activeId', activeId);
  await publishThemeToElectron(resolved);
  return resolved;
}

/** Seed Electron's cross-window theme relay. WebUI has no Electron surfaces to notify. */
export async function seedElectronTheme(theme: Theme): Promise<void> {
  await publishThemeToElectron(theme);
}
