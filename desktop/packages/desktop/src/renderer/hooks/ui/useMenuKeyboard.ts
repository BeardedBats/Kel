/**
 * VIS-10 / JR-26: one keyboard behaviour for Kel's small pop-up menus (the chat row menu, the
 * composer's model picker, the attach menu, the reply ⋯ menu), following the project chip.
 *
 * While the menu is open:
 *  - focus moves to its first item as soon as it appears;
 *  - ArrowDown / ArrowUp (and Tab / Shift+Tab) move between items, Home / End jump to the ends;
 *  - Escape closes it and puts focus back on the button that opened it;
 *  - moving to another page closes it, so a menu never lingers over a different screen.
 * Enter and Space are left to the item itself (buttons and Arco menu items already handle them).
 */
import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';
import { useLocation } from 'react-router-dom';

const ITEM_SELECTOR = [
  '[role="menuitem"]',
  '[role="menuitemradio"]',
  '[role="menuitemcheckbox"]',
  '[role="tab"]',
  'button',
  'a[href]',
].join(',');

/** The items a person can move to, in document order (disabled and hidden ones are skipped). */
export const menuItems = (menu: HTMLElement | null): HTMLElement[] => {
  if (!menu) return [];
  const seen = new Set<HTMLElement>();
  return Array.from(menu.querySelectorAll<HTMLElement>(ITEM_SELECTOR)).filter((item) => {
    if (seen.has(item)) return false;
    // A button inside a menu item is part of that item, not a separate stop.
    const owner = item.parentElement?.closest<HTMLElement>('[role="menuitem"]');
    if (owner && owner !== item && menu.contains(owner)) return false;
    seen.add(item);
    if (item.hasAttribute('disabled') || item.getAttribute('aria-disabled') === 'true') return false;
    if (item.closest('[hidden], [aria-hidden="true"]')) return false;
    return true;
  });
};

/** The element carrying `attribute="value"` (ids from React.useId need no escaping this way). */
export const findByAttribute = (attribute: string, value: string): HTMLElement | null =>
  Array.from(document.querySelectorAll<HTMLElement>(`[${attribute}]`)).find((el) => el.getAttribute(attribute) === value) ??
  null;

export type MenuKeyboardOptions = {
  open: boolean;
  onClose: () => void;
  /** The open menu's element (it may be portalled, so it is looked up rather than passed as a ref). */
  getMenu: () => HTMLElement | null;
  /** The button that opened the menu; focus returns here on Escape. */
  triggerRef?: RefObject<HTMLElement | null>;
};

export function useMenuKeyboard({ open, onClose, getMenu, triggerRef }: MenuKeyboardOptions): void {
  const latest = useRef({ onClose, getMenu, triggerRef });
  latest.current = { onClose, getMenu, triggerRef };

  // Focus the first item once the menu is in the document (pop-ups mount a frame or two late).
  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    let attempts = 0;
    const tryFocus = () => {
      if (cancelled) return;
      const menu = latest.current.getMenu();
      const items = menuItems(menu);
      if (items.length > 0) {
        if (!menu?.contains(document.activeElement)) items[0].focus();
        return;
      }
      if (attempts++ < 20) window.setTimeout(tryFocus, 16);
    };
    window.setTimeout(tryFocus, 0);
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      const { getMenu: menuOf, onClose: close, triggerRef: trigger } = latest.current;
      const menu = menuOf();
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        close();
        trigger?.current?.focus();
        return;
      }
      const items = menuItems(menu);
      if (items.length === 0) return;
      const inside = Boolean(menu?.contains(document.activeElement));
      const onTrigger = Boolean(trigger?.current && trigger.current.contains(document.activeElement));
      if (!inside && !onTrigger) return;
      const index = inside ? items.indexOf(document.activeElement as HTMLElement) : -1;
      let next: number | null = null;
      if (event.key === 'ArrowDown' || (event.key === 'Tab' && !event.shiftKey)) next = index < 0 ? 0 : (index + 1) % items.length;
      else if (event.key === 'ArrowUp' || (event.key === 'Tab' && event.shiftKey))
        next = index < 0 ? items.length - 1 : (index - 1 + items.length) % items.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = items.length - 1;
      if (next === null) return;
      event.preventDefault();
      event.stopPropagation();
      items[next].focus();
    };
    document.addEventListener('keydown', onKeyDown, true);
    return () => document.removeEventListener('keydown', onKeyDown, true);
  }, [open]);

  // A menu belongs to the page it was opened on.
  const location = useLocation();
  const route = `${location.pathname}${location.search}`;
  const lastRoute = useRef(route);
  useEffect(() => {
    if (lastRoute.current === route) return;
    lastRoute.current = route;
    if (open) latest.current.onClose();
  }, [route, open]);
}
