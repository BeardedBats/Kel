import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
/**
 * Kel V1.4 Projects workspace — Knowledge (memory) · Map · Recipes.
 * Reads `/api/work`; actions go through `/api/memory` and `/api/map`.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelLoading,
  KelSection,
  KelTable,
  formatWhen,
} from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import {
  kelMapAction,
  kelMemoryAction,
  kelRecipeHistory,
  kelRecipeLastResult,
  kelRecipePreview,
  kelRecipeRun,
  kelWork,
  type KelRecipeRun,
  type KelWork,
} from '@renderer/components/kel/kelApi';

type View = 'knowledge' | 'map' | 'recipes';

const viewFromPath = (path: string): View => {
  if (path.startsWith('/projects/map')) return 'map';
  if (path.startsWith('/projects/recipes')) return 'recipes';
  return 'knowledge';
};

export default function KelProjectsPage() {
  const { pathname } = useLocation();
  const [work, setWork] = useState<KelWork | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [runs, setRuns] = useState<{ recipe: string; sentence: string; items: KelRecipeRun[] } | null>(null);
  const navigate = useNavigate();
  const [preview, setPreview] = useState<{ recipe: string; payload: Record<string, unknown> } | null>(
    null
  );

  const load = useCallback(async () => {
    try {
      setWork(await kelWork('main'));
      setError(null);
    } catch (err) {
      setWork(null);
      setError(err);
    }
  }, []);

  // V2-07 follow-through: a run is only useful if its result can be reopened. The engine already
  // keeps every run as a job; this reads them back (history + the one-line last result) and offers
  // the run's own page. Toggle: opening the same recipe again closes the panel.
  const openRuns = useCallback(
    async (recipeId: string) => {
      if (runs?.recipe === recipeId) {
        setRuns(null);
        return;
      }
      setRuns({ recipe: recipeId, sentence: '', items: [] });
      try {
        const history = await kelRecipeHistory(recipeId);
        const last = await kelRecipeLastResult(recipeId).catch((): null => null);
        setRuns({ recipe: recipeId, sentence: last?.sentence ?? '', items: history.history ?? [] });
      } catch (err) {
        setRuns(null);
        setNote(
          `Could not read that recipe's runs. ${failureSentence(err, 'The engine did not answer — try again.')}`
        );
      }
    },
    [runs?.recipe]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const act = useCallback(
    async (label: string, fn: () => Promise<unknown>) => {
      setBusy(label);
      setNote(null);
      try {
        await fn();
        setNote(`${label} recorded.`);
        await load();
      } catch (err) {
        setNote(`${label} failed. ${failureSentence(err, 'The engine did not answer — try again.')}`);
      } finally {
        setBusy(null);
      }
    },
    [load]
  );

  useEffect(() => {
    if (work && ['/projects/map', '/projects/recipes'].includes(pathname)) document.getElementById(`project-${viewFromPath(pathname)}`)?.scrollIntoView({ block: 'start' });
  }, [pathname, work]);

  const records = work?.memory.records ?? [];
  const proposals = work?.memory.proposals ?? [];
  const conflicts = work?.memory.conflicts ?? [];
  const sections = work?.map?.sections ?? [];
  const entries = work?.recipes.entries ?? [];

  return (
    <div className="kel-scope">
      <a className="kel-skip" href="#kel-projects-main">
        Skip to main content
      </a>
      <main className="kel-page" id="kel-projects-main" tabIndex={-1}>
        <div className="kel-page__head">
          <div>
            <ShellWorkspaceLink /><h1 className="kel-h1">Projects</h1>
          </div>
          <span className="kel-grow" />
          <KelButton variant="secondary" disabled={proposals.length === 0} onClick={() => document.getElementById('project-suggestions')?.scrollIntoView({ block: 'center' })}>
            Kel suggests
          </KelButton>
        </div>

        {note && <p className="kel-meta">{note}</p>}
        {error && <KelFailureCard error={error} onRetry={() => void load()} />}
        {!error && !work && <KelLoading rows={4} />}

        {!error && work && (
          <>
            <KelCard id="project-knowledge" title="Knowledge">
              {records.length === 0 ? (
                <KelEmpty
                  title="No saved knowledge in this project yet."
                  why="Kel records what it learns while working — with its source and a trust score."
                />
              ) : (
                <KelTable
                  head={['Topic', 'Type', 'Trust', 'Status', 'Source', 'Updated', 'Actions']}
                  rows={records.map((record) => [
                    <span className="kel-strong" key={`${record.id}-topic`}>
                      {record.topic || record.summary.slice(0, 40)}
                    </span>,
                    <span className="kel-meta" key={`${record.id}-type`}>
                      {record.type}
                    </span>,
                    <span key={`${record.id}-trust`}>
                      {`${record.trust}/10`}
                      {record.user_confirmed ? ' · confirmed' : ''}
                    </span>,
                    <span className="kel-meta" key={`${record.id}-status`}>
                      {record.status}
                    </span>,
                    <span className="kel-meta" key={`${record.id}-source`}>
                      {record.source_type ? `${record.source_type}: ${String(record.source_ref).slice(0, 28)}` : '—'}
                    </span>,
                    <span className="kel-meta" key={`${record.id}-updated`}>
                      {formatWhen(record.updated)}
                    </span>,
                    <span className="kel-row" key={`${record.id}-actions`}>
                      <KelButton
                        variant="quiet"
                        disabled={busy !== null}
                        onClick={() => void act('Confirm', () => kelMemoryAction('confirm', record.id))}
                      >
                        Confirm
                      </KelButton>
                      <KelButton
                        variant="quiet"
                        disabled={busy !== null}
                        onClick={() =>
                          void act('Retract', () =>
                            kelMemoryAction('retract', record.id, { reason: 'retracted from the Knowledge panel' })
                          )
                        }
                      >
                        Retract
                      </KelButton>
                      <KelButton
                        variant="quiet"
                        disabled={busy !== null}
                        onClick={() => void act('Forget', () => kelMemoryAction('forget', record.id))}
                      >
                        Forget
                      </KelButton>
                    </span>,
                  ])}
                />
              )}
            </KelCard>
            {proposals.length > 0 && (
              <KelCard
                id="project-suggestions" title="Kel suggests"
                chip={
                  <span className="kel-meta">
                    {proposals.length === 1
                      ? 'one waiting for you'
                      : `${proposals.length} waiting for you`}
                  </span>
                }
              >
                <p className="kel-sub">
                  Kel only changes what it knows when you agree — nothing here applies by itself.
                </p>
                {proposals.slice(0, 5).map((proposal) => (
                  <div className="kel-row" key={proposal.id} style={{ alignItems: 'flex-start' }}>
                    <div className="kel-attention__text">
                      <strong>{proposal.summary || proposal.topic || 'A change Kel noticed'}</strong>
                      {proposal.why && <span className="kel-meta">Why: {proposal.why}</span>}
                    </div>
                    <span className="kel-grow" />
                    <KelButton
                      variant="secondary"
                      disabled={busy !== null}
                      onClick={() =>
                        void act('Accepted', () => kelMemoryAction('accept_proposal', proposal.id))
                      }
                    >
                      Use this
                    </KelButton>
                    <KelButton
                      variant="quiet"
                      disabled={busy !== null}
                      onClick={() =>
                        void act('Deferred', () => kelMemoryAction('defer_proposal', proposal.id))
                      }
                    >
                      Not now
                    </KelButton>
                    <KelButton
                      variant="quiet"
                      disabled={busy !== null}
                      onClick={() =>
                        void act('Rejected', () =>
                          kelMemoryAction('reject_proposal', proposal.id, {
                            reason: 'set aside from the Knowledge panel',
                          })
                        )
                      }
                    >
                      No thanks
                    </KelButton>
                  </div>
                ))}
                {proposals.length > 5 && (
                  <p className="kel-meta">
                    {`${proposals.length - 5} more waiting — clearing these first keeps it simple.`}
                  </p>
                )}
              </KelCard>
            )}
            {conflicts.length > 0 && <KelSection title="Conflicts">
              {conflicts.length === 0 ? (
                <p className="kel-meta">No conflicting knowledge for this project.</p>
              ) : (
                <pre className="kel-code">{JSON.stringify(conflicts.slice(0, 4), null, 2)}</pre>
              )}
            </KelSection>}
          </>
        )}

        {!error && work && (
          <KelCard
            id="project-map"
            title={`Project map${work.map ? ` · v${work.map.version}` : ''}`}
            actions={
              work.map ? (
                <KelButton variant="secondary" disabled={busy !== null} onClick={() => void act('Refresh map', () => kelMapAction('refresh'))}>
                  Refresh map
                </KelButton>
              ) : undefined
            }
          >
            {!work.map ? (
              <KelEmpty
                title="No map built yet."
                why="Kel builds a map of the project from its own verified work."
                actionLabel="Refresh map"
                onAction={() => void act('Refresh map', () => kelMapAction('refresh'))}
              />
            ) : (
              <KelTable
                head={['Section', 'Trust', 'Freshness', 'Digest', 'Sources']}
                rows={sections.map((section) => [
                  <span className="kel-strong" key={`${section.name}-name`}>
                    {section.name}
                  </span>,
                  <span key={`${section.name}-trust`}>{section.trust}</span>,
                  <span key={`${section.name}-fresh`}>{section.stale ? 'stale — refresh' : 'fresh'}</span>,
                  <span className="kel-code" key={`${section.name}-digest`}>
                    {String(section.digest).slice(0, 10)}
                  </span>,
                  <span className="kel-meta" key={`${section.name}-sources`}>
                    {section.sources.slice(0, 2).join(', ') || '—'}
                  </span>,
                ])}
              />
            )}
          </KelCard>
        )}

        {!error && work && (
          <KelCard id="project-recipes" title="Recipes">
            {entries.length === 0 ? (
              <KelEmpty
                title="No recipes in this project yet."
                why="Recipes capture a workflow Kel finished and verified, so it can run again with your approval."
              />
            ) : (
              <KelTable
                head={['Recipe', 'Steps', 'Inputs', 'Source', 'Dry run']}
                rows={entries.map((entry) => {
                  const recipeId = String(entry.recipe_id ?? entry.id ?? '');
                  return [
                    <span className="kel-strong" key={`${recipeId}-name`}>
                      {entry.name ?? entry.title ?? recipeId}
                    </span>,
                    <span className="kel-meta" key={`${recipeId}-steps`}>
                      {Array.isArray(entry.steps) ? entry.steps.length : '—'}
                    </span>,
                    <span className="kel-meta" key={`${recipeId}-inputs`}>
                      {Array.isArray(entry.inputs) ? entry.inputs.length : '—'}
                    </span>,
                    <span className="kel-meta" key={`${recipeId}-source`}>
                      {entry.source ?? 'project'}
                    </span>,
                    <KelButton
                      key={`${recipeId}-preview`}
                      variant="quiet"
                      disabled={busy !== null || !recipeId}
                      onClick={() =>
                        void act('Preview', async () => {
                          const payload = await kelRecipePreview(recipeId);
                          setPreview({ recipe: recipeId, payload });
                        })
                      }
                    >
                      Preview (dry run)
                    </KelButton>,
                    <KelButton
                      key={`${recipeId}-run`}
                      variant="secondary"
                      disabled={busy !== null || !recipeId}
                      onClick={() => {
                        setBusy(`Run ${recipeId}`);
                        setNote(null);
                        void (async () => {
                          try {
                            const out = await kelRecipeRun(recipeId);
                            setNote(
                              `Run submitted — follow it on the Work page (${String(out.submission).slice(0, 8)}).`
                            );
                            await load();
                          } catch (err) {
                            setNote(
                              `Run failed. ${failureSentence(err, 'The engine did not answer — try again.')}`
                            );
                          } finally {
                            setBusy(null);
                          }
                        })();
                      }}
                    >
                      Run
                    </KelButton>,
                    <KelButton
                      key={`${recipeId}-runs`}
                      variant="quiet"
                      disabled={!recipeId}
                      onClick={() => void openRuns(recipeId)}
                    >
                      {runs?.recipe === recipeId ? 'Hide runs' : 'Runs'}
                    </KelButton>,
                  ];
                })}
              />
            )}
            {runs && (
              <KelSection title={`Runs — ${runs.recipe}`}>
                {runs.sentence && <p className="kel-sub">{runs.sentence}</p>}
                {runs.items.length === 0 ? (
                  <p className="kel-meta">This recipe has not run in this project yet.</p>
                ) : (
                  <ul className="kel-meta">
                    {runs.items.map((run) => (
                      <li key={run.job_id}>
                        <span className="kel-strong">{run.job_id.slice(0, 8)}</span>{' '}
                        {`${run.state ?? 'queued'}${run.verdict ? ` · ${run.verdict}` : ''}`}{' '}
                        <KelButton variant="quiet" onClick={() => navigate('/work')}>
                          Open on Work
                        </KelButton>
                      </li>
                    ))}
                  </ul>
                )}
              </KelSection>
            )}
            {preview && (
              <KelSection title={`Dry run — ${preview.recipe}`}>
                <p className="kel-sub">
                  Compiled without running anything: this is what the recipe would do, including the
                  inputs it needs and the permissions it would ask for.
                </p>
                <pre className="kel-code">{JSON.stringify(preview.payload, null, 2).slice(0, 4000)}</pre>
              </KelSection>
            )}
          </KelCard>
        )}
      </main>
    </div>
  );
}
