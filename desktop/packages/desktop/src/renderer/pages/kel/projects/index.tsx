import knowledgeClockIcon from '@renderer/assets/figma/refresh/desktop-knowledge-clock.svg';
import knowledgeSparkleIcon from '@renderer/assets/figma/refresh/desktop-knowledge-sparkle.svg';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';
import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import mobileMapIcon from '@renderer/assets/figma/refresh/mobile-map.svg';
import mobileRecipeSearchIcon from '@renderer/assets/figma/refresh/mobile-recipe-search.svg';
import mobileRecipeStarActiveIcon from '@renderer/assets/figma/refresh/mobile-recipe-star-active.svg';
import mobileRecipeStarIcon from '@renderer/assets/figma/refresh/mobile-recipe-star.svg';
/**
 * Kel V1.4 Projects workspace — Knowledge (memory) · Map · Recipes.
 * Reads `/api/work`; actions go through `/api/memory` and `/api/map`.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ALL_PROJECTS, GENERAL_PROJECT_ID, liveProjects, useProjects } from '@renderer/components/kel/activeProject';
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
import { jobRouteFor } from '@renderer/components/kel/needsAttention';
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
  type KelMemoryProposal,
  type KelMemoryRecord,
  type KelProject,
  type KelRecipeEntry,
  type KelRecipeInput,
  type KelRecipeRun,
  type KelScope,
  type KelWork,
} from '@renderer/components/kel/kelApi';

type View = 'knowledge' | 'map' | 'recipes';

type TaggedProposal = KelMemoryProposal & { project_id?: string };

/**
 * D-54 "All projects": one read per live project, merged. Knowledge keeps each record's project so
 * its actions go to that project; built-in recipes appear once, project recipes carry their project.
 */
const mergeProjects = (reads: Array<{ project: KelProject; work: KelWork }>): KelWork => {
  const seenBuiltins = new Set<string>();
  const entries: KelRecipeEntry[] = [];
  for (const { project, work } of reads) {
    for (const entry of work.recipes?.entries ?? []) {
      const id = String(entry.recipe_id ?? entry.id ?? '');
      if (entry.source === 'builtin') {
        if (seenBuiltins.has(id)) continue;
        seenBuiltins.add(id);
        entries.push(entry);
      } else {
        entries.push({ ...entry, project_id: entry.project_id ?? project.id });
      }
    }
  }
  return {
    project_id: ALL_PROJECTS,
    memory: {
      records: reads.flatMap(({ project, work }) =>
        (work.memory?.records ?? []).map((record) => ({ ...record, project_id: record.project_id ?? project.id }))
      ),
      proposals: reads.flatMap(({ project, work }) =>
        (work.memory?.proposals ?? []).map((proposal): TaggedProposal => ({ ...proposal, project_id: project.id }))
      ),
      conflicts: reads.flatMap(({ work }) => work.memory?.conflicts ?? []),
    },
    map: null,
    recipes: { entries },
  };
};

const viewFromPath = (path: string): View => {
  if (path.startsWith('/projects/map')) return 'map';
  if (path.startsWith('/projects/recipes')) return 'recipes';
  return 'knowledge';
};

export default function KelProjectsPage() {
  const { pathname } = useLocation();
  const isMobile = Boolean(useLayoutContext()?.isMobile);
  // D-54: these pages show the active project; "All projects" reads every live project.
  const { active, projects, loaded } = useProjects();
  const allMode = active === ALL_PROJECTS;
  const live = useMemo(() => liveProjects(projects), [projects]);
  const liveKey = live.map((project) => project.id).join(',');
  const projectName = useCallback(
    (id: string | undefined) => (projects ?? []).find((project) => project.id === id)?.name ?? (id === GENERAL_PROJECT_ID ? 'General' : id ?? ''),
    [projects]
  );
  /** Reads use the active project, or every project; a write names one real project. */
  const readScope: KelScope = { project: active };
  const writeScope = (projectId?: string): KelScope => ({ project: allMode ? projectId || GENERAL_PROJECT_ID : active });
  const [needsProject, setNeedsProject] = useState<{ id: string; missing: string[] } | null>(null);
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
    if (!loaded) return;
    try {
      if (active === ALL_PROJECTS) {
        const reads = await Promise.all(
          liveProjects(projects).map(async (project) => ({ project, work: await kelWork({ project: project.id }) }))
        );
        setWork(mergeProjects(reads));
      } else {
        setWork(await kelWork({ project: active }));
      }
      setError(null);
    } catch (err) {
      setWork(null);
      setError(err);
    }
    // liveKey stands in for `projects`: a re-read of the same list must not reload the page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, loaded, liveKey]);

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
        const scope = writeScope(recipeProject(recipeId));
        const history = await kelRecipeHistory(recipeId, scope);
        const last = await kelRecipeLastResult(recipeId, scope).catch((): null => null);
        setRuns({ recipe: recipeId, sentence: last?.sentence ?? '', items: history.history ?? [] });
      } catch (err) {
        setRuns(null);
        setNote(
          `Could not read that recipe's runs. ${failureSentence(err, 'The engine did not answer — try again.')}`
        );
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [runs?.recipe, active, work]
  );

  useEffect(() => {
    void load();
  }, [load]);

  // The library's shelves are read once per visit: the categories it carries and what was used
  // recently. A failure here leaves the plain list in place rather than an error page.
  useEffect(() => {
    if (!loaded) return;
    void (async () => {
      const [cats, recents] = await Promise.all([
        kelRecipeCategories(readScope).catch((): { categories: Array<{ name: string; count: number }> } => ({ categories: [] })),
        kelRecipeRecent(5, readScope).catch((): { recent: KelRecipeEntry[] } => ({ recent: [] })),
      ]);
      setCategories(cats.categories ?? []);
      setRecent(recents.recent ?? []);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, loaded]);

  const searchRecipes = useCallback(async (value: string) => {
    setRecipeQuery(value);
    if (!value.trim()) {
      setFound(null);
      return;
    }
    if (allMode) {
      // Every project's recipes are already here; search them in place.
      const needle = value.trim().toLowerCase();
      setFound((work?.recipes.entries ?? []).filter((entry) =>
        [entry.name, entry.title, entry.category, entry.recipe_id].some((text) => String(text ?? '').toLowerCase().includes(needle))
      ));
      return;
    }
    try {
      const result = await kelRecipeSearch(value.trim(), readScope);
      setFound(result.entries ?? []);
    } catch (err) {
      setFound(null);
      setNote(`Search failed. ${failureSentence(err, 'The engine did not answer — try again.')}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, allMode, work]);

  const openMobileRecipe = useCallback(async (recipeId: string) => {
    if (mobileRecipeDetail?.id === recipeId) {
      setMobileRecipeDetail(null);
      return;
    }
    setMobileRecipeDetail({ id: recipeId, steps: [], lastResult: '', history: [], loading: true });
    try {
      const scope = writeScope(recipeProject(recipeId));
      const [definition, last, history] = await Promise.all([
        kelRecipeGet(recipeId, scope),
        kelRecipeLastResult(recipeId, scope).catch((): null => null),
        kelRecipeHistory(recipeId, scope).catch(() => ({ history: [] as KelRecipeRun[] })),
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mobileRecipeDetail?.id, active, work]);

  const prepareRecipe = useCallback(async (recipeId: string) => {
    setBusy('Prepare run');
    setNote(null);
    setNeedsProject(null);
    try {
      const { recipe } = await kelRecipeGet(recipeId, writeScope(recipeProject(recipeId)));
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, work]);

  const startRecipe = useCallback(async () => {
    if (!runDraft) return;
    const draft = runDraft;
    setBusy('Run recipe');
    setNote(null);
    setNeedsProject(null);
    try {
      const values = Object.fromEntries(Object.entries(draft.values)
        .filter(([, value]) => typeof value === 'boolean' || value.trim() !== ''));
      const scope = writeScope(recipeProject(draft.recipeId));
      const dryRun = await kelRecipePreview(draft.recipeId, values, scope);
      if (dryRun.needs_project) {
        setNote(String(dryRun.message ?? 'This recipe needs more project details.'));
        const projectId = String(dryRun.project_id ?? ('project' in scope ? scope.project : ''));
        if (projectId) setNeedsProject({ id: projectId, missing: Array.isArray(dryRun.missing) ? dryRun.missing : ['folder'] });
        return;
      }
      const out = await kelRecipeRun(draft.recipeId, values, scope);
      setNote('Run request sent — follow it in Activity.');
      setRunDraft(null);
      await load();
    } catch (err) {
      setNote(`Run failed. ${failureSentence(err, 'The engine did not answer — try again.')}`);
    } finally {
      setBusy(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runDraft, load, active, work]);

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
  const proposals: TaggedProposal[] = work?.memory.proposals ?? [];
  const conflicts = work?.memory.conflicts ?? [];
  const sections = work?.map?.sections ?? [];
  const entries = work?.recipes.entries ?? [];
  const listed = (found ?? entries).filter((entry) => !favouritesOnly || entry.favourite);
  // The engine lists recipes without a category under "Uncategorized"; their entries carry ''.
  const categoryOf = (entry: { category?: string | null }) => entry.category || 'Uncategorized';
  const mobileListed = (found ?? entries).filter((entry) => mobileRecipeTab === 'All'
    || (mobileRecipeTab === 'Favorites' ? entry.favourite : categoryOf(entry) === mobileRecipeTab));
  const desktopListed = (found ?? entries).filter((entry) => desktopRecipeTab === 'All'
    || (desktopRecipeTab === 'Favorites' ? entry.favourite : categoryOf(entry) === desktopRecipeTab));
  const libraryView = viewFromPath(pathname) === 'recipes';
  const populatedKnowledge = !libraryView && (pathname.startsWith('/projects/knowledge') || proposals.length > 0);
  /** The project a listed recipe belongs to (built-ins have none). */
  function recipeProject(recipeId: string): string | undefined {
    return (work?.recipes.entries ?? []).find((entry) => String(entry.recipe_id ?? entry.id ?? '') === recipeId)?.project_id;
  }
  /** In "All projects" a project recipe names its project. */
  const recipeName = (entry: KelRecipeEntry, recipeId: string) => {
    const name = entry.name ?? entry.title ?? recipeId;
    return allMode && entry.project_id ? `${name} · ${projectName(entry.project_id)}` : name;
  };
  const recordGroups: Array<{ id: string | undefined; name: string; records: KelMemoryRecord[] }> = allMode
    ? live
        .map((project) => ({ id: project.id, name: project.name, records: records.filter((record) => record.project_id === project.id) }))
        .filter((group) => group.records.length > 0)
    : [{ id: undefined, name: '', records }];
  const needsProjectButton = needsProject && (
    <KelButton
      variant="primary"
      onClick={() =>
        navigate(`/projects/list?edit=${encodeURIComponent(needsProject.id)}&focus=${needsProject.missing.includes('folder') ? 'folder' : 'test'}`)
      }
    >
      {needsProject.missing.includes('folder') ? 'Set project folder' : 'Set test command'}
    </KelButton>
  );

  return (
    <div className="kel-scope">
      <a className="kel-skip" href="#kel-projects-main">
        Skip to main content
      </a>
      <main className={`kel-page${libraryView ? ' kel-shell-recipe-library' : populatedKnowledge ? ' kel-project-knowledge-populated' : ''}`} id="kel-projects-main" tabIndex={-1}>
        <div className="kel-page__head">
          <div>
            <ShellWorkspaceLink /><h1 className="kel-h1">{libraryView ? 'Recipes' : !isMobile && populatedKnowledge ? 'Knowledge' : 'Projects'}</h1>
          </div>
          <span className="kel-grow" />
          {!libraryView && <KelButton variant="primary" disabled={proposals.length === 0} onClick={() => document.getElementById('project-suggestions')?.scrollIntoView({ block: 'center' })}>
            Kel suggests
          </KelButton>}
        </div>

        {note && <p className="kel-meta">{note}</p>}
        {needsProjectButton && <div className="kel-row">{needsProjectButton}</div>}
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
                <><p className="kel-knowledge-trust-note">Trust ranks run from 1 (strongest) to 7.</p>{recordGroups.map((group) => <React.Fragment key={group.id ?? 'one'}>
                {allMode && <h3 className="kel-strong kel-knowledge-project">{group.name}</h3>}
                <div className="kel-project-table-scroll kel-knowledge-records-scroll" tabIndex={0} role="region" aria-label={allMode ? `Saved knowledge in ${group.name}` : 'Saved knowledge table'}>
                <KelTable
                  head={['Topic', 'Type', isMobile ? 'Trust' : 'Trust rank', 'Status', 'Source', 'Updated', 'Actions']}
                  rows={group.records.map((record) => [
                    <span className="kel-strong" key={`${record.id}-topic`}>
                      {record.topic || record.summary.slice(0, 40)}
                    </span>,
                    <span className="kel-meta" key={`${record.id}-type`}>
                      {record.type}
                    </span>,
                    <span key={`${record.id}-trust`}>
                      {isMobile ? `${record.trust}/10` : `Rank ${record.trust}`}
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
                        disabled={busy !== null || record.status !== 'active' || record.trust === 7}
                        onClick={() => void act('Confirm', () => kelMemoryAction('confirm', record.id, {}, writeScope(record.project_id)))}
                      >
                        Confirm
                      </KelButton>
                      <KelButton
                        variant="quiet"
                        disabled={busy !== null || !['active', 'stale'].includes(record.status)}
                        onClick={() =>
                          void act('Retract', () =>
                            kelMemoryAction('retract', record.id, { reason: 'retracted from the Knowledge panel' }, writeScope(record.project_id))
                          )
                        }
                      >
                        Retract
                      </KelButton>
                      <KelButton
                        variant="quiet"
                        disabled={busy !== null}
                        onClick={() => void act('Forget', () => kelMemoryAction('forget', record.id, {}, writeScope(record.project_id)))}
                      >
                        Forget
                      </KelButton>
                    </span>,
                  ])}
                />
                </div></React.Fragment>)}</>
              )}
            </KelCard>
            {proposals.length > 0 && (
              <KelCard
                id="project-suggestions" title="Kel suggests"
                chip={
                  <span className="kel-meta">
                    {proposals.length === 1
                      ? (isMobile ? 'one waiting for you' : '1 waiting')
                      : `${proposals.length} waiting${isMobile ? ' for you' : ''}`}
                  </span>
                }
              >
                <p className="kel-sub">
                  {isMobile ? 'Kel only changes what it knows when you agree — nothing here applies by itself.' : 'Kel only changes what it knows when you agree.'}
                </p>
                {proposals.slice(0, 5).map((proposal) => (
                  <div className="kel-row kel-project-suggestion-row" key={proposal.id} style={{ alignItems: 'flex-start' }}>
                    <span className="kel-knowledge-proposal-icon" aria-hidden="true"><img src={proposal.kind === 'stale' ? knowledgeClockIcon : knowledgeSparkleIcon} alt="" /></span>
                    <div className="kel-attention__text">
                      <strong>{proposal.summary || proposal.topic || 'A change Kel noticed'}</strong>
                      {allMode && proposal.project_id && <span className="kel-meta">{projectName(proposal.project_id)}</span>}
                      {proposal.why && <span className="kel-meta"><span className="kel-project-suggestion-why-prefix">Why: </span>{proposal.why}</span>}
                    </div>
                    <span className="kel-grow" />
                    <KelButton
                      variant="secondary"
                      disabled={busy !== null}
                      onClick={() =>
                        void act('Accepted', () => kelMemoryAction('accept_proposal', proposal.id, {}, writeScope(proposal.project_id)))
                      }
                    >
                      <span className="kel-project-action-desktop">Accept</span><span className="kel-project-action-mobile">Accept</span>
                    </KelButton>
                    <KelButton
                      variant="quiet"
                      disabled={busy !== null}
                      onClick={() =>
                        void act('Deferred', () => kelMemoryAction('defer_proposal', proposal.id, {}, writeScope(proposal.project_id)))
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
                          }, writeScope(proposal.project_id))
                        )
                      }
                    >
                      <span className="kel-project-action-desktop">Reject</span><span className="kel-project-action-mobile">Reject</span>
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
            actions={allMode ? undefined : <>

              <KelButton variant="primary" disabled={busy !== null} onClick={() => void act('Refresh map', () => kelMapAction('refresh', writeScope()))}>
                <span className="kel-project-action-desktop">Refresh map</span><span className="kel-project-action-mobile">Refresh</span>
              </KelButton>
            </>}
          >
            {work.map && <div className="kel-project-map-caption"><span>v{work.map.version} · built {formatWhen(work.map.updated)}</span><p>What Kel knows about how this project is built.</p></div>}
            {allMode ? (
              <KelEmpty
                title="Choose a project to see its map."
                why="Each project has its own map. Pick one in the project switcher above."
              />
            ) : !work.map ? (
              <KelEmpty
                title="No map built yet."
                why="Kel builds a map of the project from its own verified work."
              />
            ) : (
              <>
              <div className="kel-project-table-scroll kel-project-map-desktop" tabIndex={0} role="region" aria-label="Project map table">
              <KelTable
                head={['Section', 'Trust', 'Freshness', 'Sources']}
                rows={sections.map((section) => [
                  <span className="kel-strong" key={`${section.name}-name`}>
                    <img src={mobileMapIcon} alt="" width={14} height={14} /> {section.name.replace(/(^|\s)\S/g, (letter) => letter.toUpperCase())}
                  </span>,
                  <span key={`${section.name}-trust`}>{section.trust}</span>,
                  <span className={section.stale ? 'kel-project-map-stale' : 'kel-project-map-fresh'} key={`${section.name}-fresh`}>{section.stale ? 'Stale' : 'Fresh'}</span>,
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

        {/* D-70 item 5: Recipes has one entry — the sidebar. The Project page no longer repeats a
            Recipes card; the library links to Scheduled tasks, which also stays in the Project nav. */}
        {!error && work && libraryView && (
          <KelCard id="project-recipes" title="Recipes" className="kel-recipe-library-card"
            actions={<>
              <span className="kel-recipe-count">{entries.length} available here</span>
              <KelButton variant="link" onClick={() => navigate('/scheduled')}>Scheduled tasks</KelButton>
            </>}>
            {entries.length === 0 ? (
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
                      {['All', 'Favorites', ...categories.map((category) => category.name)].map((tab) => (
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
                          aria-label={entry.favourite ? 'Remove from favorites' : 'Add to favorites'}
                          onClick={() => void act(entry.favourite ? 'Remove from favorites' : 'Add to favorites', () => kelRecipeFavourite(recipeId, !entry.favourite, writeScope(entry.project_id)))}>
                          <img src={entry.favourite ? mobileRecipeStarActiveIcon : mobileRecipeStarIcon} alt="" width={14} height={14} />
                        </button>
                        <span>{recipeName(entry, recipeId)}</span>
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
                          {needsProjectButton}
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
                          {mobileRecipeDetail.history.length > 0 && <button type="button" onClick={() => navigate(jobRouteFor(mobileRecipeDetail.history[0]?.job_id))}>Open in Activity</button>}
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
                    {['All', 'Favorites', ...categories.map((category) => category.name)].map((tab) => (
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
                            aria-label={entry.favourite ? 'Remove from favorites' : 'Add to favorites'}
                            onClick={() => void act(entry.favourite ? 'Remove from favorites' : 'Add to favorites', () => kelRecipeFavourite(recipeId, !entry.favourite, writeScope(entry.project_id)))}>
                            <img src={entry.favourite ? mobileRecipeStarActiveIcon : mobileRecipeStarIcon} alt="" width={14} height={14} />
                          </button>
                          <strong>{recipeName(entry, recipeId)}</strong>
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
                          aria-label={entry.favourite ? 'Remove from favorites' : 'Add to favorites'}
                          onClick={() => void act(entry.favourite ? 'Remove from favorites' : 'Add to favorites', () => kelRecipeFavourite(recipeId, !entry.favourite, writeScope(entry.project_id)))}>
                          <img src={entry.favourite ? mobileRecipeStarActiveIcon : mobileRecipeStarIcon} alt="" width={14} height={14} />
                        </button>
                        <button className="kel-recipe-mobile-name" type="button" aria-expanded={false}
                          onClick={() => void openMobileRecipe(recipeId)}>{recipeName(entry, recipeId)}</button>
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
                    Favorites
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
                    why="Clear the search or the favorites filter to see the whole project library."
                  />
                ) : (
              <KelTable
                head={['Recipe', 'Steps', 'Inputs', 'Source', 'Dry run', 'Run', 'History']}
                rows={listed.map((entry) => {
                  const recipeId = String(entry.recipe_id ?? entry.id ?? '');
                  return [
                    <span className="kel-strong" key={`${recipeId}-name`}>
                      {recipeName(entry, recipeId)}{' '}
                      <KelButton
                        variant="quiet"
                        disabled={busy !== null || !recipeId}
                        onClick={() =>
                          void act(entry.favourite ? 'Remove from favorites' : 'Add to favorites', () =>
                            kelRecipeFavourite(recipeId, !entry.favourite, writeScope(entry.project_id))
                          )
                        }
                      >
                        {entry.favourite ? 'Favorited' : 'Favorite'}
                      </KelButton>{' '}
                      <KelButton
                        variant="quiet"
                        disabled={busy !== null || !recipeId}
                        onClick={() => void act('Copy', () => kelRecipeDuplicate(recipeId, writeScope(entry.project_id)))}
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
                          const payload = await kelRecipePreview(recipeId, {}, writeScope(entry.project_id));
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
                  {needsProjectButton}
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
                        <KelButton variant="quiet" onClick={() => navigate(jobRouteFor(run.job_id))}>
                          Open in Activity
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
