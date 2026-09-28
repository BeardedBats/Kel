/**
 * D-68 — the row of work cards directly under the chat title (Figma "Office — D-66 explorations",
 * 4a–4d). One card per piece of work Kel's staff is doing for the active Project (every Project on
 * "All projects"); cards that do not fit go behind a "+N more" control measured from the real width;
 * finished work stays until Nick removes it; a card opens the read-only detail over a dimmed chat.
 * With no work the row renders nothing, so the chat keeps its height.
 */
import { ipcBridge } from '@/common';
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getRouteConversationIdForKelId, resolveConversationRoute } from '@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync';
import { resolveEngineConversation } from '../KelApprovalCard';
import { useProjects } from '../activeProject';
import { officeDismiss, officeItem, officeList, type OfficeItem, type OfficeTeamChip } from './officeApi';
import { KelOfficeCard } from './KelOfficeCard';
import { KelOfficeDetail } from './KelOfficeDetail';
import { StatusDot, dotToneFor, iconChev } from './workCardIcons';
import {
  OVERFLOW_MAX_DOTS,
  POLL_ACTIVE_MS,
  POLL_IDLE_MS,
  cardTeam,
  fitCards,
  isFinished,
  isLive,
  isRunning,
  orderItems,
  overflowWidth,
} from './workCardModel';
import { OPEN_WORK_CARD_EVENT, REFRESH_WORK_CARDS_EVENT, takePendingWorkCard } from './workCardEvents';
import './KelWorkCards.css';
import './KelWorkCardsRow5.css';

const hidden = () => typeof document !== 'undefined' && document.visibilityState === 'hidden';

type Teams = Record<string, { updated: number | null | undefined; team: OfficeTeamChip[] }>;

/**
 * Polls the Office list gently: every 4 s while anything runs, 30 s when idle, paused while the
 * window is hidden. A failed read keeps the last good state and says nothing.
 */
export const useOfficeItems = (project: string, pollActiveMs = POLL_ACTIVE_MS, pollIdleMs = POLL_IDLE_MS) => {
  const [items, setItems] = useState<OfficeItem[] | null>(null);
  /** Which read produced `items` (reads are numbered as they start). */
  const [readSeq, setReadSeq] = useState(0);
  const startedSeq = useRef(0);
  const [teams, setTeams] = useState<Teams>({});
  const itemsRef = useRef<OfficeItem[] | null>(null);
  const teamsRef = useRef<Teams>({});
  const kick = useRef<() => void>(() => undefined);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let running = false;
    let again = false;
    itemsRef.current = null;
    setItems(null);

    // Cards need the team's initials; when the list does not carry them, read each running item's
    // detail once per engine update (not on every poll).
    const readTeams = async (list: OfficeItem[]) => {
      const wanted = list.filter(
        (item) => isRunning(item.state) && !Array.isArray(item.team) && teamsRef.current[item.job_id]?.updated !== (item.updated_at ?? null)
      );
      if (!wanted.length) return;
      const reads = await Promise.all(
        wanted.map((item) =>
          officeItem(item.job_id)
            .then((detail) => [item.job_id, { updated: item.updated_at ?? null, team: cardTeam(detail?.staff) }] as const)
            .catch((): null => null)
        )
      );
      if (stopped) return;
      const next = { ...teamsRef.current };
      for (const read of reads) if (read) next[read[0]] = read[1];
      teamsRef.current = next;
      setTeams(next);
    };

    const schedule = () => {
      if (stopped) return;
      if (timer) clearTimeout(timer);
      if (hidden()) return;
      const live = (itemsRef.current ?? []).some((item) => isLive(item.state));
      timer = setTimeout(() => void tick(), live ? pollActiveMs : pollIdleMs);
    };

    const tick = async () => {
      if (stopped || running) return;
      if (hidden()) return;
      running = true;
      const mine = ++startedSeq.current;
      try {
        const list = await officeList(project);
        if (stopped) return;
        itemsRef.current = list.items;
        setItems(list.items);
        setReadSeq(mine);
        void readTeams(list.items);
      } catch {
        // Quiet: keep the last good state, no toast.
      } finally {
        running = false;
        if (again && !stopped) {
          again = false;
          void tick();
        } else schedule();
      }
    };

    const onVisibility = () => {
      if (hidden()) {
        if (timer) clearTimeout(timer);
        return;
      }
      void tick();
    };

    kick.current = () => {
      if (running) {
        again = true;
        return;
      }
      if (timer) clearTimeout(timer);
      void tick();
    };
    void tick();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [project, pollActiveMs, pollIdleMs]);

  const refresh = useCallback(() => kick.current(), []);
  return { items, teams, refresh, readSeq, startedSeq };
};

/** Focus the chat composer, waiting for it to mount after a navigation. */
const findComposer = () => document.querySelector<HTMLTextAreaElement>('.sendbox-panel textarea');

export const focusComposer = (attempts = 30) => {
  const tryFocus = (left: number) => {
    const textarea = findComposer();
    if (textarea) {
      textarea.focus();
      const end = textarea.value.length;
      textarea.setSelectionRange?.(end, end);
      return;
    }
    if (left > 0) window.setTimeout(() => tryFocus(left - 1), 100);
  };
  tryFocus(attempts);
};

const defaultOpenFolder = async (path: string) => {
  try {
    await ipcBridge.shell.openFile.invoke(path);
  } catch {
    await ipcBridge.shell.showItemInFolder.invoke(path);
  }
};

type Props = {
  /** The chat this row sits in (the app's conversation id). */
  conversationId?: string;
  /** Test seam: a fixed width instead of measuring the row. */
  availableWidth?: number;
  pollActiveMs?: number;
  pollIdleMs?: number;
  openFolder?: (path: string) => Promise<unknown>;
};

export const KelWorkCardRow: React.FC<Props> = ({ conversationId, availableWidth, pollActiveMs, pollIdleMs, openFolder = defaultOpenFolder }) => {
  const navigate = useNavigate();
  const { active, projects } = useProjects();
  const project = active || '*';
  const { items, teams, refresh, readSeq, startedSeq } = useOfficeItems(project, pollActiveMs, pollIdleMs);
  /**
   * Cards removed here, hidden at once: job → the last read started before the engine confirmed
   * (Infinity while waiting). A read that starts after the confirmation is the truth again.
   */
  const [dismissed, setDismissed] = useState<Map<string, number>>(() => new Map());
  const [openJob, setOpenJob] = useState<string | null>(null);
  /** D-70: a card another surface asked to open (the in-thread line, a done card, Needs you). */
  const [wanted, setWanted] = useState<string | null>(() => takePendingWorkCard());
  const [menuOpen, setMenuOpen] = useState(false);
  const [measured, setMeasured] = useState(0);
  const rowRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const chipRef = useRef<HTMLButtonElement>(null);
  const detailRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const ordered = useMemo(
    () => orderItems((items ?? []).filter((item) => !dismissed.has(item.job_id))),
    [items, dismissed]
  );

  // Measure the real width, and again whenever it changes.
  useLayoutEffect(() => {
    if (availableWidth !== undefined) return;
    const node = rowRef.current;
    if (!node) return;
    const read = () => setMeasured(node.getBoundingClientRect().width || node.clientWidth || 0);
    read();
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', read);
      return () => window.removeEventListener('resize', read);
    }
    const observer = new ResizeObserver(read);
    observer.observe(node);
    return () => observer.disconnect();
  }, [availableWidth, ordered.length > 0]);

  const width = availableWidth ?? measured;
  const visibleCount = fitCards(width, ordered.length);
  const visible = ordered.slice(0, visibleCount);
  const overflow = ordered.slice(visibleCount);
  const openItem = openJob ? ordered.find((item) => item.job_id === openJob) ?? null : null;

  const teamFor = useCallback(
    (item: OfficeItem): OfficeTeamChip[] => (Array.isArray(item.team) ? cardTeam(item.team) : teams[item.job_id]?.team ?? []),
    [teams]
  );

  /** Close the detail; focus returns to its card unless the person clicked somewhere else. */
  const closeDetail = useCallback((restoreFocus = true) => {
    setOpenJob(null);
    const trigger = triggerRef.current;
    triggerRef.current = null;
    if (restoreFocus && trigger && trigger.isConnected) trigger.focus();
  }, []);

  const openDetail = useCallback((item: OfficeItem, trigger: HTMLElement) => {
    if (item.state === 'scoping') {
      // D-70 (5e): Kel's questions live in the thread; the top card takes you to them.
      setMenuOpen(false);
      const card = document.querySelector<HTMLElement>(`[data-scoping-card="${item.scoping_id ?? item.job_id}"]`);
      if (card) {
        card.scrollIntoView({ block: 'center', behavior: 'smooth' });
        card.querySelector<HTMLElement>('button, input')?.focus({ preventScroll: true });
      } else void talkRef.current(item);
      return;
    }
    // A card inside the "+N more" menu goes away with the menu; focus then returns to the control.
    triggerRef.current = menuRef.current?.contains(trigger) ? chipRef.current ?? trigger : trigger;
    setMenuOpen(false);
    setOpenJob((current) => (current === item.job_id ? null : item.job_id));
  }, []);

  const remove = useCallback(
    (item: OfficeItem) => {
      if (!isFinished(item.state)) return;
      const mark = (value: number | null) =>
        setDismissed((current) => {
          const next = new Map(current);
          if (value === null) next.delete(item.job_id);
          else next.set(item.job_id, value);
          return next;
        });
      mark(Number.POSITIVE_INFINITY);
      if (openJob === item.job_id) setOpenJob(null);
      officeDismiss(item.job_id)
        .then(() => {
          mark(startedSeq.current);
          refresh();
        })
        // The engine kept it: the card comes back rather than disappearing untruthfully.
        .catch(() => mark(null));
    },
    [openJob, refresh, startedSeq]
  );

  const talk = useCallback(
    async (item: OfficeItem) => {
      setOpenJob(null);
      triggerRef.current = null;
      const target = item.conversation_id;
      if (!target) {
        focusComposer();
        return;
      }
      const here =
        target === conversationId ||
        getRouteConversationIdForKelId(target) === conversationId ||
        (conversationId ? (await resolveEngineConversation(conversationId).catch(() => conversationId)) === target : false);
      if (here) {
        focusComposer();
        return;
      }
      let route: string | null = null;
      const open = typeof window !== 'undefined' ? window.kelAPI?.openEngineConversation : undefined;
      if (open) {
        try {
          const donor = await open(target);
          if (donor) route = `/conversation/${donor}`;
        } catch {
          // Fall back to the chat list's own mapping.
        }
      }
      navigate(route ?? resolveConversationRoute(`/conversation/${target}`));
      focusComposer();
    },
    [conversationId, navigate]
  );

  const talkRef = useRef(talk);
  talkRef.current = talk;

  // D-70: other surfaces open this row's card (never a second copy of the work) or ask for a read.
  useEffect(() => {
    const onOpen = (event: Event) => {
      const job = (event as CustomEvent<{ job?: string }>).detail?.job;
      if (!job) return;
      takePendingWorkCard();
      setWanted(job);
      refresh();
    };
    const onRefresh = () => refresh();
    window.addEventListener(OPEN_WORK_CARD_EVENT, onOpen);
    window.addEventListener(REFRESH_WORK_CARDS_EVENT, onRefresh);
    return () => {
      window.removeEventListener(OPEN_WORK_CARD_EVENT, onOpen);
      window.removeEventListener(REFRESH_WORK_CARDS_EVENT, onRefresh);
    };
  }, [refresh]);

  useEffect(() => {
    if (!wanted || !items) return;
    if (!ordered.some((item) => item.job_id === wanted)) return;
    triggerRef.current = null;
    setMenuOpen(false);
    setOpenJob(wanted);
    setWanted(null);
  }, [wanted, items, ordered]);

  // Escape closes the menu or the detail; a click outside the menu closes it.
  useEffect(() => {
    if (!menuOpen && !openJob) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      if (menuOpen) {
        setMenuOpen(false);
        chipRef.current?.focus();
      } else closeDetail();
    };
    const onPointer = (event: MouseEvent) => {
      const target = event.target as Node;
      if (menuOpen) {
        if (menuRef.current?.contains(target) || chipRef.current?.contains(target)) return;
        setMenuOpen(false);
        return;
      }
      // Anywhere outside the detail and the row closes the detail (a card click switches instead).
      if (detailRef.current?.contains(target) || rowRef.current?.contains(target)) return;
      closeDetail(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onPointer);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onPointer);
    };
  }, [menuOpen, openJob, closeDetail]);

  // Forget a removal once a read that started after the engine confirmed it has arrived.
  useEffect(() => {
    if (![...dismissed.values()].some((seq) => seq < readSeq)) return;
    setDismissed((current) => new Map([...current].filter(([, seq]) => seq >= readSeq)));
  }, [readSeq, dismissed]);

  // The open card left (dismissed elsewhere or aged out): close its detail.
  useEffect(() => {
    if (openJob && items && !openItem) setOpenJob(null);
  }, [openJob, items, openItem]);

  if (!ordered.length) return null;

  const projectName = (id: string | null | undefined) => (id ? projects?.find((row) => row.id === id)?.name ?? null : null);
  const hiddenRunning = overflow.filter((item) => !isFinished(item.state));
  const hiddenFinished = overflow.filter((item) => isFinished(item.state));
  const dots = overflow.slice(0, OVERFLOW_MAX_DOTS);

  return (
    <div className='kel-wc-host' data-testid='kel-work-card-row'>
      {openItem ? <div className='kel-wc-backdrop' data-testid='kel-office-backdrop' aria-hidden='true' onMouseDown={() => closeDetail(false)} /> : null}
      <div className='kel-wc-stack'>
      <div className='kel-wc-row' ref={rowRef} role='list' aria-label='Work in progress'>
        {visible.map((item) => (
          <div role='listitem' key={item.job_id} className='kel-wc-slot'>
            <KelOfficeCard
              item={item}
              team={teamFor(item)}
              selected={openJob === item.job_id}
              onOpen={openDetail}
              onRemove={remove}
            />
          </div>
        ))}
        {overflow.length ? (
          <div role='listitem' className='kel-wc-slot kel-wc-overflow-slot'>
            <button
              ref={chipRef}
              type='button'
              className={`kel-wc-overflow${menuOpen ? ' is-open' : ''}`}
              style={{ width: overflowWidth(overflow.length) }}
              aria-haspopup='true'
              aria-expanded={menuOpen}
              aria-label={`${overflow.length} more: ${overflow.map((item) => `${item.title} (${stateWords(item)})`).join(', ')}`}
              onClick={() => {
                setOpenJob(null);
                setMenuOpen((open) => !open);
              }}
              data-testid='kel-office-overflow'
            >
              <span className='kel-wc-overflow__label'>
                {`+${overflow.length} more`}
                <img src={iconChev} alt='' />
              </span>
              <span className='kel-wc-overflow__dots' aria-hidden='true'>
                {dots.map((item) => (
                  <StatusDot key={item.job_id} tone={dotToneFor(item.state)} />
                ))}
              </span>
            </button>
            {menuOpen ? (
              <div className='kel-wc-menu' ref={menuRef} data-testid='kel-office-menu' role='group' aria-label='More work'>
                {hiddenRunning.length ? (
                  <>
                    <p className='kel-wc-menu__section'>Running</p>
                    {hiddenRunning.map((item) => (
                      <KelOfficeCard key={item.job_id} item={item} team={teamFor(item)} variant='menu' onOpen={openDetail} onRemove={remove} />
                    ))}
                  </>
                ) : null}
                {hiddenFinished.length ? (
                  <>
                    <p className='kel-wc-menu__section'>Finished</p>
                    {hiddenFinished.map((item) => (
                      <KelOfficeCard key={item.job_id} item={item} team={teamFor(item)} variant='menu' onOpen={openDetail} onRemove={remove} />
                    ))}
                  </>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
      {openItem ? (
        <div className='kel-wc-detail-slot' ref={detailRef}>
          <KelOfficeDetail
            key={openItem.job_id}
            item={openItem}
            projectName={projectName(openItem.project_id)}
            pollMs={isRunning(openItem.state) ? pollActiveMs ?? POLL_ACTIVE_MS : pollIdleMs ?? POLL_IDLE_MS}
            onClose={closeDetail}
            onRemove={remove}
            onTalk={(item) => void talk(item)}
            onChanged={refresh}
            openFolder={openFolder}
          />
        </div>
      ) : null}
      </div>
    </div>
  );
};

const stateWords = (item: OfficeItem) => {
  switch (item.state) {
    case 'in_review':
      return 'in review';
    case 'needs_you':
      return 'needs you';
    case 'scoping':
      return 'scoping, Kel has questions first';
    default:
      return item.state;
  }
};

export default KelWorkCardRow;
