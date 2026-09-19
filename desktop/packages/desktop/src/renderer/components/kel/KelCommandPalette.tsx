/**
 * Kel V1.4 command palette — `Ctrl+K` anywhere, `/` opens it in search mode.
 *
 * Keyboard-first: ArrowUp/ArrowDown move, Enter runs, Escape closes; the list is a real listbox.
 * Results come from the engine (`/api/state`, `/api/work`) plus fixed navigation, so the palette can
 * never show a surface or object the app cannot actually open.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { configService } from '@/common/config/configService';
import { setActiveTheme } from '@renderer/utils/theme/applyTheme';
import { kelState, kelWork } from '@renderer/components/kel/kelApi';

type PaletteItem = {
  id: string;
  group: string;
  label: string;
  hint?: string;
  run: () => void;
};

const NAVIGATION: Array<{ id: string; label: string; hint: string; path: string }> = [
  { id: 'nav-new-chat', label: 'New Chat', hint: 'start a conversation', path: '/guid' },
  { id: 'nav-work', label: 'Work', hint: 'jobs and what needs you', path: '/work' },
  { id: 'nav-transcription', label: 'Transcription', hint: 'record, upload, transcripts', path: '/transcription' },
  { id: 'nav-settings', label: 'Settings', hint: 'models, appearance, system', path: '/settings/model' },
  { id: 'nav-settings-appearance', label: 'Settings · Appearance', hint: 'theme and colors', path: '/settings/appearance' },
  { id: 'nav-settings-system', label: 'Settings · System', hint: 'data, backup, updates', path: '/settings/system' },
  { id: 'nav-knowledge', label: 'Projects · Knowledge', hint: 'what Kel learned', path: '/projects/knowledge' },
  { id: 'nav-map', label: 'Projects · Map', hint: 'project map', path: '/projects/map' },
  { id: 'nav-recipes', label: 'Projects · Recipes', hint: 'ready-made tasks', path: '/projects/recipes' },
  { id: 'nav-providers', label: 'Providers', hint: 'connect a model', path: '/providers' },
  { id: 'nav-autonomy', label: 'Permissions', hint: 'what Kel can access', path: '/autonomy' },
];

// Plain-language job states for hints; the raw states stay on the Work page.
const JOB_STATE_LABEL: Record<string, string> = {
  QUEUED: 'queued',
  READY: 'ready to run',
  RUNNING: 'working',
  WAITING_RESOURCE: 'waiting for a model',
  AWAITING_USER: 'waiting on you',
  PAUSED: 'paused',
  BLOCKED: 'blocked by a safety rule',
  CLOSED: 'finished',
  CANCELLED: 'cancelled',
};

function isTypingTarget(target: EventTarget | null): boolean {
  const element = target as HTMLElement | null;
  if (!element) return false;
  const tag = element.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || element.isContentEditable === true;
}

const KelCommandPalette: React.FC = () => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<'command' | 'search'>('command');
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const [dynamic, setDynamic] = useState<PaletteItem[]>([]);
  const [found, setFound] = useState<PaletteItem[]>([]);
  const [loading, setLoading] = useState(false);
  const loadedOnce = useRef(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const close = useCallback(() => {
    setOpen(false);
    setQuery('');
    setActive(0);
  }, []);

  const load = useCallback(async () => {
    if (loadedOnce.current) return;
    loadedOnce.current = true;
    setLoading(true);
    try {
      const [state, work] = await Promise.all([
        kelState().catch((): Awaited<ReturnType<typeof kelState>> => ({ jobs: [], providers: [], projects: [] })),
        kelWork('main').catch((): null => null),
      ]);
      const items: PaletteItem[] = [];
      (state.jobs ?? []).forEach((job) => {
        items.push({
          id: `job-${job.id}`,
          group: 'Jobs',
          label: job.contract?.request?.slice(0, 60) ?? job.id,
          hint: JOB_STATE_LABEL[job.state] ?? job.state.toLowerCase().replace(/_/g, ' '),
          run: () => navigate('/work'),
        });
      });
      (work?.memory.records ?? []).forEach((record) => {
        items.push({
          id: `memory-${record.id}`,
          group: 'Knowledge',
          label: record.topic || record.summary.slice(0, 60),
          hint: `${record.type} · trust ${record.trust}/10`,
          run: () => navigate('/projects/knowledge'),
        });
      });
      (work?.recipes.entries ?? []).forEach((entry, index) => {
        const id = String(entry.recipe_id ?? entry.id ?? `recipe-${index}`);
        items.push({
          id: `recipe-${id}`,
          group: 'Recipes',
          label: entry.name ?? entry.title ?? id,
          hint: 'dry run from Projects · Recipes',
          run: () => navigate('/projects/recipes'),
        });
      });
      setDynamic(items);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      if ((event.ctrlKey || event.metaKey) && key === 'k') {
        event.preventDefault();
        setOpen((wasOpen) => {
          if (!wasOpen) {
            setMode('command');
            void load();
          }
          return !wasOpen;
        });
        return;
      }
      if (event.key === '/' && !isTypingTarget(event.target)) {
        event.preventDefault();
        setMode('search');
        setOpen(true);
        void load();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [load]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    const needle = query.trim();
    if (!open || needle.length < 2) {
      setFound([]);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      const bridge = (window as unknown as { kelAPI?: { request: (route: string, payload?: unknown) => Promise<{
        transcripts?: Array<{ id: string; title: string; snippet: string }>;
        vetting?: Array<{ id: string; title: string; snippet: string }>;
        conversations?: Array<{ id: string; title: string; snippet: string }>;
      }> } }).kelAPI;
      if (!bridge) return;
      bridge
        .request('/api/search', { q: needle })
        .then((data) => {
          if (cancelled) return;
          const items: PaletteItem[] = [];
          (data.transcripts ?? []).forEach((row) => items.push({
            id: `found-transcript-${row.id}`, group: 'Transcripts',
            label: row.title, hint: row.snippet || 'open Transcription',
            run: () => navigate('/transcription'),
          }));
          (data.vetting ?? []).forEach((row) => items.push({
            id: `found-vetting-${row.id}`, group: 'Vetting',
            label: row.title, hint: row.snippet || 'open the chat; Vetting lives in the Work panel',
            run: () => navigate('/guid'),
          }));
          (data.conversations ?? []).forEach((row) => items.push({
            id: `found-chat-${row.id}`, group: 'Chats',
            label: row.title, hint: row.snippet || 'open the chat list',
            run: () => navigate('/guid'),
          }));
          setFound(items);
        })
        .catch(() => setFound([]));
    }, 260);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [navigate, open, query]);

  const items = useMemo(() => {
    const navigation: PaletteItem[] = NAVIGATION.map((entry) => ({
      id: entry.id,
      group: 'Go to',
      label: entry.label,
      hint: entry.hint,
      run: () => navigate(entry.path),
    }));
    // Actions are real, verified behaviours: theme switch and a composer handoff that prefills
    // a vetting start. Anything that cannot actually run never appears here.
    const activeThemeId = (configService.get('theme.activeId') as string | undefined) ?? 'light';
    const otherTheme = activeThemeId === 'dark' ? 'Light' : 'Dark';
    const actions: PaletteItem[] = [
      {
        id: 'action-theme',
        group: 'Actions',
        label: `Switch to ${otherTheme} theme`,
        hint: 'appearance',
        run: () => {
          void setActiveTheme(otherTheme.toLowerCase());
        },
      },
      {
        id: 'action-vetting',
        group: 'Actions',
        label: 'Start design vetting',
        hint: 'prefills the chat',
        run: () => {
          try {
            window.sessionStorage.setItem('kel.transcription.draft', 'start design vetting: ');
          } catch {
            /* the chat still opens without the prefill */
          }
          navigate('/guid');
        },
      },
    ];
    const all = mode === 'command' ? [...actions, ...navigation, ...dynamic, ...found] : [...found, ...dynamic];
    const needle = query.trim().toLowerCase();
    if (!needle) return all.slice(0, 24);
    return all
      .filter((item) => `${item.label} ${item.hint ?? ''}`.toLowerCase().includes(needle))
      .slice(0, 24);
  }, [dynamic, mode, navigate, query]);

  useEffect(() => {
    setActive(0);
  }, [query, mode]);

  const runActive = useCallback(() => {
    const item = items[active];
    if (!item) return;
    item.run();
    close();
  }, [active, close, items]);

  const onInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((index) => Math.min(index + 1, Math.max(items.length - 1, 0)));
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      runActive();
    }
  };

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(20,22,26,.32)',
        zIndex: 400,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '12vh',
      }}
      onClick={close}
    >
      <div
        role='dialog'
        aria-modal='true'
        aria-label='Command palette'
        className='kel-card'
        style={{ width: 620, maxWidth: '92vw', padding: 12, background: 'var(--kel-surface-1)' }}
        onClick={(event) => event.stopPropagation()}
      >
        <label className='kel-meta' htmlFor='kel-palette-input'>
          {mode === 'search' ? 'Search your work and knowledge' : 'Search or jump to…'}
        </label>
        <input
          id='kel-palette-input'
          ref={inputRef}
          className='kel-input'
          style={{ width: '100%', marginTop: 6 }}
          role='combobox'
          aria-expanded='true'
          aria-controls='kel-palette-list'
          aria-activedescendant={items[active] ? `kel-palette-${items[active].id}` : undefined}
          placeholder={mode === 'search' ? 'Search…' : 'Type to search…'}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={onInputKeyDown}
        />
        <ul
          id='kel-palette-list'
          role='listbox'
          aria-label='Palette results'
          style={{ listStyle: 'none', margin: '10px 0 0', padding: 0, maxHeight: '48vh', overflowY: 'auto' }}
        >
          {loading && items.length === 0 && (
            <li className='kel-meta' style={{ padding: '8px 10px' }}>
              Loading…
            </li>
          )}
          {!loading && items.length === 0 && (
            <li className='kel-meta' style={{ padding: '8px 10px' }}>
              Nothing matches “{query}”. Try a job, a topic, a recipe, a role — or an action like “new chat”.
            </li>
          )}
          {items.map((item, index) => (
            <li
              key={item.id}
              id={`kel-palette-${item.id}`}
              role='option'
              aria-selected={index === active}
              className='kel-row'
              style={{
                padding: '8px 10px',
                borderRadius: 8,
                cursor: 'pointer',
                background: index === active ? 'var(--kel-surface-2)' : 'transparent',
              }}
              onMouseEnter={() => setActive(index)}
              onClick={runActive}
            >
              <span className='kel-meta' style={{ width: 92, flexShrink: 0 }}>
                {item.group}
              </span>
              <span className='kel-strong'>{item.label}</span>
              <span className='kel-grow' />
              {item.hint && <span className='kel-meta'>{item.hint}</span>}
            </li>
          ))}
        </ul>
        <p className='kel-meta' style={{ marginTop: 10 }}>
          Enter runs · Arrow keys move · Escape closes · <span className='kel-code'>Ctrl+K</span> opens ·
          {' '}
          <span className='kel-code'>/</span> searches
        </p>
      </div>
    </div>
  );
};

export default KelCommandPalette;
