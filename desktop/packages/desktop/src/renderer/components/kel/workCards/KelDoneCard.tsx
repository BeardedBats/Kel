/**
 * D-70 item 2 — the compact done card on Kel's result message (Figma 5d). Title, the verified
 * state ("Done and checked" only for work whose checks passed, D-53), "N of N checks passed", one
 * sentence of the result, where a coding change was applied (D-65 truth from changeApplication.ts)
 * with Undo and Open folder, and Details, which opens the work's top card. Failed, stopped and
 * needs-you results use the same card with their own words. Work without a top card (from before
 * the cards) renders `fallback` instead — today's message details.
 */
import { ipcBridge } from '@/common';
import type { KelMessageMeta } from '@/common/chat/kelMessageMeta';
import React, { useCallback, useEffect, useState } from 'react';
import { applicationLine, isApplied } from '../changeApplication';
import { kelUndoChange, type KelChangeApplication } from '../kelApi';
import { officeItem, type OfficeItemDetail } from './officeApi';
import { openWorkCard, refreshWorkCards } from './workCardEvents';
import { StateIcon, iconFolder, iconFolder13, iconUndo } from './workCardIcons';
import { clockTime, detailStateLabel } from './workCardModel';
import './KelWorkCardsRow5.css';

const PASS = new Set(['passed', 'pass', 'verified', 'ok', 'success', 'accepted']);

/** "4 of 4 checks passed" from the checks the engine recorded with the result (never invented). */
export const checksLine = (meta: Pick<KelMessageMeta, 'checks'> | null | undefined): string | null => {
  const checks = meta?.checks ?? [];
  if (!checks.length) return null;
  const passedCount = checks.filter((check) => PASS.has(String(check?.verdict ?? '').toLowerCase())).length;
  return `${passedCount} of ${checks.length} check${checks.length === 1 ? '' : 's'} passed`;
};

/**
 * One sentence of the result: the published text without Kel's lead-in ("Here's … — it passed its
 * checks."), first sentence only. Null when there is nothing beyond the lead-in.
 */
export const resultSentence = (text: string | null | undefined): string | null => {
  let body = String(text ?? '').trim();
  if (!body) return null;
  body = body.replace(/^Here[’']s[^\n]*?—\s*it passed its checks\.\s*/i, '').trim();
  const first = body.split(/\n\s*\n/)[0]?.replace(/\s+/g, ' ').trim() ?? '';
  if (!first) return null;
  const sentence = first.match(/^.+?[.!?](?=\s|$)/)?.[0] ?? first;
  return sentence.length > 220 ? `${sentence.slice(0, 219).trimEnd()}…` : sentence;
};

/** "Applied to <folder> at 10:31 AM · you can undo it", or the D-65 words for other states. */
export const appliedWords = (application: KelChangeApplication | null | undefined, at: number | null | undefined): string | null => {
  if (!application) return null;
  if (isApplied(application) && application.state === 'APPLIED') {
    const when = clockTime(at);
    return `Applied to ${application.root ?? 'your project'}${when ? ` at ${when}` : ''} · you can undo it`;
  }
  return applicationLine(application);
};

const defaultOpenFolder = async (path: string) => {
  try {
    await ipcBridge.shell.openFile.invoke(path);
  } catch {
    await ipcBridge.shell.showItemInFolder.invoke(path);
  }
};

type Props = {
  job: string;
  meta?: KelMessageMeta | null;
  /** Shown instead when this work has no top card (older work). */
  fallback?: React.ReactNode;
  openFolder?: (path: string) => Promise<unknown>;
};

export const KelDoneCard: React.FC<Props> = ({ job, meta, fallback = null, openFolder = defaultOpenFolder }) => {
  const [detail, setDetail] = useState<OfficeItemDetail | null>(null);
  const [noCard, setNoCard] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const read = useCallback(async () => {
    try {
      const next = await officeItem(job);
      setDetail(next);
      setNoCard(false);
    } catch {
      setNoCard(true);
    }
  }, [job]);

  useEffect(() => {
    void read();
  }, [read]);

  if (noCard) return <>{fallback}</>;
  if (!detail) return null;

  const application = detail.application ?? null;
  const applied = (detail.kind ?? '') === 'code' && isApplied(application);
  const folder = application?.root ?? null;
  const state = detail.state;
  const label = state === 'failed' ? 'Didn’t pass its checks' : detailStateLabel(detail);
  const sentence = resultSentence(detail.result) ?? (detail.status_line?.trim() || null);
  const applyWords = (detail.kind ?? '') === 'code' ? appliedWords(application, detail.finished_at) : null;
  const checks = checksLine(meta);

  const guarded = async (action: () => Promise<unknown>) => {
    if (busy) return;
    setBusy(true);
    setNotice('');
    try {
      await action();
    } catch (error) {
      setNotice(String((error as Error)?.message || '').trim() || 'Kel could not reach its engine just now.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className={`kel-dc kel-dc--${state}`}
      aria-label={`${detail.title}: ${label}`}
      data-testid='kel-done-card'
      data-done-card={job}
      data-state={state}
    >
      <div className='kel-dc__head'>
        <span className='kel-dc__lead'>
          <StateIcon state={state} size='detail' />
        </span>
        <span className='kel-dc__title'>{detail.title}</span>
        <span className='kel-dc__state' data-testid='kel-done-card-state'>
          {label}
        </span>
        <span className='kel-wc-push' />
        {checks ? <span className='kel-dc__checks'>{checks}</span> : null}
      </div>
      {sentence ? <p className='kel-dc__result'>{sentence}</p> : null}
      {applyWords ? (
        <div className='kel-dc__applied' data-testid='kel-done-card-applied'>
          <img src={iconFolder13} alt='' />
          <span>{applyWords}</span>
        </div>
      ) : null}
      <div className='kel-dc__actions'>
        {applied ? (
          <button
            type='button'
            className='kel-wd-button'
            disabled={busy}
            onClick={() =>
              void guarded(async () => {
                await kelUndoChange(job);
                refreshWorkCards();
                await read();
              })
            }
            data-testid='kel-done-card-undo'
          >
            <img src={iconUndo} alt='' />
            Undo
          </button>
        ) : null}
        {applied && folder ? (
          <button
            type='button'
            className='kel-wd-button'
            disabled={busy}
            onClick={() => void guarded(async () => openFolder(folder))}
            data-testid='kel-done-card-folder'
          >
            <img src={iconFolder} alt='' />
            Open folder
          </button>
        ) : null}
        <span className='kel-wc-push' />
        <button type='button' className='kel-wd-button' onClick={() => openWorkCard(job)} data-testid='kel-done-card-details'>
          Details
        </button>
      </div>
      {notice ? (
        <p className='kel-dc__notice' role='alert'>
          {notice}
        </p>
      ) : null}
    </section>
  );
};

export default KelDoneCard;
