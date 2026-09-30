import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KelButton, KelCard } from './KelPrimitives';
import { KEL_ALL_CONVERSATIONS, kelArtifacts, kelHubSearch, kelOffice, kelProcedures, kelState, kelTaskOutcomes, kelWorkImports, type KelArtifactVersion, type KelContextStatus, type KelImportPreview, type KelProcedure, type KelOfficeItem, type KelTaskOutcome } from './kelApi';
import { ALL_PROJECTS, useProjects } from './activeProject';
import { jobRouteFor } from './needsAttention';
import { openWorkCard } from './workCards/workCardEvents';
import { failureSentence } from './engineFailure';

/** Import always starts with review. Pasted content never becomes an instruction automatically. */
export function WorkImport({ projectId }: { projectId: string }) {
  const navigate = useNavigate();
  const [content, setContent] = useState('');
  const [source, setSource] = useState('other');
  const [format, setFormat] = useState('text');
  const [preview, setPreview] = useState<KelImportPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1; setPreview(null); setError(''); setBusy(false);
    return () => { generation.current += 1; };
  }, [projectId]);
  const run = async (confirm: boolean) => {
    if (busy) return;
    const epoch = generation.current;
    setBusy(true); setError('');
    try {
      if (!confirm) {
        const result = await kelWorkImports.preview(projectId, { content, source, format });
        if (epoch === generation.current) setPreview(result);
      } else if (preview) {
        const imported = await kelWorkImports.confirm(projectId, preview);
        if (epoch !== generation.current) return;
        const open = window.kelAPI?.openEngineConversation;
        if (!open) throw new Error('Kel cannot open the imported chat on this device. The import was saved.');
        const chat = await open(imported.conversation_id);
        if (!chat) throw new Error('The import was saved, but Kel could not open its chat.');
        if (epoch === generation.current) navigate(`/conversation/${encodeURIComponent(chat)}`);
      }
    } catch (failure) { if (epoch === generation.current) setError(failureSentence(failure, 'Kel could not complete this action.')); }
    finally { if (epoch === generation.current) setBusy(false); }
  };
  const invalidate = () => { generation.current += 1; setPreview(null); setError(''); };
  return <KelCard title="Bring work into Kel">
    <details><summary>Import a transcript</summary>
      <p>Paste text or a Kel transcript. Kel saves a separate chat in this Project. External sessions do not resume here.</p>
      <div className="kel-row">
        <label>Source <select className="kel-select" disabled={busy} value={source} onChange={e => { invalidate(); setSource(e.target.value); }}>
          {['other', 'codex', 'claude', 'deepseek'].map(value => <option key={value} value={value}>{value === 'other' ? 'Other' : value}</option>)}
        </select></label>
        <label>Format <select className="kel-select" disabled={busy} value={format} onChange={e => { invalidate(); setFormat(e.target.value); }}>
          <option value="text">Plain text</option><option value="kel-transcript">Kel transcript JSON</option>
        </select></label>
      </div>
      <label>Transcript<textarea className="kel-input" rows={6} style={{ width: '100%' }} disabled={busy} value={content}
        onChange={e => { invalidate(); setContent(e.target.value); }} /></label>
      {preview && <section aria-label="Import review"><h3>{preview.title}</h3><p>{preview.message_count} messages</p>
        <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{preview.snippet}</pre>
        {preview.omissions.length > 0 && <><strong>Not imported</strong><ul>{preview.omissions.map((item, i) => <li key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>)}</ul></>}
        <p>Imported text stays source material. Review it before asking Kel to act.</p>
      </section>}
      {error && <p role="alert">{error}</p>}
      <KelButton disabled={busy || !content.trim()} onClick={() => void run(Boolean(preview))}>
        {busy ? 'Working…' : preview ? 'Confirm import and open chat' : 'Review import'}
      </KelButton>
    </details>
  </KelCard>;
}

export function ProcedureStatus({ projectId, recipeId }: { projectId: string; recipeId: string }) {
  const [procedure, setProcedure] = useState<KelProcedure | null>(null);
  const [job, setJob] = useState('');
  const [evidence, setEvidence] = useState<KelOfficeItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1;
    let alive = true; setProcedure(null); setError(''); setJob(''); setEvidence([]); setBusy(false);
    Promise.all([kelOffice({ project: projectId }), kelState(KEL_ALL_CONVERSATIONS, projectId)]).then(([value, state]) => {
      const verified = new Set((state.jobs ?? []).filter(item => item.state === 'CLOSED' && item.verdict === 'VERIFIED').map(item => item.id));
      if (alive) setEvidence((value.items ?? []).filter(item => item.state === 'done' && verified.has(item.job_id)));
    }).catch(() => { /* The review endpoint still validates evidence; a failed list offers no review action. */ });
    kelProcedures.get(projectId, recipeId).then(value => { if (alive) setProcedure(value); })
      .catch(failure => { if (alive) setError(failureSentence(failure, 'Kel could not complete this action.')); });
    return () => { alive = false; generation.current += 1; };
  }, [projectId, recipeId]);
  const act = async (action: 'review' | 'retire' | 'restore') => {
    if (!procedure || busy) return;
    const epoch = generation.current;
    setBusy(true); setError('');
    try { const result = await (action === 'review' ? kelProcedures.review(projectId, recipeId, procedure.version, job.trim())
      : kelProcedures[action](projectId, recipeId, procedure.version)); if (epoch === generation.current) setProcedure(result); }
    catch (failure) { if (epoch === generation.current) setError(failureSentence(failure, 'Kel could not complete this action.')); }
    finally { if (epoch === generation.current) setBusy(false); }
  };
  return <section aria-label="Recipe review"><p>{procedure ? `${procedure.state === 'reviewed' ? 'Reviewed procedure' : procedure.state === 'retired' ? 'Retired procedure' : 'Draft procedure'} · Version ${procedure.version}` : error ? 'Recipe status is unavailable.' : 'Reading recipe status…'}</p>
    {procedure?.evidence_job_id && <p>Kel recorded checked work for this version.</p>}
    {procedure && procedure.state !== 'retired' && <>
      {evidence.length > 0 ? <><label>Checked work <select className="kel-select" value={job} onChange={e => setJob(e.target.value)} disabled={busy}>
        <option value="">Choose a completed result</option>{evidence.map(item => <option value={item.job_id} key={item.job_id}>{item.title}</option>)}
      </select></label><p>Kel checks that this result passed verification in this Project.</p>
      <KelButton disabled={busy || !job} onClick={() => void act('review')}>Mark reviewed</KelButton></>
      : <p>Complete checked work in this Project before marking this procedure reviewed.</p>}
      <KelButton disabled={busy} onClick={() => void act('retire')}>Retire this version</KelButton>
    </>}
    {procedure?.state === 'retired' && <><p>This version cannot run. Restore it to make it available.</p>
      <KelButton disabled={busy} onClick={() => void act('restore')}>Restore this version</KelButton></>}
    {error && <p role="alert">{error}</p>}
  </section>;
}

export function ResultFeedback({ projectId, jobId, onRevise }: { projectId: string; jobId: string; onRevise: () => void }) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1; setBusy(false); setNote(''); setError('');
    return () => { generation.current += 1; };
  }, [projectId, jobId]);
  const give = async (response: 'useful' | 'revision_requested') => {
    if (busy) return;
    const epoch = generation.current;
    setBusy(true); setError('');
    try { await kelTaskOutcomes.feedback(projectId, jobId, response); if (epoch !== generation.current) return;
      setNote(response === 'useful' ? 'Saved. Thank you.' : 'Revision request saved.'); if (response === 'revision_requested') onRevise(); }
    catch (failure) { if (epoch === generation.current) setError(failureSentence(failure, 'Kel could not complete this action.')); }
    finally { if (epoch === generation.current) setBusy(false); }
  };
  return <div aria-label="Optional result feedback"><span className="kel-meta">Was this useful? </span>
    <KelButton disabled={busy} onClick={() => void give('useful')}>Useful</KelButton>
    <KelButton disabled={busy} onClick={() => void give('revision_requested')}>Needs changes</KelButton>
    {note && <p role="status">{note}</p>}{error && <p role="alert">{error}</p>}
  </div>;
}

export function OutputVersions({ jobId }: { jobId: string }) {
  const [versions, setVersions] = useState<KelArtifactVersion[]>([]);
  const [selected, setSelected] = useState('');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const request = useRef(0);
  useEffect(() => {
    let alive = true; setVersions([]); setSelected(''); setContent(''); setError(''); setBusy(false);
    kelArtifacts.versions(jobId).then(value => { if (alive) setVersions(value.versions ?? []); })
      .catch(failure => { if (alive) setError(failureSentence(failure, 'Kel could not complete this action.')); });
    return () => { alive = false; request.current += 1; };
  }, [jobId]);
  const read = async (id: string) => {
    const epoch = ++request.current; setSelected(id); setBusy(true); setContent(''); setError('');
    try { const text = await kelArtifacts.read(id); if (epoch === request.current) setContent(text); }
    catch (failure) { if (epoch === request.current) setError(failureSentence(failure, 'Kel could not complete this action.')); }
    finally { if (epoch === request.current) setBusy(false); }
  };
  return <details><summary>Outputs</summary><section aria-label="Output versions">
    {versions.length > 0 ? <ul>{versions.map(version => <li key={version.id}>
      <KelButton onClick={() => void read(version.id)} ariaPressed={selected === version.id}>{version.filename}</KelButton>
      <span className="kel-meta"> {version.superseded_by ? 'Earlier version' : 'Current version'} · {new Date(version.created * 1000).toLocaleString()}</span>
    </li>)}</ul> : <p>{error ? 'Output records are unavailable.' : 'No saved output versions were found.'}</p>}
    {busy && <p role="status">Reading this version…</p>}
    {content && <pre tabIndex={0} style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 360, overflow: 'auto' }}>{content}</pre>}
    {error && <p role="alert">Outputs could not be read. {error}</p>}
  </section></details>;
}

/** Home reads existing work facts. Opening a card never restarts its job. */
export function HomeResume() {
  const { active, loaded } = useProjects();
  const [items, setItems] = useState<KelOfficeItem[]>([]);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1;
    if (!loaded) return;
    let alive = true; setItems([]); setError('');
    kelOffice(active === ALL_PROJECTS ? '*' : { project: active }).then(value => {
      if (alive) setItems((value.items ?? []).slice(0, 4));
    }).catch(failure => { if (alive) setError(failureSentence(failure, 'Kel could not complete this action.')); });
    return () => { alive = false; generation.current += 1; };
  }, [active, loaded]);
  if (!items.length && !error) return null;
  return <section className="kel-card" aria-label="Continue your work"><h2>Continue your work</h2>
    {items.map(item => <div className="kel-row" key={item.job_id}>
      <KelButton onClick={() => {
        const open = window.kelAPI?.openEngineConversation;
        const epoch = generation.current;
        if (!item.conversation_id || !open) { navigate(jobRouteFor(item.job_id)); return; }
        void open(item.conversation_id).then(chat => {
          if (epoch !== generation.current) return;
          if (chat) { openWorkCard(item.job_id); navigate(`/conversation/${encodeURIComponent(chat)}`); }
          else navigate(jobRouteFor(item.job_id));
        }).catch(() => { if (epoch === generation.current) navigate(jobRouteFor(item.job_id)); });
      }}>{item.title || 'Open work'}</KelButton>
      <span className="kel-meta">{item.status_line || item.progress?.label || ({ working: 'Working', in_review: 'Checking', needs_you: 'Needs you', done: 'Complete', failed: 'Could not finish', stopped: 'Stopped' }[item.state])}</span>
    </div>)}
    {error && <p role="status">Recent work could not be read. {error}</p>}
  </section>;
}

export function ProjectWorkSearch({ projectId }: { projectId: string }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Record<string, Array<Record<string, unknown>>> | null>(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const epoch = useRef(0);
  const navigate = useNavigate();
  useEffect(() => {
    epoch.current += 1; setResults(null); setText(''); setBusy(false); setError('');
    return () => { epoch.current += 1; };
  }, [projectId]);
  const search = async (event: React.FormEvent) => {
    event.preventDefault(); const current = ++epoch.current; setBusy(true); setError(''); setText('');
    try { const value = await kelHubSearch(projectId, query.trim());
      if (current === epoch.current) setResults(Object.fromEntries(Object.entries(value).filter(([, rows]) => Array.isArray(rows))) as Record<string, Array<Record<string, unknown>>>); }
    catch (failure) { if (current === epoch.current) setError(failureSentence(failure, 'Search could not finish.')); }
    finally { if (current === epoch.current) setBusy(false); }
  };
  const open = async (group: string, row: Record<string, unknown>) => {
    const current = ++epoch.current; setError(''); setText('');
    const link = row.link as { kind?: string; id?: string; job_id?: string; conversation_id?: string } | undefined;
    const id = String(link?.id ?? row.id ?? '');
    try {
      if (group === 'artifacts') {
        setBusy(true); const value = await kelArtifacts.read(id);
        if (current === epoch.current) setText(value); return;
      }
      if (group === 'knowledge') {
        const target = document.getElementById(`knowledge-${id}`);
        target?.scrollIntoView({ block: 'center', behavior: 'auto' }); target?.focus(); return;
      }
      const conversation = String(group === 'conversations' || group === 'imports' ? link?.id ?? row.conversation_id ?? id : row.conversation_id ?? link?.conversation_id ?? '');
      if (conversation && window.kelAPI?.openEngineConversation) {
        const chat = await window.kelAPI.openEngineConversation(conversation);
        if (current !== epoch.current) return;
        if (chat) { if (group === 'work') openWorkCard(id); navigate(`/conversation/${encodeURIComponent(chat)}`); return; }
      }
      if (group === 'work') navigate(jobRouteFor(id));
      else throw new Error('Kel could not open this saved chat.');
    } catch (failure) { if (current === epoch.current) setError(failureSentence(failure, 'This result could not open.')); }
    finally { if (current === epoch.current) setBusy(false); }
  };
  const groups = ['conversations', 'work', 'artifacts', 'knowledge', 'imports'];
  const labels: Record<string, string> = { conversations: 'Chats', work: 'Work', artifacts: 'Output versions', knowledge: 'Knowledge', imports: 'Imported work' };
  const count = groups.reduce((total, key) => total + (results?.[key]?.length ?? 0), 0);
  return <KelCard title="Find work in this Project"><form className="kel-row" onSubmit={event => void search(event)}>
    <label className="kel-grow">Search <input className="kel-input" value={query} maxLength={120} onChange={event => {
      epoch.current += 1; setQuery(event.target.value); setResults(null); setText(''); setError(''); setBusy(false);
    }} /></label><KelButton disabled={busy || query.trim().length < 2} onClick={() => undefined} type="submit">Search</KelButton>
  </form>
    {busy && <p role="status">Reading saved work…</p>}
    {results && count === 0 && <p>No saved work matches this search.</p>}
    {groups.map(group => results?.[group]?.length ? <section key={group} aria-label={labels[group]}><h3>{labels[group]}</h3>
      <ul>{results[group].map((row, index) => <li key={String(row.id ?? index)}>
        <KelButton disabled={busy} onClick={() => void open(group, row)}>{String(row.title || row.id || 'Open result')}</KelButton>
        {row.superseded_by && <span className="kel-meta"> Earlier version</span>}
        {row.snippet && <p>{String(row.snippet)}</p>}
      </li>)}</ul></section> : null)}
    {results?.omissions?.length ? <p className="kel-meta">Some saved material was outside this search. {results.omissions.map(item => String(item.reason ?? '')).join(' ')}</p> : null}
    {text && <pre tabIndex={0} style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 360, overflow: 'auto' }}>{text}</pre>}
    {error && <p role="alert">{error}</p>}
  </KelCard>;
}

export function TaskOutcomeFacts({ projectId, jobId }: { projectId: string; jobId: string }) {
  const [facts, setFacts] = useState<KelTaskOutcome | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true; setFacts(null); setError('');
    kelTaskOutcomes.get(projectId, jobId).then(value => {
      if (!alive) return;
      if (!value || value.job_id !== jobId || !value.costs || typeof value.costs !== 'object') {
        setError('Work records are unavailable for this result.'); return;
      }
      setFacts(value);
    })
      .catch(failure => { if (alive) setError(failureSentence(failure, 'These records could not be read.')); });
    return () => { alive = false; };
  }, [projectId, jobId]);
  const money = (value: number | null | undefined) => typeof value === 'number' ? `$${value.toFixed(4)}` : 'Unknown';
  return <details><summary>Work records</summary>
    {facts ? <dl>
      <dt>Elapsed time</dt><dd>{typeof facts.elapsed_ms === 'number' ? `${Math.round(facts.elapsed_ms / 1000)} seconds` : 'Unknown'}</dd>
      <dt>Worker retries</dt><dd>{facts.worker_retries ?? 'Unknown'}</dd><dt>Model calls</dt><dd>{facts.call_count ?? 'Unknown'}</dd>
      <dt>Reported cost</dt><dd>{money(facts.costs?.reported)}</dd><dt>Estimated cost</dt><dd>{money(facts.costs?.estimated)}</dd>
      {typeof facts.costs?.subscription_equivalent === 'number' && <><dt>Subscription equivalent estimate</dt><dd>{money(facts.costs.subscription_equivalent)}</dd></>}
      <dt>Calls with unknown cost</dt><dd>{facts.costs?.unknown_calls ?? 'Unknown'}</dd>
      <dt>Saved feedback</dt><dd>{facts.feedback ? `${facts.feedback_current === true ? '' : 'Earlier result: '}${facts.feedback.response === 'useful' ? 'Useful' : 'Needs changes'}` : 'No feedback saved'}</dd>
    </dl> : <p>{error || 'Reading work records…'}</p>}
    <p className="kel-meta">These records describe this work. They do not change Kel’s model choices.</p>
  </details>;
}

export function ContextStatusFacts({ status }: { status: KelContextStatus }) {
  const omissions = status.omissions ?? [];
  const freshness = status.freshness ?? {};
  return <details><summary>Context: {status.state === 'ready' ? 'Ready' : 'Some context was unavailable'}</summary>
    {status.requires_attention && <p>Kel needs attention before using this context.</p>}
    {omissions.length > 0 && <><p>Kel could not include some context.</p><ul>{omissions.map((item, index) => <li key={index}>
      {String(item.reason || item.code || 'A context source was unavailable.')}
    </li>)}</ul></>}
    {['checked', 'stale', 'unknown'].map(key => typeof freshness[key] === 'number' || Array.isArray(freshness[key]) ? <p key={key}>
      {key === 'checked' ? 'Sources checked' : key === 'stale' ? 'Sources that may need an update' : 'Sources with unknown freshness'}: {Array.isArray(freshness[key]) ? freshness[key].length : String(freshness[key])}
    </p> : null)}
  </details>;
}

