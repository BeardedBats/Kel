/** Kel work controls, using AionUI's Arco components and theme tokens. */
import React, { useEffect, useState } from 'react';
import { Badge, Button, Drawer, Modal, Popconfirm, Select, Input, Form, Alert, Space, Typography, Tabs, Message } from '@arco-design/web-react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router-dom';
import Markdown from '@/renderer/components/Markdown';
import { MemoryProposal, MemoryProposalReview } from '@/renderer/components/kel/KelMemoryProposal';
import { memoryRecordActions } from '@/renderer/components/kel/memoryRecordActions';
import { KelCapabilityCard } from '@/renderer/components/kel/KelCapabilityCard';
import type { CapabilityRecommendation } from '@/renderer/components/kel/capabilityRecommendation';
import type { ApprovalItem as WaitingItem } from '@/renderer/components/kel/KelApprovalCard';
type Project = { id: string; name: string; root: string; context: string; test_command?: string[] };
type Job = {
  id: string;
  state: string;
  verdict: string;
  contract: { request: string; kind: string; milestones: { id: string; filename: string }[] };
  milestones: Record<string, { state: string; error?: string; recommendation?: CapabilityRecommendation | null }>;
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
type LineageVersion = {
  id: string;
  filename: string;
  relpath: string;
  bytes: number | null;
  created: number;
  conversation_id: string;
  project_id: string;
  run_id: string;
  turn_ref: string;
  supersedes: string | null;
  superseded_by: string | null;
};
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
  memory: { records: MemoryRecord[]; conflicts: MemoryConflict[]; proposals?: MemoryProposal[] };
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
    [waiting, setWaiting] = useState<WaitingItem[]>([]),
    [extras, setExtras] = useState<WorkExtras>(),
    [preview, setPreview] = useState(''),
    [draft, setDraft] = useState<{ id: string; summary: string } | null>(null);
  const [history, setHistory] = useState<{ at: number; text: string }[] | null>(null);
  const [lineage, setLineage] = useState<{ request: string; versions: LineageVersion[] } | null>(null);
  const [dismissed, setDismissed] = useState<Record<string, boolean>>({});
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
  const loadWaiting = async (conversation: string) => {
    try {
      const out = await request<{ items: WaitingItem[] }>(
        '/api/approvals?conversation=' + conversation
      );
      const pending = (out.items || []).filter((item) => item.state === 'pending');
      setWaiting(pending);
      setPendingApprovals(pending.length);
    } catch {
      /* the badge keeps its last value; chat still shows its own cards */
    }
  };
  const refresh = async () => {
    try {
      const data = await request<State>('/api/state?conversation=' + cid);
      setState(data);
      await loadWaiting(cid);
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
        await loadWaiting(active);
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
        await loadWaiting(cid);
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
  async function approvalAct(item: WaitingItem, extra: Record<string, unknown> = {}) {
    // Same durable resolution the chat card uses; Work simply reflects it right after.
    // The declared conversation scopes the resolution exactly like the read path (APR-02).
    const allow = extra.allow !== false;
    await action('/api/approvals', { kind: item.kind, id: item.id, allow, conversation: cid, ...extra });
  }
  async function loadHistory() {
    try {
      const out = await request<{ entries: { at: number; text: string }[] }>('/api/memory', {
        action: 'history',
        conversation: cid,
      });
      setHistory(out.entries || []);
    } catch {
      setHistory([]);
    }
  }
  useEffect(() => {
    if (!visible) return;
    void loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, cid]);
  async function memoryAct(p: MemoryProposal, act: 'accept' | 'reject' | 'defer') {
    setBusy(true);
    try {
      await request('/api/memory', { action: act + '_proposal', conversation: cid, id: p.id });
      await refresh();
      void loadHistory();
      Message.success(
        act === 'accept'
          ? 'Saved knowledge updated.'
          : act === 'reject'
            ? 'Kept what was saved.'
            : 'Postponed — Kel will wait.'
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function openLineage(job: Job, m: { id: string; filename: string }) {
    try {
      const out = await request<{ versions: LineageVersion[] }>(
        '/api/lineage?job=' + job.id + '&milestone=' + m.id
      );
      setLineage({ request: job.contract.request, versions: out.versions || [] });
    } catch (e) {
      setError(String(e));
    }
  }
  async function revealArtifact(relpath: string) {
    try {
      const api = (window as unknown as { kelAPI?: { revealArtifact?: (p: string) => Promise<unknown> } }).kelAPI;
      await api?.revealArtifact?.(relpath);
    } catch (e) {
      setError(String(e));
    }
  }
  async function copyArtifactPath(relpath: string) {
    try {
      await navigator.clipboard.writeText(relpath);
      Message.success('Path copied.');
    } catch {
      setError('Could not copy the path.');
    }
  }
  const conversationName = (id: string) => state?.conversations.find((c) => c.id === id)?.title || '';
  const projectName = (id: string) => state?.projects.find((p) => p.id === id)?.name || '';
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
                      <React.Fragment key={m.id}>
                        <Button
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
                        <Button
                          size='small'
                          onClick={() => void openLineage(job, m)}
                          data-testid='kel-lineage-open'
                        >
                          {'Where from?'}
                        </Button>
                      </React.Fragment>
                    ))}
                </Space>
                {Object.entries(job.milestones || {})
                  .filter(([mid, m]) => m.recommendation && !dismissed[job.id + ':' + mid])
                  .map(([mid, m]) => (
                    <KelCapabilityCard
                      key={job.id + ':' + mid}
                      conversation={cid}
                      recommendation={m.recommendation as CapabilityRecommendation}
                      detail={m.error}
                      onDone={() => setDismissed((d) => ({ ...d, [job.id + ':' + mid]: true }))}
                    />
                  ))}
              </section>
            ))}
            {waiting.map((item) => (
              <section key={item.kind + ':' + item.id} className='py-16px' data-testid='kel-work-waiting'>
                <Typography.Title heading={6}>
                  {item.kind === 'access' ? 'Access needed' : t('common.kel.approval')}
                </Typography.Title>
                <div data-testid='kel-work-waiting-title'>
                  <Typography.Text bold>{item.title}</Typography.Text>
                </div>
                {item.target ? (
                  <div
                    className='mt-4px text-12px break-all text-t-secondary'
                    data-testid='kel-work-waiting-target'
                  >
                    {item.target}
                  </div>
                ) : null}
                {item.summary ? <div className='mt-4px text-12px'>It wants to {item.summary}.</div> : null}
                {item.why ? (
                  <div className='mt-4px text-12px text-t-secondary' data-testid='kel-work-waiting-why'>
                    {item.why}
                  </div>
                ) : null}
                <Space className='mt-8px' wrap>
                  {item.kind === 'access' ? (
                    <>
                      <Button
                        data-testid='kel-work-allow-once'
                        onClick={() => void approvalAct(item, { grant_kind: 'once' })}
                      >
                        Allow once
                      </Button>
                      <Button
                        data-testid='kel-work-allow-project'
                        onClick={() => void approvalAct(item, { grant_kind: 'project' })}
                      >
                        Allow for this project
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button data-testid='kel-work-allow' onClick={() => void approvalAct(item)}>
                        Approve
                      </Button>
                      {item.repeatable ? (
                        <Button
                          data-testid='kel-work-remember'
                          onClick={() => void approvalAct(item, { remember: true })}
                        >
                          Always allow
                        </Button>
                      ) : null}
                    </>
                  )}
                  <Button
                    data-testid='kel-work-deny'
                    onClick={() => void approvalAct(item, { allow: false })}
                  >
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
            {(extras?.memory.proposals || [])
              .filter((p) => p.state === 'pending' || p.state === 'deferred')
              .map((p) => (
                <section
                  key={p.id}
                  className='py-12px border-b border-solid border-[var(--color-border-2)]'
                  data-testid='kel-work-proposal'
                >
                  <MemoryProposalReview proposal={p} busy={busy} onAct={(act) => void memoryAct(p, act)} />
                </section>
              ))}
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
            {(extras?.memory.records || []).map((r) => {
              const acts = memoryRecordActions(r);
              return (
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
                    <Typography.Paragraph>{r.summary || 'Content removed.'}</Typography.Paragraph>
                    <Typography.Paragraph type='secondary'>
                      {t('common.kel.source')}: {r.source_type}{r.source_ref ? ' · ' + r.source_ref : ''}
                    </Typography.Paragraph>
                    <Space wrap>
                      {acts.confirm && (
                        <Button disabled={busy} onClick={() => action('/api/memory', { action: 'confirm', conversation: cid, id: r.id })}>
                          {t('common.kel.confirmMemory')}
                        </Button>
                      )}
                      {acts.edit && (
                        <Button disabled={busy} onClick={() => setDraft({ id: r.id, summary: r.summary })}>
                          {t('common.kel.editMemory')}
                        </Button>
                      )}
                      {acts.retract && (
                        <Button disabled={busy} onClick={() => action('/api/memory', { action: 'retract', conversation: cid, id: r.id, reason: 'work context' })}>
                          {t('common.kel.retractMemory')}
                        </Button>
                      )}
                      {acts.forget && (
                        <Popconfirm
                          title='Forget this record?'
                          content='Its saved content is removed and cannot be recovered. A blank placeholder stays in the history.'
                          okText='Forget'
                          cancelText='Cancel'
                          onOk={() => action('/api/memory', { action: 'forget', conversation: cid, id: r.id })}
                        >
                          <Button disabled={busy} status='danger'>
                            {t('common.kel.forgetMemory')}
                          </Button>
                        </Popconfirm>
                      )}
                    </Space>
                  </>
                )}
              </section>
              );
            })}
            <Typography.Title heading={6} style={{ marginTop: 16 }}>
              {'What changed'}
            </Typography.Title>
            {(history || []).length === 0 ? (
              <Typography.Paragraph type='secondary' data-testid='kel-memory-history-empty'>
                {'Nothing has changed in what Kel knows about this project yet.'}
              </Typography.Paragraph>
            ) : (
              (history || []).map((h, i) => (
                <Typography.Paragraph key={`${h.at}-${i}`} type='secondary' data-testid='kel-memory-history-entry'>
                  {new Date(h.at * 1000).toLocaleDateString()} — {h.text}
                </Typography.Paragraph>
              ))
            )}
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
      <Modal
        title='Where this file came from'
        visible={Boolean(lineage)}
        footer={null}
        onCancel={() => setLineage(null)}
        autoFocus={false}
        style={{ width: 520 }}
        unmountOnExit
      >
        {lineage ? (
          <div className='text-12px leading-20px' data-testid='kel-lineage-body'>
            <Typography.Paragraph type='secondary'>
              {'You asked: '}
              {lineage.request}
            </Typography.Paragraph>
            {lineage.versions.map((v, i) => (
              <section key={v.id} className='py-8px border-b border-solid border-[var(--color-border-2)]'>
                <Typography.Paragraph>
                  <Typography.Text bold>{v.filename}</Typography.Text>
                  {i === 0 ? <Typography.Text type='secondary'>{' · current version'}</Typography.Text> : null}
                </Typography.Paragraph>
                <Typography.Paragraph type='secondary'>
                  {(conversationName(v.conversation_id) || 'This work') +
                    (projectName(v.project_id) ? ' · ' + projectName(v.project_id) : '') +
                    ' · ' +
                    new Date(v.created * 1000).toLocaleString() +
                    (v.bytes ? ' · ' + Math.round(v.bytes / 102.4) / 10 + ' KB' : '')}
                </Typography.Paragraph>
                <Space wrap size={6}>
                  <Button
                    size='small'
                    onClick={async () => {
                      try {
                        setReport(await request<string>('/api/artifact?lineage=' + v.id));
                        setLineage(null);
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    {i === 0 ? 'Open' : 'Open this version'}
                  </Button>
                  <Button size='small' onClick={() => void revealArtifact(v.relpath)}>
                    {'Show in folder'}
                  </Button>
                  <Button size='small' onClick={() => void copyArtifactPath(v.relpath)}>
                    {'Copy path'}
                  </Button>
                </Space>
              </section>
            ))}
            <Typography.Paragraph type='secondary'>
              {'Kel produced this file while working on the task above; every earlier version stays readable here.'}
            </Typography.Paragraph>
          </div>
        ) : null}
      </Modal>
    </>
  );
}
