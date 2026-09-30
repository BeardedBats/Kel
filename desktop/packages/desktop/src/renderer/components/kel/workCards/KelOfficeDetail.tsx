/**
 * D-66 / D-68 / D-79 — the detail that drops down from under the work-card row. Simplified (D-79):
 * the title with "Open" (the project folder) beside it and Remove (or Stop) top right; the status in
 * plain short words ("Complete", its date and time in the tooltip); three columns — the team (role in
 * its own colour, model and reasoning; what it did in a tooltip), the steps (one line each) and the
 * Review Team (one status, and one line on any open problem and who is on it); "Talk to Kel about this"
 * bottom right. No Undo here: Nick asks Kel.
 */
import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ProgressFill, RollText, SwapIn, cardStateTransition, fillTone, measure, playFlip, snapshotGhost, stepTickTransition, type Point, type Snapshot } from '@renderer/motion';
import { answeredMorph, panelHeightEase } from './workCardMotion';
import { kelControl, kelHandoff, type KelChangeApplication, type KelContextStatus } from '../kelApi';
import { applicationLine } from '../changeApplication';
import { ContextStatusFacts, OutputVersions, ResultFeedback, TaskOutcomeFacts } from '../WorkHubControls';
import type { OfficeItem, OfficeItemDetail, OfficeStaff, OfficeStep } from './officeApi';
import { officeItem } from './officeApi';
import { KelAnsweredLine, KelNeedsAnswer, type AnsweredNote } from './KelNeedsAnswer';
import { KelBudgetStop } from './KelBudgetStop';
import { refreshWorkCards } from './workCardEvents';
import { usageHeaderLine } from '../usage/usageWords';
import {
  StateIcon,
  StatusDot,
  iconCheck14,
  iconFolder,
  iconLoader,
  iconRemove,
  iconStop,
  iconWarning,
  iconWarningAmber,
  stepPending,
} from './workCardIcons';
import {
  COMPLETE_LABEL,
  clockTime,
  completedAt,
  isCommander,
  isFinished,
  isUncertain,
  isUndone,
  memberTooltip,
  modelLine,
  panelStateLabel,
  plainResultText,
  progressFraction,
  reviewProblemLine,
  reviewTeamState,
  roleColorKey,
  roleName,
  teamHeading,
  undoneLine,
} from './workCardModel';

type Props = {
  item: OfficeItem;
  projectName?: string | null;
  /** D-79: the project's folder, for "Open" when the work has no applied change of its own. */
  projectRoot?: string | null;
  pollMs: number;
  onClose: () => void;
  onRemove: (item: OfficeItem) => void;
  onTalk: (item: OfficeItem) => void;
  /** Called after Stop so the row reads the new state at once. */
  onChanged: () => void;
  /** LIVE-3: open a page in Kel (Settings → Staff & models from a needs-you card); the row navigates. */
  onOpenSettings?: (path: string) => void;
  /** Open a folder on this computer (injected so tests and the remote surface can decide). */
  openFolder?: (path: string) => Promise<unknown>;
  /**
   * `panel` drops down under the desktop row (Figma 4b/4d). `sheet` is the phone's bottom sheet
   * (inferred from the phone sheets, docs/v2/FIGMA_GAPS.md): one column that scrolls, with the
   * actions in a foot that stays in reach above the home indicator.
   */
  variant?: 'panel' | 'sheet';
};

const FOCUSABLE = 'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

const STEP_DONE = new Set(['done', 'accepted', 'verified', 'passed', 'complete', 'completed']);
const STEP_NOW = new Set(['running', 'working', 'in_progress', 'active', 'claimed', 'review', 'in_review']);
const STEP_FAILED = new Set(['failed', 'blocked', 'stopped']);

type StepPhase = 'done' | 'now' | 'paused' | 'interrupted' | 'failed' | 'pending';
const stepPhase = (step: OfficeStep): StepPhase => {
  const state = (step.state ?? '').toLowerCase();
  if (state === 'paused') return 'paused';
  if (STEP_DONE.has(state)) return 'done';
  // LIVE-3: a restart or a lost worker stopped this step part-way (the engine's marker, not a wording).
  if (step.interrupted === true) return 'interrupted';
  if (STEP_NOW.has(state)) return 'now';
  if (STEP_FAILED.has(state)) return 'failed';
  return 'pending';
};

/** "Calc demo" -> "calc-demo-change-report.md". */
export const reportFileName = (title: string | null | undefined): string => {
  const slug = String(title ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48);
  return `${slug || 'kel'}-change-report.md`;
};

const SectionHead: React.FC<{ title: string; id?: string }> = ({ title, id }) => (
  <div className='kel-wd-section-head'>
    <h3 id={id}>{title}</h3>
  </div>
);

/** The phone sheet scrolls its middle; the desktop panel scrolls as one. */
const SheetBody: React.FC<{ sheet: boolean; children: React.ReactNode }> = ({ sheet, children }) =>
  sheet ? (
    <div className='kel-wd-sheet__body' data-testid='kel-office-sheet-body'>
      {children}
    </div>
  ) : (
    <>{children}</>
  );

/** D-79: role (in its own colour), model and reasoning; what it did is in the tooltip. */
const Member: React.FC<{ member: OfficeStaff }> = ({ member }) => {
  const commander = isCommander(member);
  return (
    <li className={`kel-wd-member kel-role--${roleColorKey(member)}`} data-testid='kel-office-member' title={memberTooltip(member)}>
      <span className='kel-wd-member__line'>
        <strong className='kel-wd-member__role' data-testid='kel-office-role'>
          {roleName(member)}
        </strong>
        {commander ? <span className='kel-wc-sr'>, Commander</span> : null}
        {member.step_label ? (
          <span className='kel-wd-step-tag' data-testid='kel-office-step-label'>
            {member.step_label.split(':')[0]}
          </span>
        ) : null}
        {/* §10.15: when the model line changes (a fallback), it rolls. */}
        <RollText className='kel-wd-model' value={modelLine(member)} flipSiblings={false} testId='kel-office-model' />
      </span>
    </li>
  );
};

export const KelOfficeDetail: React.FC<Props> = ({
  item,
  projectName,
  projectRoot,
  pollMs,
  onClose,
  onRemove,
  onTalk,
  onChanged,
  onOpenSettings,
  openFolder,
  variant = 'panel',
}) => {
  const sheet = variant === 'sheet';
  const [detail, setDetail] = useState<OfficeItemDetail | null>(null);
  const [unreadable, setUnreadable] = useState(false);
  const [handoffApplication, setHandoffApplication] = useState<KelChangeApplication | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  /** D-70 (5b): the answer Nick just sent from this panel, and the question it answered. */
  const [answered, setAnswered] = useState<(AnsweredNote & { question: string }) | null>(null);
  /** Routing 2 §5.4: what raising the budget did, in plain words (kept until the panel closes). */
  const [budgetNote, setBudgetNote] = useState<string | null>(null);
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
    setAnswered(null);
    setBudgetNote(null);
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
  const [contextStatus, setContextStatus] = useState<KelContextStatus | null>(null);
  const running = !finished;
  const coding = (view.kind ?? item.kind) === 'code';

  // D-65: the engine's hand-off view knows whether a checked change was applied and can be undone.
  const submission = view.links?.submission_id ?? view.submission_id;
  const conversation = view.links?.conversation_id ?? view.conversation_id;
  useEffect(() => {
    let alive = true; setContextStatus(null);
    if (submission && conversation) kelHandoff(conversation, submission).then(value => { if (alive) setContextStatus(value.context_status ?? null); }).catch(() => {});
    return () => { alive = false; };
  }, [submission, conversation]);
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

  // D-78 §10.6: "Kel is asking you" becomes "You answered" — the section's surface morphs into the
  // line, the blocks below FLIP up and the panel's own height eases down. Copied before React swaps it.
  const answeredSeen = useRef(answered);
  const answerSnap = useRef<{ question: Snapshot | null; below: Map<HTMLElement, Point>; height: number } | null>(null);
  if (answered && !answeredSeen.current && !answerSnap.current && dialogRef.current) {
    const question = dialogRef.current.querySelector<HTMLElement>(':scope .kel-na');
    const below: HTMLElement[] = [];
    let next = question?.nextElementSibling ?? null;
    while (next) {
      below.push(next as HTMLElement);
      next = next.nextElementSibling;
    }
    answerSnap.current = { question: snapshotGhost(question), below: measure(below), height: dialogRef.current.getBoundingClientRect().height };
  }
  useLayoutEffect(() => {
    const was = answeredSeen.current;
    answeredSeen.current = answered;
    const snap = answerSnap.current;
    answerSnap.current = null;
    const dialog = dialogRef.current;
    if (!answered || was || !snap || !dialog) return;
    const line = dialog.querySelector<HTMLElement>('.kel-na-answered');
    if (line) answeredMorph(snap.question, line);
    void playFlip(snap.below, 'morph');
    panelHeightEase(dialog, snap.height);
  }, [answered]);

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

  // D-79: "Open" beside the title opens the project folder (the applied change's folder, else the project's).
  const folder = application?.root ?? projectRoot ?? null;
  const showFolder = () =>
    guarded(async () => {
      if (folder && openFolder) await openFolder(folder);
    });

  const staff = view.staff ?? [];

  // VIS-6: paused work marks the step it paused at (amber warning, "Paused"). The engine's own step
  // state wins; until it sends one, the step in progress (or the next one) of paused work is it.
  const pausedWork = !finished && (view.paused === true || view.question?.kind === 'paused' || /\bpaused\b/i.test(view.status_line ?? ''));
  const rawSteps = view.steps ?? [];
  const engineMarkedPause = rawSteps.some((step) => stepPhase(step) === 'paused');
  const nowIndex = rawSteps.findIndex((step) => stepPhase(step) === 'now');
  const pausedIndex =
    engineMarkedPause || !pausedWork ? -1 : nowIndex >= 0 ? nowIndex : rawSteps.findIndex((step) => stepPhase(step) === 'pending');
  const steps = rawSteps.map((step, index) => (index === pausedIndex ? { ...step, state: 'paused' } : step));
  const pausedAt = steps.findIndex((step) => stepPhase(step) === 'paused');
  const firstPending = steps.findIndex((step) => stepPhase(step) === 'pending');
  // LIVE-3: nothing comes "Next" while a step waits to be started again.
  const stalled = pausedAt >= 0 || steps.some((step) => stepPhase(step) === 'interrupted');

  const uncertain = finished && isUncertain(view);
  // D-79 Review Team: one status, and one line on any open problem and who is on it.
  const reviewState = reviewTeamState(view);
  const reviewTone: 'done' | 'failed' | 'review' | 'next' =
    reviewState === 'Passed' ? 'done' : reviewState === 'Failed' ? 'failed' : reviewState === 'Not started' ? 'next' : 'review';
  const problem = reviewProblemLine(view);

  const started = clockTime(view.started_at);
  const total = view.progress?.total ?? 0;
  const stepNow = total > 0 ? Math.min((view.progress?.done ?? 0) + 1, total) : 0;
  const runningMeta =
    pausedAt >= 0 && steps.length ? `Paused at step ${pausedAt + 1} of ${steps.length}` : total > 0 ? `Step ${stepNow} of ${total}` : null;
  // D-79: finished work carries no "5 of 5" and no finish time (the "Complete" tooltip has the when).
  const subtitle = [running ? runningMeta : null, running && started ? `Started ${started}` : null, projectName || null].filter(Boolean);

  // D-72: what the work has used so far (cost or "Included in your plan", tokens, model time).
  const usageLine = usageHeaderLine(view.usage);
  // LIVE-10 / LIVE-12: no literal backticks, and no second "Applied to <path>:" once the head says
  // where the change went (or that it was undone).
  const resultText = plainResultText(view.result, coding ? application : null) || (view.status_line ?? '').trim();
  const attention = view.state === 'needs_you' || view.state === 'failed' || view.state === 'stopped';
  const headSettles = cardStateTransition(view.state) === 'settling';
  // VIS-5: the result line is not said twice ("You stopped this work." as the result and as the why).
  const attentionText = [view.why, view.next]
    .filter((part) => part && part.trim() && (!finished || part.trim() !== resultText))
    .join(' ');
  // LIVE-12: an undone change says when it was undone and what came back (the engine's record).
  const undone = coding && isUndone({ undone: view.undone, application });
  const appliedLine = coding ? (undone ? undoneLine({ undone: view.undone, application }) : applicationLine(application)) : null;
  const titleId = `kel-office-detail-title-${job}`;
  const stateWords = panelStateLabel(view);
  const completeTip = stateWords === COMPLETE_LABEL ? completedAt(view.finished_at ?? view.updated_at) ?? undefined : undefined;

  // Top right: Remove once finished; Stop (with its confirm) while it runs. No Undo (D-79: Nick asks Kel).
  const topActions = confirming ? (
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
        <button type='button' className='kel-wd-button' disabled={busy} onClick={() => onRemove(item)} data-testid='kel-office-remove'>
          <img src={iconRemove} alt='' />
          Remove
        </button>
      )}
    </div>
  );
  const talkButton = (
    <button type='button' className='kel-wd-button kel-wd-button--primary' onClick={() => onTalk(item)} data-testid='kel-office-talk'>
      Talk to Kel about this
    </button>
  );

  return (
    <div
      ref={dialogRef}
      className={`kel-wd kel-wd--${view.state}${sheet ? ' kel-wd--sheet' : ''}${uncertain ? ' is-uncertain' : ''}`}
      role='dialog'
      aria-modal='true'
      aria-labelledby={titleId}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      data-testid='kel-office-detail'
    >
      {sheet ? <div className='kel-wd-sheet__handle' aria-hidden='true' /> : null}
      <div className='kel-wd-head'>
        <div className='kel-wd-title'>
          <div className='kel-wd-title__row'>
            <h2 id={titleId}>{view.title}</h2>
            {folder && openFolder ? (
              <button
                type='button'
                className='kel-wd-button kel-wd-open'
                disabled={busy}
                onClick={() => void showFolder()}
                aria-label='Open the project folder'
                title='Open the project folder'
                data-testid='kel-office-open-folder'
              >
                <img src={iconFolder} alt='' />
                Open
              </button>
            ) : null}
          </div>
          <div className='kel-wd-state' role='status' aria-live='polite'>
            <SwapIn className='kel-wc-state-icon' swapKey={`${view.state}${uncertain ? ':u' : ''}`} draw={view.state === 'done'} settle={headSettles}>
              <StateIcon state={view.state} size='detail' uncertain={uncertain} />
            </SwapIn>
            <span className='kel-wd-state__word' title={completeTip} data-testid='kel-office-detail-state-word'>
              <RollText className='kel-wd-state__label' value={stateWords} settle={headSettles} testId='kel-office-detail-state' />
            </span>
            {subtitle.length ? <RollText className='kel-wd-state__meta' value={sheet ? subtitle.join('  ·  ') : `·  ${subtitle.join('  ·  ')}`} /> : null}
          </div>
          {usageLine ? (
            <div className='kel-wd-usage' data-testid='kel-office-usage'>
              {usageLine}
            </div>
          ) : null}
        </div>
        <span className='kel-wc-push' />
        {sheet ? null : topActions}
      </div>
      <SheetBody sheet={sheet}>
        {notice ? (
          <p className='kel-wd-notice' role='alert'>
            {notice}
          </p>
        ) : null}
        {/* D-70 (5a/5b): Kel's question, or the answer just sent, sits above the bar. */}
        {budgetNote ? (
          <section className='kel-wd-result' aria-label='Budget raised' data-testid='kel-budget-raised'>
            <p>{budgetNote}</p>
          </section>
        ) : view.budget?.stopped && !finished ? (
          // Routing 2 §5.4: stopped on its budget — the numbers, and "Raise budget" (Nick's own act).
          <KelBudgetStop
            job={job}
            budget={view.budget}
            onRaised={(words) => {
              setBudgetNote(words);
              onChanged();
              refreshWorkCards();
              void read();
            }}
          />
        ) : answered && (!view.question || view.question.text === answered.question) ? (
          <KelAnsweredLine note={answered} />
        ) : view.state === 'needs_you' && view.question ? (
          <KelNeedsAnswer
            question={view.question}
            onOpenSettings={onOpenSettings}
            onAnswered={(note) => {
              setAnswered({ ...note, question: view.question?.text ?? '' });
              onChanged();
              refreshWorkCards();
              void read();
            }}
          />
        ) : !finished && view.state === 'needs_you' && attentionText ? (
          <section className='kel-wd-result kel-wd-result--needs' aria-label='What Kel needs' data-testid='kel-office-needs'>
            <div className='kel-wd-result__head'>
              <StatusDot tone='needs' />
              <strong>Needs you</strong>
            </div>
            <p>{attentionText}</p>
          </section>
        ) : null}
        <div className='kel-wc-progress kel-wd-progress' aria-hidden='true'>
          <ProgressFill fraction={progressFraction(view)} tone={fillTone(view.state, uncertain)} />
        </div>
        {finished && (resultText || appliedLine) ? (
          <section className='kel-wd-result' aria-label='Result' data-testid='kel-office-result'>
            <div className='kel-wd-result__head'>
              <StateIcon state={view.state} size='detail' uncertain={uncertain} />
              <strong>Result</strong>
              {appliedLine ? <RollText className='kel-wd-meta' value={appliedLine} settle={undone} flipSiblings={false} testId='kel-office-applied' /> : null}
            </div>
            {resultText ? <p>{resultText}</p> : null}
            {view.state === 'done' && <OutputVersions key={`outputs-${view.job_id}`} jobId={view.job_id} />}
            {view.project_id && <TaskOutcomeFacts key={`facts-${view.job_id}`} projectId={view.project_id} jobId={view.job_id} />}
            {view.state === 'done' && view.project_id && <ResultFeedback key={`feedback-${view.job_id}`} projectId={view.project_id} jobId={view.job_id} onRevise={() => onTalk(item)} />}
            {attention && attentionText ? <p className='kel-wd-result__why'>{attentionText}</p> : null}
          </section>
        ) : null}
        {contextStatus && <ContextStatusFacts status={contextStatus} />}
        {detail === null && unreadable ? <p className='kel-wd-loading'>Kel couldn’t read the details just now. It will try again.</p> : null}
        {detail === null && !unreadable ? <p className='kel-wd-loading'>Reading the details…</p> : null}
        {detail ? (
          <div className='kel-wd-columns'>
            <section className='kel-wd-col kel-wd-col--team' aria-labelledby={`${titleId}-team`}>
              <SectionHead id={`${titleId}-team`} title={staff.length ? teamHeading(staff) : 'Team'} />
              {staff.length ? (
                <ul className='kel-wd-list'>
                  {staff.map((member) => (
                    <Member key={member.id} member={member} />
                  ))}
                </ul>
              ) : (
                <p className='kel-wd-empty'>Kel is handling this alone.</p>
              )}
            </section>
            <section className='kel-wd-col kel-wd-col--steps' aria-labelledby={`${titleId}-steps`}>
              <SectionHead id={`${titleId}-steps`} title='Steps' />
              {steps.length ? (
                <ol className='kel-wd-list kel-wd-steps'>
                  {steps.map((step, index) => {
                    const phase = stepPhase(step);
                    const last = stepTickTransition(index, steps.length) === 'settling';
                    return (
                      <li key={step.id} className={`kel-wd-step kel-wd-step--${phase}`} data-testid='kel-office-step' title={step.label ?? undefined}>
                        {/* D-78: each row owns its icon; only its state animates (the loader turns once, a check draws on). */}
                        <SwapIn className='kel-wd-step__lead' swapKey={phase} draw={phase === 'done'} turn={phase === 'now'} settle={phase === 'done' && last}>
                          <img
                            src={
                              phase === 'done'
                                ? iconCheck14
                                : phase === 'now'
                                  ? iconLoader
                                  : phase === 'failed'
                                    ? iconWarning
                                    : phase === 'paused' || phase === 'interrupted'
                                      ? iconWarningAmber
                                      : stepPending
                            }
                            alt=''
                          />
                        </SwapIn>
                        {/* D-79: one line each; the full words are in the tooltip. */}
                        <span className='kel-wd-step__label' data-testid='kel-office-step-text'>
                          {step.label}
                        </span>
                        <RollText
                          className='kel-wd-step__when'
                          flipSiblings={false}
                          value={
                            phase === 'now'
                              ? 'Now'
                              : phase === 'paused'
                                ? 'Paused'
                                : phase === 'interrupted'
                                  ? 'Interrupted'
                                  : phase === 'pending' && index === firstPending && running && !stalled
                                    ? 'Next'
                                    : ''
                          }
                        />
                        <span className='kel-wc-sr'>
                          {phase === 'done'
                            ? ', done'
                            : phase === 'now'
                              ? ', in progress'
                              : phase === 'paused'
                                ? ', paused here'
                                : phase === 'interrupted'
                                  ? ', stopped part-way when Kel’s worker stopped'
                                  : phase === 'failed'
                                    ? ', did not finish'
                                    : ', not started'}
                        </span>
                      </li>
                    );
                  })}
                </ol>
              ) : (
                <p className='kel-wd-empty'>No steps reported yet.</p>
              )}
            </section>
            <section className='kel-wd-col kel-wd-col--review' aria-labelledby={`${titleId}-review`}>
              <SectionHead id={`${titleId}-review`} title='Review Team' />
              <div className='kel-wd-review' data-testid='kel-office-review'>
                <div className='kel-wd-review__status'>
                  <StatusDot tone={reviewTone} />
                  <RollText
                    className={`kel-wd-review__word kel-wd-tone--${reviewTone === 'next' ? 'quiet' : reviewTone}`}
                    value={reviewState}
                    settle={reviewState === 'Passed' || reviewState === 'Failed'}
                    testId='kel-office-review-state'
                  />
                </div>
                {problem ? (
                  <p className='kel-wd-review__problem' data-testid='kel-office-review-problem'>
                    {problem}
                  </p>
                ) : null}
              </div>
            </section>
          </div>
        ) : null}
        {sheet ? null : <div className='kel-wd-foot'>{talkButton}</div>}
      </SheetBody>
      {sheet ? (
        <div className='kel-wd-sheet__foot' data-testid='kel-office-sheet-foot'>
          {topActions}
          {talkButton}
        </div>
      ) : null}
    </div>
  );
};

export default KelOfficeDetail;
