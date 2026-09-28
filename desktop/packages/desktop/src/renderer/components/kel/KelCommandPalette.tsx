/**
 * Kel V1.4 command palette — `Ctrl+K` anywhere, `/` opens it in search mode.
 *
 * Keyboard-first: ArrowUp/ArrowDown move, Enter runs, Escape closes; the list is a real listbox.
 * Results come from the engine (`/api/state`, `/api/work`) plus fixed navigation, so the palette can
 * never show a surface or object the app cannot actually open.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ipcBridge } from '@/common';
import { configService } from '@/common/config/configService';
import { DARK_THEME_ID } from '@/common/theme/constants';
import { setActiveTheme } from '@renderer/utils/theme/applyTheme';
import { KEL_ALL_CONVERSATIONS, kelState, kelWork } from '@renderer/components/kel/kelApi';
import { workWords } from '@renderer/components/kel/workLanguage';
import { requestTitle, jobRouteFor } from '@renderer/components/kel/needsAttention';
import searchIcon from '@renderer/assets/figma/palette/search.svg';
import workIcon from '@renderer/assets/figma/palette/work.svg';
import activityIcon from '@renderer/assets/figma/palette/activity.svg';
import clockIcon from '@renderer/assets/figma/palette/clock.svg';
import captureIcon from '@renderer/assets/figma/palette/capture.svg';
import playIcon from '@renderer/assets/figma/palette/play.svg';
import recipeIcon from '@renderer/assets/figma/palette/recipe.svg';
import chatIcon from '@renderer/assets/figma/palette/chat.svg';
import { searchKelConversationMessages } from '@renderer/utils/chat/kelHistorySearch';

/**
 * CH-17: one search experience. The header search button (and the phone sidebar's search entry)
 * open this palette in search mode instead of a second, donor search popover.
 */
const OPEN_EVENT = 'kel:open-command-palette';
export const openKelCommandPalette = (mode: 'command' | 'search' = 'search'): void => {
  window.dispatchEvent(new CustomEvent(OPEN_EVENT, { detail: { mode } }));
};

type PaletteItem = {
  id: string;
  group: string;
  label: string;
  hint?: string;
  /** Extra text the filter matches (a job's full request) without showing it. */
  search?: string;
  icon?: string;
  run: () => void;
};

const NAVIGATION: Array<{ id: string; label: string; hint: string; path: string }> = [
  { id: 'nav-activity', label: 'Activity', hint: 'every job and what needs you', path: '/activity' },
  { id: 'nav-scheduled', label: 'Scheduled tasks', hint: 'recurring work', path: '/scheduled' },
  { id: 'nav-new-chat', label: 'New Chat', hint: 'start a conversation', path: '/guid' },
  { id: 'nav-transcription', label: 'Ramble', hint: 'record, upload, transcripts', path: '/transcription' },
  { id: 'nav-settings', label: 'Settings', hint: 'models, appearance, system', path: '/settings/model' },
  { id: 'nav-settings-appearance', label: 'Settings · Appearance', hint: 'theme and colors', path: '/settings/appearance' },
  { id: 'nav-settings-system', label: 'Settings · System', hint: 'data, backup, updates', path: '/settings/system' },
  { id: 'nav-knowledge', label: 'Projects · Knowledge', hint: 'what Kel learned', path: '/projects/knowledge' },
  { id: 'nav-map', label: 'Projects · Map', hint: 'project map', path: '/projects/map' },
  { id: 'nav-recipes', label: 'Recipes', hint: 'ready-made tasks', path: '/projects/recipes' },
  { id: 'nav-providers', label: 'Settings · Providers', hint: 'connect a model', path: '/settings/providers' },
  { id: 'nav-staff', label: 'Settings · Staff & models', hint: 'the model each role uses', path: '/settings/staff' },
  { id: 'nav-connections', label: 'Connections', hint: 'services Kel can use', path: '/connections' },
  { id: 'nav-autonomy', label: 'Settings · Permissions', hint: 'what Kel can access', path: '/settings/permissions' },
  { id: 'nav-dogfood', label: 'Kibble', hint: 'what you captured with Ctrl+Shift+F', path: '/dogfood' },
  { id: 'nav-diagnostics', label: 'Settings · Diagnostics', hint: 'health and an issue report', path: '/settings/diagnostics' },
  { id: 'nav-setup', label: 'Set up Kel', hint: 'models, projects and permissions', path: '/onboarding' },
];

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
  const inputRef = useRef<HTMLInputElement | null>(null);

  const close = useCallback(() => {
    setOpen(false);
    setQuery('');
    setActive(0);
  }, []);

  // WK-15: re-read every time the palette opens, so jobs started since the last open are findable.
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [state, work, sidebar] = await Promise.all([
        kelState(KEL_ALL_CONVERSATIONS).catch((): Awaited<ReturnType<typeof kelState>> => ({ jobs: [], providers: [], projects: [] })),
        kelWork('main').catch((): null => null),
        ipcBridge.sidebar.get.invoke({ archived: false, limit: 5 }).catch((): null => null),
      ]);
      const items: PaletteItem[] = [];
      (state.jobs ?? []).forEach((job) => {
        const title = requestTitle(job);
        items.push({
          id: `job-${job.id}`,
          group: 'Jobs',
          label: title.length > 60 ? `${title.slice(0, 59).trimEnd()}…` : title,
          hint: workWords(job).label,
          search: job.contract?.request ?? '',
          run: () => navigate(jobRouteFor(job.id)),
        });
      });
      (work?.memory?.records ?? []).forEach((record) => {
        items.push({
          id: `memory-${record.id}`,
          group: 'Knowledge',
          label: record.topic || record.summary.slice(0, 60),
          hint: `${record.type} · trust ${record.trust}/10`,
          run: () => navigate('/projects/knowledge'),
        });
      });
      (work?.recipes?.entries ?? []).forEach((entry, index) => {
        const id = String(entry.recipe_id ?? entry.id ?? `recipe-${index}`);
        items.push({
          id: `recipe-${id}`,
          group: 'Recipes',
          label: entry.name ?? entry.title ?? id,
          hint: 'dry run from Projects · Recipes',
          run: () => navigate('/projects/recipes'),
        });
      });
      const seenChats = new Set<string>();
      (sidebar?.groups ?? []).forEach((group) => group.items.forEach((item) => {
        if (item.type !== 'conversation' || seenChats.has(item.conversation.id)) return;
        seenChats.add(item.conversation.id);
        items.push({
          id: `chat-${item.conversation.id}`,
          group: 'Chats',
          label: item.conversation.name || 'New Chat',
          run: () => navigate(`/conversation/${item.conversation.id}`),
        });
      }));
      setDynamic(items);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      if (event.key === 'Escape' && open) {
        event.preventDefault();
        close();
        return;
      }
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
    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, [close, load, open]);

  useEffect(() => {
    const onOpen = (event: Event) => {
      const requested = (event as CustomEvent<{ mode?: 'command' | 'search' }>).detail?.mode;
      setMode(requested === 'command' ? 'command' : 'search');
      setOpen(true);
      void load();
    };
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_EVENT, onOpen);
  }, [load]);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const keepFocus = (event: FocusEvent) => {
      const dialog = document.querySelector('.kel-palette[role="dialog"]');
      if (dialog && !dialog.contains(event.target as Node)) inputRef.current?.focus();
    };
    document.addEventListener('focusin', keepFocus);
    return () => document.removeEventListener('focusin', keepFocus);
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
        vetting?: Array<{ id: string; title: string; snippet: string; conversation_id?: string | null }>;
        conversations?: Array<{ id: string; title: string; snippet: string }>;
      }> } }).kelAPI;
      const chatHits = searchKelConversationMessages({ keyword: needle, page_size: 8 }).catch((): null => null);
      if (!bridge) return;
      bridge
        .request('/api/search', { q: needle })
        .then(async (data) => {
          const chats = await chatHits;
          if (cancelled) return;
          const items: PaletteItem[] = [];
          const seen = new Set<string>();
          (chats?.items ?? []).forEach((row) => {
            if (seen.has(row.conversation.id)) return;
            seen.add(row.conversation.id);
            const preview = (row.preview_text || '').replace(/\s+/g, ' ').trim();
            items.push({
              id: `found-chat-${row.conversation.id}`, group: 'Chats',
              label: row.conversation.name || 'Chat',
              hint: preview.length > 80 ? `${preview.slice(0, 79)}…` : preview || 'open the chat',
              icon: chatIcon,
              run: () => navigate(`/conversation/${row.conversation.id}`),
            });
          });
          (data.transcripts ?? []).forEach((row) => items.push({
            id: `found-transcript-${row.id}`, group: 'Transcripts',
            label: row.title, hint: row.snippet || 'open Ramble',
            run: () => navigate('/transcription'),
          }));
          // Vetting runs in its chat (the Work panel is gone): a session opens the chat it lives in; when
          // the engine does not say which, a new chat, where "start design vetting: …" picks it up.
          (data.vetting ?? []).forEach((row) => items.push({
            id: `found-vetting-${row.id}`, group: 'Vetting',
            label: row.title, hint: row.snippet || (row.conversation_id ? 'open its chat to continue' : 'continue it in a chat'),
            run: () => {
              const open = (window as unknown as { kelAPI?: { openEngineConversation?: (cid: string) => Promise<string | null> } }).kelAPI?.openEngineConversation;
              if (!row.conversation_id || !open) {
                navigate('/guid');
                return;
              }
              void open(row.conversation_id)
                .then((donor) => navigate(donor ? `/conversation/${donor}` : '/guid'))
                .catch(() => navigate('/guid'));
            },
          }));
          // The engine's chat rows only when the chats themselves could not be searched.
          if (!chats) (data.conversations ?? []).forEach((row) => items.push({
            id: `found-engine-chat-${row.id}`, group: 'Chats',
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
      icon: entry.id === 'nav-activity' ? activityIcon : entry.id === 'nav-scheduled' ? clockIcon : undefined,
      run: () => navigate(entry.path),
    }));
    // Actions are real, verified behaviours: theme switch and a composer handoff that prefills
    // a vetting start. Anything that cannot actually run never appears here.
    const activeThemeId = (configService.get('theme.activeId') as string | undefined) || DARK_THEME_ID;
    const otherTheme = activeThemeId === 'dark' ? 'Light' : 'Dark';
    const actions: PaletteItem[] = [
      {
        id: 'action-capture', group: 'Actions', label: 'Capture a fix', hint: 'Ctrl+Shift+F', icon: captureIcon,
        run: () => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'F', ctrlKey: true, shiftKey: true, bubbles: true, cancelable: true })),
      },
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
        icon: playIcon,
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
    const preferred = navigation.slice(0, 3);
    const rest = navigation.slice(3);
    const all = mode === 'command' ? [...preferred, ...actions, ...dynamic, ...rest, ...found] : [...found, ...dynamic];
    const needle = query.trim().toLowerCase();
    if (!needle && mode === 'command') return [...preferred, actions[0], actions[2], ...dynamic.filter((item) => item.group === 'Recipes').slice(0, 1), ...dynamic.filter((item) => item.group === 'Chats').slice(0, 2)].filter(Boolean);
    if (!needle) return all.slice(0, 24);
    return all
      .filter((item) => `${item.label} ${item.hint ?? ''} ${item.search ?? ''}`.toLowerCase().includes(needle))
      .slice(0, 24);
  }, [dynamic, found, mode, navigate, query]);

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
    <div className='kel-palette-backdrop' onClick={close}>
      <div
        role='dialog'
        aria-modal='true'
        aria-label='Command palette'
        className='kel-palette'
        onClick={(event) => event.stopPropagation()}
      >
        <div className='kel-palette__search'>
          <img src={searchIcon} alt='' />
          <input
            id='kel-palette-input'
            ref={inputRef}
            role='combobox'
            aria-label={mode === 'search' ? 'Search your work and knowledge' : 'Search or jump to'}
            aria-expanded='true'
            aria-controls='kel-palette-list'
            aria-activedescendant={items[active] ? `kel-palette-${items[active].id}` : undefined}
            placeholder={mode === 'search' ? 'Search…' : 'Search or jump to…'}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onInputKeyDown}
          />
          <kbd>Esc</kbd>
        </div>
        <ul
          id='kel-palette-list'
          role='listbox'
          aria-label='Palette results'
          className='kel-palette__results'
        >
          {loading && items.length === 0 && (
            <li className='kel-palette__empty'>
              Loading…
            </li>
          )}
          {!loading && items.length === 0 && (
            <li className='kel-palette__empty'>
              Nothing matches “{query}”. Try a job, a topic, a recipe, a role — or an action like “new chat”.
            </li>
          )}
          {items.map((item, index) => (
            <React.Fragment key={item.id}>
              {(index === 0 || items[index - 1].group !== item.group) && <li className='kel-palette__group' role='presentation'>{item.group}</li>}
              <li
                id={`kel-palette-${item.id}`}
                role='option'
                aria-selected={index === active}
                className='kel-palette__item'
                onMouseEnter={() => setActive(index)}
                onClick={() => { item.run(); close(); }}
              >
                <img src={item.icon ?? (item.group === 'Recipes' ? recipeIcon : item.group === 'Chats' ? chatIcon : item.group === 'Actions' ? playIcon : workIcon)} alt='' />
                <span>{item.label}</span>
                {index === active && <span className='kel-palette__key'>↵</span>}
                {item.id === 'action-capture' && <span className='kel-palette__key'>Ctrl+Shift+F</span>}
              </li>
            </React.Fragment>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default KelCommandPalette;
