/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * React side of the shared-element morph. `run` morphs A into B and renders the given React content
 * into the travelling surface — A's content leaving, B's content arriving — through portals, so the
 * surface carries real React output rather than a DOM clone. Render `portal` anywhere in the
 * component; it is empty while nothing is moving.
 *
 *   const shared = useSharedMorph();
 *   useEffect(() => { if (open) void shared.run({ source: cardEl, target: panelEl, enter: <PanelBody /> }); }, [open]);
 *   return <>{...}{shared.portal}</>;
 */

import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { createMorph, type MorphHandle, type MorphOptions } from './morph';

export type SharedMorphRun = MorphOptions & {
  /** A's content, leaving inside the surface. */
  exit?: React.ReactNode;
  /** B's content, arriving inside the surface. Its `[data-motion-block]`s (or children) stagger. */
  enter?: React.ReactNode;
};

type Flight = {
  handle: MorphHandle;
  exit: React.ReactNode;
  enter: React.ReactNode;
  resolve: () => void;
};

export function useSharedMorph(): {
  run: (options: SharedMorphRun) => Promise<void>;
  portal: React.ReactNode;
  morphing: boolean;
} {
  const [flight, setFlight] = useState<Flight | null>(null);
  const current = useRef<Flight | null>(null);

  const run = useCallback((options: SharedMorphRun): Promise<void> => {
    current.current?.handle.cancel();
    const { exit, enter, ...morphOptions } = options;
    const handle = createMorph(morphOptions);
    return new Promise<void>((resolve) => {
      const next: Flight = { handle, exit: exit ?? null, enter: enter ?? null, resolve };
      current.current = next;
      setFlight(next);
    });
  }, []);

  // Start once the portals have committed, so the content is in the surface before it moves.
  useLayoutEffect(() => {
    if (!flight) return;
    let live = true;
    void flight.handle.start().then(() => {
      flight.resolve();
      if (live && current.current === flight) {
        current.current = null;
        setFlight(null);
      }
    });
    return () => {
      live = false;
    };
  }, [flight]);

  useEffect(
    () => () => {
      current.current?.handle.cancel();
    },
    []
  );

  const portal = flight ? (
    <>
      {flight.exit ? createPortal(flight.exit, flight.handle.exitHost) : null}
      {flight.enter ? createPortal(flight.enter, flight.handle.enterHost) : null}
    </>
  ) : null;

  return { run, portal, morphing: flight !== null };
}
