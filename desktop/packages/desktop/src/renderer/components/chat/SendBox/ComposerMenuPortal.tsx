/**
 * Renders a composer menu (the slash command menu) in a body-level layer, pinned above the composer.
 *
 * The composer surfaces use `backdrop-filter`, which makes them a backdrop root: a glass menu nested
 * inside one only blurs the composer's own (transparent) layer, so the chat thread shows straight
 * through it and the menu text becomes unreadable (VS-3). Portalled to <body>, the menu's own blur
 * reaches the thread behind it again, matching the Figma glass surface.
 */
import React, { useLayoutEffect, useState } from 'react';
import { createPortal } from 'react-dom';

type Placement = { left: number; bottom: number; width: number; maxHeight: number };

type ComposerMenuPortalProps = {
  /** The composer surface the menu belongs to. */
  anchor: HTMLElement | null;
  /** Horizontal inset from the anchor's left edge (px). */
  inset?: number;
  /** Gap between the menu and the anchor's top edge (px). */
  gap?: number;
  /** Menu width; defaults to the anchor width minus both insets. */
  width?: number;
  className?: string;
  children: React.ReactNode;
};

const measure = (anchor: HTMLElement, inset: number, gap: number, width?: number): Placement => {
  const rect = anchor.getBoundingClientRect();
  const available = Math.max(0, rect.width - inset * 2);
  return {
    left: rect.left + inset,
    bottom: window.innerHeight - rect.top + gap,
    width: width ? Math.min(width, available || width) : available,
    maxHeight: Math.max(120, rect.top - gap - 16),
  };
};

const ComposerMenuPortal: React.FC<ComposerMenuPortalProps> = ({ anchor, inset = 12, gap = 8, width, className, children }) => {
  const [placement, setPlacement] = useState<Placement | null>(() =>
    anchor ? measure(anchor, inset, gap, width) : null
  );

  useLayoutEffect(() => {
    if (!anchor) return undefined;
    const update = () => setPlacement(measure(anchor, inset, gap, width));
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(update);
    observer?.observe(anchor);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
      observer?.disconnect();
    };
  }, [anchor, inset, gap, width]);

  if (typeof document === 'undefined') return null;
  const style: React.CSSProperties = placement
    ? {
        position: 'fixed',
        left: placement.left,
        bottom: placement.bottom,
        width: placement.width,
        maxHeight: placement.maxHeight,
        zIndex: 1000,
      }
    : { position: 'fixed', visibility: 'hidden', zIndex: 1000 };

  return createPortal(
    <div className={['kel-composer-menu-layer', className].filter(Boolean).join(' ')} style={style} data-testid='composer-menu-layer'>
      {children}
    </div>,
    document.body
  );
};

export default ComposerMenuPortal;
