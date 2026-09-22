import { describe, expect, it, vi } from 'vitest';
const state = vi.hoisted(() => ({ overrides: {} as Record<string, Record<string, string>> }));
vi.mock('@/common/config/configService', () => ({ configService: { get: (key: string) => key === 'theme.overrides' ? state.overrides : undefined } }));
vi.mock('@/common', () => ({ ipcBridge: {} }));
import { applyTheme } from '@renderer/utils/theme/applyTheme';
import { BUILTIN_THEMES } from '@renderer/theme/builtinThemes';

describe('shell appearance override lifecycle', () => {
  it('applies explicit colors and removes them when switching themes without deleting font choices', () => {
    const doc = document.implementation.createHTMLDocument('theme');
    doc.documentElement.style.setProperty('--app-font-family', 'Test font');
    state.overrides = { dark: { '--bg-base': '#123456', '--bg-1': '#234567', '--success': '#445566' } };
    applyTheme(BUILTIN_THEMES.find(t => t.id === 'dark')!, doc);
    expect(doc.documentElement.style.getPropertyValue('--kel-shell-custom-canvas')).toBe('#123456');
    expect(doc.documentElement.style.getPropertyValue('--kel-shell-custom-panel')).toBe('#234567');
    expect(doc.documentElement.style.getPropertyValue('--success')).toBe('#445566');
    applyTheme(BUILTIN_THEMES.find(t => t.id === 'light')!, doc);
    expect(doc.documentElement.style.getPropertyValue('--kel-shell-custom-canvas')).toBe('');
    expect(doc.documentElement.style.getPropertyValue('--success')).toBe('');
    expect(doc.documentElement.style.getPropertyValue('--app-font-family')).toBe('Test font');
    expect(doc.body.getAttribute('arco-theme')).toBe('light');
    expect(state.overrides.dark['--bg-base']).toBe('#123456');
  });
});
