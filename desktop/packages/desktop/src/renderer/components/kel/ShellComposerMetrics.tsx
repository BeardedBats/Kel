import React from 'react';
import type { TokenUsageData } from '@/common/config/storage';
import costIcon from '@renderer/assets/figma/chat-shell/cost.svg';
import tokensIcon from '@renderer/assets/figma/chat-shell/tokens.svg';
import cacheIcon from '@renderer/assets/figma/chat-shell/cache.svg';
import contextIcon from '@renderer/assets/figma/chat-shell/context.svg';

/** Missing measurements stay unknown; screenshot values never enter live state.
 *  Nothing is shown until the conversation has reported usage (FIX-0010): an empty row of dashes on
 *  Home or before the first reply is noise, not information. */
export default function ShellComposerMetrics({ usage = null, contextLimit = 0 }: { usage?: TokenUsageData | null; contextLimit?: number }) {
  if (!usage) return null;
  const input = usage?.breakdown?.input_tokens;
  const cached = usage?.breakdown?.cached_read_tokens;
  const cache = input && cached !== undefined ? `${Math.round(cached / input * 100)}%` : '—';
  const remaining = usage && contextLimit > 0 ? Math.max(0, Math.min(100, 100 - usage.total_tokens / contextLimit * 100)) : null;
  const cost = usage?.cost ? new Intl.NumberFormat('en-US', { style: 'currency', currency: usage.cost.currency }).format(usage.cost.amount) : '—';
  return <div className='kel-shell-composer-metrics' aria-label='Conversation usage'>
    <span title='Reported session cost'><img src={costIcon} alt='' />{cost}</span>
    <span title='Reported tokens'><img src={tokensIcon} alt='' />{usage ? new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(usage.total_tokens) : '—'} tokens</span>
    <span title='Reported cached input share'><img src={cacheIcon} alt='' />{cache} cache</span>
    <span title='Reported context remaining'><img src={contextIcon} alt='' /><span className='kel-shell-context-track'><span style={{ width: `${remaining ?? 0}%` }} /></span>{remaining === null ? '—' : `${Math.round(remaining)}%`} remaining</span>
  </div>;
}
