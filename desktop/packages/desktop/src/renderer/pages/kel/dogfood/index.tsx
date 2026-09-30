/**
 * Dogfood Fixes (V2.0 preflight) — the place Nick reviews what Fix Capture recorded.
 *
 * Captured reports can be exported or sent to Kel. Work stays attached to each report.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Message } from '@arco-design/web-react';
import { useNavigate } from 'react-router-dom';
import { KelButton, KelCard, KelEmpty, KelLoading, KelTabs, formatWhen } from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import '@renderer/styles/kel-work.css';
import { kelDogfood, type KelFix, type KelFixList, type KelFixStatus } from '@renderer/components/kel/kelApi';
import styles from './index.module.css';
import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';

const STATUS_COPY: Record<KelFixStatus, string> = {
  OPEN: 'Open',
  BATCHED: 'Batched',
  FIXED: 'Fixed',
  DISMISSED: 'Dismissed',
};

const STATUS_ORDER: KelFixStatus[] = ['OPEN', 'BATCHED', 'FIXED', 'DISMISSED'];

const DogfoodFixes: React.FC = () => {
  const navigate = useNavigate();
  const isMobile = Boolean(useLayoutContext()?.isMobile);
  const [data, setData] = useState<KelFixList | null>(null);
  const [tab, setTab] = useState<KelFixStatus>('OPEN');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [note, setNote] = useState<string | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [prompt, setPrompt] = useState<{ text: string; path: string; ids: string[] } | null>(null);
  const [workError, setWorkError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<number | null>(null);
  const [draftNotes, setDraftNotes] = useState<Record<string, string>>({});
  const load = useCallback(async () => {
    try {
      const result = await kelDogfood.list();
      setData(result);
      setError(null);
      setLastChecked(Date.now());
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const fixes = useMemo(() => data?.fixes ?? [], [data]);
  const openFixes = useMemo(() => fixes.filter((fix) => fix.status === 'OPEN'), [fixes]);
  const visible = useMemo(() => fixes.filter((fix) => fix.status === tab), [fixes, tab]);
  const selected = useMemo(() => fixes.find((fix) => fix.id === selectedId) ?? null, [fixes, selectedId]);
  const workingFixes = useMemo(() => fixes.filter((fix) => fix.work), [fixes]);

  // Refresh durable work after its report moves to Batched. Do not overlap requests.
  useEffect(() => {
    if (!workingFixes.length) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      if (!cancelled) await load();
      if (!cancelled) timer = setTimeout(() => void refresh(), 2500);
    };
    timer = setTimeout(() => void refresh(), 2500);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [workingFixes.length, load]);

  const sendToKel = useCallback(
    async (fix: KelFix) => {
      setBusy(true);
      setWorkError(null);
      try {
        const result = await kelDogfood.sendToKel(fix.id);
        if (!result.work) throw new Error('Kel did not return a work record. Refresh before sending again.');
        await load();
        setNote(`${fix.id} was sent to Kel. Follow its work below.`);
      } catch (err) {
        setWorkError(err instanceof Error ? err.message : 'Kel could not start this report. Try again.');
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  const updateWork = async (fix: KelFix, action: 'apply' | 'build' | 'retry' | 'install' | 'reveal') => {
    setBusy(true);
    setWorkError(null);
    try {
      if (action === 'apply') await kelDogfood.applyWork(fix.id);
      else if (action === 'build') await kelDogfood.buildUpdate(fix.id);
      else if (action === 'retry') await kelDogfood.retryWork(fix.id);
      else {
        if (!window.kelAPI?.kibbleInstaller)
          throw new Error('Open this report in the desktop app to install its update.');
        await window.kelAPI.kibbleInstaller(fix.id, action === 'reveal');
        setNote(
          action === 'install'
            ? 'Installer opened. Finish installation, then reopen Kel to confirm it.'
            : 'Update installer shown in its folder.'
        );
      }
      await load();
    } catch (err) {
      setWorkError(err instanceof Error ? err.message : 'Kel could not finish this action. Try again.');
    } finally {
      setBusy(false);
    }
  };
  const openWorkChat = async (conversation: string) => {
    try {
      const open = window.kelAPI?.openEngineConversation;
      if (!open) throw new Error('Open this work chat from the desktop app. The log stays available here.');
      const id = await open(conversation);
      if (!id) throw new Error('Kel could not open that work chat. Try again.');
      navigate(`/conversation/${encodeURIComponent(id)}`);
    } catch (err) {
      setWorkError(err instanceof Error ? err.message : 'Kel could not open the work chat.');
    }
  };
  const addNote = async (fix: KelFix) => {
    setBusy(true);
    setWorkError(null);
    try {
      await kelDogfood.setNote(fix.id, draftNotes[fix.id] ?? '');
      await load();
    } catch (err) {
      setWorkError(err instanceof Error ? err.message : 'Kel could not save the note.');
    } finally {
      setBusy(false);
    }
  };

  // Every open fix is included by default; deselecting one is a deliberate act.
  useEffect(() => {
    setChecked((previous) => {
      const next: Record<string, boolean> = {};
      for (const fix of openFixes) next[fix.id] = previous[fix.id] ?? true;
      return next;
    });
  }, [openFixes]);

  useEffect(() => {
    let cancelled = false;
    setImage(null);
    if (!selected?.has_screenshot || !selected.screenshot) return;
    void (async () => {
      const url = await kelDogfood.screenshot(selected.screenshot);
      if (!cancelled) setImage(url);
    })();
    return () => {
      cancelled = true;
    };
  }, [selected?.id, selected?.screenshot, selected?.has_screenshot]);

  const act = useCallback(
    async (fix: KelFix, status: KelFixStatus) => {
      setBusy(true);
      setNote(null);
      try {
        await kelDogfood.setStatus(fix.id, status);
        await load();
        setNote(`${fix.id} is ${STATUS_COPY[status].toLowerCase()}.`);
      } catch (err) {
        Message.error('Kel could not change that fix just now. Try again.');
        setError(err);
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  const included = openFixes.filter((fix) => checked[fix.id] !== false);
  const preparePrompt = useCallback(async () => {
    if (!included.length) return;
    setBusy(true);
    setNote(null);
    try {
      const result = await kelDogfood.preparePrompt(included.map((fix) => fix.id));
      setPrompt({ text: result.prompt, path: result.path, ids: result.fix_ids });
      await load();
    } catch (err) {
      Message.error('Kel could not prepare the fix prompt just now. Try again.');
      setError(err);
    } finally {
      setBusy(false);
    }
  }, [included, load]);

  const copyPrompt = useCallback(async () => {
    if (!prompt) return;
    try {
      await navigator.clipboard.writeText(prompt.text);
      setNote('Fix prompt copied — paste it into a coding session.');
    } catch {
      setNote('Copying is blocked here — select the text and copy it yourself.');
    }
  }, [prompt]);

  const revealPrompt = useCallback(() => {
    if (!prompt) return;
    const api = window.kelAPI;
    if (!api?.revealArtifact) {
      setNote('Kel cannot open that folder on this surface.');
      return;
    }
    void api.revealArtifact(prompt.path).catch(() => setNote('Kel could not open that folder here.'));
  }, [prompt]);

  const tabs = STATUS_ORDER.map((status) => ({
    id: status,
    label: isMobile
      ? `${STATUS_COPY[status]} (${data?.counts?.[status] ?? 0})`
      : `${STATUS_COPY[status]} · ${data?.counts?.[status] ?? 0}`,
  }));

  const promptActions = (
    <KelButton variant='primary' disabled={busy || !included.length} onClick={() => void preparePrompt()}>
      {`${isMobile ? 'Prepare Fix Prompt' : 'Prepare prompt'} (${included.length})`}
    </KelButton>
  );

  if (error && !data) {
    return (
      <div className='kel-scope'>
        <div className='kel-page'>
          <KelFailureCard error={error} onRetry={() => void load()} />
        </div>
      </div>
    );
  }

  return (
    <div className='kel-scope'>
      <a className='kel-skip' href='#kel-dogfood-main'>
        Skip to main content
      </a>
      <div className={`kel-page ${!isMobile ? `kel-shell-kibble ${styles.desktop}` : ''}`}>
        <button className='kel-dogfood-mobile-back' type='button' onClick={() => void navigate('/settings/tools')}>
          ← Tools
        </button>
        <header className='kel-page__head'>
          <div>
            {!isMobile && <ShellWorkspaceLink />}
            <h1 className='kel-h1'>Kibble</h1>
            {isMobile && (
              <p className='kel-sub'>Review what you captured. Send a report to Kel and follow its work here.</p>
            )}
          </div>
        </header>
        {!isMobile && (
          <p className='kel-sub kel-kibble-intro'>
            What you flagged with Ctrl+Shift+F. Send a report to Kel and follow its work here.
          </p>
        )}
        {error && data && <KelFailureCard error={error} onRetry={() => void load()} />}
        {workError && (
          <p className={styles.workError} role='alert'>
            {workError}
          </p>
        )}

        {data === null ? (
          <KelLoading rows={3} />
        ) : (
          <>
            <div className={!isMobile ? styles.topPanels : styles.mobileContents}>
              <KelCard
                className={!isMobile ? styles.actionPanel : undefined}
                title='Prepare a fix prompt'
                actions={isMobile ? promptActions : undefined}
              >
                {!isMobile && <p className='kel-sub'>Pick fixes. Kel turns them into one prompt.</p>}
                <p className={isMobile ? 'kel-sub' : styles.explanation}>
                  Open fixes are included by default. Preparing a prompt moves them to Batched — it never starts
                  development on its own.
                </p>
                {openFixes.length === 0 ? (
                  <p className='kel-meta'>Nothing is open right now.</p>
                ) : (
                  <ul className={styles.pickList}>
                    {openFixes.map((fix) => (
                      <li key={fix.id}>
                        <label className={styles.pick}>
                          <input
                            type='checkbox'
                            checked={checked[fix.id] !== false}
                            onChange={(event) =>
                              setChecked((previous) => ({ ...previous, [fix.id]: event.target.checked }))
                            }
                            data-testid={`fix-pick-${fix.id}`}
                          />
                          {isMobile ? (
                            <>
                              <span className='kel-strong'>{fix.id}</span>
                              <span className={styles.preview}>{preview(said(fix))}</span>
                              <span className='kel-meta'>{fix.route || 'screen not recorded'}</span>
                            </>
                          ) : (
                            <span className={styles.pickText}>
                              <span className='kel-strong'>{fix.id}</span>
                              <span className={styles.preview}>{preview(said(fix))}</span>
                            </span>
                          )}
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
                {!isMobile && <div className={styles.panelActions}>{promptActions}</div>}
              </KelCard>
            </div>

            {prompt && (
              <KelCard
                title={`Fix prompt (${prompt.ids.length})`}
                actions={
                  <>
                    <KelButton variant='primary' onClick={() => void copyPrompt()}>
                      Copy
                    </KelButton>
                    <KelButton variant='quiet' onClick={revealPrompt}>
                      Show the file
                    </KelButton>
                  </>
                }
              >
                <p className='kel-sub'>
                  Saved as <span className='kel-code'>{prompt.path}</span> — hand it to a coding session whenever you
                  are ready.
                </p>
                <textarea className={styles.prompt} value={prompt.text} readOnly rows={14} data-testid='fix-prompt' />
              </KelCard>
            )}

            {workingFixes.length > 0 && (
              <section className={`kel-card ${styles.workPanel}`} aria-label='Kel’s work' data-testid='kibble-work'>
                <div className={styles.workHead}>
                  <h2 className='kel-h2'>Kel’s work</h2>
                  <KelButton variant='quiet' onClick={() => void load()}>
                    Refresh work
                  </KelButton>
                </div>
                <p className='kel-meta'>
                  Updates every few seconds.{' '}
                  {lastChecked && `Last checked ${new Date(lastChecked).toLocaleTimeString()}.`}
                </p>
                {workingFixes.map((fix) => {
                  const work = fix.work!;
                  return (
                    <article key={fix.id} className={styles.workItem}>
                      <div className={styles.workHead}>
                        <h3>{fix.id}</h3>
                        <span className={styles.workState} role='status'>{workLabel(work.state)}</span>
                      </div>
                      <p className={styles.transcript}>{said(fix)}</p>
                      {work.error && (
                        <p className={styles.workError} role='alert'>
                          {work.error}
                        </p>
                      )}
                      <p className='kel-meta'>
                        Review: {work.verification ? workLabel(work.verification) : 'Incomplete'} · Update:{' '}
                        {work.installed
                          ? 'Installed'
                          : work.application?.state === 'APPLIED'
                            ? 'Source changes applied; app install pending'
                            : 'Not installed'}
                      </p>
                      {work.application?.waiting_reason && (
                        <p className='kel-meta'>{work.application.waiting_reason}</p>
                      )}
                      <ol className={styles.workSteps}>
                        {work.milestones?.map((step) => (
                          <li key={step.id}>
                            <span>{workLabel(step.id)}</span>
                            <span className='kel-meta'>{workLabel(step.state)}</span>
                            {step.error && <p className={styles.workError}>{step.error}</p>}
                          </li>
                        ))}
                      </ol>
                      {work.messages?.length > 0 && (
                        <details>
                          <summary>Work log ({work.messages.length})</summary>
                          <div className={styles.workLog}>
                            {work.messages.map((entry) => (
                              <p key={entry.seq}>{entry.text}</p>
                            ))}
                          </div>
                        </details>
                      )}
                      {work.activity?.length > 0 && (
                        <details>
                          <summary>Recent activity ({work.activity.length})</summary>
                          <ol className={styles.workLog}>
                            {work.activity.map((entry) => (
                              <li key={entry.seq}>
                                {entry.text} <span className='kel-meta'>· {workLabel(entry.state)}</span>
                              </li>
                            ))}
                          </ol>
                        </details>
                      )}
                      {work.release && (
                        <div className={styles.release}>
                          <p className='kel-strong'>{work.release.stage}</p>
                          {work.release.error && (
                            <p role='alert' className={styles.workError}>
                              {work.release.error}
                            </p>
                          )}
                          {work.release.log?.length > 0 && (
                            <details>
                              <summary>Build log</summary>
                              <pre className={styles.workLog}>{work.release.log.join('\n')}</pre>
                            </details>
                          )}
                          {work.release.installed && <p className='kel-meta'>This update is installed.</p>}
                        </div>
                      )}
                      <div className={styles.workActions}>
                        <KelButton variant='quiet' onClick={() => void openWorkChat(work.conversation)}>
                          Open work chat
                        </KelButton>
                        {['FAILED', 'INTERRUPTED'].includes(work.state) && !work.job_id && (
                          <KelButton variant='primary' disabled={busy} onClick={() => void updateWork(fix, 'retry')}>
                            Retry work
                          </KelButton>
                        )}
                        {work.verification === 'VERIFIED' && work.application?.state !== 'APPLIED' && (
                          <KelButton variant='primary' disabled={busy} onClick={() => void updateWork(fix, 'apply')}>
                            Apply source changes
                          </KelButton>
                        )}
                        {work.application?.state === 'APPLIED' &&
                          (!work.release || ['FAILED', 'INTERRUPTED'].includes(work.release.state)) && (
                            <KelButton variant='primary' disabled={busy} onClick={() => void updateWork(fix, 'build')}>
                              Build update
                            </KelButton>
                          )}
                        {work.release?.state === 'READY' && !work.release.installed && (
                          <>
                            <KelButton
                              variant='primary'
                              disabled={busy}
                              onClick={() => void updateWork(fix, 'install')}
                            >
                              Install update
                            </KelButton>
                            <KelButton variant='quiet' disabled={busy} onClick={() => void updateWork(fix, 'reveal')}>
                              Show installer
                            </KelButton>
                          </>
                        )}
                      </div>
                    </article>
                  );
                })}
              </section>
            )}

            <section
              id='kel-dogfood-main'
              tabIndex={-1}
              className={!isMobile ? `kel-card ${styles.fixesPanel}` : styles.mobileContents}
              aria-label='Fixes'
            >
              {!isMobile && <h2 className='kel-h2'>Fixes</h2>}
              <KelTabs
                tabs={tabs}
                active={tab}
                onSelect={(id) => {
                  setTab(id as KelFixStatus);
                  setSelectedId(null);
                }}
              />

              {visible.length === 0 ? (
                <KelEmpty
                  title={`No ${STATUS_COPY[tab].toLowerCase()} fixes.`}
                  why='Press Ctrl+Shift+F while something in Kel bothers you, click it, and say what is wrong.'
                />
              ) : (
                <ul className={styles.list} data-testid='fix-list'>
                  {visible.map((fix) => (
                    <li key={fix.id} className={styles.item}>
                      <div className={!isMobile ? styles.fixRow : undefined}>
                        <button
                          type='button'
                          className={styles.itemButton}
                          aria-expanded={fix.id === selectedId}
                          onClick={() => setSelectedId(fix.id === selectedId ? null : fix.id)}
                        >
                          {!isMobile && (
                            <svg
                              className={styles.bugIcon}
                              viewBox='0 0 16 16'
                              fill='none'
                              stroke='currentColor'
                              aria-hidden='true'
                            >
                              <path d='M5 5h6v5a3 3 0 0 1-6 0V5ZM6 5V3h4v2M2 7h3m6 0h3M2 10h3m6 0h3M4 13l2-2m4 0 2 2' />
                            </svg>
                          )}
                          {isMobile ? (
                            <>
                              <span className='kel-strong'>{fix.id}</span>
                              <span className={styles.preview}>{preview(said(fix))}</span>
                            </>
                          ) : (
                            <span className={styles.fixText}>
                              <span className='kel-strong'>{fix.id}</span>
                              <span className={styles.preview}>{`“${preview(said(fix))}”`}</span>
                            </span>
                          )}
                          {isMobile && (
                            <span className='kel-meta'>
                              {STATUS_COPY[fix.status]} · {fix.route || 'screen not recorded'} ·{' '}
                              {formatWhen(fix.created)}
                            </span>
                          )}
                        </button>
                        {!isMobile && (
                          <>
                            <span className={styles.surface}>
                              {fix.page_title || fix.route || 'Screen not recorded'}
                            </span>
                            <div className={styles.rowActions}>
                              {['OPEN', 'BATCHED'].includes(fix.status) &&
                                !fix.work &&
                                (fix.transcript.trim() ? (
                                  <KelButton variant='primary' disabled={busy} onClick={() => void sendToKel(fix)}>
                                    Send to Kel
                                  </KelButton>
                                ) : (
                                  <KelButton variant='quiet' onClick={() => setSelectedId(fix.id)}>
                                    Add note
                                  </KelButton>
                                ))}
                              {fix.status !== 'DISMISSED' && (
                                <KelButton variant='quiet' disabled={busy} onClick={() => void act(fix, 'DISMISSED')}>
                                  Dismiss
                                </KelButton>
                              )}
                              {fix.status !== 'FIXED' && (
                                <button
                                  type='button'
                                  className={styles.markFixed}
                                  disabled={busy}
                                  onClick={() => void act(fix, 'FIXED')}
                                >
                                  ✓ Mark fixed
                                </button>
                              )}
                              {fix.status !== 'OPEN' && (
                                <KelButton variant='quiet' disabled={busy} onClick={() => void act(fix, 'OPEN')}>
                                  Reopen
                                </KelButton>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                      {fix.id === selectedId && (
                        <div className={styles.detail} data-testid={`fix-detail-${fix.id}`}>
                          <div className={isMobile ? styles.mobileContents : styles.detailText}>
                            {!isMobile && <p className='kel-meta'>What you said</p>}
                            <p className={styles.transcript}>{said(fix)}</p>
                            {!fix.transcript.trim() && !fix.work && (
                              <div className={styles.noteEditor}>
                                <label htmlFor={`note-${fix.id}`}>What went wrong?</label>
                                <textarea
                                  id={`note-${fix.id}`}
                                  className={styles.prompt}
                                  rows={3}
                                  value={draftNotes[fix.id] ?? ''}
                                  onChange={(event) =>
                                    setDraftNotes((old) => ({ ...old, [fix.id]: event.target.value }))
                                  }
                                />
                                <KelButton
                                  variant='primary'
                                  disabled={busy || !draftNotes[fix.id]?.trim()}
                                  onClick={() => void addNote(fix)}
                                >
                                  Save note
                                </KelButton>
                              </div>
                            )}
                            {voiceOf(fix) === 'partial' && (
                              <p className='kel-meta'>Only part of the voice note came through.</p>
                            )}
                            {!isMobile && (
                              <p className='kel-meta'>
                                {formatWhen(fix.created)} · {fix.route || 'Screen not recorded'}
                              </p>
                            )}
                            <p className='kel-meta'>{detailLine(fix)}</p>
                          </div>
                          {fix.has_screenshot && image && fix.element?.rect && fix.window?.width ? (
                            <ScreenshotWithTarget
                              src={image}
                              rect={fix.element.rect}
                              contentWidth={fix.window.width}
                              label={`The Kel screen where ${fix.id} was captured`}
                            />
                          ) : (
                            <p className='kel-meta'>
                              {fix.has_screenshot
                                ? 'The screenshot could not be shown on this surface.'
                                : 'No screenshot was saved for this fix.'}
                            </p>
                          )}
                          {isMobile && (
                            <div className='kel-row'>
                              {['OPEN', 'BATCHED'].includes(fix.status) && !fix.work && fix.transcript.trim() && (
                                <KelButton variant='primary' disabled={busy} onClick={() => void sendToKel(fix)}>
                                  Send to Kel
                                </KelButton>
                              )}
                              {fix.status !== 'FIXED' && (
                                <KelButton variant='secondary' disabled={busy} onClick={() => void act(fix, 'FIXED')}>
                                  Mark Fixed
                                </KelButton>
                              )}
                              {fix.status !== 'DISMISSED' && (
                                <KelButton variant='quiet' disabled={busy} onClick={() => void act(fix, 'DISMISSED')}>
                                  Dismiss
                                </KelButton>
                              )}
                              {fix.status !== 'OPEN' && (
                                <KelButton variant='quiet' disabled={busy} onClick={() => void act(fix, 'OPEN')}>
                                  Reopen
                                </KelButton>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}

        {note && (
          <p className='kel-meta' data-testid='dogfood-note'>
            {note}
          </p>
        )}
      </div>
    </div>
  );
};

/** What the person-facing list shows when the voice note did not come through (FIX-0019). */
const NO_WORDS = 'No words came through — the screenshot and the spot you clicked were saved.';
const WORK_COPY: Record<string, string> = {
  PLANNING: 'Planning',
  DISPATCHED: 'Starting work',
  RUNNING: 'Working',
  READY: 'Ready',
  VERIFYING: 'Checking',
  COMPLETED: 'Work finished',
  DONE: 'Work finished',
  FAILED: 'Failed',
  NEEDS_YOU: 'Needs you',
  INTERRUPTED: 'Interrupted',
  PAUSED: 'Paused',
  QUEUED: 'Waiting',
  PASSED: 'Passed',
  PASS: 'Passed',
  ACCEPTED: 'Accepted',
  BLOCKED: 'Blocked',
  PENDING: 'Waiting',
  VERIFIED: 'Verified',
  UNVERIFIED: 'Not verified',
  NEEDS_HUMAN: 'Needs you',
  build: 'Build',
  verify: 'Review',
  review: 'Review',
  test: 'Tests',
  discover: 'Discovery',
  architect: 'Plan',
  started: 'Started',
  completed: 'Finished',
};
const workLabel = (value: string): string =>
  WORK_COPY[value] ??
  String(value || 'Waiting')
    .replace(/_/g, ' ')
    .toLowerCase();
const voiceOf = (fix: KelFix): unknown => fix.diagnostics?.voice;
const said = (fix: KelFix): string => (String(fix.transcript || '').trim() ? fix.transcript : NO_WORDS);

const preview = (text: string): string => {
  const collapsed = String(text || '')
    .replace(/\s+/g, ' ')
    .trim();
  return collapsed.length > 110 ? `${collapsed.slice(0, 109).trimEnd()}…` : collapsed;
};

/** The person-facing facts of a fix. Internal ids stay out of this line on purpose. */
const detailLine = (fix: KelFix): string => {
  const bits: string[] = [];
  if (fix.element?.tag) bits.push(`<${fix.element.tag}>`);
  if (fix.element?.text) bits.push(`“${fix.element.text}”`);
  else if (fix.element?.label) bits.push(`“${fix.element.label}”`);
  if (fix.version) bits.push(`Kel ${fix.version}`);
  if (fix.project_id) bits.push('in a project');
  if (fix.conversation) bits.push('from a conversation');
  if (fix.window?.width) bits.push(`${fix.window.width}×${fix.window.height} window`);
  return bits.join(' · ');
};

/**
 * The saved screenshot with the selected target outlined — drawn here, never baked into the PNG, so
 * a person can always see what the note was about and later tooling can render it its own way.
 */
const ScreenshotWithTarget: React.FC<{
  src: string;
  rect: { x: number; y: number; width: number; height: number };
  contentWidth: number;
  label: string;
}> = ({ src, rect, contentWidth, label }) => {
  const imageRef = React.useRef<HTMLImageElement | null>(null);
  const [scale, setScale] = useState(1);
  const measure = useCallback(() => {
    const element = imageRef.current;
    if (element && element.clientWidth > 0 && contentWidth > 0) {
      setScale(element.clientWidth / contentWidth);
    }
  }, [contentWidth]);
  useEffect(() => {
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [measure]);
  return (
    <figure className={styles.shotWrap}>
      <img ref={imageRef} className={styles.shot} src={src} alt={label} onLoad={measure} />
      <span
        className={styles.shotTarget}
        style={{
          left: Math.round(rect.x * scale),
          top: Math.round(rect.y * scale),
          width: Math.round(rect.width * scale),
          height: Math.round(rect.height * scale),
        }}
        aria-hidden='true'
        data-testid='fix-shot-target'
      />
    </figure>
  );
};

export default DogfoodFixes;
