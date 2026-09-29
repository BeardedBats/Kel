/**
 * D-68 — the row of work cards directly under the chat title (Figma "Office — D-66 explorations",
 * 4a–4d). D-73.4: in an open chat the row shows that chat's project's work (and always this chat's own
 * work, so the in-thread "follow it above" line has its card); in a new chat it follows the active
 * project (every project on "All projects"). Cards that do not fit go behind a "+N more" control measured from the real width;
 * finished work stays until Nick removes it; a card opens the read-only detail over a dimmed chat.
 * With no work the row renders nothing, so the chat keeps its height.
 *
 * On the phone (`phone`) the same cards sit in a compact strip under the header that scrolls
 * sideways (no "+N more" menu), and a card opens its detail as a bottom sheet over the chat
 * (inferred from the phone sheets — docs/v2/FIGMA_GAPS.md "Work cards on the phone").
 */
import { ipcBridge } from '@/common';
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { getRouteConversationIdForKelId, resolveConversationRoute } from '@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync';
import { resolveEngineConversation } from '../KelApprovalCard';
import { useConversationProject, useProjects } from '../activeProject';
import {
  officeDismiss,
  officeItem,
  officeList,
  officeListForChat,
  scopingDismiss,
  type OfficeItem,
  type OfficeItemDetail,
  type OfficeTeamChip,
} from './officeApi';
import { KelOfficeCard } from './KelOfficeCard';
import { KelOfficeDetail } from './KelOfficeDetail';
import { StatusDot, dotToneFor, iconChev } from './workCardIcons';
import {
  OVERFLOW_MAX_DOTS,
  POLL_ACTIVE_MS,
  POLL_IDLE_MS,
  cardStateLabel,
  cardTeam,
  cardUncertain,
  fitCards,
  isFinished,
  isLive,
  isRunning,
  orderItems,
  overflowWidth,
} from './workCardModel';
import { OPEN_WORK_CARD_EVENT, REFRESH_WORK_CARDS_EVENT, refreshWorkCards, takePendingWorkCard } from './workCardEvents';
import { MOTION, claimShared, exitGhostAt, isArrivalTime, snapshotGhost, useFlip, type Snapshot } from '@renderer/motion';
import {
  backdropIn,
  backdropOut,
  cardIntoTile,
  closeDetailMorph,
  closeMenuMorph,
  handoffFlight,
  openDetailMorph,
  openMenuMorph,
  revealCard,
  type OpenHandle,
} from './workCardMotion';
import './KelWorkCards.css';
import './KelWorkCardsRow5.css';
import './KelWorkCardsPhone.css';

const hidden = () => typeof document !== 'undefined' && document.visibilityState === 'hidden';

type Teams = Record<string, { updated: number | null | undefined; team: OfficeTeamChip[] }>;

/**
 * One list from the project's cards and this chat's own cards (D-73.4): the project's read decides the
 * order; this chat's work the project read did not carry (it landed in another project) follows it.
 */
export const mergeOfficeLists = (projectItems: OfficeItem[], chatItems: OfficeItem[] | null | undefined): OfficeItem[] => {
  const seen = new Set(projectItems.map((item) => item.job_id));
  const extra = (chatItems ?? []).filter((item) => !seen.has(item.job_id));
  if (!extra.length) return projectItems;
  // Two engine orders cannot be compared; the row then groups live work before finished work itself.
  return [...projectItems, ...extra].map(({ order: _order, ...item }) => item);
};

/**
 * Polls the Office list gently: every 4 s while anything runs, 30 s when idle, paused while the
 * window is hidden. A failed read keeps the last good state and says nothing. `project` null means
 * the scope is not known yet (nothing is read); `conversation` (the engine's id) adds that chat's work.
 */
export const useOfficeItems = (
  project: string | null,
  pollActiveMs = POLL_ACTIVE_MS,
  pollIdleMs = POLL_IDLE_MS,
  conversation: string | null = null
) => {
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
    if (project === null) return;

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
        const [list, chat] = await Promise.all([
          officeList(project),
          conversation ? officeListForChat(conversation).catch((): null => null) : Promise.resolve(null),
        ]);
        if (stopped) return;
        const merged = mergeOfficeLists(list.items, chat?.items);
        itemsRef.current = merged;
        setItems(merged);
        setReadSeq(mine);
        void readTeams(merged);
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
  }, [project, conversation, pollActiveMs, pollIdleMs]);

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

/** How long the scoping questions stay highlighted after the Scoping card takes you to them. */
export const SCOPING_HIGHLIGHT_MS = 2400;

/**
 * LIVE-7: take Nick to Kel's scoping questions in the thread — scroll them into view, highlight them
 * and put focus on the first answer. The card may still be arriving (the message's details land a
 * moment after the text), so this looks again for a short while before settling on the newest message.
 */
export const revealScopingQuestions = (id: string, attempts = 20, gapMs = 150): void => {
  const look = (left: number) => {
    const card = document.querySelector<HTMLElement>(`[data-scoping-card="${id}"]`);
    if (card) {
      card.scrollIntoView?.({ block: 'center', behavior: 'smooth' });
      card.classList.add('is-highlighted');
      window.setTimeout(() => card.classList.remove('is-highlighted'), SCOPING_HIGHLIGHT_MS);
      card.querySelector<HTMLElement>('button:not([disabled]), input')?.focus({ preventScroll: true });
      return;
    }
    if (left > 0) {
      window.setTimeout(() => look(left - 1), gapMs);
      return;
    }
    const items = document.querySelectorAll<HTMLElement>('.message-item');
    items[items.length - 1]?.scrollIntoView?.({ block: 'end', behavior: 'smooth' });
  };
  look(attempts);
};

/** A card's detail read, shaped as a list item so the row can show work its scope did not list. */
const asItem = (detail: OfficeItemDetail): OfficeItem => {
  const { staff, ...rest } = detail;
  return { ...(rest as unknown as OfficeItem), team: cardTeam(staff) };
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
  /** The phone layout: a sideways-scrolling strip, and the detail as a bottom sheet. */
  phone?: boolean;
};

export const KelWorkCardRow: React.FC<Props> = ({
  conversationId,
  availableWidth,
  pollActiveMs,
  pollIdleMs,
  openFolder = defaultOpenFolder,
  phone = false,
}) => {
  const navigate = useNavigate();
  const { active, projects } = useProjects();
  // D-73.4: an open chat shows its own project's work; a chat Kel has not seen yet (its project is
  // "pending") follows the active project, like Home. Nothing is read until the chat's project is known.
  const chat = useConversationProject(conversationId);
  const [engineChat, setEngineChat] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    setEngineChat(null);
    if (!conversationId) return;
    void resolveEngineConversation(conversationId).then((cid) => {
      if (alive) setEngineChat(cid || null);
    });
    return () => {
      alive = false;
    };
  }, [conversationId]);
  const followsActive = !conversationId || chat.pending || !chat.project;
  const project = conversationId && !chat.loaded ? null : followsActive ? active || '*' : chat.project?.id ?? active ?? '*';
  const { items: listed, teams, refresh, readSeq, startedSeq } = useOfficeItems(
    project,
    pollActiveMs,
    pollIdleMs,
    conversationId && !chat.pending ? engineChat : null
  );
  /** Work another surface asked to open that this row's scope does not list (read from its detail). */
  const [pinned, setPinned] = useState<OfficeItem[]>([]);
  const items = useMemo(() => (listed ? mergeOfficeLists(listed, pinned) : listed), [listed, pinned]);
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
    if (availableWidth !== undefined || phone) return;
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
  }, [availableWidth, phone, ordered.length > 0]);

  const width = availableWidth ?? measured;
  // The phone strip scrolls, so every card is in it; the desktop row fits what the width allows.
  const visibleCount = phone ? ordered.length : fitCards(width, ordered.length);
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
      // D-70 (5e) / LIVE-7: Kel's questions live in the thread; the top card takes you to them
      // (in their own chat when they were asked elsewhere) and highlights them — never "Talk to Kel".
      setMenuOpen(false);
      void goToScopingRef.current(item);
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

  /**
   * D-74.3: "Not now" on an open scoping card cancels Kel's questions (nothing starts). The card goes
   * at once; if the engine keeps it, it comes back rather than disappearing untruthfully.
   */
  const notNow = useCallback(
    (item: OfficeItem) => {
      if (item.state !== 'scoping') return;
      const mark = (value: number | null) =>
        setDismissed((current) => {
          const next = new Map(current);
          if (value === null) next.delete(item.job_id);
          else next.set(item.job_id, value);
          return next;
        });
      mark(Number.POSITIVE_INFINITY);
      scopingDismiss(item.scoping_id ?? item.job_id)
        .then(() => {
          mark(startedSeq.current);
          refresh();
          // The questions in the thread read again and settle into their "Not now" line.
          refreshWorkCards();
        })
        .catch(() => mark(null));
    },
    [refresh, startedSeq]
  );

  /** LIVE-3: a needs-you card's "Change the model in Staff & models" goes to Settings; nothing is sent. */
  const openSettings = useCallback(
    (path: string) => {
      setOpenJob(null);
      triggerRef.current = null;
      navigate(path);
    },
    [navigate]
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


  const goToScoping = useCallback(
    async (item: OfficeItem) => {
      const id = item.scoping_id ?? item.job_id;
      const target = item.conversation_id;
      const here =
        !target ||
        target === conversationId ||
        target === engineChat ||
        getRouteConversationIdForKelId(target) === conversationId ||
        (conversationId ? (await resolveEngineConversation(conversationId).catch(() => conversationId)) === target : false);
      if (!here) {
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
        revealScopingQuestions(id, 40);
        return;
      }
      revealScopingQuestions(id);
    },
    [conversationId, engineChat, navigate]
  );
  const goToScopingRef = useRef(goToScoping);
  goToScopingRef.current = goToScoping;

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
    if (!ordered.some((item) => item.job_id === wanted)) {
      // The in-thread line or a done card asked for work this row's scope does not list (it belongs to
      // another project): read it and show its card here rather than doing nothing.
      if (pinned.some((item) => item.job_id === wanted)) return;
      let alive = true;
      officeItem(wanted)
        .then((detail) => {
          if (alive && detail && typeof detail.job_id === 'string') setPinned((current) => [...current, asItem(detail)]);
          else if (alive) setWanted(null);
        })
        .catch(() => {
          if (alive) setWanted(null);
        });
      return () => {
        alive = false;
      };
    }
    triggerRef.current = null;
    setMenuOpen(false);
    setOpenJob(wanted);
    setWanted(null);
  }, [wanted, items, ordered, pinned]);

  // A pinned card leaves once its detail closes (or once the row's own read lists it).
  useEffect(() => {
    if (!pinned.length || !listed) return;
    const keep = pinned.filter((item) => (item.job_id === openJob || item.job_id === wanted) && !listed.some((row) => row.job_id === item.job_id));
    if (keep.length !== pinned.length) setPinned(keep);
  }, [pinned, listed, openJob, wanted]);

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

  // The phone sheet holds the page still behind it (the chat does not scroll under the scrim).
  useEffect(() => {
    if (!phone || !openJob || typeof document === 'undefined') return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [phone, openJob]);

  // Forget a removal once a read that started after the engine confirmed it has arrived.
  useEffect(() => {
    if (![...dismissed.values()].some((seq) => seq < readSeq)) return;
    setDismissed((current) => new Map([...current].filter(([, seq]) => seq >= readSeq)));
  }, [readSeq, dismissed]);

  // The open card left (dismissed elsewhere or aged out): close its detail.
  useEffect(() => {
    if (openJob && items && !openItem) setOpenJob(null);
  }, [openJob, items, openItem]);

  /* ─── D-78 motion (MOTION.md §10.2, §10.3, §10.10). Keyed to real changes: the open card, the menu,
     and which work is in the row — never to a poll that changed nothing. ─── */
  const hostRef = useRef<HTMLDivElement>(null);
  const stackRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const visibleIds = visible.map((item) => item.job_id);
  const orderedIds = ordered.map((item) => item.job_id);
  // Existing cards FLIP to their new places when work arrives or leaves (resizes snap).
  useFlip(rowRef, `${visibleIds.join('|')}#${overflow.length}`, { selector: ':scope > .kel-wc-slot', enabled: !phone });
  const motionSeen = useRef<{ open: string | null; menu: boolean; visible: string[]; ordered: string[]; loaded: boolean } | null>(null);
  const snaps = useRef<{ panel?: Snapshot | null; menu?: Snapshot | null; cards: Map<string, Snapshot> }>({ cards: new Map() });
  const opening = useRef<OpenHandle | null>(null);
  const cardEl = (job: string | null | undefined): HTMLElement | null =>
    job ? rowRef.current?.querySelector<HTMLElement>(`.kel-wc[data-job="${job.replace(/"/g, '\\"')}"]`) ?? null : null;
  // Before React changes the DOM, copy what is about to leave it (the panel, the menu, departing cards).
  const seen = motionSeen.current;
  if (seen && !phone) {
    if (seen.open && seen.open !== openJob && snaps.current.panel === undefined) {
      snaps.current.panel = snapshotGhost(detailRef.current?.firstElementChild);
    }
    if (seen.menu && !menuOpen && snaps.current.menu === undefined) snaps.current.menu = snapshotGhost(menuRef.current);
    for (const id of seen.visible) {
      if (!visibleIds.includes(id) && !snaps.current.cards.has(id)) {
        const snap = snapshotGhost(cardEl(id));
        if (snap) snaps.current.cards.set(id, snap);
      }
    }
  }
  useLayoutEffect(() => {
    const before = motionSeen.current;
    motionSeen.current = { open: openJob, menu: menuOpen, visible: visibleIds, ordered: orderedIds, loaded: items !== null };
    const taken = snaps.current;
    snaps.current = { cards: new Map() };
    const stack = stackRef.current;
    if (phone || !before || !stack) return;
    // The card and its panel.
    if (before.open !== openJob) {
      opening.current?.cancel();
      opening.current = null;
      if (before.open) void closeDetailMorph(stack, taken.panel ?? null, cardEl(before.open) ?? chipRef.current);
      if (!openJob) backdropOut(hostRef.current, stack);
      const panel = detailRef.current?.firstElementChild as HTMLElement | null;
      if (openJob && panel) {
        const source = cardEl(openJob) ?? chipRef.current;
        if (source) opening.current = openDetailMorph(stack, source, panel);
        if (!before.open) backdropIn(backdropRef.current);
      }
    }
    // "+N more" and its menu.
    if (before.menu !== menuOpen) {
      if (menuOpen && chipRef.current && menuRef.current) openMenuMorph(stack, chipRef.current, menuRef.current);
      else if (!menuOpen) void closeMenuMorph(stack, taken.menu ?? null, chipRef.current);
    }
    // Work that arrived while Nick watches: lifted out of its in-thread line, or revealed from its top edge.
    if (before.loaded) {
      for (const id of visibleIds) {
        if (before.ordered.includes(id)) continue;
        const card = cardEl(id);
        if (!card) continue;
        const line = claimShared(`handoff:${id}`);
        if (line) void handoffFlight(line.el, card, MOTION.handoffBeatMs - (Date.now() - line.at));
        else if (isArrivalTime()) revealCard(card);
      }
      for (const [id, snap] of taken.cards) {
        if (orderedIds.includes(id) && chipRef.current) void cardIntoTile(stack, snap, chipRef.current);
        else if (!orderedIds.includes(id)) void exitGhostAt(snap, { scale: 0.96, blur: 4, ms: 130 });
      }
    }
  });

  if (!ordered.length) return null;

  const projectName = (id: string | null | undefined) => (id ? projects?.find((row) => row.id === id)?.name ?? null : null);
  const projectRoot = (id: string | null | undefined) => (id ? projects?.find((row) => row.id === id)?.root ?? null : null);
  const hiddenRunning = overflow.filter((item) => !isFinished(item.state));
  const hiddenFinished = overflow.filter((item) => isFinished(item.state));
  const dots = overflow.slice(0, OVERFLOW_MAX_DOTS);

  return (
    <div ref={hostRef} className={`kel-wc-host${phone ? ' kel-wc-host--phone' : ''}`} data-testid='kel-work-card-row' data-layout={phone ? 'phone' : 'desktop'}>
      {openItem && !phone ? <div ref={backdropRef} className='kel-wc-backdrop' data-testid='kel-office-backdrop' aria-hidden='true' onMouseDown={() => closeDetail(false)} /> : null}
      <div className='kel-wc-stack' ref={stackRef}>
      <div className={`kel-wc-row${phone ? ' kel-wc-row--phone' : ''}`} ref={rowRef} role='list' aria-label='Work in progress'>
        {visible.map((item) => (
          <div role='listitem' key={item.job_id} className='kel-wc-slot'>
            <KelOfficeCard
              item={item}
              team={teamFor(item)}
              variant={phone ? 'strip' : 'row'}
              selected={openJob === item.job_id}
              onOpen={openDetail}
              // On the phone a finished card is removed from its sheet (a 44pt Remove), not a tiny ×.
              onRemove={phone ? undefined : remove}
              onNotNow={notNow}
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
                  <StatusDot key={item.job_id} tone={cardUncertain(item) ? 'needs' : dotToneFor(item.state)} />
                ))}
              </span>
            </button>
            {menuOpen ? (
              <div className='kel-wc-menu' ref={menuRef} data-testid='kel-office-menu' role='group' aria-label='More work'>
                {hiddenRunning.length ? (
                  <>
                    <p className='kel-wc-menu__section'>Running</p>
                    {hiddenRunning.map((item) => (
                      <KelOfficeCard
                        key={item.job_id}
                        item={item}
                        team={teamFor(item)}
                        variant='menu'
                        onOpen={openDetail}
                        onRemove={remove}
                        onNotNow={notNow}
                      />
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
      {openItem && phone
        ? createPortal(
            <div className='kel-wc-sheet' data-testid='kel-work-sheet'>
              <button type='button' className='kel-wc-sheet__scrim' aria-label='Close work details' onClick={() => closeDetail(false)} />
              <div className='kel-wc-sheet__panel' ref={detailRef}>
                <KelOfficeDetail
                  key={openItem.job_id}
                  variant='sheet'
                  item={openItem}
                  projectName={projectName(openItem.project_id)}
                  pollMs={isRunning(openItem.state) ? pollActiveMs ?? POLL_ACTIVE_MS : pollIdleMs ?? POLL_IDLE_MS}
                  onClose={closeDetail}
                  onRemove={remove}
                  onTalk={(item) => void talk(item)}
                  onChanged={refresh}
                  onOpenSettings={openSettings}
                />
              </div>
            </div>,
            document.body
          )
        : null}
      {openItem && !phone ? (
        <div className='kel-wc-detail-slot' ref={detailRef}>
          <KelOfficeDetail
            key={openItem.job_id}
            item={openItem}
            projectName={projectName(openItem.project_id)}
            projectRoot={projectRoot(openItem.project_id)}
            pollMs={isRunning(openItem.state) ? pollActiveMs ?? POLL_ACTIVE_MS : pollIdleMs ?? POLL_IDLE_MS}
            onClose={closeDetail}
            onRemove={remove}
            onTalk={(item) => void talk(item)}
            onChanged={refresh}
            onOpenSettings={openSettings}
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
      // "never ran" and "undone" as the card itself says them.
      return cardStateLabel(item).toLowerCase();
  }
};

export default KelWorkCardRow;
