/** Kel work controls, using AionUI's Arco components and theme tokens. */
import React, { useEffect, useState } from 'react';
import { Badge, Button, Drawer, Select, Input, Form, Alert, Space, Typography, Tabs, Message } from '@arco-design/web-react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router-dom';
import Markdown from '@/renderer/components/Markdown';
type Project = { id: string; name: string; root: string; context: string; test_command?: string[] };
type Job = {
  id: string;
  state: string;
  verdict: string;
  contract: { request: string; kind: string; milestones: { id: string; filename: string }[] };
  milestones: Record<string, { state: string }>;
};
type ContinuationEntry = {
  job_id: string;
  title: string;
  state: string;
  verdict?: string;
  accepted: number;
  total: number;
};
type MemoryRecord = {
  id: string;
  type: string;
  topic: string;
  summary: string;
  trust: number;
  status: string;
  user_confirmed: number;
  source_type: string;
  source_ref: string;
  updated: number;
};
type MemoryConflict = { id: string; memory_a: string; memory_b: string; state: string };
type MapSection = { name: string; trust: string; stale: boolean; sources: string[] };
type MapInfo = { version: number; fingerprint: string; note?: string; sections: MapSection[] };
type RecipeEntry = { recipe_id: string; name: string; version: string; scope: string; kind: string };
type VettingQuestion = {
  id: string;
  section: string;
  prompt: string;
  open: boolean;
  visual: number;
  options: { code: string; label: string }[];
  answer?: { status: string; selected: string[]; custom: string } | null;
};
type VettingGreybox = { id: string; question_id: string; name: string; description: string; svg: string; is_base: number };
type VettingPanelData = {
  session: { id: string; topic: string; state: string } | null;
  progress?: { answered: number; handled: number; total: number };
  questions?: VettingQuestion[];
  unanswered?: string[];
  decisions?: { statement: string; rationale: string }[];
  conflicts?: { id: string; statement: string }[];
  spec?: { id: string; created: number; coverage: Record<string, number> } | null;
  greyboxes?: VettingGreybox[];
  pending?: { question_id: string; option: string }[];
};
type WorkExtras = {
  project_id: string;
  memory: { records: MemoryRecord[]; conflicts: MemoryConflict[] };
  map: MapInfo | null;
  recipes: { entries: RecipeEntry[] };
};
type State = {
  projects: Project[];
  conversations: { id: string; title: string; project_id: string }[];
  jobs: Job[];
  messages: { role: string; text: string }[];
  approvals: { id: string; job_id: string; action: string }[];
  continuation?: ContinuationEntry[];
};
declare global {
  interface Window {
    kelAPI?: {
      request: (route: string, body?: unknown) => Promise<unknown>;
      history: (id: string) => Promise<unknown>;
      conversation: (id: string) => Promise<unknown>;
      historySearch: (query: string) => Promise<unknown>;
      /** OS-backed credential custody: metadata only — there is deliberately no value getter. */
      credentials?: {
        status: () => Promise<{ available: boolean; providers: Record<string, string[]> }>;
        set: (
          provider: string,
          field: string,
          value: string
        ) => Promise<{ provider: string; fields: string[] }>;
        remove: (provider: string) => Promise<{ provider: string; removed: number }>;
      };
    };
  }
}
async function request<T>(route: string, body?: unknown): Promise<T> {
  if (!window.kelAPI) throw Error('Kel connection is unavailable');
  return (await window.kelAPI.request(route, body)) as T;
}
function previewText(result: Record<string, unknown>): string {
  if (result.continuation) return 'Continuation flow: ' + ((result.stages as string[]) || []).join(' → ');
  if (result.needs_project) return String(result.message || 'This recipe needs a project with a test command.');
  const lines = ['Request: ' + String(result.request || '')];
  for (const m of (result.milestones as { id: string; objective: string }[]) || [])
    lines.push('- ' + m.id + ': ' + m.objective);
  lines.push('Terminal states: ' + ((result.terminal_states as string[]) || []).join(', '));
  lines.push('Budget: ' + String(result.budget ?? ''));
  return lines.join('\n');
}
export default function KelWorkPanel() {
  const { t } = useTranslation();
  const location = useLocation();
  const [visible, setVisible] = useState(false),
    [state, setState] = useState<State>(),
    [cid, setCid] = useState('main');
  const [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [projectId, setProjectId] = useState('default');
  const [context, setContext] = useState(''),
    [checks, setChecks] = useState(''),
    [report, setReport] = useState('');
  const [pendingApprovals, setPendingApprovals] = useState(0),
    [extras, setExtras] = useState<WorkExtras>(),
    [preview, setPreview] = useState(''),
    [draft, setDraft] = useState<{ id: string; summary: string } | null>(null);
  const [vetting, setVetting] = useState<VettingPanelData>(),
    [vettingTopic, setVettingTopic] = useState(''),
    [vettingSpec, setVettingSpec] = useState(''),
    [unansweredOnly, setUnansweredOnly] = useState(false),
    [combineNote, setCombineNote] = useState('');
  const vettingAction = async (body: Record<string, unknown>, quiet = false) => {
    setBusy(true);
    try {
      const result = await request<Record<string, unknown>>('/api/vetting', { ...body, conversation: cid });
      const message = typeof result.message === 'string' ? result.message : '';
      if (!quiet && message) Message.info(message.slice(0, 240));
      if (typeof result.markdown === 'string') setVettingSpec(result.markdown);
      await refresh();
      return result;
    } catch (e) {
      setError(String(e));
      return null;
    } finally {
      setBusy(false);
    }
  };
  const refresh = async () => {
    try {
      const data = await request<State>('/api/state?conversation=' + cid);
      setState(data);
      setPendingApprovals((data.approvals || []).length);
      // The drawer follows the conversation the app is actually showing: when the historical
      // hard-coded 'main' is not among the conversations, the newest one becomes the drawer's
      // target, so Work, Knowledge, Map, Recipes and Vetting never point at a conversation
      // that does not exist while the open chat is somewhere else.
      let active = cid;
      if (cid === 'main' && data.conversations?.length && !data.conversations.some((c) => c.id === cid)) {
        active = data.conversations[0].id;
        setCid(active);
        const fresh = await request<State>('/api/state?conversation=' + active);
        setState(fresh);
        setPendingApprovals((fresh.approvals || []).length);
      }
      try {
        setExtras(await request<WorkExtras>('/api/work?conversation=' + active));
      } catch {
        /* the drawer still works from /api/state alone when extras are unavailable */
      }
      try {
        setVetting(await request<VettingPanelData>('/api/vetting', { action: 'panel', conversation: active }));
      } catch {
        /* vetting is an added surface; its absence must not break the drawer */
      }
      setError('');
    } catch (e) {
      setError(String(e));
    }
  };
  useEffect(() => {
    if (!visible) return;
    void refresh();
    const timer = setInterval(() => void refresh(), 1500);
    return () => clearInterval(timer);
  }, [visible, cid]);
  // Attention badge: while the drawer is closed, poll the engine's global
  // pending-approval list so "Kel needs you" is visible from anywhere in the
  // app. Silent failure is fine — the badge simply stays hidden until data
  // arrives (no extra dialogs or notifications).
  useEffect(() => {
    const poll = async () => {
      if (visible) return;
      try {
        const data = await request<State>('/api/state?conversation=' + cid);
        setPendingApprovals((data.approvals || []).length);
      } catch {
        /* engine not ready yet */
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), 5000);
    return () => clearInterval(timer);
  }, [visible, cid]);
  useEffect(() => {
    const id = location.pathname.match(/^\/conversation\/([^/]+)/)?.[1];
    if (!id) return;
    void window.kelAPI
      ?.conversation(id)
      .then((saved: unknown) => {
        if (typeof saved === 'string' && saved) setCid(saved);
      })
      .catch((e: unknown) => setError(String(e)));
  }, [location.pathname, visible]);
  const project = state?.projects.find((p) => p.id === projectId);
  useEffect(() => {
    if (!project) return;
    setContext(project.context || '');
    setChecks(project.test_command ? JSON.stringify(project.test_command) : '');
  }, [projectId, project?.context, JSON.stringify(project?.test_command)]);
  useEffect(() => {
    const conversation = state?.conversations.find((c) => c.id === cid);
    if (conversation) setProjectId(conversation.project_id);
  }, [cid, state?.conversations.length]);
  async function action(route: string, body: unknown) {
    setBusy(true);
    try {
      await request(route, body);
      await refresh();
      Message.success(t('common.kel.saved'));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Badge count={pendingApprovals} maxCount={9} offset={[10, -4]}>
        <Button
          long
          type='text'
          onClick={() => setVisible(true)}
          className='kel-work-context-btn'
        >
          {t('common.kel.workContext')}
        </Button>
      </Badge>
      <Drawer
        title={t('common.kel.workContext')}
        visible={visible}
        escToExit={!report}
        width={Math.min(600, window.innerWidth)}
        footer={null}
        onCancel={() => setVisible(false)}
      >
        {error && <Alert type='error' content={error} closable onClose={() => setError('')} />}
        <Form layout='vertical'>
          <Form.Item label={t('common.kel.conversation')}>
            <Select
              value={cid}
              onChange={setCid}
              options={state?.conversations.map((c) => ({ value: c.id, label: c.title }))}
            />
          </Form.Item>
        </Form>
        <Tabs defaultActiveTab='work'>
          <Tabs.TabPane key='work' title={t('common.kel.work')}>
            {state?.jobs.length === 0 && <Typography.Paragraph>{t('common.kel.noWork')}</Typography.Paragraph>}
            {state?.jobs.map((job) => (
              <section key={job.id} className='py-16px border-b border-solid border-[var(--color-border-2)]'>
                <Typography.Paragraph>{job.contract.request}</Typography.Paragraph>
                <Typography.Paragraph type='secondary'>
                  {job.state} · {job.verdict}
                </Typography.Paragraph>
                <Space wrap>
                  {!['CLOSED', 'CANCELLED'].includes(job.state) && (
                    <>
                      <Button disabled={busy} onClick={() => action('/api/control', { job: job.id, action: 'pause' })}>
                        {t('common.kel.pause')}
                      </Button>
                      <Button disabled={busy} onClick={() => action('/api/control', { job: job.id, action: 'resume' })}>
                        {t('common.kel.resume')}
                      </Button>
                      <Button disabled={busy} onClick={() => action('/api/control', { job: job.id, action: 'cancel' })}>
                        {t('common.kel.cancel')}
                      </Button>
                    </>
                  )}
                  {job.verdict === 'VERIFIED' && job.contract.kind === 'coding' && (
                    <Button disabled={busy} onClick={() => action('/api/apply', { job: job.id })}>
                      {t('common.kel.apply')}
                    </Button>
                  )}
                  {job.contract.milestones
                    .filter((m) => job.milestones[m.id]?.state === 'ACCEPTED')
                    .map((m) => (
                      <Button
                        key={m.id}
                        onClick={async () => {
                          try {
                            setReport(await request<string>('/api/artifact?job=' + job.id + '&milestone=' + m.id));
                          } catch (e) {
                            setError(String(e));
                          }
                        }}
                      >
                        {m.filename}
                      </Button>
                    ))}
                </Space>
              </section>
            ))}
            {state?.approvals
              .filter((a) => state.jobs.some((j) => j.id === a.job_id))
              .map((a) => (
                <section key={a.id} className='py-16px'>
                  <Typography.Title heading={6}>{t('common.kel.approval')}</Typography.Title>
                  <pre className='whitespace-pre-wrap break-all'>{a.action}</pre>
                  <Space>
                    <Button onClick={() => action('/api/approval', { id: a.id, allow: true })}>
                      {t('common.kel.allow')}
                    </Button>
                    <Button onClick={() => action('/api/approval', { id: a.id, allow: false })}>
                      {t('common.kel.deny')}
                    </Button>
                  </Space>
                </section>
              ))}
          </Tabs.TabPane>
          <Tabs.TabPane key='vetting' title='Vetting'>
            {!vetting?.session && (
              <>
                <Typography.Paragraph type='secondary'>
                  Turn a rough idea into a developer-ready spec: Kel asks in batches, you answer with
                  numbers in the chat (like 12: A), and every decision is kept with its rationale.
                </Typography.Paragraph>
                <Space>
                  <Input
                    value={vettingTopic}
                    onChange={setVettingTopic}
                    placeholder='What are you designing? e.g. a basketball matchup dashboard'
                    style={{ width: 300 }}
                  />
                  <Button
                    type='primary'
                    disabled={busy || !vettingTopic.trim()}
                    onClick={() => vettingAction({ action: 'start', topic: vettingTopic })}
                  >
                    Start vetting session
                  </Button>
                </Space>
              </>
            )}
            {vetting?.session && (
              <>
                <Typography.Paragraph>
                  <Typography.Text bold>{vetting.session.topic}</Typography.Text> · {vetting.session.state}
                  {vetting.progress ? ` · ${vetting.progress.handled}/${vetting.progress.total} recorded` : ''}
                </Typography.Paragraph>
                <Space wrap>
                  <Button
                    disabled={busy}
                    onClick={() =>
                      void vettingAction({ action: 'process' }, true).then((r) => r && Message.info('Next batch is in the chat.'))
                    }
                  >
                    Process answers
                  </Button>
                  <Button disabled={busy} onClick={() => vettingAction({ action: 'finish' })}>
                    Finish spec now
                  </Button>
                  <Button disabled={busy} onClick={() => vettingAction({ action: 'preview' })}>
                    Preview spec
                  </Button>
                  <Button onClick={() => setUnansweredOnly((value) => !value)}>
                    {unansweredOnly ? 'Show all questions' : 'Show unanswered only'}
                  </Button>
                </Space>
                {(vetting.pending || []).length > 0 && (
                  <Alert
                    style={{ marginTop: 8 }}
                    content={`Suggested mapping: ${(vetting.pending || [])
                      .map((pending) => `${pending.question_id} → ${pending.option}`)
                      .join(', ')}`}
                    action={
                      <Space>
                        <Button size='mini' onClick={() => vettingAction({ action: 'apply_pending', accept: true })}>
                          Confirm
                        </Button>
                        <Button size='mini' onClick={() => vettingAction({ action: 'apply_pending', accept: false })}>
                          Dismiss
                        </Button>
                      </Space>
                    }
                  />
                )}
                {(vetting.conflicts || []).map((conflict) => (
                  <section key={conflict.id} className='py-12px border-b border-solid border-[var(--color-border-2)]'>
                    <Typography.Paragraph>{conflict.statement}</Typography.Paragraph>
                    <Space wrap>
                      <Button size='small' onClick={() => vettingAction({ action: 'conflict', conflict: conflict.id, choice: 'keep_earlier' })}>
                        Keep earlier
                      </Button>
                      <Button size='small' onClick={() => vettingAction({ action: 'conflict', conflict: conflict.id, choice: 'use_newer' })}>
                        Use newer
                      </Button>
                      <Button size='small' onClick={() => vettingAction({ action: 'conflict', conflict: conflict.id, choice: 'show_tradeoff' })}>
                        Show tradeoff
                      </Button>
                      <Button size='small' onClick={() => vettingAction({ action: 'conflict', conflict: conflict.id, choice: 'resolve_later' })}>
                        Resolve later
                      </Button>
                    </Space>
                  </section>
                ))}
                <section className='py-12px'>
                  {(vetting.questions || [])
                    .filter((question) => !unansweredOnly || (vetting.unanswered || []).includes(question.id))
                    .map((question) => (
                      <Typography.Paragraph key={question.id}>
                        <Typography.Text bold>{question.id}</Typography.Text> {question.prompt}{' '}
                        <Typography.Text type='secondary'>
                          {question.answer ? question.answer.status.toLowerCase().replace(/_/g, ' ') : 'unanswered'}
                          {question.answer?.custom ? ` · ${question.answer.custom}` : ''}
                        </Typography.Text>{' '}
                        {question.visual ? (
                          <Button
                            size='mini'
                            disabled={busy}
                            onClick={() => vettingAction({ action: 'greybox', question: question.id, mode: 'design' })}
                          >
                            Show greyboxes
                          </Button>
                        ) : null}
                      </Typography.Paragraph>
                    ))}
                </section>
                {(vetting.greyboxes || []).length > 0 && (
                  <section className='py-12px'>
                    <Typography.Title heading={6}>Greybox directions</Typography.Title>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 8 }}>
                      {(vetting.greyboxes || []).map((box) => (
                        <div key={box.id} style={{ border: '1px solid var(--color-border-2)', borderRadius: 8, padding: 8 }}>
                          <div dangerouslySetInnerHTML={{ __html: box.svg }} />
                          <Typography.Paragraph type='secondary' style={{ fontSize: 12 }}>
                            {box.name}
                          </Typography.Paragraph>
                          <Space wrap>
                            <Button
                              size='mini'
                              type={box.is_base ? 'primary' : 'default'}
                              onClick={() =>
                                vettingAction({ action: 'greybox', question: box.question_id, mode: 'feedback', feedback_kind: 'choose_base', greybox_id: box.id })
                              }
                            >
                              Choose as base
                            </Button>
                            <Button
                              size='mini'
                              onClick={() => vettingAction({ action: 'greybox', question: box.question_id, mode: 'feedback', feedback_kind: 'like', greybox_id: box.id }, true)}
                            >
                              Like
                            </Button>
                            <Button
                              size='mini'
                              onClick={() => vettingAction({ action: 'greybox', question: box.question_id, mode: 'feedback', feedback_kind: 'dislike', greybox_id: box.id }, true)}
                            >
                              Dislike
                            </Button>
                          </Space>
                        </div>
                      ))}
                    </div>
                    <Space style={{ marginTop: 8 }}>
                      <Input
                        value={combineNote}
                        onChange={setCombineNote}
                        placeholder='Direction 4 → base, Direction 2 → header'
                        style={{ width: 300 }}
                      />
                      <Button
                        size='small'
                        disabled={busy || !combineNote.trim()}
                        onClick={() => {
                          const target =
                            (vetting.questions || []).find((question) => question.visual)?.id ||
                            (vetting.greyboxes || [])[0]?.question_id;
                          if (target) void vettingAction({ action: 'greybox', question: target, mode: 'combine', note: combineNote });
                        }}
                      >
                        Combine directions
                      </Button>
                    </Space>
                  </section>
                )}
                {(vetting.decisions || []).length > 0 && (
                  <section className='py-12px'>
                    <Typography.Title heading={6}>Decisions</Typography.Title>
                    {(vetting.decisions || []).map((decision, index) => (
                      <Typography.Paragraph key={index}>
                        {decision.statement}
                        {decision.rationale ? <Typography.Text type='secondary'> — {decision.rationale}</Typography.Text> : null}
                      </Typography.Paragraph>
                    ))}
                  </section>
                )}
                {vettingSpec && (
                  <section className='py-12px'>
                    <Typography.Title heading={6}>Spec preview</Typography.Title>
                    <Markdown>{vettingSpec}</Markdown>
                    <Button onClick={() => setVettingSpec('')}>Close preview</Button>
                  </section>
                )}
              </>
            )}
          </Tabs.TabPane>
          <Tabs.TabPane key='context' title={t('common.kel.context')}>
            <Form
              layout='vertical'
              onSubmit={() => {
                if (!project) return;
                try {
                  const command = checks.trim() ? JSON.parse(checks) : undefined;
                  void action('/api/project', {
                    id: project.id,
                    name: project.name,
                    root: project.root,
                    context,
                    test_command: command,
                  });
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              <Form.Item label={t('common.kel.project')}>
                <Select
                  value={projectId}
                  onChange={setProjectId}
                  options={state?.projects.map((p) => ({ value: p.id, label: p.name }))}
                />
              </Form.Item>
              <Typography.Paragraph type='secondary'>{project?.root}</Typography.Paragraph>
              <Form.Item label={t('common.kel.context')}>
                <Input.TextArea value={context} onChange={setContext} autoSize={{ minRows: 4 }} />
              </Form.Item>
              <Form.Item label={t('common.kel.checks')} extra={t('common.kel.checksHint')}>
                <Input.TextArea value={checks} onChange={setChecks} autoSize={{ minRows: 2 }} />
              </Form.Item>
              <Button type='primary' htmlType='submit' loading={busy}>
                {t('common.kel.save')}
              </Button>
            </Form>
          </Tabs.TabPane>
          <Tabs.TabPane key='history' title={t('common.kel.savedHistory')}>
            {state?.messages.map((m, i) => (
              <section key={i} className='py-12px'>
                <Typography.Text bold>{m.role === 'user' ? t('common.kel.you') : 'Kel'}</Typography.Text>
                <Markdown>{m.text}</Markdown>
              </section>
            ))}
          </Tabs.TabPane>
          <Tabs.TabPane key='continue' title={t('common.kel.continueWork')}>
            {(state?.continuation || []).length === 0 && (
              <Typography.Paragraph>{t('common.kel.noCandidates')}</Typography.Paragraph>
            )}
            {(state?.continuation || []).map((entry) => (
              <section key={entry.job_id} className='py-12px border-b border-solid border-[var(--color-border-2)]'>
                <Typography.Paragraph>{entry.title || entry.job_id}</Typography.Paragraph>
                <Typography.Paragraph type='secondary'>
                  {entry.state.toLowerCase().replace(/_/g, ' ')} · {entry.accepted}/{entry.total}
                </Typography.Paragraph>
                <Button
                  type='primary'
                  disabled={busy}
                  onClick={() =>
                    action('/api/send', {
                      id: crypto.randomUUID(),
                      conversation: cid,
                      text: 'continue ' + (entry.title || ''),
                      kind: 'continue',
                      job_id: entry.job_id,
                    })
                  }
                >
                  {t('common.kel.continueJob')}
                </Button>
              </section>
            ))}
          </Tabs.TabPane>
          <Tabs.TabPane key='knowledge' title={t('common.kel.knowledge')}>
            {(extras?.memory.conflicts || []).map((c) => (
              <section key={c.id} className='py-12px border-b border-solid border-[var(--color-border-2)]'>
                <Typography.Title heading={6}>{t('common.kel.conflicts')}</Typography.Title>
                <Typography.Paragraph>{t('common.kel.conflictPrompt')}</Typography.Paragraph>
                <Space wrap>
                  <Button onClick={() => action('/api/memory', { action: 'resolve_conflict', conversation: cid, id: c.id, choice: 'a' })}>
                    {t('common.kel.keepFirst')}
                  </Button>
                  <Button onClick={() => action('/api/memory', { action: 'resolve_conflict', conversation: cid, id: c.id, choice: 'b' })}>
                    {t('common.kel.keepSecond')}
                  </Button>
                  <Button onClick={() => action('/api/memory', { action: 'resolve_conflict', conversation: cid, id: c.id, choice: 'dismiss' })}>
                    {t('common.kel.leaveBoth')}
                  </Button>
                </Space>
              </section>
            ))}
            {(extras?.memory.records || []).length === 0 && (
              <Typography.Paragraph>{t('common.kel.knowledgeEmpty')}</Typography.Paragraph>
            )}
            {(extras?.memory.records || []).map((r) => (
              <section key={r.id} className='py-12px border-b border-solid border-[var(--color-border-2)]'>
                <Typography.Paragraph>
                  <Typography.Text bold>{r.topic}</Typography.Text> · {r.type} · {t('common.kel.trust')} {r.trust} · {r.status}
                </Typography.Paragraph>
                {draft && draft.id === r.id ? (
                  <>
                    <Input.TextArea
                      value={draft.summary}
                      onChange={(v) => setDraft({ id: r.id, summary: v })}
                      autoSize={{ minRows: 2 }}
                    />
                    <Space>
                      <Button
                        type='primary'
                        disabled={busy}
                        onClick={async () => {
                          await action('/api/memory', { action: 'correct', conversation: cid, id: r.id, summary: draft.summary });
                          setDraft(null);
                        }}
                      >
                        {t('common.kel.saveEdit')}
                      </Button>
                      <Button onClick={() => setDraft(null)}>{t('common.kel.cancelEdit')}</Button>
                    </Space>
                  </>
                ) : (
                  <>
                    <Typography.Paragraph>{r.summary}</Typography.Paragraph>
                    <Typography.Paragraph type='secondary'>
                      {t('common.kel.source')}: {r.source_type}{r.source_ref ? ' · ' + r.source_ref : ''}
                    </Typography.Paragraph>
                    <Space wrap>
                      {!r.user_confirmed && r.trust > 2 && r.trust < 7 && (
                        <Button disabled={busy} onClick={() => action('/api/memory', { action: 'confirm', conversation: cid, id: r.id })}>
                          {t('common.kel.confirmMemory')}
                        </Button>
                      )}
                      <Button disabled={busy} onClick={() => setDraft({ id: r.id, summary: r.summary })}>
                        {t('common.kel.editMemory')}
                      </Button>
                      <Button disabled={busy} onClick={() => action('/api/memory', { action: 'retract', conversation: cid, id: r.id, reason: 'work context' })}>
                        {t('common.kel.retractMemory')}
                      </Button>
                      <Button disabled={busy} status='danger' onClick={() => action('/api/memory', { action: 'forget', conversation: cid, id: r.id })}>
                        {t('common.kel.forgetMemory')}
                      </Button>
                    </Space>
                  </>
                )}
              </section>
            ))}
          </Tabs.TabPane>
          <Tabs.TabPane key='map' title={t('common.kel.projectMap')}>
            <Space>
              <Button type='primary' disabled={busy} onClick={() => action('/api/map', { action: 'refresh', conversation: cid })}>
                {t('common.kel.refreshMap')}
              </Button>
            </Space>
            {extras?.map ? (
              <>
                <Typography.Paragraph type='secondary'>
                  v{extras.map.version} · {extras.map.fingerprint.slice(0, 24)} · {extras.map.note}
                </Typography.Paragraph>
                {extras.map.sections.map((s) => (
                  <Typography.Paragraph key={s.name}>
                    <Typography.Text bold>{s.name}</Typography.Text> · {s.trust}
                    {s.stale ? ' · ' + t('common.kel.staleSection') : ''} · {s.sources.join(', ')}
                  </Typography.Paragraph>
                ))}
              </>
            ) : (
              <Typography.Paragraph>{t('common.kel.mapEmpty')}</Typography.Paragraph>
            )}
          </Tabs.TabPane>
          <Tabs.TabPane key='recipes' title={t('common.kel.recipes')}>
            {(extras?.recipes.entries || []).map((recipe) => (
              <section key={recipe.recipe_id} className='py-12px border-b border-solid border-[var(--color-border-2)]'>
                <Typography.Paragraph>
                  <Typography.Text bold>{recipe.name}</Typography.Text> · v{recipe.version} · {recipe.scope} · {recipe.kind}
                </Typography.Paragraph>
                <Space>
                  <Button
                    disabled={busy}
                    onClick={async () => {
                      try {
                        const result = await request<Record<string, unknown>>('/api/recipes', {
                          action: 'preview',
                          conversation: cid,
                          recipe_id: recipe.recipe_id,
                        });
                        setPreview(recipe.recipe_id + '\n' + previewText(result));
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    {t('common.kel.previewRecipe')}
                  </Button>
                  <Button type='primary' disabled={busy} onClick={() => action('/api/recipes', { action: 'run', conversation: cid, recipe_id: recipe.recipe_id })}>
                    {t('common.kel.runRecipe')}
                  </Button>
                </Space>
              </section>
            ))}
            {preview && (
              <section className='py-12px'>
                <pre className='whitespace-pre-wrap break-all'>{preview}</pre>
                <Button onClick={() => setPreview('')}>{t('common.kel.closePreview')}</Button>
              </section>
            )}
          </Tabs.TabPane>
        </Tabs>
      </Drawer>
      <Drawer
        title={t('common.kel.checkedReport')}
        visible={Boolean(report)}
        width={Math.min(800, window.innerWidth)}
        onCancel={() => setReport('')}
        footer={
          <Button
            onClick={() => {
              const url = URL.createObjectURL(new Blob([report], { type: 'text/markdown' }));
              const a = document.createElement('a');
              a.href = url;
              a.download = 'checked-report.md';
              a.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            }}
          >
            {t('common.kel.download')}
          </Button>
        }
      >
        <Markdown>{report}</Markdown>
      </Drawer>
    </>
  );
}
