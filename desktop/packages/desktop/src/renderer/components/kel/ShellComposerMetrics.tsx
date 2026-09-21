import React from 'react';
import type { TokenUsageData } from '@/common/config/storage';

/** Missing measurements stay unknown; screenshot values never enter live state. */
export default function ShellComposerMetrics({ usage = null, contextLimit = 0 }: { usage?: TokenUsageData | null; contextLimit?: number }) {
  const input = usage?.breakdown?.input_tokens;
  const cached = usage?.breakdown?.cached_read_tokens;
  const cache = input && cached !== undefined ? `${Math.round(cached / input * 100)}%` : '—';
  const remaining = usage && contextLimit > 0 ? Math.max(0, Math.min(100, 100 - usage.total_tokens / contextLimit * 100)) : null;
  const cost = usage?.cost ? new Intl.NumberFormat('en-US', { style: 'currency', currency: usage.cost.currency }).format(usage.cost.amount) : '—';
  const icon = (path: string) => <svg aria-hidden='true' width='14' height='14' viewBox='0 0 16 16' fill='none' stroke='currentColor' strokeWidth='1.2'><path d={path} /></svg>;
  return <div className='kel-shell-composer-metrics' aria-label='Conversation usage'>
    <span title='Reported session cost'>{icon('M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1ZM10 5H7a1.5 1.5 0 0 0 0 3h2a1.5 1.5 0 0 1 0 3H6M8 3v10')}{cost}</span>
    <span title='Reported tokens'>{icon('M4 1h5l3 3v11H4ZM9 1v4h3M6 8h4M6 11h4')}{usage ? new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(usage.total_tokens) : '—'} tokens</span>
    <span title='Reported cached input share'>{icon('M3 4c0-3 10-3 10 0s-10 3-10 0ZM3 4v8c0 3 10 3 10 0V4M3 8c0 3 10 3 10 0')}{cache} cache</span>
    <span title='Reported context remaining'>{icon('M3 13V8M7 13V5M11 13V2')}<span className='kel-shell-context-track'><span style={{ width: `${remaining ?? 0}%` }} /></span>{remaining === null ? '—' : `${Math.round(remaining)}%`} remaining</span>
  </div>;
}
