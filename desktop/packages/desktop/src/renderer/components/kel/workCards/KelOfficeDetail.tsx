/**
 * D-66 / D-68 — the detail that drops down from under the work-card row (Figma 4b running, 4d
 * finished). Three columns: the team (role · model · version · reasoning, and what each is doing),
 * steps and files changed, then review, the Oracle and verification. Read-only apart from "Talk to
 * Kel about this", Stop while the work runs (the same confirmed cancel as the in-chat work card),
 * and, once finished, Remove plus the D-65 Undo / Open folder when an applied change allows it.
 */
import kelMark from '@renderer/assets/figma/kel-mark.png';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { kelControl, kelHandoff, kelUndoChange, type KelChangeApplication } from '../kelApi';
import { applicationLine, isApplied } from '../changeApplication';
import type { OfficeFinding, OfficeItem, OfficeItemDetail, OfficeStaff, OfficeStep } from './officeApi';
import { officeItem } from './officeApi';
import {
  StateIcon,
  StatusDot,
  iconCheck14,
  iconFile,
  iconFolder,
  iconLoader,
  iconRemove,
  iconStop,
  iconUndo,
  iconWarning,
  stepPending,
} from './workCardIcons';
import {
  clockTime,
  detailStateLabel,
  duration,
  failedChecks,
  isCommander,
  isFinished,
  modelLine,
  oracleLine,
  passed,
  progressFraction,
  reasoningLabel,
  ringTone,
  roleName,
  initials,
} from './workCardModel';

type Props = {
  item: OfficeItem;
  projectName?: string | null;
  pollMs: number;
  onClose: () => void;
  onRemove: (item: OfficeItem) => void;
  onTalk: (item: OfficeItem) => void;
  /** Called after Stop or Undo so the row reads the new state at once. */
  onChanged: () => void;
  /** Open a folder on this computer (injected so tests and the remote surface can decide). */
  openFolder?: (path: string) => Promise<unknown>;
};

const FOCUSABLE = 'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

const STEP_DONE = new Set(['done', 'accepted', 'verified', 'passed', 'complete', 'completed']);
const STEP_NOW = new Set(['running', 'working', 'in_progress', 'active', 'claimed', 'review', 'in_review']);
const STEP_FAILED = new Set(['failed', 'blocked', 'stopped']);

type StepPhase = 'done' | 'now' | 'failed' | 'pending';
const stepPhase = (step: OfficeStep): StepPhase => {
  const state = (step.state ?? '').toLowerCase();
  if (STEP_DONE.has(state)) return 'done';
  if (STEP_NOW.has(state)) return 'now';
  if (STEP_FAILED.has(state)) return 'failed';
  return 'pending';
};

const openFindings = (findings: OfficeFinding[] | null | undefined) =>
  (findings ?? []).filter((finding) => finding.status !== 'resolved' && finding.severity !== 'note');

const SectionHead: React.FC<{ title: string; meta?: string | null; id?: string }> = ({ title, meta, id }) => (
  <div className='kel-wd-section-head'>
    <h3 id={id}>{title}</h3>
    <span className='kel-wc-push' />
    {meta ? <span className='kel-wd-meta'>{meta}</span> : null}
  </div>
);

const Member: React.FC<{ member: OfficeStaff; itemState: string }> = ({ member, itemState }) => {
  const commander = isCommander(member);
  const tone = commander && !member.state ? 'working' : ringTone(member, itemState);
  return (
    <li className='kel-wd-member' data-testid='kel-office-member'>
      <span className={`kel-wd-avatar kel-wc-avatar--${tone}`} aria-hidden='true'>
        {commander ? <img src={kelMark} alt='' /> : initials(member)}
      </span>
      <span className='kel-wd-member__text'>
        <span className='kel-wd-member__line'>
          <strong>{roleName(member)}</strong>
          {commander ? <span className='kel-wc-sr'>, Commander</span> : null}
          <span className='kel-wd-model' data-testid='kel-office-model'>
            {modelLine(member)}
          </span>
        </span>
        {member.doing ? <span className='kel-wd-doing'>{member.doing}</span> : null}
        {member.note ? <span className='kel-wd-note-line'>{member.note}</span> : null}
      </span>
    </li>
  );
};

export const KelOfficeDetail: React.FC<Props> = ({ item, projectName, pollMs, onClose, onRemove, onTalk, onChanged, openFolder }) => {
  const [detail, setDetail] = useState<OfficeItemDetail | null>(null);
  const [unreadable, setUnreadable] = useState(false);
  const [handoffApplication, setHandoffApplication] = useState<KelChangeApplication | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const dialogRef = useRef<HTMLDivElement>(null);
  const job = item.job_id;

  const read = useCallback(async () => {
    try {
      const next = await officeItem(job);
      if (next && typeof next === 'object') {
        setDetail(next);
        setUnreadable(false);
      }
    } catch {
      // Quiet: keep what was last read.
      setUnreadable(true);
    }
  }, [job]);

  useEffect(() => {
    setDetail(null);
    setConfirming(false);
    setNotice('');
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      if (typeof document === 'undefined' || document.visibilityState !== 'hidden') await read();
      if (!stopped) timer = setTimeout(() => void tick(), pollMs);
    };
    void tick();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [read, pollMs]);

  const view: OfficeItemDetail = { ...item, ...detail } as OfficeItemDetail;
  const finished = isFinished(view.state);
  const running = !finished;
  const coding = (view.kind ?? item.kind) === 'code';

  // D-65: the engine's hand-off view knows whether a checked change was applied and can be undone.
  const submission = view.links?.submission_id ?? view.submission_id;
  const conversation = view.links?.conversation_id ?? view.conversation_id;
  useEffect(() => {
    if (!finished || !coding || view.application !== undefined || !submission || !conversation) return;
    let alive = true;
    kelHandoff(conversation, submission)
      .then((handoff) => {
        if (alive) setHandoffApplication(handoff.application ?? null);
      })
      .catch((): void => undefined);
    return () => {
      alive = false;
    };
  }, [finished, coding, view.application, submission, conversation]);
  const application = view.application !== undefined ? view.application : handoffApplication;
  const applied = coding && isApplied(application);

  // Focus moves into the dialog (its heading is announced) and stays there — Tab wraps — until it
  // closes. The dialog itself takes focus so no action looks pre-selected.
  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== 'Tab') return;
    const nodes = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
    if (!nodes.length) {
      event.preventDefault();
      return;
    }
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialogRef.current)) {
      event.preventDefault();
      first.focus();
    }
  };

  const guarded = async (action: () => Promise<unknown>) => {
    if (busy) return;
    setBusy(true);
    setNotice('');
    try {
      await action();
    } catch (error) {
      const detailText = String((error as Error)?.message || '').trim();
      setNotice(detailText || 'Kel could not reach its engine just now. Try again in a moment.');
    } finally {
      setBusy(false);
    }
  };

  const stop = () =>
    guarded(async () => {
      await kelControl(job, 'cancel');
      setConfirming(false);
      onChanged();
      await read();
    });

  const undo = () =>
    guarded(async () => {
      await kelUndoChange(job);
      setHandoffApplication((current) => (current ? { ...current, state: 'UNDONE' } : current));
      onChanged();
      await read();
    });

  const folder = application?.root ?? null;
  const showFolder = () =>
    guarded(async () => {
      if (folder && openFolder) await openFolder(folder);
    });

  const staff = view.staff ?? [];
  const helpers = staff.filter((member) => !isCommander(member));
  const hasKel = staff.some(isCommander);
  const allDone = staff.length > 0 && staff.every((member) => member.state === 'done');
  const teamMeta = staff.length
    ? `${hasKel ? `Kel + ${helpers.length}` : `${helpers.length}`}${finished ? (allDone ? ', all done' : '') : ' on it'}`
    : null;

  const steps = view.steps ?? [];
  const firstPending = steps.findIndex((step) => stepPhase(step) === 'pending');
  const stepMeta =
    view.progress && view.progress.total > 0 ? `${Math.min(view.progress.done, view.progress.total)} of ${view.progress.total}` : null;

  const files = view.files_changed;
  const review = view.review ?? null;
  const findings = openFindings(review?.findings);
  const reviewPassed = passed(view);
  const reviewFailed = failedChecks(view);
  const verifier = staff.find((member) => (member.role ?? '').toLowerCase() === 'verifier');
  const oracleStaff = staff.find((member) => (member.role ?? '').toLowerCase() === 'oracle');
  const oracleModel =
    view.oracle?.model_label
      ? [view.oracle.model_label, reasoningLabel(view.oracle.reasoning)].filter(Boolean).join(' · ')
      : oracleStaff
        ? modelLine(oracleStaff)
        : null;
  const reviewTone = findings.length ? 'review' : reviewPassed ? 'done' : reviewFailed ? 'failed' : 'review';
  const reviewWord = findings.length
    ? `${findings.length} to fix`
    : reviewPassed
      ? 'Passed'
      : reviewFailed
        ? 'Didn’t pass'
        : review?.verdict
          ? 'Reviewing'
          : 'Not yet';
  const reviewText = findings.length
    ? findings.map((finding) => finding.summary).filter(Boolean).join(' ')
    : review?.checked_by
      ? `Checked by ${review.checked_by}.`
      : null;

  const verification = view.verification ?? null;
  const verificationTone = reviewPassed ? 'done' : reviewFailed ? 'failed' : 'review';
  const verificationWord = verification?.result
    ? reviewPassed
      ? 'Passed'
      : reviewFailed
        ? 'Didn’t pass'
        : verification.result.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
    : running
      ? 'In progress'
      : 'Not reported';
  const verificationText = [verificationWord, ...(verification?.summary ?? [])].filter(Boolean).join(' · ');

  const started = clockTime(view.started_at);
  const ended = clockTime(view.finished_at ?? view.updated_at);
  const took = finished ? duration(view.started_at, view.finished_at ?? view.updated_at) : null;
  const total = view.progress?.total ?? 0;
  const stepNow = total > 0 ? Math.min((view.progress?.done ?? 0) + 1, total) : 0;
  const subtitle = [
    running ? (total > 0 ? `Step ${stepNow} of ${total}` : null) : ended ? `Finished ${ended}` : null,
    running ? (started ? `Started ${started}` : null) : took ? `Took ${took}` : null,
    projectName || null,
  ].filter(Boolean);

  const resultText = (view.result ?? '').trim() || (view.status_line ?? '').trim();
  const attention = view.state === 'needs_you' || view.state === 'failed' || view.state === 'stopped';
  const attentionText = [view.why, view.next].filter((part) => part && part.trim()).join(' ');
  const appliedLine = coding ? applicationLine(application) : null;
  const titleId = `kel-office-detail-title-${job}`;

  return (
    <div
      ref={dialogRef}
      className={`kel-wd kel-wd--${view.state}`}
      role='dialog'
      aria-modal='true'
      aria-labelledby={titleId}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      data-testid='kel-office-detail'
    >
      <div className='kel-wd-head'>
        <div className='kel-wd-title'>
          <h2 id={titleId}>{view.title}</h2>
          <div className='kel-wd-state' role='status' aria-live='polite'>
            <StateIcon state={view.state} size='detail' />
            <span className='kel-wd-state__label' data-testid='kel-office-detail-state'>
              {detailStateLabel(view)}
            </span>
            {subtitle.length ? <span className='kel-wd-state__meta'>{`·  ${subtitle.join('  ·  ')}`}</span> : null}
          </div>
        </div>
        <span className='kel-wc-push' />
        {confirming ? (
          <div className='kel-wd-confirm' data-testid='kel-office-stop-confirm'>
            <span>Stop this work? Anything already checked is kept.</span>
            <button type='button' className='kel-wd-button' disabled={busy} onClick={() => setConfirming(false)}>
              Keep going
            </button>
            <button type='button' className='kel-wd-button kel-wd-button--danger' disabled={busy} onClick={() => void stop()} data-testid='kel-office-stop-yes'>
              Stop it
            </button>
          </div>
        ) : (
          <div className='kel-wd-actions'>
            {running ? (
              <button type='button' className='kel-wd-button' disabled={busy} onClick={() => setConfirming(true)} data-testid='kel-office-stop'>
                <img src={iconStop} alt='' />
                Stop
              </button>
            ) : (
              <>
                <button type='button' className='kel-wd-button' disabled={busy} onClick={() => onRemove(item)} data-testid='kel-office-remove'>
                  <img src={iconRemove} alt='' />
                  Remove
                </button>
                {applied ? (
                  <button type='button' className='kel-wd-button' disabled={busy} onClick={() => void undo()} data-testid='kel-office-undo'>
                    <img src={iconUndo} alt='' />
                    Undo
                  </button>
                ) : null}
                {applied && folder && openFolder ? (
                  <button type='button' className='kel-wd-button' disabled={busy} onClick={() => void showFolder()} data-testid='kel-office-open-folder'>
                    <img src={iconFolder} alt='' />
                    Open folder
                  </button>
                ) : null}
              </>
            )}
            <button type='button' className='kel-wd-button kel-wd-button--primary' onClick={() => onTalk(item)} data-testid='kel-office-talk'>
              Talk to Kel about this
            </button>
          </div>
        )}
      </div>
      {notice ? (
        <p className='kel-wd-notice' role='alert'>
          {notice}
        </p>
      ) : null}
      <div className='kel-wc-progress kel-wd-progress' aria-hidden='true'>
        <span className='kel-wc-progress__fill' style={{ width: `${(progressFraction(view) * 100).toFixed(2)}%` }} />
      </div>
      {finished && (resultText || appliedLine) ? (
        <section className='kel-wd-result' aria-label='Result' data-testid='kel-office-result'>
          <div className='kel-wd-result__head'>
            <StateIcon state={view.state} size='detail' />
            <strong>Result</strong>
            {appliedLine ? <span className='kel-wd-meta'>{appliedLine}</span> : null}
          </div>
          {resultText ? <p>{resultText}</p> : null}
          {attention && attentionText ? <p className='kel-wd-result__why'>{attentionText}</p> : null}
        </section>
      ) : null}
      {!finished && view.state === 'needs_you' && attentionText ? (
        <section className='kel-wd-result kel-wd-result--needs' aria-label='What Kel needs' data-testid='kel-office-needs'>
          <div className='kel-wd-result__head'>
            <StatusDot tone='needs' />
            <strong>Needs you</strong>
          </div>
          <p>{attentionText}</p>
        </section>
      ) : null}
      {detail === null && unreadable ? <p className='kel-wd-loading'>Kel couldn’t read the details just now. It will try again.</p> : null}
      {detail === null && !unreadable ? <p className='kel-wd-loading'>Reading the details…</p> : null}
      {detail ? (
        <div className='kel-wd-columns'>
          <section className='kel-wd-col kel-wd-col--team' aria-labelledby={`${titleId}-team`}>
            <SectionHead id={`${titleId}-team`} title='Team' meta={teamMeta} />
            {staff.length ? (
              <ul className='kel-wd-list'>
                {staff.map((member) => (
                  <Member key={member.id} member={member} itemState={view.state} />
                ))}
              </ul>
            ) : (
              <p className='kel-wd-empty'>Kel is handling this alone.</p>
            )}
          </section>
          <div className='kel-wd-col kel-wd-col--steps'>
            <section aria-labelledby={`${titleId}-steps`}>
              <SectionHead id={`${titleId}-steps`} title='Steps' meta={stepMeta} />
              {steps.length ? (
                <ol className='kel-wd-list kel-wd-steps'>
                  {steps.map((step, index) => {
                    const phase = stepPhase(step);
                    const at = phase === 'done' || phase === 'failed' ? clockTime(step.at) : null;
                    return (
                      <li key={step.id} className={`kel-wd-step kel-wd-step--${phase}`} data-testid='kel-office-step'>
                        <span className='kel-wd-step__lead' aria-hidden='true'>
                          <img
                            src={phase === 'done' ? iconCheck14 : phase === 'now' ? iconLoader : phase === 'failed' ? iconWarning : stepPending}
                            alt=''
                          />
                        </span>
                        <span className='kel-wd-step__label'>{step.label}</span>
                        <span className='kel-wd-step__when'>
                          {phase === 'now' ? 'Now' : phase === 'pending' ? (index === firstPending && running ? 'Next' : '') : at ?? ''}
                        </span>
                        <span className='kel-wc-sr'>
                          {phase === 'done' ? ', done' : phase === 'now' ? ', in progress' : phase === 'failed' ? ', did not finish' : ', not started'}
                        </span>
                      </li>
                    );
                  })}
                </ol>
              ) : (
                <p className='kel-wd-empty'>No steps reported yet.</p>
              )}
            </section>
            {Array.isArray(files) ? (
              <section aria-labelledby={`${titleId}-files`}>
                <SectionHead
                  id={`${titleId}-files`}
                  title='Files changed'
                  meta={`${files.length} file${files.length === 1 ? '' : 's'}`}
                />
                {files.length ? (
                  <ul className='kel-wd-list'>
                    {files.map((path) => (
                      <li key={path} className='kel-wd-file'>
                        <img src={iconFile} alt='' />
                        <span>{path}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className='kel-wd-empty'>No files changed.</p>
                )}
              </section>
            ) : null}
          </div>
          <section className='kel-wd-col kel-wd-col--review' aria-labelledby={`${titleId}-review`}>
            <SectionHead id={`${titleId}-review`} title='Review and checks' />
            <div className='kel-wd-finding' data-testid='kel-office-review'>
              <div className='kel-wd-finding__head'>
                <StatusDot tone={reviewTone} />
                <strong>Verifier</strong>
                {verifier ? <span className='kel-wc-sr'>{`, ${modelLine(verifier)}`}</span> : null}
                <span className='kel-wc-push' />
                <span className={`kel-wd-finding__word kel-wd-tone--${reviewTone}`}>{reviewWord}</span>
              </div>
              {reviewText ? <p>{reviewText}</p> : null}
              {review?.independence && review.independence !== 'full' ? (
                <p className='kel-wd-note'>{`Independence: ${review.independence}.`}</p>
              ) : null}
            </div>
            <div className='kel-wd-oracle' data-testid='kel-office-oracle'>
              <StatusDot tone='next' />
              <span className='kel-wd-member__text'>
                <span className='kel-wd-member__line'>
                  <strong>Oracle</strong>
                  {oracleModel ? <span className='kel-wd-model'>{oracleModel}</span> : null}
                </span>
                <span className='kel-wd-oracle__why'>
                  {oracleLine(view.oracle)}
                  {view.oracle?.independence && view.oracle.independence !== 'full' ? ` Independence: ${view.oracle.independence}.` : ''}
                </span>
              </span>
            </div>
            <div className='kel-wd-verification' data-testid='kel-office-verification'>
              <strong>Verification</strong>
              <span className={`kel-wd-tone--${verificationTone}`}>{verificationText}</span>
            </div>
          </section>
        </div>
      ) : null}
      <p className='kel-wd-footer'>
        {finished
          ? 'Finished work stays at the top until you remove it. Click anywhere outside to close.'
          : 'Read-only. Kel runs the team; ask Kel for any change. Click anywhere outside to close.'}
      </p>
    </div>
  );
};

export default KelOfficeDetail;
