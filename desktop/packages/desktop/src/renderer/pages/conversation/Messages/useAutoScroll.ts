/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * useAutoScroll - Auto-scroll hook for a plain scroll container
 *
 * Strategy:
 * - Track whether the user has intentionally scrolled away from the bottom.
 * - Observe content/scroller size changes and keep the list pinned to bottom
 *   only while auto-follow mode is active.
 * - Use DOM-native scrollIntoView for explicit message jumps.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { TMessage } from '@/common/chat/chatLib';
import { glide, isArrivalTime } from '@renderer/motion';

const PROGRAMMATIC_SCROLL_GUARD_MS = 150;
const AT_BOTTOM_THRESHOLD_PX = 100;
const FOLLOW_BOTTOM_THRESHOLD_PX = 4;

interface UseAutoScrollOptions {
  messages: TMessage[];
  itemCount: number;
}

interface ScrollElementIntoViewOptions {
  behavior?: ScrollBehavior;
  block?: ScrollLogicalPosition;
}

interface UseAutoScrollReturn {
  handleScrollerRef: (ref: HTMLDivElement | null) => void;
  handleContentRef: (ref: HTMLDivElement | null) => void;
  handleScroll: (e: React.UIEvent<HTMLDivElement>) => void;
  handleWheel: (e: React.WheelEvent<HTMLDivElement>) => void;
  handlePointerDown: () => void;
  showScrollButton: boolean;
  scrollToBottom: (behavior?: ScrollBehavior) => void;
  scrollElementIntoView: (element: HTMLElement | null, options?: ScrollElementIntoViewOptions) => void;
  hideScrollButton: () => void;
}

const getBottomGap = (element: HTMLElement): number => {
  return element.scrollHeight - element.clientHeight - element.scrollTop;
};

export function useAutoScroll({ messages, itemCount }: UseAutoScrollOptions): UseAutoScrollReturn {
  const [scrollerEl, setScrollerEl] = useState<HTMLDivElement | null>(null);
  const [contentEl, setContentEl] = useState<HTMLDivElement | null>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  const userScrolledRef = useRef(false);
  const lastScrollTopRef = useRef(0);
  const previousListLengthRef = useRef(messages.length);
  const previousLastMessageRef = useRef<TMessage | undefined>(messages[messages.length - 1]);
  const lastProgrammaticScrollTimeRef = useRef(0);
  const initialScrollDoneRef = useRef(false);
  const pendingAutoFollowFrameRef = useRef<number | null>(null);
  const userInputActiveRef = useRef(false);
  // FIX-0025: where the first message sat in the list's viewport after the last change (layout
  // position, unaffected by the glide's transform).
  const anchorRef = useRef<{ el: HTMLElement; top: number } | null>(null);

  const markProgrammaticScroll = useCallback(() => {
    lastProgrammaticScrollTimeRef.current = Date.now();
  }, []);

  const updateBottomState = useCallback((element: HTMLDivElement) => {
    const bottomGap = getBottomGap(element);
    const withinButtonThreshold = bottomGap <= AT_BOTTOM_THRESHOLD_PX;
    const pinnedToBottom = bottomGap <= FOLLOW_BOTTOM_THRESHOLD_PX;
    setShowScrollButton(!withinButtonThreshold);

    if (pinnedToBottom) {
      userScrolledRef.current = false;
      userInputActiveRef.current = false;
      lastProgrammaticScrollTimeRef.current = Date.now() - (PROGRAMMATIC_SCROLL_GUARD_MS - 50);
    }

    return pinnedToBottom;
  }, []);

  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = 'smooth') => {
      if (itemCount <= 0 || !scrollerEl) return;

      markProgrammaticScroll();
      scrollerEl.scrollTo({
        top: scrollerEl.scrollHeight - scrollerEl.clientHeight,
        behavior,
      });
      userScrolledRef.current = false;
      setShowScrollButton(false);
    },
    [itemCount, markProgrammaticScroll, scrollerEl]
  );

  const measureAnchor = useCallback((): { el: HTMLElement; top: number } | null => {
    if (!scrollerEl || !contentEl) return null;
    const el = contentEl.querySelector<HTMLElement>(':scope > .message-item');
    if (!el) return null;
    // Both boxes carry the glide's transform, so their difference is the layout offset.
    return { el, top: el.getBoundingClientRect().top - contentEl.getBoundingClientRect().top - scrollerEl.scrollTop };
  }, [contentEl, scrollerEl]);

  /**
   * Keep the thread on its newest line and make every movement of it a glide (FIX-0025, D-78 §8.1).
   * Called from the ResizeObserver, which runs after layout and before paint, so a displaced frame is
   * never painted: when the thread follows the bottom — by scrolling, or, in a short chat, because the
   * list is bottom-aligned and grows upward — the old messages are shown where they were and spring to
   * their new place. The same holds when the Thinking row leaves and the list gets taller.
   */
  const followNow = useCallback(() => {
    if (!scrollerEl) return;
    const before = anchorRef.current;
    if (!userScrolledRef.current && getBottomGap(scrollerEl) > 2) scrollToBottom('auto');
    const now = measureAnchor();
    anchorRef.current = now;
    if (!before || !now || before.el !== now.el || userScrolledRef.current) return;
    const moved = now.top - before.top;
    // D-78: the list glides to its new place, never jumps (never on first paint).
    if (contentEl && initialScrollDoneRef.current && isArrivalTime()) glide(contentEl, -moved, { clip: contentEl.parentElement });
  }, [contentEl, measureAnchor, scrollToBottom, scrollerEl]);

  const scheduleAutoFollow = useCallback(() => {
    if (!scrollerEl || userScrolledRef.current) return;

    if (pendingAutoFollowFrameRef.current !== null) {
      cancelAnimationFrame(pendingAutoFollowFrameRef.current);
    }

    pendingAutoFollowFrameRef.current = requestAnimationFrame(() => {
      pendingAutoFollowFrameRef.current = null;
      if (!scrollerEl || userScrolledRef.current) return;
      followNow();
    });
  }, [followNow, scrollerEl]);

  const handleScrollerRef = useCallback((ref: HTMLDivElement | null) => {
    setScrollerEl(ref);
  }, []);

  const handleContentRef = useCallback((ref: HTMLDivElement | null) => {
    setContentEl(ref);
  }, []);

  const scrollElementIntoView = useCallback(
    (element: HTMLElement | null, options?: ScrollElementIntoViewOptions) => {
      if (!element) return;

      userScrolledRef.current = false;
      setShowScrollButton(false);
      markProgrammaticScroll();
      element.scrollIntoView({
        behavior: options?.behavior ?? 'smooth',
        block: options?.block ?? 'start',
        inline: 'nearest',
      });
    },
    [markProgrammaticScroll]
  );

  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const target = e.currentTarget;
      const currentScrollTop = target.scrollTop;
      const timeSinceGuard = Date.now() - lastProgrammaticScrollTimeRef.current;
      const delta = currentScrollTop - lastScrollTopRef.current;
      const bottomGap = getBottomGap(target);
      const pinnedToBottom = bottomGap <= FOLLOW_BOTTOM_THRESHOLD_PX;
      // A scroll that lands on the bottom with no input from Nick is the browser clamping after the
      // thread got shorter; the resize that caused it glides it (followNow), so keep the anchor.
      const byNick = userInputActiveRef.current || !pinnedToBottom;

      if (
        !pinnedToBottom &&
        Math.abs(delta) > 2 &&
        (userInputActiveRef.current || timeSinceGuard >= PROGRAMMATIC_SCROLL_GUARD_MS)
      ) {
        userScrolledRef.current = true;
      }

      if (pinnedToBottom) {
        userInputActiveRef.current = false;
      } else if (Math.abs(delta) > 2) {
        userInputActiveRef.current = false;
      }

      lastScrollTopRef.current = currentScrollTop;
      // Nick's own scrolling is never replayed as a glide.
      if (byNick) anchorRef.current = measureAnchor();
      updateBottomState(target);
    },
    [measureAnchor, updateBottomState]
  );

  const handleWheel = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    if (Math.abs(e.deltaY) > 0 || Math.abs(e.deltaX) > 0) {
      userInputActiveRef.current = true;
    }
  }, []);

  const handlePointerDown = useCallback(() => {
    userInputActiveRef.current = true;
  }, []);

  useEffect(() => {
    if (!scrollerEl || !contentEl) return;

    const observer = new ResizeObserver(() => {
      followNow();
      updateBottomState(scrollerEl);
    });

    observer.observe(scrollerEl);
    observer.observe(contentEl);

    return () => observer.disconnect();
  }, [contentEl, followNow, scrollerEl, updateBottomState]);

  useEffect(() => {
    if (!scrollerEl || initialScrollDoneRef.current || itemCount === 0) return;

    initialScrollDoneRef.current = true;
    requestAnimationFrame(() => {
      scrollToBottom('auto');
      lastScrollTopRef.current = scrollerEl.scrollTop;
    });
  }, [itemCount, scrollerEl, scrollToBottom]);

  useEffect(() => {
    const currentListLength = messages.length;
    const previousLength = previousListLengthRef.current;
    const lastMessage = messages[messages.length - 1];
    const previousLastMessage = previousLastMessageRef.current;
    const isNewMessage = currentListLength > previousLength;
    const isLastMessageUpdated = currentListLength > 0 && lastMessage !== previousLastMessage;

    previousListLengthRef.current = currentListLength;
    previousLastMessageRef.current = lastMessage;

    if (!isNewMessage) {
      if (isLastMessageUpdated) {
        scheduleAutoFollow();
      }
      return;
    }

    if (lastMessage?.position !== 'right') {
      // CH polish: a new reply is brought into view when it answers what the person just sent,
      // or when they are still reading near the bottom — a small scroll must not hide the
      // answer behind the "scroll to bottom" button. Reading far up the chat is left alone.
      const answersTheirMessage = previousLastMessage?.position === 'right';
      const nearBottom = scrollerEl ? getBottomGap(scrollerEl) <= AT_BOTTOM_THRESHOLD_PX * 3 : false;
      if (answersTheirMessage || nearBottom) userScrolledRef.current = false;
      scheduleAutoFollow();
      return;
    }

    userScrolledRef.current = false;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        // D-78 §10.1: earlier messages glide up as Nick's message lands.
        followNow();
      });
    });
  }, [messages, scheduleAutoFollow, followNow]);

  useEffect(() => {
    return () => {
      if (pendingAutoFollowFrameRef.current !== null) {
        cancelAnimationFrame(pendingAutoFollowFrameRef.current);
      }
    };
  }, []);

  const hideScrollButton = useCallback(() => {
    userScrolledRef.current = false;
    setShowScrollButton(false);
  }, []);

  return {
    handleScrollerRef,
    handleContentRef,
    handleScroll,
    handleWheel,
    handlePointerDown,
    showScrollButton,
    scrollToBottom,
    scrollElementIntoView,
    hideScrollButton,
  };
}
