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
  KelErrorState,
  KelLoading,
  KelSection,
  KelTable,
  KelTabs,
  formatWhen,
} from '@renderer/components/kel/KelPrimitives';
import { kelMapAction, kelMemoryAction, kelRecipePreview, kelWork, type KelWork } from '@renderer/components/kel/kelApi';

type View = 'knowledge' | 'map' | 'recipes';

const viewFromPath = (path: string): View => {
  if (path.startsWith('/projects/map')) return 'map';
  if (path.startsWith('/projects/recipes')) return 'recipes';
  return 'knowledge';
};

export default function KelProjectsPage() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [view, setView] = useState<View>(viewFromPath(pathname));
  useEffect(() => {
    setView(viewFromPath(pathname));
  }, [pathname]);

  const [work, setWork] = useState<KelWork | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ recipe: string; payload: Record<string, unknown> } | null>(
    null
  );

  const load = useCallback(async () => {
    try {
      setWork(await kelWork('main'));
      setError(null);
    } catch (err) {
      setWork(null);
      setError(err instanceof Error ? err.message : 'The engine did not answer.');
    }
  }, []);

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
        setNote(`${label} failed: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setBusy(null);
      }
    },
    [load]
  );

  const records = work?.memory.records ?? [];
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
            <h1 className="kel-h1">Projects</h1>
            <p className="kel-sub">
              {work
                ? `${work.project_id} · ${records.length} knowledge records · map ${work.map ? 'v' + work.map.version : '—'} · ${entries.length} recipes`
                : 'Loading project context…'}
            </p>
          </div>
          <span className="kel-grow" />
          <KelButton variant="secondary" onClick={() => void load()}>
            Reload
          </KelButton>
        </div>

        <KelTabs
          tabs={[
            { id: 'knowledge', label: 'Knowledge' },
            { id: 'map', label: 'Map' },
            { id: 'recipes', label: 'Recipes' },
          ]}
          active={view}
          onSelect={(id) => {
            setView(id as View);
            navigate('/projects/' + id);
          }}
        />

        {note && <p className="kel-meta">{note}</p>}
        {error && (
          <KelErrorState
            title="Project context could not be loaded"
            cause={error}
            fix="Check that the Kel engine is running, then press Reload."
          />
        )}
        {!error && !work && <KelLoading rows={4} />}

        {!error && work && view === 'knowledge' && (
          <>
            <KelCard title="Knowledge">
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
            <KelSection title="Conflicts">
              {conflicts.length === 0 ? (
                <p className="kel-meta">No conflicting knowledge for this project.</p>
              ) : (
                <pre className="kel-code">{JSON.stringify(conflicts.slice(0, 4), null, 2)}</pre>
              )}
            </KelSection>
          </>
        )}

        {!error && work && view === 'map' && (
          <KelCard
            title={`Project map${work.map ? ` · v${work.map.version}` : ''}`}
            actions={
              <KelButton variant="secondary" disabled={busy !== null} onClick={() => void act('Refresh map', () => kelMapAction('refresh'))}>
                Refresh map
              </KelButton>
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

        {!error && work && view === 'recipes' && (
          <KelCard title="Recipes">
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
                  ];
                })}
              />
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
