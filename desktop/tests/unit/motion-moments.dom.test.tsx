/**
 * D-78 — each of MOTION.md's fifteen moments is wired to the real component (§10). jsdom has no
 * layout, so boxes are stubbed; these tests check the hooks fire on real changes (and never on first
 * paint or a poll that changed nothing), that the settling fade is used for resting end states, and
 * that nothing new moves rows around (icons stay in their own slot, final layout first).
 */
import React from 'react';
import fs from 'node:fs';
import path from 'node:path';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCardRow } from '@renderer/components/kel/workCards/KelWorkCardRow';
import { KelOfficeCard } from '@renderer/components/kel/workCards/KelOfficeCard';
import { KelWorkLine } from '@renderer/components/kel/workCards/KelWorkLine';
import { KelWorkCard } from '@renderer/components/kel/KelWorkCard';
import { KelDoneCard } from '@renderer/components/kel/workCards/KelDoneCard';
import { KelScopingCard } from '@renderer/components/kel/workCards/KelScopingCard';
import KelThinkingIndicator from '@renderer/components/kel/KelThinkingIndicator';
import { KelTabs } from '@renderer/components/kel/KelPrimitives';
import { KelDesktopProjectMenu } from '@renderer/components/kel/KelDesktopProjectMenu';
import { REFRESH_WORK_CARDS_EVENT } from '@renderer/components/kel/workCards/workCardEvents';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import type { OfficeItem, OfficeItemDetail, ScopingView } from '@renderer/components/kel/workCards/officeApi';
import {
  MOTION,
  claimShared,
  motionClock,
  setReducedMotionOverride,
  setSceneSettledForTests,
  useMessageArrival,
} from '@renderer/motion';
import { MIC, MIC_DETAIL, RECEIPTS, RECEIPTS_DETAIL } from './fixtures/kelOfficeFixtures';

const renderer = path.resolve(__dirname, '../../packages/desktop/src/renderer');

let list: OfficeItem[] = [];
let details: Record<string, OfficeItemDetail> = {};
let extra: ((route: string, body?: unknown) => unknown) | null = null;

const install = () => {
  const request = vi.fn(async (route: string, body?: unknown) => {
    const custom = extra?.(route, body);
    if (custom !== undefined) return custom;
    if (route === '/api/project') return { projects: [{ id: 'personal', name: 'Personal', kind: 'user', root: 'C:\\Personal' }], active: '*' };
    if (route.startsWith('/api/office?project=')) return { generated: 1, project: '*', items: list };
    if (route.startsWith('/api/office/item?job=')) {
      const job = decodeURIComponent(route.split('=')[1]);
      if (details[job]) return details[job];
      throw new Error('unknown job');
    }
    if (route.startsWith('/api/handoff')) return { application: null };
    return { ok: true };
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request,
    conversation: vi.fn(async (id: string) => id),
    openEngineConversation: vi.fn(async (cid: string) => cid),
  };
  return request;
};

const stubBoxes = () => {
  // jsdom lays nothing out; give every element a box so the choreography runs its real path.
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (this: Element) {
    const job = (this as HTMLElement).dataset?.job;
    const x = job === RECEIPTS.job_id ? 210 : 0;
    return { left: x, top: 0, x, y: 0, width: 198, height: 74, right: x + 198, bottom: 74, toJSON: () => ({}) } as DOMRect;
  });
};

beforeEach(() => {
  list = [];
  details = { [MIC.job_id]: MIC_DETAIL, [RECEIPTS.job_id]: RECEIPTS_DETAIL };
  extra = null;
  resetProjectsForTests();
  setReducedMotionOverride(false);
  setSceneSettledForTests(true);
  stubBoxes();
});

afterEach(() => {
  cleanup();
  motionClock.reset();
  motionClock.setManual(false);
  setReducedMotionOverride(null);
  vi.restoreAllMocks();
  document.querySelectorAll('.kel-motion-layer').forEach((el) => el.remove());
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const Row: React.FC = () => <KelWorkCardRow availableWidth={920} pollActiveMs={60000} pollIdleMs={60000} />;
const renderRow = () =>
  render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path='/' element={<Row />} />
      </Routes>
    </MemoryRouter>
  );

describe('10.1 send → Thinking → reply', () => {
  it('Thinking enters on arrival, and fades out where it was when it leaves (FIX-0025)', () => {
    motionClock.setManual(true);
    const { container, unmount } = render(<KelThinkingIndicator label='Thinking…' meta='0s' />);
    const mark = container.querySelector<HTMLElement>('.kel-thinking__mark')!;
    expect(Number(mark.style.opacity)).toBe(0);
    act(() => motionClock.advance(400));
    expect(mark.style.opacity).toBe('');
    unmount();
    // One ghost of the whole row, fading in place — no flying mark.
    const ghosts = document.querySelectorAll('.kel-motion-exit');
    expect(ghosts.length).toBe(1);
    expect(ghosts[0].classList.contains('kel-thinking')).toBe(true);
    expect(document.querySelector('.kel-motion-fly')).toBeNull();
  });

  it('on first paint Thinking just shows', () => {
    setSceneSettledForTests(false);
    const { container } = render(<KelThinkingIndicator label='Thinking…' />);
    expect(container.querySelector<HTMLElement>('.kel-thinking__mark')!.style.opacity).toBe('');
  });

  it('the reply’s mark and time fade in in place — nothing flies to the avatar (FIX-0025)', () => {
    motionClock.setManual(true);
    const thinking = render(<KelThinkingIndicator label='Thinking…' />);
    thinking.unmount();
    const Turn: React.FC = () => {
      const ref = React.useRef<HTMLDivElement>(null);
      useMessageArrival(ref, 'kel');
      return (
        <div ref={ref}>
          <div className='kel-shell-message-meta'>
            <span className='kel-shell-message-avatar'>
              <img alt='Kel' />
            </span>
            <time>9:12 AM</time>
          </div>
        </div>
      );
    };
    const { container } = render(<Turn />);
    const avatar = container.querySelector<HTMLElement>('.kel-shell-message-avatar')!;
    const time = container.querySelector<HTMLElement>('time')!;
    expect(avatar.querySelector('img')!.style.visibility).toBe('');
    expect(document.querySelector('.kel-motion-fly')).toBeNull();
    expect(Number(avatar.style.opacity)).toBe(0);
    expect(Number(time.style.opacity)).toBe(0);
    expect(avatar.style.transform ?? '').not.toMatch(/translate/);
    act(() => motionClock.advance(400));
    expect(avatar.style.opacity).toBe('');
    expect(time.style.opacity).toBe('');
  });
});

describe('10.2 the hand-off', () => {
  it('asks the row to read at once when work is handed off (not on the 30 s poll)', async () => {
    install();
    const refreshed = vi.fn();
    window.addEventListener(REFRESH_WORK_CARDS_EVENT, refreshed);
    extra = (route) =>
      route.startsWith('/api/handoff') ? { phase: 'running', job_id: 'job-new', staffed: true, accepted: 0, total: 5, title: 'Mic mute', office_state: 'working' } : undefined;
    render(
      <MemoryRouter>
        <KelWorkCard submissionId='sub-1' conversationId='conv-1' pollMs={60000} />
      </MemoryRouter>
    );
    await waitFor(() => expect(refreshed).toHaveBeenCalled());
    window.removeEventListener(REFRESH_WORK_CARDS_EVENT, refreshed);
  });

  it('a line that arrives reveals from its leading edge and offers itself to the new top card', () => {
    motionClock.setManual(true);
    render(<KelWorkLine view={{ job_id: 'job-mic', phase: 'running', accepted: 1, total: 5, title: 'Mic mute', office_state: 'working' } as never} />);
    const line = screen.getByTestId('kel-work-line');
    expect(line.style.clipPath).toMatch(/^inset\(0 100%/);
    expect(claimShared('handoff:job-mic')?.el).toBe(line);
  });

  it('the new card waits for the beat, then the surface lifts out of the line and lands as the card', async () => {
    install();
    renderRow();
    await act(async () => undefined);
    const line = document.createElement('button');
    line.className = 'kel-wl';
    line.innerHTML = '<span class="kel-wl__lead"><span class="kel-wc-dot"><img alt=""></span></span><span>Handed to the team</span>';
    document.body.appendChild(line);
    motionClock.setManual(true);
    const { offerShared } = await import('@renderer/motion');
    offerShared(`handoff:${MIC.job_id}`, line);
    list = [MIC];
    act(() => {
      window.dispatchEvent(new CustomEvent(REFRESH_WORK_CARDS_EVENT));
    });
    const card = await screen.findByTestId('kel-office-card');
    expect(card.classList.contains('kel-motion-hidden')).toBe(true);
    await act(async () => {
      await motionClock.advanceAsync(MOTION.handoffBeatMs + 50);
    });
    expect(document.querySelector('.kel-motion-surface')).not.toBeNull();
    await act(async () => {
      await motionClock.advanceAsync(1200);
    });
    expect(card.classList.contains('kel-motion-hidden')).toBe(false);
    expect(document.querySelector('.kel-motion-surface')).toBeNull();
    line.remove();
  });
});

describe('10.3 card ↔ detail panel', () => {
  it('opens as one surface growing from the card, the real panel clipped to it, and closes back into the card', async () => {
    list = [MIC];
    install();
    renderRow();
    const card = await screen.findByTestId('kel-office-card');
    motionClock.setManual(true);
    fireEvent.click(within(card).getByRole('button', { name: /^Mic mute toggle app,/ }));
    const panel = await screen.findByTestId('kel-office-detail');
    const stack = document.querySelector('.kel-wc-stack')!;
    expect(stack.querySelector(':scope > .kel-motion-surface')).not.toBeNull();
    expect(panel.classList.contains('kel-motion-bare')).toBe(true);
    expect(panel.style.clipPath).toMatch(/^inset/);
    expect(screen.getByTestId('kel-office-backdrop').style.opacity).toBe('0');
    await act(async () => {
      await motionClock.advanceAsync(1200);
    });
    expect(panel.classList.contains('kel-motion-bare')).toBe(false);
    expect(panel.style.clipPath).toBe('');
    expect(stack.querySelector(':scope > .kel-motion-surface')).toBeNull();

    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('kel-office-detail')).toBeNull());
    // The panel's copy travels back; the card stays hidden until the surface lands.
    expect(stack.querySelector(':scope > .kel-motion-surface')).not.toBeNull();
    const again = screen.getByTestId('kel-office-card');
    await act(async () => {
      await motionClock.advanceAsync(150);
    });
    expect(again.classList.contains('kel-motion-hidden')).toBe(true);
    await act(async () => {
      await motionClock.advanceAsync(1200);
    });
    expect(again.classList.contains('kel-motion-hidden')).toBe(false);
    expect(document.querySelectorAll('.kel-wc-backdrop').length).toBe(0);
  });

  it('under reduced motion there is no surface: the panel cross-fades in place', async () => {
    setReducedMotionOverride(true);
    list = [MIC];
    install();
    renderRow();
    fireEvent.click(within(await screen.findByTestId('kel-office-card')).getByRole('button', { name: /^Mic mute toggle app,/ }));
    await screen.findByTestId('kel-office-detail');
    expect(document.querySelector('.kel-motion-surface')).toBeNull();
  });
});

describe('10.4 / 10.5 card state changes, progress and steps', () => {
  const card = (item: OfficeItem) => <KelOfficeCard item={item} team={[{ role: 'builder' }, { role: 'verifier' }]} onOpen={() => undefined} />;

  it('a poll that changes nothing replays nothing', () => {
    const { rerender, container } = render(card(MIC));
    rerender(card({ ...MIC }));
    expect(container.querySelector('.kel-roll__old, .kel-swap__old, .kel-progress-lead')).toBeNull();
  });

  it('working → in review: the label rolls in its slot, the icon swaps in its own slot, the colour sweeps along the bar', () => {
    motionClock.setManual(true);
    const { rerender, container } = render(card(MIC));
    rerender(card({ ...MIC, state: 'in_review', progress: { done: 4, total: 5 } }));
    expect(screen.getByTestId('kel-office-card-state').textContent).toBe('In review');
    expect(container.querySelector('.kel-wc-state-label .kel-roll__old')?.textContent).toBe('Working');
    expect(container.querySelector('.kel-wc-state-icon .kel-swap__old')).not.toBeNull();
    expect(container.querySelector('.kel-progress-old')).not.toBeNull();
    // quick, not settling: the new words are fully in by 300 ms.
    act(() => motionClock.advance(300));
    expect(screen.getByTestId('kel-office-card-state').style.opacity).toBe('');
  });

  it('reaching Done is a resting end state: it settles in slower, and the check draws on', () => {
    motionClock.setManual(true);
    const { rerender, container } = render(card({ ...MIC, state: 'in_review' }));
    rerender(card({ ...RECEIPTS, job_id: MIC.job_id, title: MIC.title }));
    const label = screen.getByTestId('kel-office-card-state');
    act(() => motionClock.advance(300));
    expect(Number(label.style.opacity)).toBeLessThan(1);
    expect(label.style.filter).toMatch(/blur/);
    const check = container.querySelector<HTMLElement>('.kel-wc-state-icon .kel-swap__now img')!;
    expect(check.style.clipPath).toMatch(/inset/);
    act(() => motionClock.advance(MOTION.settleMs + 200));
    expect(label.style.opacity).toBe('');
  });

  it('a step that starts turns its loader once in its own row; the last step’s tick settles', async () => {
    motionClock.setManual(true);
    const { KelOfficeDetail } = await import('@renderer/components/kel/workCards/KelOfficeDetail');
    const steps = [
      { id: 'a', label: 'Plan', state: 'done', at: 1 },
      { id: 'b', label: 'Build', state: 'running', at: null },
    ];
    let detail: OfficeItemDetail = { ...MIC_DETAIL, steps };
    install();
    extra = (route) => (route.startsWith('/api/office/item') ? detail : undefined);
    const view = (d: OfficeItemDetail) => (
      <KelOfficeDetail item={d as unknown as OfficeItem} pollMs={30} onClose={() => undefined} onRemove={() => undefined} onTalk={() => undefined} onChanged={() => undefined} />
    );
    const { rerender } = render(view(detail));
    await screen.findAllByTestId('kel-office-member');
    const rows = () => screen.getAllByTestId('kel-office-step');
    const leadImg = (row: HTMLElement) => row.querySelector<HTMLElement>(':scope > .kel-wd-step__lead .kel-swap__now img')!;
    detail = { ...detail, steps: [{ ...steps[0] }, { ...steps[1], state: 'done', at: 2 }] };
    rerender(view(detail));
    await waitFor(() => expect(rows()[1].className).toContain('kel-wd-step--done'));
    // The old loader leaves from the same slot in the same row; the check draws on and, being the
    // last step, settles in.
    expect(rows()[1].querySelector(':scope > .kel-wd-step__lead .kel-swap__old')).not.toBeNull();
    expect(leadImg(rows()[1]).style.clipPath).toMatch(/inset/);
    act(() => motionClock.advance(300));
    expect(Number(rows()[1].querySelector<HTMLElement>(':scope > .kel-wd-step__lead .kel-swap__now')!.style.opacity)).toBeLessThan(1);
  });
});

describe('10.6 a Needs you answer', () => {
  it('a picked chip’s gradient grows from where it was pressed', async () => {
    motionClock.setManual(true);
    const { KelChoiceChips } = await import('@renderer/components/kel/workCards/KelChoiceChips');
    render(<KelChoiceChips label='Pick' options={[{ id: 'a', label: 'Battery' }]} onPick={() => undefined} />);
    fireEvent.click(screen.getByRole('radio', { name: 'Battery' }), { clientX: 20, clientY: 10 });
    const bloom = document.querySelector<HTMLElement>('.kel-bloom')!;
    expect(bloom.style.clipPath).toMatch(/^circle\(0px/);
    await act(async () => {
      await motionClock.advanceAsync(600);
    });
    expect(document.querySelector('.kel-bloom')).toBeNull();
  });
});

describe('10.7 scoping → Start', () => {
  it('the card collapses into its summary: a surface travels, the summary settles in', async () => {
    const open: ScopingView = {
      id: 'sc-1',
      state: 'open',
      title: 'Mic mute',
      summary: 'A tray app.',
      questions: [{ id: 'q1', question: 'Which hotkey?', options: [{ code: 'a', label: 'Ctrl+Shift+M' }] }],
    } as ScopingView;
    let view: ScopingView = open;
    install();
    extra = (route) => (route.startsWith('/api/scoping') ? view : undefined);
    render(<KelScopingCard scopingId='sc-1' />);
    await screen.findByTestId('kel-scoping-card');
    motionClock.setManual(true);
    view = { ...open, state: 'started', answer_line: 'Ctrl+Shift+M', started_at: 1 } as ScopingView;
    act(() => {
      window.dispatchEvent(new CustomEvent(REFRESH_WORK_CARDS_EVENT));
    });
    const line = await screen.findByTestId('kel-scoping-collapsed');
    expect(line.classList.contains('kel-motion-hidden')).toBe(true);
    expect(document.querySelector('.kel-motion-layer .kel-motion-surface')).not.toBeNull();
    // Step the clock until the surface lands (promise chains resolve between frames).
    for (let i = 0; i < 12 && line.classList.contains('kel-motion-hidden'); i++) {
      await act(async () => {
        await motionClock.advanceAsync(200);
      });
    }
    expect(line.classList.contains('kel-motion-hidden')).toBe(false);
  });
});

describe('10.8 / 10.9 the result and its done card', () => {
  it('unfolds from its top edge when it arrives, and simply shows on first paint', async () => {
    install();
    motionClock.setManual(true);
    render(<KelDoneCard job={RECEIPTS.job_id} meta={null} />);
    const card = await screen.findByTestId('kel-done-card');
    expect(card.style.clipPath).toMatch(/^inset\(0 0 100%/);
    cleanup();
    setSceneSettledForTests(false);
    install();
    render(<KelDoneCard job={RECEIPTS.job_id} meta={null} />);
    expect((await screen.findByTestId('kel-done-card')).style.clipPath).toBe('');
  });

  it('D-79: no Undo button; the applied line rolls to "Undone" and settles when Nick has Kel undo it', async () => {
    install();
    const code = { ...RECEIPTS_DETAIL, kind: 'code', application: { state: 'APPLIED', auto: true, root: 'C:\\R', files: 2, waiting_reason: null } } as OfficeItemDetail;
    details = { [RECEIPTS.job_id]: code };
    render(<KelDoneCard job={RECEIPTS.job_id} meta={null} />);
    await screen.findByTestId('kel-done-card');
    expect(screen.queryByTestId('kel-done-card-undo')).toBeNull();
    motionClock.setManual(true);
    details = { [RECEIPTS.job_id]: { ...code, application: { ...code.application!, state: 'UNDONE' } } };
    act(() => {
      window.dispatchEvent(new CustomEvent(REFRESH_WORK_CARDS_EVENT));
    });
    await waitFor(() => expect(screen.getByTestId('kel-done-card-applied').textContent).toContain('Undone'));
    const words = screen.getByTestId('kel-done-card-applied').querySelector<HTMLElement>('.kel-roll__now')!;
    act(() => motionClock.advance(300));
    expect(Number(words.style.opacity)).toBeLessThan(1);
  });
});

describe('10.10 the "+N more" menu', () => {
  it('grows out of its tile and folds back into it', async () => {
    list = [MIC, RECEIPTS, { ...MIC, job_id: 'job-c', title: 'C' }, { ...MIC, job_id: 'job-d', title: 'D' }, { ...MIC, job_id: 'job-e', title: 'E' }];
    install();
    render(
      <MemoryRouter>
        <KelWorkCardRow availableWidth={500} pollActiveMs={60000} pollIdleMs={60000} />
      </MemoryRouter>
    );
    const tile = await screen.findByTestId('kel-office-overflow');
    motionClock.setManual(true);
    fireEvent.click(tile);
    const menu = await screen.findByTestId('kel-office-menu');
    expect(menu.classList.contains('kel-motion-hidden')).toBe(true);
    await act(async () => {
      await motionClock.advanceAsync(1200);
    });
    expect(menu.classList.contains('kel-motion-hidden')).toBe(false);
    fireEvent.click(tile);
    await waitFor(() => expect(screen.queryByTestId('kel-office-menu')).toBeNull());
    expect(document.querySelector('.kel-wc-stack > .kel-motion-surface')).not.toBeNull();
  });
});

describe('10.11 / 10.12 indicators and popovers', () => {
  it('a tab’s pill stretches to the next tab (two edges, one element) and only moves on a real change', () => {
    motionClock.setManual(true);
    vi.spyOn(HTMLElement.prototype, 'offsetLeft', 'get').mockImplementation(function (this: HTMLElement) {
      return this.textContent === 'Fixed' ? 120 : this.classList.contains('kel-tab') ? 0 : 0;
    });
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(60);
    vi.spyOn(HTMLElement.prototype, 'offsetParent', 'get').mockImplementation(function (this: HTMLElement) {
      return this.parentElement;
    });
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(28);
    const tabs = [
      { id: 'open', label: 'Open' },
      { id: 'fixed', label: 'Fixed' },
    ];
    const { rerender } = render(<KelTabs tabs={tabs} active='open' onSelect={() => undefined} />);
    const pill = screen.getByTestId('kel-edge-pill');
    expect(pill.style.transform).toBe('translate(0.00px, 0.00px)');
    rerender(<KelTabs tabs={tabs} active='fixed' onSelect={() => undefined} />);
    act(() => motionClock.advance(80));
    const width = parseFloat(pill.style.width);
    expect(width).toBeGreaterThan(60); // stretched between the two tabs
    act(() => motionClock.advance(800));
    expect(pill.style.transform).toBe('translate(120.00px, 0.00px)');
    expect(parseFloat(pill.style.width)).toBe(60);
  });

  it('the Settings nav pill sits 10 px inside both sides of the 200 px nav (Figma 311:2239)', () => {
    const shell = fs.readFileSync(path.join(renderer, 'styles/kel-shell.css'), 'utf8');
    expect(shell).toMatch(/\.kel-in-chat-frame__card \{[^}]*grid-template-columns: 200px/);
    expect(shell).toMatch(/\.kel-in-chat-frame__nav \{[^}]*padding: 16px 10px/);
    expect(shell).toMatch(/\.kel-in-chat-frame__nav-row \{[^}]*width: 100%/);
    // The pill takes the row's own box (spanIn), so its insets are the nav's padding: 10 px each side.
    const nav = document.createElement('nav');
    nav.style.position = 'relative';
    const row = document.createElement('button');
    row.setAttribute('aria-current', 'page');
    nav.appendChild(row);
    document.body.appendChild(nav);
    vi.spyOn(row, 'offsetLeft', 'get').mockReturnValue(10);
    vi.spyOn(row, 'offsetTop', 'get').mockReturnValue(40);
    vi.spyOn(row, 'offsetWidth', 'get').mockReturnValue(179);
    vi.spyOn(row, 'offsetHeight', 'get').mockReturnValue(28);
    vi.spyOn(row, 'offsetParent', 'get').mockReturnValue(nav);
    return import('@renderer/motion').then(({ spanIn }) => {
      const span = spanIn(row, nav, 'y');
      const navWidth = 200 - 1; // content box + padding inside the 1px right border
      expect(span.cross).toBe(10);
      expect(navWidth - (span.cross + span.crossSize)).toBe(10);
      nav.remove();
    });
  });

  it('a popover grows in from its corner and leaves as a fading copy', () => {
    motionClock.setManual(true);
    const { unmount } = render(<KelDesktopProjectMenu projects={[{ id: 'p', name: 'Mic' }]} selected='p' onSelect={() => undefined} onBrowse={() => undefined} />);
    const menu = screen.getByTestId('kel-desktop-project-menu');
    expect(menu.style.transform).toMatch(/scale\(0\.94/);
    act(() => motionClock.advance(600));
    expect(menu.style.transform).toBe('');
    unmount();
    expect(document.querySelector('.kel-motion-exit')).not.toBeNull();
  });
});

describe('10.13 toasts', () => {
  it('Arco’s message classes carry Kel’s enter and exit (rise out of a blur; leave with blur and scale)', () => {
    const css = fs.readFileSync(path.join(renderer, 'styles/arco-override.css'), 'utf8');
    expect(css).toMatch(/\.fadeMessage-enter,\s*\.fadeMessage-appear \{[^}]*translateY\(10px\) scale\(0\.96\)[^}]*blur\(6px\)/);
    expect(css).toMatch(/\.fadeMessage-exit-active \{[^}]*scale\(0\.97\)[^}]*blur\(4px\)[^}]*140ms/);
  });
});

describe('§9 nothing loops except Thinking', () => {
  it('the stop button no longer breathes and the running mark no longer pulses', () => {
    const sendbox = fs.readFileSync(path.join(renderer, 'components/chat/SendBox/sendbox.css'), 'utf8');
    expect(sendbox).not.toMatch(/bg-animate[^{]*\{[^}]*animation:/);
    const card = fs.readFileSync(path.join(renderer, 'components/kel/KelWorkCard.css'), 'utf8');
    expect(card).not.toMatch(/__mark--active \{[^}]*animation:/);
  });
});
