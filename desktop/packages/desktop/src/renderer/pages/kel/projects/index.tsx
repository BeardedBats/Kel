import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import mobileMapIcon from '@renderer/assets/figma/refresh/mobile-map.svg';
import mobileRecipeSearchIcon from '@renderer/assets/figma/refresh/mobile-recipe-search.svg';
import mobileRecipeStarActiveIcon from '@renderer/assets/figma/refresh/mobile-recipe-star-active.svg';
import mobileRecipeStarIcon from '@renderer/assets/figma/refresh/mobile-recipe-star.svg';
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
  kelRecipeCategories,
  kelRecipeDuplicate,
  kelRecipeFavourite,
  kelRecipeGet,
  kelRecipeHistory,
  kelRecipeLastResult,
  kelRecipePreview,
  kelRecipeRecent,
  kelRecipeRun,
  kelRecipeSearch,
  kelWork,
  type KelRecipeEntry,
  type KelRecipeInput,
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
  // V2-07 library controls: search, categories, favourites, recent and duplicate — each one goes
  // through the engine's own recipe actions, scoped to this project.
  const [recipeQuery, setRecipeQuery] = useState('');
  const [found, setFound] = useState<KelRecipeEntry[] | null>(null);
  const [categories, setCategories] = useState<Array<{ name: string; count: number }>>([]);
  const [recent, setRecent] = useState<KelRecipeEntry[]>([]);
  const [favouritesOnly, setFavouritesOnly] = useState(false);
  const [mobileRecipeTab, setMobileRecipeTab] = useState('All');
  const [desktopRecipeTab, setDesktopRecipeTab] = useState('All');
  const [showRecipeTools, setShowRecipeTools] = useState(false);
  const [mobileRecipeDetail, setMobileRecipeDetail] = useState<{
    id: string; steps: Array<{ id: string; title: string }>; lastResult: string;
    history: KelRecipeRun[]; loading: boolean;
  } | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [runs, setRuns] = useState<{ recipe: string; sentence: string; items: KelRecipeRun[] } | null>(null);
  const navigate = useNavigate();
  const [preview, setPreview] = useState<{ recipe: string; payload: Record<string, unknown> } | null>(
    null
  );
  const [runDraft, setRunDraft] = useState<{
    recipeId: string;
    name: string;
    inputs: KelRecipeInput[];
    values: Record<string, string | boolean>;
  } | null>(null);

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

  // The library's shelves are read once per visit: the categories it carries and what was used
  // recently. A failure here leaves the plain list in place rather than an error page.
  useEffect(() => {
    void (async () => {
      const [cats, recents] = await Promise.all([
        kelRecipeCategories().catch((): { categories: Array<{ name: string; count: number }> } => ({ categories: [] })),
        kelRecipeRecent().catch((): { recent: KelRecipeEntry[] } => ({ recent: [] })),
      ]);
      setCategories(cats.categories ?? []);
      setRecent(recents.recent ?? []);
    })();
  }, []);

  const searchRecipes = useCallback(async (value: string) => {
    setRecipeQuery(value);
    if (!value.trim()) {
      setFound(null);
      return;
    }
    try {
      const result = await kelRecipeSearch(value.trim());
      setFound(result.entries ?? []);
    } catch (err) {
      setFound(null);
      setNote(`Search failed. ${failureSentence(err, 'The engine did not answer — try again.')}`);
    }
  }, []);

  const openMobileRecipe = useCallback(async (recipeId: string) => {
    if (mobileRecipeDetail?.id === recipeId) {
      setMobileRecipeDetail(null);
      return;
    }
    setMobileRecipeDetail({ id: recipeId, steps: [], lastResult: '', history: [], loading: true });
    try {
      const [definition, last, history] = await Promise.all([
        kelRecipeGet(recipeId),
        kelRecipeLastResult(recipeId).catch((): null => null),
        kelRecipeHistory(recipeId).catch(() => ({ history: [] as KelRecipeRun[] })),
      ]);
      setMobileRecipeDetail((current) => current?.id === recipeId ? {
        id: recipeId,
        steps: definition.recipe.steps ?? [],
        lastResult: last?.state === 'never_run' ? '' : last?.sentence ?? '',
        history: history.history ?? [],
        loading: false,
      } : current);
    } catch (err) {
      setMobileRecipeDetail((current) => current?.id === recipeId ? null : current);
      setNote(`Could not open this recipe. ${failureSentence(err, 'The engine did not answer — try again.')}`);
    }
  }, [mobileRecipeDetail?.id]);

  const prepareRecipe = useCallback(async (recipeId: string) => {
    setBusy('Prepare run');
    setNote(null);
    try {
      const { recipe } = await kelRecipeGet(recipeId);
      setRunDraft({
        recipeId,
        name: recipe.name,
        inputs: recipe.inputs ?? [],
        values: Object.fromEntries((recipe.inputs ?? [])
          .filter((input) => input.default !== undefined)
          .map((input) => [input.name, input.default as string | boolean])),
      });
    } catch (err) {
      setNote(`Could not open this recipe. ${failureSentence(err, 'The engine did not answer — try again.')}`);
    } finally {
      setBusy(null);
    }
  }, []);

  const startRecipe = useCallback(async () => {
    if (!runDraft) return;
    const draft = runDraft;
    setBusy('Run recipe');
    setNote(null);
    try {
      const values = Object.fromEntries(Object.entries(draft.values)
        .filter(([, value]) => typeof value === 'boolean' || value.trim() !== ''));
      const dryRun = await kelRecipePreview(draft.recipeId, values);
      if (dryRun.needs_project) {
        setNote(String(dryRun.message ?? 'This recipe needs more project details.'));
        return;
      }
      const out = await kelRecipeRun(draft.recipeId, values);
      setNote(`Run request sent — follow it on Work (${String(out.submission).slice(0, 8)}).`);
      setRunDraft(null);
      await load();
    } catch (err) {
      setNote(`Run failed. ${failureSentence(err, 'The engine did not answer — try again.')}`);
    } finally {
      setBusy(null);
    }
  }, [runDraft, load]);

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
    if (work && pathname === '/projects/map') document.getElementById('project-map')?.scrollIntoView({ block: 'start' });
  }, [pathname, work]);

  useEffect(() => {
    if (runDraft) document.getElementById('recipe-run-draft')?.scrollIntoView({ block: 'nearest' });
  }, [runDraft?.recipeId]);

  const records = work?.memory.records ?? [];
  const proposals = work?.memory.proposals ?? [];
  const conflicts = work?.memory.conflicts ?? [];
  const sections = work?.map?.sections ?? [];
  const entries = work?.recipes.entries ?? [];
  const listed = (found ?? entries).filter((entry) => !favouritesOnly || entry.favourite);
  const mobileListed = (found ?? entries).filter((entry) => mobileRecipeTab === 'All'
    || (mobileRecipeTab === 'Favourites' ? entry.favourite : entry.category === mobileRecipeTab));
  const desktopListed = (found ?? entries).filter((entry) => desktopRecipeTab === 'All'
    || (desktopRecipeTab === 'Favourites' ? entry.favourite : entry.category === desktopRecipeTab));
  const libraryView = viewFromPath(pathname) === 'recipes';
  const projectRecipes = entries.filter((entry) => entry.source !== 'builtin');

  return (
    <div className="kel-scope">
      <a className="kel-skip" href="#kel-projects-main">
        Skip to main content
      </a>
      <main className={`kel-page${libraryView ? ' kel-shell-recipe-library' : ''}`} id="kel-projects-main" tabIndex={-1}>
        <div className="kel-page__head">
          <div>
            <ShellWorkspaceLink /><h1 className="kel-h1">{libraryView ? 'Recipes' : 'Projects'}</h1>
          </div>
          <span className="kel-grow" />
          {!libraryView && <KelButton variant="secondary" disabled={proposals.length === 0} onClick={() => document.getElementById('project-suggestions')?.scrollIntoView({ block: 'center' })}>
            Kel suggests
          </KelButton>}
        </div>

        {note && <p className="kel-meta">{note}</p>}
        {error && <KelFailureCard error={error} onRetry={() => void load()} />}
        {!error && !work && <KelLoading rows={4} />}

        {!error && work && !libraryView && (
          <>
            <KelCard id="project-knowledge" title="Knowledge">
              {records.length === 0 ? (
                <KelEmpty
                  title="No saved knowledge in this project yet."
                  why="Kel records what it learns while working — with its source and a trust score."
                />
              ) : (
                <div className="kel-project-table-scroll">
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
                </div>
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
                  <div className="kel-row kel-project-suggestion-row" key={proposal.id} style={{ alignItems: 'flex-start' }}>
                    <div className="kel-attention__text">
                      <strong>{proposal.summary || proposal.topic || 'A change Kel noticed'}</strong>
                      {proposal.why && <span className="kel-meta"><span className="kel-project-suggestion-why-prefix">Why: </span>{proposal.why}</span>}
                    </div>
                    <span className="kel-grow" />
                    <KelButton
                      variant="secondary"
                      disabled={busy !== null}
                      onClick={() =>
                        void act('Accepted', () => kelMemoryAction('accept_proposal', proposal.id))
                      }
                    >
                      <span className="kel-project-action-desktop">Use this</span><span className="kel-project-action-mobile">Accept</span>
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
                      <span className="kel-project-action-desktop">No thanks</span><span className="kel-project-action-mobile">Reject</span>
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

        {!error && work && !libraryView && (
          <KelCard
            id="project-map"
            title="Project map"
            actions={
              work.map ? (
                <>
                <span className="kel-project-map-version">v{work.map.version}</span>
                <KelButton variant="secondary" disabled={busy !== null} onClick={() => void act('Refresh map', () => kelMapAction('refresh'))}>
                  <span className="kel-project-action-desktop">Refresh map</span><span className="kel-project-action-mobile">Refresh</span>
                </KelButton>
                </>
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
              <>
              <div className="kel-project-table-scroll kel-project-map-desktop">
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
              </div>
              <div className="kel-project-map-mobile">
                {sections.map((section) => (
                  <div className="kel-project-map-mobile__row" key={section.name}>
                    <span className="kel-project-map-mobile__icon" aria-hidden="true"><img src={mobileMapIcon} alt="" /></span>
                    <span>{section.name.replace(/(^|\s)\S/g, (letter) => letter.toUpperCase())}</span>
                    <span className={section.stale ? 'kel-project-map-mobile__stale' : 'kel-project-map-mobile__fresh'}>
                      {section.stale ? 'Stale' : 'Fresh'}
                    </span>
                  </div>
                ))}
              </div>
              </>
            )}
          </KelCard>
        )}

        {!error && work && (
          <KelCard id="project-recipes" title="Recipes" className={libraryView ? 'kel-recipe-library-card' : undefined}
            actions={libraryView ? <span className="kel-recipe-count">{entries.length} available here</span> : undefined}>
            {!libraryView ? (
              <KelEmpty
                title={projectRecipes.length === 0 ? 'No recipes in this project yet.' : `${projectRecipes.length} recipes in this project.`}
                why="Open Recipes to search, preview, and run a workflow."
              />
            ) : entries.length === 0 ? (
              <KelEmpty
                title="No recipes in this project yet."
                why="Recipes capture a workflow Kel finished and verified, so it can run again with your approval."
              />
            ) : (
              <>
                <div className="kel-recipe-desktop-current">
                  <div className="kel-recipe-desktop-intro">
                    <p>Steps Kel saved from finished work. Run one again any time.</p>
                  </div>
                  <div className="kel-recipe-desktop-controls">
                    <label className="kel-recipe-desktop-search">
                      <img src={mobileRecipeSearchIcon} alt="" width={14} height={14} />
                      <input value={recipeQuery} onChange={(event) => void searchRecipes(event.target.value)}
                        placeholder="Search recipes" aria-label="Search recipes" />
                    </label>
                    <div className="kel-recipe-desktop-tabs" role="tablist" aria-label="Recipe filters">
                      {['All', 'Favourites', ...categories.map((category) => category.name)].map((tab) => (
                        <button key={tab} type="button" role="tab" aria-selected={desktopRecipeTab === tab}
                          onClick={() => setDesktopRecipeTab(tab)}>{tab}</button>
                      ))}
                    </div>
                  </div>
                  {desktopListed.length === 0 ? <KelEmpty title="Nothing matches that." why="Clear search or choose All." /> : desktopListed.map((entry) => {
                    const recipeId = String(entry.recipe_id ?? entry.id ?? '');
                    const expanded = mobileRecipeDetail?.id === recipeId;
                    const preparing = runDraft?.recipeId === recipeId;
                    return <div className="kel-recipe-desktop-entry" key={recipeId}>
                      <div className="kel-recipe-desktop-row">
                        <button type="button" className="kel-recipe-desktop-star" disabled={busy !== null}
                          aria-label={entry.favourite ? 'Remove favourite' : 'Add favourite'}
                          onClick={() => void act(entry.favourite ? 'Unfavourite' : 'Favourite', () => kelRecipeFavourite(recipeId, !entry.favourite))}>
                          <img src={entry.favourite ? mobileRecipeStarActiveIcon : mobileRecipeStarIcon} alt="" width={14} height={14} />
                        </button>
                        <span>{entry.name ?? entry.title ?? recipeId}</span>
                        {(expanded || preparing) ? <button type="button" className="kel-recipe-desktop-link"
                          onClick={() => { setMobileRecipeDetail(null); setRunDraft(null); }}>Close</button> : <>
                          <button type="button" className="kel-recipe-desktop-link"
                            onClick={() => void openMobileRecipe(recipeId)}>Preview</button>
                          <KelButton variant="primary" disabled={busy !== null || !recipeId}
                            onClick={() => void prepareRecipe(recipeId)}>Run</KelButton>
                        </>}
                      </div>
                      {preparing && runDraft && <div className="kel-recipe-desktop-expanded kel-recipe-desktop-run">
                        <p>Check the inputs. Then start the recipe.</p>
                        <div className="kel-recipe-desktop-fields">
                          {runDraft.inputs.map((input) => <label key={input.name}>
                            <span>{input.name}{input.required ? ' *' : ''}</span>
                            {input.type === 'bool' ? <input type="checkbox"
                              checked={runDraft.values[input.name] === true}
                              onChange={(event) => setRunDraft((draft) => draft && ({
                                ...draft, values: { ...draft.values, [input.name]: event.target.checked },
                              }))} /> : input.type === 'choice' ? <select
                                value={String(runDraft.values[input.name] ?? '')}
                                onChange={(event) => setRunDraft((draft) => draft && ({
                                  ...draft, values: { ...draft.values, [input.name]: event.target.value },
                                }))}>
                                <option value="">Choose one</option>
                                {(input.choices ?? []).map((choice) => <option key={choice} value={choice}>{choice}</option>)}
                              </select> : <input type="text" maxLength={input.max_chars}
                                value={String(runDraft.values[input.name] ?? '')}
                                onChange={(event) => setRunDraft((draft) => draft && ({
                                  ...draft, values: { ...draft.values, [input.name]: event.target.value },
                                }))} />}
                          </label>)}
                        </div>
                        <div className="kel-recipe-desktop-expanded-actions">
                          <KelButton variant="primary" disabled={busy !== null} onClick={() => void startRecipe()}>Start recipe</KelButton>
                        </div>
                      </div>}
                      {expanded && !preparing && <div className="kel-recipe-desktop-expanded">
                        <div className="kel-recipe-desktop-expanded-label">What Kel will do</div>
                        {mobileRecipeDetail.loading ? <p>Loading recipe…</p> : <ol>
                          {mobileRecipeDetail.steps.map((step) => <li key={step.id}>{step.title}</li>)}
                        </ol>}
                        {mobileRecipeDetail.history.length > 0 && <div className="kel-recipe-desktop-history">
                          <span>Last runs</span>
                          {mobileRecipeDetail.history.slice(0, 2).map((run) => <div key={run.job_id}>
                            {formatWhen(run.created ?? 0)} <strong>{run.verdict ?? run.state ?? 'Working'}</strong>
                          </div>)}
                        </div>}
                        <div className="kel-recipe-desktop-expanded-actions">
                          {mobileRecipeDetail.history.length > 0 && <button type="button" onClick={() => navigate('/work')}>Open on Work</button>}
                          <button type="button" onClick={() => setShowRecipeTools((previous) => !previous)}>More actions</button>
                          <KelButton variant="primary" disabled={busy !== null || mobileRecipeDetail.loading}
                            onClick={() => void prepareRecipe(recipeId)}>Run</KelButton>
                        </div>
                      </div>}
                    </div>;
                  })}
                </div>
                <div className="kel-recipe-mobile-list">
                  <label className="kel-recipe-mobile-search">
                    <img src={mobileRecipeSearchIcon} alt="" width={14} height={14} />
                    <input
                      value={recipeQuery}
                      onChange={(event) => void searchRecipes(event.target.value)}
                      placeholder="Search recipes"
                      aria-label="Search recipes"
                    />
                  </label>
                  <div className="kel-recipe-mobile-tabs" role="tablist" aria-label="Recipe filters">
                    {['All', 'Favourites', ...categories.map((category) => category.name)].map((tab) => (
                      <button key={tab} type="button" role="tab" aria-selected={mobileRecipeTab === tab}
                        onClick={() => setMobileRecipeTab(tab)}>{tab}</button>
                    ))}
                  </div>
                  {mobileListed.length === 0 ? <KelEmpty title="Nothing matches that." why="Clear the search or choose All." /> : mobileListed.map((entry) => {
                    const recipeId = String(entry.recipe_id ?? entry.id ?? '');
                    const expanded = mobileRecipeDetail?.id === recipeId;
                    return <div className="kel-recipe-mobile-entry" key={recipeId}>
                      {expanded ? <div className="kel-recipe-mobile-preview">
                        <div className="kel-recipe-mobile-row">
                          <button className="kel-recipe-mobile-star" type="button" disabled={busy !== null}
                            aria-label={entry.favourite ? 'Remove favourite' : 'Add favourite'}
                            onClick={() => void act(entry.favourite ? 'Unfavourite' : 'Favourite', () => kelRecipeFavourite(recipeId, !entry.favourite))}>
                            <img src={entry.favourite ? mobileRecipeStarActiveIcon : mobileRecipeStarIcon} alt="" width={14} height={14} />
                          </button>
                          <strong>{entry.name ?? entry.title ?? recipeId}</strong>
                          <button className="kel-recipe-mobile-close" type="button" onClick={() => setMobileRecipeDetail(null)}>Close</button>
                        </div>
                        <div className="kel-recipe-mobile-preview-label">What Kel will do</div>
                        {mobileRecipeDetail.loading ? <p>Loading recipe…</p> : <ol>
                          {mobileRecipeDetail.steps.map((step) => <li key={step.id}>{step.title}</li>)}
                        </ol>}
                        {mobileRecipeDetail.lastResult && <p className="kel-recipe-mobile-last-result">{mobileRecipeDetail.lastResult}</p>}
                        <KelButton variant="primary" disabled={busy !== null || mobileRecipeDetail.loading}
                          onClick={() => void prepareRecipe(recipeId)}>Run</KelButton>
                      </div> : <div className="kel-recipe-mobile-row">
                        <button className="kel-recipe-mobile-star" type="button" disabled={busy !== null}
                          aria-label={entry.favourite ? 'Remove favourite' : 'Add favourite'}
                          onClick={() => void act(entry.favourite ? 'Unfavourite' : 'Favourite', () => kelRecipeFavourite(recipeId, !entry.favourite))}>
                          <img src={entry.favourite ? mobileRecipeStarActiveIcon : mobileRecipeStarIcon} alt="" width={14} height={14} />
                        </button>
                        <button className="kel-recipe-mobile-name" type="button" aria-expanded={false}
                          onClick={() => void openMobileRecipe(recipeId)}>{entry.name ?? entry.title ?? recipeId}</button>
                        <KelButton variant="primary" disabled={busy !== null || !recipeId}
                          onClick={() => void prepareRecipe(recipeId)}>Run</KelButton>
                      </div>}
                    </div>;
                  })}
                </div>
                <div className={`kel-recipe-desktop-list${showRecipeTools ? ' kel-recipe-desktop-list--open' : ''}`}>
                <div className="kel-row" data-testid="recipe-library-controls">
                  <input
                    className="kel-input"
                    value={recipeQuery}
                    onChange={(event) => void searchRecipes(event.target.value)}
                    placeholder="Search recipes"
                    aria-label="Search recipes"
                    data-testid="recipe-search"
                  />
                  <KelButton
                    variant={favouritesOnly ? 'primary' : 'quiet'}
                    onClick={() => setFavouritesOnly((previous) => !previous)}
                  >
                    Favourites
                  </KelButton>
                  {categories.map((category) => (
                    <KelButton
                      key={category.name}
                      variant="quiet"
                      onClick={() => void searchRecipes(category.name)}
                    >
                      {category.name}
                    </KelButton>
                  ))}
                </div>
                {recent.length > 0 && (
                  <p className="kel-meta">
                    {`Recently used: ${recent
                      .map((entry) => String(entry.name ?? entry.recipe_id ?? ''))
                      .filter(Boolean)
                      .join(', ')}`}
                  </p>
                )}
                {listed.length === 0 ? (
                  <KelEmpty
                    title="Nothing matches that."
                    why="Clear the search or the favourites filter to see the whole project library."
                  />
                ) : (
              <KelTable
                head={['Recipe', 'Steps', 'Inputs', 'Source', 'Dry run', 'Run', 'History']}
                rows={listed.map((entry) => {
                  const recipeId = String(entry.recipe_id ?? entry.id ?? '');
                  return [
                    <span className="kel-strong" key={`${recipeId}-name`}>
                      {entry.name ?? entry.title ?? recipeId}{' '}
                      <KelButton
                        variant="quiet"
                        disabled={busy !== null || !recipeId}
                        onClick={() =>
                          void act(entry.favourite ? 'Unfavourite' : 'Favourite', () =>
                            kelRecipeFavourite(recipeId, !entry.favourite)
                          )
                        }
                      >
                        {entry.favourite ? 'Favourited' : 'Favourite'}
                      </KelButton>{' '}
                      <KelButton
                        variant="quiet"
                        disabled={busy !== null || !recipeId}
                        onClick={() => void act('Copy', () => kelRecipeDuplicate(recipeId))}
                      >
                        Copy
                      </KelButton>
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
                      onClick={() => void prepareRecipe(recipeId)}
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
                </div>
              </>
            )}
            {libraryView && runDraft && (
              <div id="recipe-run-draft"><KelSection title={`Run — ${runDraft.name}`}>
                <p className="kel-sub">Review the inputs before Kel starts this recipe.</p>
                {note && <p className="kel-meta" role="status">{note}</p>}
                {runDraft.inputs.map((input) => (
                  <label key={input.name} className="kel-recipe-input">
                    <span className="kel-strong">{input.name}{input.required ? ' *' : ''}</span>
                    {input.description && <span className="kel-meta">{input.description}</span>}
                    {input.type === 'bool' ? (
                      <input
                        type="checkbox"
                        checked={runDraft.values[input.name] === true}
                        onChange={(event) => setRunDraft((draft) => draft && ({
                          ...draft, values: { ...draft.values, [input.name]: event.target.checked },
                        }))}
                      />
                    ) : input.type === 'choice' ? (
                      <select
                        className="kel-input"
                        value={String(runDraft.values[input.name] ?? '')}
                        onChange={(event) => setRunDraft((draft) => draft && ({
                          ...draft, values: { ...draft.values, [input.name]: event.target.value },
                        }))}
                      >
                        <option value="">Choose one</option>
                        {(input.choices ?? []).map((choice) => <option key={choice} value={choice}>{choice}</option>)}
                      </select>
                    ) : (
                      <input
                        className="kel-input"
                        type="text"
                        maxLength={input.max_chars}
                        value={String(runDraft.values[input.name] ?? '')}
                        onChange={(event) => setRunDraft((draft) => draft && ({
                          ...draft, values: { ...draft.values, [input.name]: event.target.value },
                        }))}
                      />
                    )}
                  </label>
                ))}
                <div className="kel-row">
                  <KelButton variant="primary" disabled={busy !== null} onClick={() => void startRecipe()}>Start recipe</KelButton>
                  <KelButton variant="quiet" disabled={busy !== null} onClick={() => setRunDraft(null)}>Cancel</KelButton>
                </div>
              </KelSection></div>
            )}
            {libraryView && runs && (
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
            {libraryView && preview && (
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
