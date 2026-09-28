/**
 * D-72 — the compact usage chips under one of Kel's replies: cost (or "Included in your plan"),
 * tokens, time and the model, in the composer footer's stat-chip style (Figma chat footer in
 * `185:4284`: 16px icon + 8px gap + muted text). Only what the engine measured is shown.
 */
import React from 'react';
import type { KelUsage } from '@/common/chat/kelMessageMeta';
import costIcon from '@renderer/assets/figma/chat-shell/cost.svg';
import tokensIcon from '@renderer/assets/figma/chat-shell/tokens.svg';
import { usageChips } from './usageWords';
import './KelUsageChips.css';

const ICONS: Record<string, string> = { cost: costIcon, tokens: tokensIcon };

export const KelUsageChips: React.FC<{ usage: KelUsage | null | undefined }> = ({ usage }) => {
  const chips = usageChips(usage);
  if (!chips.length) return null;
  return (
    <div className='kel-usage-chips' aria-label='What this reply used' data-testid='kel-usage-chips'>
      {chips.map((chip) => (
        <span key={chip.key} className='kel-usage-chip' title={chip.hint} data-chip={chip.key}>
          {ICONS[chip.key] ? <img src={ICONS[chip.key]} alt='' /> : null}
          {chip.text}
        </span>
      ))}
    </div>
  );
};

export default KelUsageChips;
