/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

import kelMark from '@renderer/assets/figma/kel-mark.png';
import classNames from 'classnames';
import React from 'react';

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
}) => (
  <div
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

export default KelThinkingIndicator;
