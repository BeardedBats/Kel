/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

import kelMark from '@renderer/assets/figma/kel-mark.png';
import classNames from 'classnames';
import React, { useLayoutEffect, useRef } from 'react';
import { exitGhostAt, snapshotGhost, useArrival, useEntrance } from '@renderer/motion';

type KelThinkingIndicatorProps = {
  /** Main label, e.g. "Thinking…" or a runtime status such as "Starting agent…". */
  label: React.ReactNode;
  /** Optional muted suffix, e.g. elapsed time. */
  meta?: React.ReactNode;
  /** Animate the mark and shimmer the label. */
  active?: boolean;
  className?: string;
  title?: string;
  children?: React.ReactNode;
};

/** Claude-style working indicator: pulsing Kel mark beside shimmering text, no card or spinner. */
const KelThinkingIndicator: React.FC<KelThinkingIndicatorProps> = ({
  label,
  meta,
  active = true,
  className,
  title,
  children,
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const arrived = useArrival();
  // D-78 §10.1: Thinking arrives as an in-flow insert, mark, words and seconds 40 ms apart.
  useEntrance(ref, arrived, { parts: ['.kel-thinking__mark', '.kel-thinking__label', '.kel-thinking__meta'], stagger: 40 });
  // When it goes (the reply is here), the whole row fades out where it was — nothing flies or jumps
  // (FIX-0025); the reply's own mark fades in at the reply.
  useLayoutEffect(() => {
    const row = ref.current;
    const route = typeof window !== 'undefined' ? window.location.hash : '';
    return () => {
      if (!row || !row.isConnected || (typeof window !== 'undefined' && window.location.hash !== route)) return;
      void exitGhostAt(snapshotGhost(row), { ms: 140, scale: 1, blur: 3, y: 0 });
    };
  }, []);
  return (
    <div
      ref={ref}
      className={classNames('kel-thinking', { 'kel-thinking--active': active }, className)}
      role='status'
      aria-live='polite'
      title={title}
    >
      <span className='kel-thinking__mark' aria-hidden='true'>
        <img src={kelMark} alt='' width={18} height={18} />
      </span>
      <span className='kel-thinking__label'>{label}</span>
      {meta && <span className='kel-thinking__meta'>{meta}</span>}
      {children}
    </div>
  );
};

export default KelThinkingIndicator;
