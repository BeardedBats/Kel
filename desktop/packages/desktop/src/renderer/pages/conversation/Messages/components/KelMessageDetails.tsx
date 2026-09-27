/**
 * CH-2/CP-14: the details behind one of Kel's messages — who answered, and for a checked result
 * what the checks found and who did and reviewed the work. Nothing shows until the person opens
 * "Details" (a Link-style disclosure); the message text itself carries no trust footer.
 */
import React from 'react';
import type { KelMessageMeta, KelWorkerLabel } from '@/common/chat/kelMessageMeta';
import './KelMessageDetails.css';

export type KelDetailRow = { label: string; lines: string[] };

const VERDICT_WORDS: Record<string, string> = {
  VERIFIED: 'Passed its checks',
  FAILED: "Didn't pass its checks",
  UNCERTAIN: 'Not fully checked',
};

/** Check kinds in plain words (the engine's kinds never reach the person). */
const CHECK_WORDS: Record<string, string> = {
  repository_evidence: 'Tests',
  citation_evidence: 'Sources',
  research_evidence: 'Sources',
  manual_review: 'Review',
  min_chars: 'Length',
  contains: 'Required content',
};

const names = (workers: Array<KelWorkerLabel | null | undefined> | undefined): string[] => {
  const out: string[] = [];
  for (const worker of workers ?? []) {
    const label = String(worker?.label || '').trim();
    if (label && !out.includes(label)) out.push(label);
  }
  return out;
};

/** One line per kind of check: "Tests: passed", "Review: 1 of 2 passed". */
const checkLines = (checks: KelMessageMeta['checks']): string[] => {
  const groups = new Map<string, string[]>();
  for (const check of checks ?? []) {
    const label = CHECK_WORDS[String(check?.kind ?? '')] ?? 'Other check';
    groups.set(label, [...(groups.get(label) ?? []), String(check?.verdict ?? '')]);
  }
  return [...groups].map(([label, verdicts]) => {
    const passed = verdicts.filter((verdict) => verdict === 'VERIFIED').length;
    if (passed === verdicts.length) return `${label}: passed`;
    if (verdicts.length === 1) return `${label}: ${verdicts[0] === 'FAILED' ? 'failed' : 'not confirmed'}`;
    return `${label}: ${passed} of ${verdicts.length} passed`;
  });
};

const LIMITATION = '• Limitation: ';

/** The labelled lines a Details disclosure shows for one message's metadata. */
export const kelDetailRows = (meta: KelMessageMeta | null | undefined): KelDetailRow[] => {
  if (!meta) return [];
  const rows: KelDetailRow[] = [];
  const add = (label: string, lines: string[]) => {
    const kept = lines.map((line) => line.trim()).filter(Boolean);
    if (kept.length) rows.push({ label, lines: kept });
  };
  if (meta.kind === 'result') {
    add('Result', [meta.verdict ? (VERDICT_WORDS[meta.verdict] ?? 'Not checked') : '']);
    add('Answered by', [names(meta.executed_by).join(', ')]);
    add('Checked by', [names(meta.reviewed_by).join(', ')]);
    add('Checks', checkLines(meta.checks));
    add(
      'Limits',
      (meta.summary ?? []).filter((line) => line.startsWith(LIMITATION)).map((line) => line.slice(LIMITATION.length))
    );
    return rows;
  }
  add('Answered by', [names([meta.answered_by]).join(', ')]);
  if (meta.fallback_from) {
    const chosen = names([meta.fallback_from])[0] ?? '';
    const note = String(meta.fallback_from.note || '').trim();
    add('You chose', [chosen ? (note ? `${chosen} (${note})` : chosen) : '']);
  }
  return rows;
};

export const KelMessageDetails: React.FC<{ meta: KelMessageMeta | null | undefined }> = ({ meta }) => {
  const rows = kelDetailRows(meta);
  if (!rows.length) return null;
  return (
    <details className='kel-message-details' data-testid='kel-message-details'>
      <summary>Details</summary>
      <dl>
        {rows.map((row) => (
          <div key={row.label} className='kel-message-details__row'>
            <dt>{row.label}</dt>
            <dd>
              {row.lines.map((line, index) => (
                <span key={index}>{line}</span>
              ))}
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
};

/** A note Kel posts about the conversation itself (a stopped reply, a restart): one quiet line. */
export const KelMessageNote: React.FC<{ text: string }> = ({ text }) => (
  <div className='kel-message-note' role='note' data-testid='kel-message-note'>
    {text}
  </div>
);

export default KelMessageDetails;
