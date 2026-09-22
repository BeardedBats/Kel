/**
 * Theme colors — semantic foundation controls for the CURRENTLY SELECTED theme.
 *
 * The user adjusts plain semantic colors (App background, Panels, Accent, ...); the values are
 * stored as per-theme overrides and merged over the theme's base tokens when it is applied.
 * Built-in themes are never mutated: switching themes keeps each theme's own overrides, and
 * "Restore all colors" removes them for the selected theme only.
 */
import React, { useCallback, useMemo, useState } from 'react';
import { Button, Input, Message, Tooltip } from '@arco-design/web-react';
import { THEME_TOKENS } from '@/common/theme/tokenContract';
import { configService } from '@/common/config/configService';
import { BUILTIN_THEMES } from '@renderer/theme/builtinThemes';
import type { Theme } from '@/common/theme/types';
import { clearThemeOverrides, setThemeOverride, themeOverrides } from '@renderer/utils/theme/applyTheme';

type FeaturedRow = { token: string; label: string; why: string };

/** The ten semantic colors a person actually thinks in. The rest stay behind More colors. */
const FEATURED: FeaturedRow[] = [
  { token: '--bg-base', label: 'App background', why: 'The base behind everything' },
  { token: '--bg-1', label: 'Panels', why: 'Cards and side panels' },
  { token: '--bg-2', label: 'Elevated surfaces', why: 'Menus and raised cards' },
  { token: '--text-primary', label: 'Primary text', why: 'Headings and body text' },
  { token: '--text-secondary', label: 'Secondary text', why: 'Hints and metadata' },
  { token: '--border-base', label: 'Borders', why: 'Dividers and outlines' },
  { token: '--primary', label: 'Accent', why: 'Buttons and highlights' },
  { token: '--success', label: 'Success', why: 'Confirmations' },
  { token: '--warning', label: 'Warning', why: 'Caution states' },
  { token: '--danger', label: 'Error', why: 'Failures and destructive actions' },
];

const hex = (value: string) => {
  const trimmed = (value || '').trim();
  if (/^#[0-9a-fA-F]{3}$/.test(trimmed)) {
    return (
      '#' +
      trimmed
        .slice(1)
        .split('')
        .map((c) => c + c)
        .join('')
    ).toLowerCase();
  }
  if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) return trimmed.toLowerCase();
  const rgb = trimmed.match(/rgba?\((\d+)[,\s]+(\d+)[,\s]+(\d+)/i);
  if (rgb) {
    return (
      '#' +
      [rgb[1], rgb[2], rgb[3]]
        .map((n) => Number(n).toString(16).padStart(2, '0'))
        .join('')
    ).toLowerCase();
  }
  return null;
};

const luminance = (color: string) => {
  const parsed = hex(color);
  if (!parsed) return null;
  const channels = [1, 3, 5].map((i) => parseInt(parsed.slice(i, i + 2), 16) / 255);
  const linear = channels.map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)));
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
};

const contrast = (a: string, b: string) => {
  const la = luminance(a);
  const lb = luminance(b);
  if (la === null || lb === null) return null;
  const [hi, lo] = la >= lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
};

const readVar = (token: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(token).trim();

const activeThemeName = (): string => {
  const activeId = (configService.get('theme.activeId') as string | undefined) ?? 'light';
  if (activeId === 'system') return 'Follow system';
  const builtin = BUILTIN_THEMES.find((t: Theme) => t.id === activeId);
  if (builtin) return builtin.name;
  const user = ((configService.get('theme.userThemes') as Theme[] | undefined) ?? []).find((t) => t.id === activeId);
  return user?.name ?? 'Selected theme';
};

const activeThemeId = (): string => (configService.get('theme.activeId') as string | undefined) ?? 'light';

const ThemeColorRow: React.FC<{ token: string; label: string; hint?: string; onChanged?: () => void }> = ({ token, label, hint, onChanged }) => {
  const [rev, setRev] = useState(0);
  const overrides = themeOverrides(activeThemeId());
  const saved = overrides[token];
  const effective = saved ?? readVar(token);
  const hexValue = hex(effective) ?? '#000000';
  const [draft, setDraft] = useState(hexValue);

  const apply = useCallback(
    async (value: string | null) => {
      await setThemeOverride(activeThemeId(), token, value);
      setRev((n) => n + 1);
      onChanged?.();
    },
    [onChanged, token]
  );

  // Keep the text field in sync when the theme switches or an override is cleared.
  const key = `${token}:${hexValue}:${saved ?? ''}:${rev}`;
  void key;

  return (
    <div className='kel-shell-theme-color-row flex items-center gap-12px py-8px'>
      <input
        type='color'
        aria-label={`${label} color picker`}
        data-testid={`theme-color-${token.replace(/^--/, '')}`}
        value={hexValue}
        onChange={(event) => {
          setDraft(event.target.value);
          void apply(event.target.value);
        }}
        className='h-24px w-32px cursor-pointer rd-6px border border-border-2 bg-transparent p-0'
      />
      <div className='w-160px text-13px text-t-primary'>{label}</div>
      <Tooltip content={hint ?? 'Semantic color'}>
        <Input
          size='small'
          value={draft}
          aria-label={`${label} hex value`}
          data-testid={`theme-hex-${token.replace(/^--/, '')}`}
          onChange={(value) => {
            setDraft(value);
            const parsed = hex(value);
            if (parsed) void apply(parsed);
          }}
          style={{ maxWidth: 120 }}
        />
      </Tooltip>
      {saved ? (
        <Button
          size='mini'
          data-testid={`theme-reset-${token.replace(/^--/, '')}`}
          onClick={() => {
            void apply(null);
            setDraft(readVar(token));
          }}
        >
          Reset
        </Button>
      ) : null}
      {saved ? <span className='text-11px text-t-secondary'>Changed</span> : null}
    </div>
  );
};

export const ThemeColorsSection: React.FC = () => {
  const [refresh, setRefresh] = useState(0);
  const [showAll, setShowAll] = useState(false);
  const handleChanged = useCallback(() => setRefresh((value) => value + 1), []);
  const themeId = activeThemeId();
  const overrides = useMemo(() => themeOverrides(themeId), [themeId, refresh]);
  const extraTokens = THEME_TOKENS.filter((token) => !FEATURED.some((row) => row.token === token.key));

  const warnings = useMemo(() => {
    void refresh;
    const pairs: Array<[string, string, number, string]> = [
      ['--text-primary', '--bg-base', 4.5, 'Primary text on the app background'],
      ['--text-primary', '--bg-1', 4.5, 'Primary text on panels'],
      ['--text-secondary', '--bg-base', 3, 'Secondary text on the app background'],
      ['--primary', '--bg-base', 2.5, 'Accent on the app background'],
    ];
    const found: string[] = [];
    for (const [fg, bg, min, label] of pairs) {
      const fgColor = themeOverrides(themeId)[fg] ?? readVar(fg);
      const bgColor = themeOverrides(themeId)[bg] ?? readVar(bg);
      const ratio = contrast(fgColor, bgColor);
      if (ratio !== null && ratio < min) {
        found.push(`${label} is low contrast (${ratio.toFixed(1)}:1) — it may be hard to read.`);
      }
    }
    const danger = hex(themeOverrides(themeId)['--danger'] ?? readVar('--danger'));
    const success = hex(themeOverrides(themeId)['--success'] ?? readVar('--success'));
    if (danger && success && danger === success) {
      found.push('Success and Error use the same color — the two states are no longer distinct.');
    }
    return found;
  }, [themeId, refresh]);

  const changed = Object.keys(overrides).length;

  return (
    <div className='px-16px md:px-24px lg:px-28px py-14px md:py-16px bg-2 rd-16px' data-testid='theme-colors-section'>
      <div className='flex items-center justify-between mb-4px'>
        <h2 className='kel-h2'>Theme colors</h2>
        {(
          <Button
            size='small'
            status='danger'
            type='text'
            data-testid='theme-colors-restore'
            onClick={() => {
              void clearThemeOverrides(themeId).then(() => {
                setRefresh((n) => n + 1);
                Message.success('Theme colors restored to their defaults.');
              });
            }}
          >
            Restore all colors
          </Button>
        )}
      </div>
      {warnings.length > 0 ? (
        <div className='mb-8px rd-8px bg-1 px-12px py-8px text-12px text-t-primary' data-testid='theme-color-warnings'>
          {warnings.map((warning) => (
            <div key={warning} className='flex items-start gap-6px'>
              <span aria-hidden>!</span>
              <span>{warning}</span>
            </div>
          ))}
        </div>
      ) : null}
      <div className='divide-y divide-border-2' key={`${themeId}:${refresh}`}>
        {FEATURED.map((row) => (
          <ThemeColorRow key={`${themeId}:${row.token}:${refresh}`} token={row.token} label={row.label} hint={row.why} onChanged={handleChanged} />
        ))}
      </div>
      <button
        type='button'
        className='mt-8px text-12px text-t-secondary hover:text-t-primary cursor-pointer bg-transparent border-none p-0'
        data-testid='theme-colors-more'
        onClick={() => setShowAll((value) => !value)}
      >
        {showAll ? 'Hide additional colors' : `More colors (${extraTokens.length})`}
      </button>
      {showAll ? (
        <div className='mt-4px divide-y divide-border-2'>
          {extraTokens.map((token) => (
            <ThemeColorRow key={`${themeId}:${token.key}:${refresh}`} token={token.key} label={token.key.replace(/^--/, '')} hint={token.description} onChanged={handleChanged} />
          ))}
        </div>
      ) : null}
    </div>
  );
};

export default ThemeColorsSection;
