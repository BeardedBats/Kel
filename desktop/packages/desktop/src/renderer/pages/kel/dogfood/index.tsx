/**
 * Dogfood Fixes (V2.0 preflight) — the place Nick reviews what Fix Capture recorded.
 *
 * Deliberately small: four statuses, no assignees, no comments, no boards. The point of the view is
 * (a) to remember, so nothing said while using Kel is lost, and (b) to hand the open set to a coding
 * session as one structured prompt.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Message } from '@arco-design/web-react';
import { useNavigate } from 'react-router-dom';
import { KelButton, KelCard, KelEmpty, KelLoading, KelTabs, formatWhen } from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { kelDogfood, type KelBuildCandidate, type KelBuildMission, type KelFix, type KelFixList, type KelFixStatus } from '@renderer/components/kel/kelApi';
import styles from './index.module.css';

const STATUS_COPY: Record<KelFixStatus, string> = {
  OPEN: 'Open',
  BATCHED: 'Batched',
  FIXED: 'Fixed',
  DISMISSED: 'Dismissed',
};

const STATUS_ORDER: KelFixStatus[] = ['OPEN', 'BATCHED', 'FIXED', 'DISMISSED'];

const DogfoodFixes: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<KelFixList | null>(null);
  const [tab, setTab] = useState<KelFixStatus>('OPEN');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [note, setNote] = useState<string | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [prompt, setPrompt] = useState<{ text: string; path: string; ids: string[] } | null>(null);
  // Kibble Build Update (D-46/D-47): the selected findings become a development mission whose
  // candidate is reviewed on this page. None of it changes a Fix Capture status, and installing is
  // deliberately not offered here.
  const [sourceRoot, setSourceRoot] = useState('');
  const [mission, setMission] = useState<string | null>(null);
  const [buildState, setBuildState] = useState<{
    mission: KelBuildMission;
    job: {
      id: string;
      state?: string;
      verdict?: string;
      milestones?: Record<string, { state?: string; attempts?: number }>;
    } | null;
    candidate: KelBuildCandidate | null;
  } | null>(null);
  const [reviewNote, setReviewNote] = useState('');

  const load = useCallback(async () => {
    try {
      const result = await kelDogfood.list();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const fixes = useMemo(() => data?.fixes ?? [], [data]);
  const openFixes = useMemo(() => fixes.filter((fix) => fix.status === 'OPEN'), [fixes]);
  const visible = useMemo(
    () => fixes.filter((fix) => fix.status === tab),
    [fixes, tab]
  );
  const selected = useMemo(() => fixes.find((fix) => fix.id === selectedId) ?? null, [fixes, selectedId]);

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

  const included = openFixes.filter((fix) => checked[fix.id]);
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
    label: `${STATUS_COPY[status]} (${data?.counts?.[status] ?? 0})`,
  }));

  if (error && !data) {
    return (
      <div className='kel-scope'>
        <div className='kel-page'>
          <KelFailureCard error={error} onRetry={() => void load()} />
        </div>
      </div>
    );
  }

  const refreshBuild = useCallback(async (missionId: string) => {
    try {
      const state = await kelDogfood.buildUpdate.status(missionId);
      let candidate = state.candidate;
      if ((state.job?.state ?? '') === 'CLOSED') {
        const assembled = await kelDogfood.buildUpdate.candidate(missionId);
        candidate = assembled.candidate ?? candidate;
      }
      setBuildState({ mission: state.mission, job: state.job, candidate });
    } catch (err) {
      setError(err);
    }
  }, []);

  const startBuildUpdate = useCallback(async () => {
    if (!included.length || !sourceRoot.trim()) return;
    setBusy(true);
    setNote(null);
    try {
      const started = await kelDogfood.buildUpdate.start(
        included.map((fix) => fix.id),
        sourceRoot.trim()
      );
      setMission(started.mission.id);
      setBuildState({ mission: started.mission, job: { id: started.job }, candidate: null });
      setNote(
        `Development mission started for ${included.length} finding(s). Fix Capture statuses were not changed.`
      );
    } catch (err) {
      Message.error('Kel could not start a development mission just now. Try again.');
      setError(err);
    } finally {
      setBusy(false);
    }
  }, [included, sourceRoot]);

  const reviewCandidate = useCallback(
    async (decision: 'approve' | 'reject') => {
      const candidateId = buildState?.candidate?.id;
      if (!candidateId) return;
      setBusy(true);
      setNote(null);
      try {
        const reviewed = await kelDogfood.buildUpdate.review(candidateId, decision, reviewNote);
        setBuildState((previous) => (previous ? { ...previous, candidate: reviewed } : previous));
        setNote(
          decision === 'approve'
            ? 'Candidate approved. Nothing was installed.'
            : 'Candidate rejected. Nothing was installed.'
        );
      } catch (err) {
        Message.error('Kel could not record that review just now. Try again.');
        setError(err);
      } finally {
        setBusy(false);
      }
    },
    [buildState?.candidate?.id, reviewNote]
  );

  return (
    <div className='kel-scope'>
      <a className='kel-skip' href='#kel-dogfood-main'>
        Skip to main content
      </a>
      <div className='kel-page'>
        <header className='kel-page__head'>
          <div><h1 className='kel-h1'>Kibble</h1>
          <p className='kel-sub'>
            What Ctrl+Shift+F captured while you were using Kel. Everything stays on this computer
            until you deliberately prepare a fix prompt.
          </p></div>
        </header>

        {data === null ? (
          <KelLoading rows={3} />
        ) : (
          <>
            <KelCard
              title='Prepare a fix prompt'
              actions={
                <KelButton
                  variant='primary'
                  disabled={busy || !included.length}
                  onClick={() => void preparePrompt()}
                >
                  {`Prepare Fix Prompt (${included.length})`}
                </KelButton>
              }
            >
              <p className='kel-sub'>
                Open fixes are included by default. Preparing a prompt moves them to Batched — it never
                starts development on its own.
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
                          checked={Boolean(checked[fix.id])}
                          onChange={(event) =>
                            setChecked((previous) => ({ ...previous, [fix.id]: event.target.checked }))
                          }
                          data-testid={`fix-pick-${fix.id}`}
                        />
                        <span className='kel-strong'>{fix.id}</span>
                        <span className={styles.preview}>{preview(fix.transcript)}</span>
                        <span className='kel-meta'>{fix.route || 'screen not recorded'}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </KelCard>

            <KelCard
              title='Build Update'
              actions={
                <>
                  <KelButton
                    variant='primary'
                    disabled={busy || !included.length || !sourceRoot.trim()}
                    onClick={() => void startBuildUpdate()}
                  >
                    {`Start update (${included.length})`}
                  </KelButton>
                  {mission && (
                    <KelButton variant='quiet' disabled={busy} onClick={() => void refreshBuild(mission)}>
                      Refresh
                    </KelButton>
                  )}
                </>
              }
            >
              <p className='kel-sub'>
                Kel fixes the selected findings in a copy of this repository and offers the result for
                review. Fix Capture statuses stay exactly as they are, and nothing is installed.
              </p>
              <label className='kel-meta' htmlFor='kel-build-source'>
                Repository folder
              </label>
              <input
                id='kel-build-source'
                className='kel-input'
                value={sourceRoot}
                onChange={(event) => setSourceRoot(event.target.value)}
                placeholder='C:\\path\\to\\the\\repository'
                data-testid='build-source-root'
              />
              {!buildState && (
                <p className='kel-meta'>Pick the findings above, name the repository folder, then start.</p>
              )}
              {buildState && (
                <div className={styles.buildState}>
                  <p className='kel-strong'>{`Mission ${buildState.mission.id.slice(0, 8)} · ${buildState.mission.state ?? 'OPEN'}`}</p>
                  {buildState.job && (
                    <p className='kel-meta'>{`Job ${buildState.job.id.slice(0, 8)} · ${buildState.job.state ?? 'queued'}${buildState.job.verdict ? ` · ${buildState.job.verdict}` : ''}`}</p>
                  )}
                  {buildState.job?.milestones && (
                    <ul className={styles.buildList}>
                      {Object.entries(buildState.job.milestones).map(([milestoneId, milestone]) => (
                        <li key={milestoneId} className='kel-meta'>
                          {`${milestoneId}: ${milestone?.state ?? 'queued'}${milestone?.attempts ? ` · ${milestone.attempts} attempt(s)` : ''}`}
                        </li>
                      ))}
                    </ul>
                  )}
                  {buildState.candidate ? (
                    <>
                      <p className='kel-strong'>{`Candidate ${buildState.candidate.id.slice(0, 8)} · ${buildState.candidate.review_state ?? 'BUILDING'}`}</p>
                      <p className='kel-meta'>
                        {`verified: ${buildState.candidate.verified === true || buildState.candidate.verified === 1 ? 'yes' : 'no'} · revision ${String(buildState.candidate.revision ?? '—').slice(0, 12)}`}
                      </p>
                      {buildState.candidate.artifact && (
                        <p className='kel-meta'>{`evidence: ${buildState.candidate.artifact}`}</p>
                      )}
                      {Boolean(buildState.candidate.fixed_findings?.length) && (
                        <p className='kel-meta'>{`fixed: ${(buildState.candidate.fixed_findings ?? []).join(', ')}`}</p>
                      )}
                      {Boolean(buildState.candidate.unresolved_findings?.length) && (
                        <p className='kel-meta'>{`unresolved: ${(buildState.candidate.unresolved_findings ?? []).join(', ')}`}</p>
                      )}
                      {Boolean(buildState.candidate.limitations?.length) && (
                        <ul className={styles.buildList}>
                          {(buildState.candidate.limitations ?? []).map((line, index) => (
                            <li key={`${index}-${line}`} className='kel-meta'>
                              {line}
                            </li>
                          ))}
                        </ul>
                      )}
                      {(buildState.candidate.review_state ?? '') === 'BUILDING' ? (
                        <p className='kel-meta'>Still building — review it when it is ready.</p>
                      ) : buildState.candidate.review_state === 'APPROVED' ||
                        buildState.candidate.review_state === 'REJECTED' ? (
                        <p className='kel-meta'>{`Reviewed: ${buildState.candidate.review_state.toLowerCase()}.`}</p>
                      ) : (
                        <>
                          <input
                            className='kel-input'
                            value={reviewNote}
                            onChange={(event) => setReviewNote(event.target.value)}
                            placeholder='A note for this review (optional)'
                            data-testid='build-review-note'
                          />
                          <KelButton
                            variant='primary'
                            disabled={busy}
                            onClick={() => void reviewCandidate('approve')}
                          >
                            Approve candidate
                          </KelButton>
                          <KelButton
                            variant='quiet'
                            disabled={busy}
                            onClick={() => void reviewCandidate('reject')}
                          >
                            Reject
                          </KelButton>
                        </>
                      )}
                    </>
                  ) : (
                    <p className='kel-meta'>No candidate yet — one appears when the mission settles.</p>
                  )}
                </div>
              )}
              {note && <p className='kel-meta' role='status'>{note}</p>}
            </KelCard>

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
                  Saved as <span className='kel-code'>{prompt.path}</span> — hand it to a coding session
                  whenever you are ready.
                </p>
                <textarea
                  className={styles.prompt}
                  value={prompt.text}
                  readOnly
                  rows={14}
                  data-testid='fix-prompt'
                />
              </KelCard>
            )}

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
                    <button
                      type='button'
                      className={styles.itemButton}
                      aria-expanded={fix.id === selectedId}
                      onClick={() => setSelectedId(fix.id === selectedId ? null : fix.id)}
                    >
                      <span className='kel-strong'>{fix.id}</span>
                      <span className={styles.preview}>{preview(fix.transcript)}</span>
                      <span className='kel-meta'>
                        {STATUS_COPY[fix.status]} · {fix.route || 'screen not recorded'} ·{' '}
                        {formatWhen(fix.created)}
                      </span>
                    </button>
                    {fix.id === selectedId && (
                      <div className={styles.detail} data-testid={`fix-detail-${fix.id}`}>
                        <p className={styles.transcript}>{fix.transcript}</p>
                        <p className='kel-meta'>{detailLine(fix)}</p>
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
                        <div className='kel-row'>
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
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
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

const preview = (text: string): string => {
  const collapsed = String(text || '').replace(/\s+/g, ' ').trim();
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
