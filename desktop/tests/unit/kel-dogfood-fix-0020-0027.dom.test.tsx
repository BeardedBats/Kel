/**
 * Nick's Kibble findings FIX-0020..0027 (2026-09-29), one behaviour each:
 * 0020 no glow under the chat box when it is focused; 0021 the composer's controls stay on its bottom
 * row; 0022 with the sidebar hidden its controls stay top left; 0023 Settings pages switch without a
 * loading flash and Appearance has no theme or colour choice (D-82); 0024 a wider reading column;
 * 0025 a reply arrives without jumps; 0026 the reply's usage sits on its timestamp line; 0027 no ⋯ menu.
 * CSS that jsdom cannot lay out is read as rules; the rest is rendered.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import React from 'react';
import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/renderer/pages/conversation/Preview/hooks/useLocalFilePreview', () => ({ useLocalFilePreview: () => undefined }));
vi.mock('@/renderer/hooks/chat/useForkConversation', () => ({ useForkConversation: () => vi.fn() }));
vi.mock('@/renderer/utils/model/agentLogo', () => ({ useAgentLogos: () => ({}), resolveAgentLogo: () => null }));
vi.mock('@renderer/components/Markdown', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock('@/renderer/hooks/context/ThemeContext', () => ({
  useThemeContext: () => ({
    theme: 'dark',
    fontSizes: { app: 14, chat: 16, markdown: 16, code: 14 },
    setFontSize: vi.fn(),
    fontFamilies: {},
    setFontFamily: vi.fn(),
    fontWeights: {},
    setFontWeight: vi.fn(),
  }),
}));
vi.mock('@renderer/hooks/context/ThemeContext', () => ({
  useThemeContext: () => ({
    theme: 'dark',
    fontSizes: { app: 14, chat: 16, markdown: 16, code: 14 },
    setFontSize: vi.fn(),
    fontFamilies: {},
    setFontFamily: vi.fn(),
    fontWeights: {},
    setFontWeight: vi.fn(),
  }),
}));
vi.mock('@/renderer/components/settings/ScaleControl', () => ({ default: () => <span data-testid='scale-control' /> }));
vi.mock('@/renderer/utils/platform', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  isElectronDesktop: () => true,
  isMacOS: () => false,
}));
vi.mock('@renderer/components/layout/WindowControls', () => ({ default: () => <span data-testid='window-controls' /> }));
vi.mock('@/renderer/components/layout/WindowControls', () => ({ default: () => <span data-testid='window-controls' /> }));

import MessageText from '@renderer/pages/conversation/Messages/components/MessageText';
import { ConversationProvider } from '@/renderer/hooks/context/ConversationContext';
import { LayoutContext } from '@/renderer/hooks/context/LayoutContext';
import { useInputFocusRing } from '@/renderer/hooks/chat/useInputFocusRing';
import Titlebar from '@renderer/components/layout/Titlebar';
import AppearanceModalContent from '@/renderer/components/settings/SettingsModal/contents/AppearanceModalContent';
import { useAutoScroll } from '@renderer/pages/conversation/Messages/useAutoScroll';
import { motionClock, setReducedMotionOverride, setSceneSettledForTests } from '@renderer/motion';
import type { IMessageText, TMessage } from '@/common/chat/chatLib';
import type { KelMessageMeta } from '@/common/chat/kelMessageMeta';

const renderer = path.resolve(__dirname, '../../packages/desktop/src/renderer');
const read = (relative: string) => readFileSync(path.join(renderer, relative), 'utf8');
const css = read('styles/kel-shell.css');

afterEach(() => {
  cleanup();
  motionClock.reset();
  motionClock.setManual(false);
  setReducedMotionOverride(null);
  vi.restoreAllMocks();
});

const reply = (content: string, kel_meta?: KelMessageMeta): IMessageText =>
  ({
    id: 'r-1',
    msg_id: 'r-1',
    type: 'text',
    position: 'left',
    conversation_id: 'donor',
    created_at: new Date(2026, 8, 29, 18, 0).getTime(),
    content: kel_meta ? { content, kel_meta } : { content },
  }) as IMessageText;

const PLAN = { calls: 1, tokens: 2900, ms: 3600, cost: null, billing: 'plan', model_label: 'ChatGPT Luna', models: ['ChatGPT Luna'] };

const renderReply = (message: IMessageText, props: Partial<React.ComponentProps<typeof MessageText>> = {}) =>
  render(
    <MemoryRouter>
      <ConversationProvider value={{ conversation_id: 'donor', type: 'acp' } as never}>
        <MessageText message={message} isLastMessage {...props} />
      </ConversationProvider>
    </MemoryRouter>
  );

describe('FIX-0020 no glow under the focused chat box', () => {
  it('the focus ring has no shadow — focus shows only as the border colour', () => {
    const { result } = renderHook(() => useInputFocusRing());
    expect(result.current.activeShadow).toBe('none');
  });
});

describe('FIX-0021 the composer’s controls stay on its bottom row', () => {
  it('the home composer bottom-aligns its + and send/model/mic columns, so only the text grows', () => {
    // The desktop rule that wins (the last one for the composer grid).
    const grids = css.match(/\.kel-v2-shell \.kel-shell-composer \{ display: grid;[^}]*\}/g) ?? [];
    const grid = grids[grids.length - 1] ?? '';
    expect(grid).toMatch(/align-items: end/);
    // Centres on the last text line: 25 px text + 6.5, 28 px + + 5, 36 px send + 1 → all 19 px up.
    expect(css).toMatch(/\.kel-v2-shell \.kel-shell-composer > textarea \{[^}]*margin-bottom: 6\.5px/);
    expect(css).toMatch(/\.kel-v2-shell \.kel-shell-composer-attach \{ grid-column: 1; grid-row: 1; margin-bottom: 5px; \}/);
    expect(css).toMatch(/\.kel-v2-shell \.kel-shell-composer-submit \{ grid-column: 3; grid-row: 1; margin-bottom: 1px; \}/);
  });
});

describe('FIX-0022 a hidden sidebar keeps its controls at the top left', () => {
  const renderBar = (siderCollapsed: boolean) =>
    render(
      <MemoryRouter initialEntries={['/guid']}>
        <LayoutContext.Provider value={{ isMobile: false, siderCollapsed, setSiderCollapsed: vi.fn() }}>
          <Titlebar workspaceAvailable={false} />
        </LayoutContext.Provider>
      </MemoryRouter>
    );

  it('shows "Show the sidebar", search and back/forward together in a top-left group, not by the window controls', () => {
    renderBar(true);
    const show = screen.getByRole('button', { name: 'Show the sidebar' });
    const group = screen.getByTestId('titlebar-menu');
    expect(group.classList.contains('app-titlebar__menu--floating')).toBe(true);
    expect(group.contains(show)).toBe(true);
    expect(group.contains(screen.getByTestId('titlebar-search'))).toBe(true);
    expect(screen.getByTestId('window-controls').closest('.app-titlebar__toolbar')?.contains(show)).toBe(false);
    const rule = /\.app-titlebar__menu--floating \{([^}]*)\}/.exec(css)?.[1] ?? '';
    expect(rule).toMatch(/position: fixed/);
    expect(rule).toMatch(/left: 12px/);
  });

  it('the group is not floating while the sidebar is shown', () => {
    renderBar(false);
    expect(screen.getByTestId('titlebar-menu').classList.contains('app-titlebar__menu--floating')).toBe(false);
  });
});

describe('FIX-0023 Settings pages switch without a flash; Appearance has no colour choice (D-82)', () => {
  it('Appearance keeps text size and zoom and has no theme gallery or theme colours', () => {
    render(<AppearanceModalContent />);
    expect(screen.getByText('Text size and zoom')).toBeTruthy();
    expect(screen.queryByText('Theme')).toBeNull();
    expect(screen.queryByText('Theme colors')).toBeNull();
    expect(screen.queryByText('Add theme')).toBeNull();
    expect(screen.queryByText('Light')).toBeNull();
  });

  it('routes share one Suspense boundary above <Routes>, so a page switch keeps the current page until the next is ready', () => {
    const router = read('components/layout/Router.tsx');
    expect(router).toMatch(/<Suspense fallback=\{<AppLoader \/>\}>\s*<Routes>/);
    expect(router.match(/<Suspense/g)?.length).toBe(1);
  });
});

describe('FIX-0024 the reading column', () => {
  it('is about half the window on wide screens, and Nick’s messages widen with it', () => {
    expect(css).toMatch(/--kel-shell-content-width: clamp\(920px, 50vw, 1280px\)/);
    expect(css).toMatch(/\.chat-layout-header \{[^}]*max-width: var\(--kel-shell-content-width\)/);
    expect(css).toMatch(/\[data-message-position='right'\] \.kel-shell-message-turn \{ max-width: max\(390px, 60%\); \}/);
    expect(read('components/kel/workCards/KelWorkCards.css')).toMatch(/max-width: var\(--kel-shell-content-width, 920px\)/);
  });
});

describe('FIX-0026 / FIX-0027 the reply’s line and actions', () => {
  it('puts "· ChatGPT Luna · 3.6 s" on the timestamp line, with the plan and tokens only in a tooltip', () => {
    renderReply(reply('Sounds good.', { usage: PLAN } as KelMessageMeta));
    const meta = document.querySelector('.kel-shell-message-meta')!;
    const usage = screen.getByTestId('kel-reply-usage');
    expect(meta.contains(usage)).toBe(true);
    expect(meta.textContent).toBe('6:00 PM·ChatGPT Luna·3.6 s');
    expect(document.body.textContent).not.toContain('Included in your plan');
    expect(document.body.textContent).not.toContain('tokens');
    expect(usage.getAttribute('aria-label')).toBe('ChatGPT Luna · 3.6 s · Included in your plan · 2.9K tokens');
    expect(screen.queryByTestId('kel-usage-chips')).toBeNull();
  });

  it('offers Answer again and Copy as icon buttons, left-aligned with the reply, and no ⋯ menu', () => {
    renderReply(reply('Sounds good.'));
    expect(screen.queryByLabelText('More reply actions')).toBeNull();
    const again = screen.getByRole('button', { name: 'Answer again' });
    const copy = screen.getByRole('button', { name: 'Copy' });
    const row = again.closest('.kel-shell-message-actions')!;
    expect(row.contains(copy)).toBe(true);
    expect(row.classList.contains('kel-shell-message-actions--reply')).toBe(true);
    expect(css).toMatch(/\.kel-shell-message-actions--reply \{ margin-left: -6px; \}/);
    expect(screen.queryAllByText('Answer again').filter((el) => el.closest('[role="menu"]'))).toEqual([]);
  });
});

describe('FIX-0025 a reply arrives without jumps', () => {
  it('while the reply streams, its actions row already holds its place (empty), so nothing is pushed when it arrives', () => {
    const { rerender } = renderReply(reply('Streaming…'), { showCopyRow: false, reserveActionsRow: true });
    const reserved = document.querySelector<HTMLElement>('.kel-shell-message-actions')!;
    expect(reserved.dataset.reserved).toBe('true');
    expect(reserved.getAttribute('aria-hidden')).toBe('true');
    expect(reserved.querySelector('button')).toBeNull();
    rerender(
      <MemoryRouter>
        <ConversationProvider value={{ conversation_id: 'donor', type: 'acp' } as never}>
          <MessageText message={reply('Streaming… done.')} isLastMessage showCopyRow />
        </ConversationProvider>
      </MemoryRouter>
    );
    const row = document.querySelector<HTMLElement>('.kel-shell-message-actions')!;
    expect(row.dataset.reserved).toBeUndefined();
    expect(row.querySelector('button[aria-label="Copy"]')).not.toBeNull();
  });

  describe('the thread glides instead of jumping', () => {
    let observe: (() => void) | null = null;
    let itemTop = 500;
    beforeEach(() => {
      observe = null;
      itemTop = 500;
      setReducedMotionOverride(false);
      setSceneSettledForTests(true);
      motionClock.setManual(true);
      vi.stubGlobal('ResizeObserver', class {
        constructor(cb: () => void) { observe = cb; }
        observe() {}
        disconnect() {}
      });
      vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => { cb(0); return 1; });
      vi.stubGlobal('cancelAnimationFrame', () => undefined);
      (Element.prototype as unknown as { scrollTo: () => void }).scrollTo = () => undefined;
    });
    afterEach(() => vi.unstubAllGlobals());

    const Harness: React.FC<{ messages: TMessage[] }> = ({ messages }) => {
      const scroll = useAutoScroll({ messages, itemCount: messages.length });
      return (
        <div ref={scroll.handleScrollerRef} data-testid='scroller' onScroll={scroll.handleScroll} onWheel={scroll.handleWheel}>
          <div data-testid='clip'>
            <div ref={scroll.handleContentRef} data-testid='content'>
              <div className='message-item' data-testid='first' />
            </div>
          </div>
        </div>
      );
    };

    it('a short chat growing upward (the list is bottom-aligned) glides by the growth, with no painted jump', () => {
      const messages = [{ id: 'u', position: 'right', type: 'text' } as TMessage];
      render(<Harness messages={messages} />);
      const content = screen.getByTestId('content');
      const first = screen.getByTestId('first');
      // A short chat: nothing to scroll; the first message sits 500 px down the list.
      vi.spyOn(content, 'getBoundingClientRect').mockImplementation(() => ({ top: 0 }) as DOMRect);
      vi.spyOn(first, 'getBoundingClientRect').mockImplementation(() => ({ top: itemTop }) as DOMRect);
      act(() => observe?.());
      expect(content.style.transform).toBe('');
      // The reply's first lines arrive: the bottom-aligned list pushes the first message up 60 px.
      itemTop = 440;
      act(() => observe?.());
      expect(content.style.transform).toBe('translateY(60.00px)');
      // While it moves, the box around it clips, so the moving content never changes the scroll range.
      expect(screen.getByTestId('clip').style.overflow).toBe('clip');
      act(() => motionClock.advance(1000));
      expect(content.style.transform).toBe('');
      expect(screen.getByTestId('clip').style.overflow).toBe('');
    });

    it('the list getting taller (Thinking leaving) glides the thread down, not a snap', () => {
      render(<Harness messages={[{ id: 'u', position: 'right', type: 'text' } as TMessage]} />);
      const content = screen.getByTestId('content');
      const first = screen.getByTestId('first');
      vi.spyOn(content, 'getBoundingClientRect').mockImplementation(() => ({ top: 0 }) as DOMRect);
      vi.spyOn(first, 'getBoundingClientRect').mockImplementation(() => ({ top: itemTop }) as DOMRect);
      act(() => observe?.());
      itemTop = 536;
      act(() => observe?.());
      expect(content.style.transform).toBe('translateY(-36.00px)');
    });

    it('a browser scroll clamp (the thread got shorter at the bottom) still glides', () => {
      render(<Harness messages={[{ id: 'u', position: 'right', type: 'text' } as TMessage]} />);
      const scroller = screen.getByTestId('scroller');
      const content = screen.getByTestId('content');
      const first = screen.getByTestId('first');
      vi.spyOn(content, 'getBoundingClientRect').mockImplementation(() => ({ top: 0 }) as DOMRect);
      vi.spyOn(first, 'getBoundingClientRect').mockImplementation(() => ({ top: itemTop }) as DOMRect);
      act(() => observe?.());
      // A card in the thread got 61 px shorter: the browser clamps the scroll (no input from Nick)
      // before the resize is observed.
      itemTop = 561;
      fireEvent.scroll(scroller);
      act(() => observe?.());
      expect(content.style.transform).toBe('translateY(-61.00px)');
    });

    it('never replays Nick’s own scrolling as a glide', () => {
      render(<Harness messages={[{ id: 'u', position: 'right', type: 'text' } as TMessage]} />);
      const scroller = screen.getByTestId('scroller');
      const content = screen.getByTestId('content');
      const first = screen.getByTestId('first');
      vi.spyOn(content, 'getBoundingClientRect').mockImplementation(() => ({ top: 0 }) as DOMRect);
      vi.spyOn(first, 'getBoundingClientRect').mockImplementation(() => ({ top: itemTop }) as DOMRect);
      act(() => observe?.());
      itemTop = 300;
      fireEvent.wheel(scroller, { deltaY: -200 });
      fireEvent.scroll(scroller);
      act(() => observe?.());
      expect(content.style.transform).toBe('');
    });
  });
});
