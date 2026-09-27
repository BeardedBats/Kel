/**
 * D-61 — Kel ships in English (en-US) only: every language hint resolves to en-US, i18next knows no
 * other language, and no other locale bundle or language picker remains.
 */
import { existsSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalizeLanguageCode } from '@/common/config/i18n';

const here = path.dirname(fileURLToPath(import.meta.url));
const renderer = path.resolve(here, '../../packages/desktop/src/renderer');

describe('English only (D-61)', () => {
  it('resolves every language hint to en-US', () => {
    expect(DEFAULT_LANGUAGE).toBe('en-US');
    expect(SUPPORTED_LANGUAGES).toEqual(['en-US']);
    for (const hint of ['zh-CN', 'ja', 'fa-IR', 'de_DE', 'en-GB', '', undefined, null]) {
      expect(normalizeLanguageCode(hint)).toBe('en-US');
    }
  });

  it('loads only the en-US strings into i18next', async () => {
    const { default: i18n } = await import('@/renderer/services/i18n');
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(i18n.language).toBe('en-US');
    expect(Object.keys(i18n.store.data)).toEqual(['en-US']);
    expect(i18n.t('login.brand')).toBe('Kel');
    await i18n.changeLanguage('zh-CN');
    // Unknown languages fall back to English strings.
    expect(i18n.t('login.brand')).toBe('Kel');
  });

  it('ships no other locale bundle and no language picker', () => {
    expect(readdirSync(path.join(renderer, 'services/i18n/locales'))).toEqual(['en-US']);
    expect(existsSync(path.join(renderer, 'components/settings/LanguageSwitcher.tsx'))).toBe(false);
  });
});
