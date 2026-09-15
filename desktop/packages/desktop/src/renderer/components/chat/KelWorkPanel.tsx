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
type State = {
  projects: Project[];
  conversations: { id: string; title: string; project_id: string }[];
  jobs: Job[];
  messages: { role: string; text: string }[];
  approvals: { id: string; job_id: string; action: string }[];
};
declare global {
  interface Window {
    kelAPI?: {
      request: (route: string, body?: unknown) => Promise<unknown>;
      history: (id: string) => Promise<import('@/common/chat/chatLib').TMessage[]>;
      conversation: (id: string) => Promise<string | null>;
      historySearch: (query: string) => Promise<import('@/common/chat/chatLib').TMessage[]>;
    };
  }
}
async function request<T>(route: string, body?: unknown): Promise<T> {
  if (!window.kelAPI) throw Error('Kel connection is unavailable');
  return (await window.kelAPI.request(route, body)) as T;
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
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const refresh = async () => {
    try {
      const data = await request<State>('/api/state?conversation=' + cid);
      setState(data);
      setPendingApprovals((data.approvals || []).length);
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
      .then((saved) => {
        if (saved) setCid(saved);
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
        <Button long type='text' onClick={() => setVisible(true)}>
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
