/**
 * Kel in-chat approvals — the decision card that appears in the conversation where Kel is waiting.
 *
 * Pending: plain-language buttons (Allow once / Allow for this project / Deny, or Approve / Deny).
 * Resolved: the same card stays in history as a plain sentence ("Allowed once"), so old active
 * buttons never linger. Every action goes through the Kel engine's durable approval records —
 * the card is a presentation surface only, and it reads live state, so chat and Work agree.
 */
import { Button, Modal, Space, Typography } from '@arco-design/web-react';
import React, { useCallback, useEffect, useRef, useState } from 'react';

export type ApprovalItem = {
  id: string;
  kind: 'access' | 'action';
  state: 'pending' | 'allowed_once' | 'allowed_project' | 'approved' | 'denied' | 'expired';
  created?: number | null;
  resolved_at?: number | null;
  job_id?: string | null;
  title: string;
  target?: string | null;
  what?: string | null;
  why?: string | null;
  benefit?: string | null;
  fallback?: string | null;
  summary?: string | null;
  repeatable?: boolean | null;
  seconds_left?: number | null;
  message_seq?: number | null;
  message_at?: number | null;
};

const api = () =>
  (
    window as unknown as {
      kelAPI?: {
        request: (route: string, payload?: unknown) => Promise<unknown>;
        conversation?: (id: string) => Promise<unknown>;
      };
    }
  ).kelAPI;

/** Mirrored rows carry the donor conversation id; the engine reads need its own id. */
export const resolveEngineConversation = async (id: string): Promise<string> => {
  try {
    const value = (await api()?.conversation?.(id)) ?? null;
    if (typeof value === 'string' && value) return value;
    const fromObject = value && typeof value === 'object' ? (value as { id?: string }).id : null;
    if (fromObject) return fromObject;
  } catch {
    /* fall back to the id we were given */
  }
  return id;
};

export const kelApprovalRequest = <T,>(body: Record<string, unknown>): Promise<T> => {
  const bridge = api();
  if (!bridge) return Promise.reject(new Error('Kel connection is unavailable'));
  return bridge.request('/api/approvals', body) as Promise<T>;
};

export const fetchApprovalItems = async (conversationId: string): Promise<ApprovalItem[]> => {
  const bridge = api();
  if (!bridge) return [];
  const out = (await bridge.request(
    `/api/approvals?conversation=${encodeURIComponent(conversationId)}`
  )) as { items?: ApprovalItem[] } | null;
  return out?.items || [];
};

const resolvedWords = (item: ApprovalItem): string => {
  switch (item.state) {
    case 'allowed_once':
      return 'Allowed once — Kel is continuing.';
    case 'allowed_project':
      return 'Allowed for this project — Kel won\u2019t need to ask again for this.';
    case 'approved':
      return 'Approved — Kel is continuing.';
    case 'denied':
      return item.kind === 'access'
        ? 'Denied — Kel will not ask again for this.'
        : 'Denied — Kel stopped this step.';
    case 'expired':
      return 'Expired — this request is no longer active.';
    default:
      return 'This request is no longer active.';
  }
};

const headline = (item: ApprovalItem | null | undefined, kind: 'access' | 'action'): string => {
  if (item?.title) return item.title;
  return kind === 'access' ? 'Kel needs access to continue' : 'Kel needs your OK to continue';
};

type CardProps = {
  kind: 'access' | 'action';
  refId: string;
  conversationId: string;
};

export const KelApprovalCard: React.FC<CardProps> = ({ kind, refId, conversationId }) => {
  const [item, setItem] = useState<ApprovalItem | null | undefined>(undefined);
  const [engineCid, setEngineCid] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [details, setDetails] = useState(false);
  const inFlight = useRef(false);

  useEffect(() => {
    let alive = true;
    void resolveEngineConversation(conversationId).then((cid) => {
      if (alive) setEngineCid(cid);
    });
    return () => {
      alive = false;
    };
  }, [conversationId]);

  const refresh = useCallback(async () => {
    if (!engineCid) return;
    try {
      const items = await fetchApprovalItems(engineCid);
      const found = items.find((row) => row.kind === kind && row.id === refId) || null;
      setItem(found);
    } catch {
      // Keep the last known state; the next poll retries.
    }
  }, [engineCid, kind, refId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!item || item.state !== 'pending') return;
    const timer = setInterval(() => void refresh(), 3000);
    return () => clearInterval(timer);
  }, [item, refresh]);

  const act = async (allow: boolean, extra: Record<string, unknown> = {}) => {
    // One durable resolution: a double-click can never submit twice.
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setNotice('');
    try {
      await kelApprovalRequest({ kind, id: refId, allow, ...extra });
      await refresh();
    } catch {
      setNotice('That request was already settled — Kel refreshed the latest state.');
      await refresh();
    } finally {
      setBusy(false);
      inFlight.current = false;
    }
  };

  if (item === undefined) {
    return null; // still loading; the message text above already explains the pause
  }
  if (item === null) {
    return (
      <div className='w-360px max-w-[84vw] hairline-border rounded-8px p-12px bg-[var(--color-bg-2)]'
        data-testid='kel-approval-card'>
        <Typography.Text className='text-13px'>
          This request is no longer active.
        </Typography.Text>
      </div>
    );
  }

  const pending = item.state === 'pending';

  return (
    <div className='w-360px max-w-[84vw] hairline-border rounded-8px p-12px bg-[var(--color-bg-2)]'
      data-testid='kel-approval-card'>
      <Typography.Text bold className='text-13px' data-testid='kel-approval-headline'>
        {headline(item, kind)}
      </Typography.Text>
      {item.target ? (
        <div className='mt-6px text-12px rounded-6px px-8px py-6px break-all'
          style={{ background: 'var(--color-fill-2)' }} data-testid='kel-approval-target'>
          {item.target}
        </div>
      ) : null}
      <div className='mt-8px text-12px leading-18px text-t-secondary' data-testid='kel-approval-body'>
        {kind === 'action' && item.summary ? <div>{`It wants to ${item.summary}.`}</div> : null}
        {item.what ? <div className='mt-2px'>{item.what}</div> : null}
        {item.why ? <div className='mt-2px' data-testid='kel-approval-why'>{item.why}</div> : null}
        {pending ? <div className='mt-2px'>Kel is paused until you decide.</div> : null}
      </div>
      {pending ? (
        <Space className='mt-10px' wrap size={6}>
          {kind === 'access' ? (
            <>
              <Button type='primary' size='small' disabled={busy} data-testid='kel-approval-allow-once'
                onClick={() => void act(true, { grant_kind: 'once' })}>
                Allow once
              </Button>
              <Button size='small' disabled={busy} data-testid='kel-approval-allow-project'
                onClick={() => void act(true, { grant_kind: 'project' })}>
                Allow for this project
              </Button>
            </>
          ) : (
            <>
              <Button type='primary' size='small' disabled={busy} data-testid='kel-approval-approve'
                onClick={() => void act(true)}>
                Approve
              </Button>
              {item.repeatable ? (
                <Button size='small' disabled={busy} data-testid='kel-approval-remember'
                  onClick={() => void act(true, { remember: true })}>
                  Always allow for this project
                </Button>
              ) : null}
            </>
          )}
          <Button size='small' disabled={busy} data-testid='kel-approval-deny'
            onClick={() => void act(false)}>
            Deny
          </Button>
          <Button size='small' type='text' data-testid='kel-approval-details'
            onClick={() => setDetails(true)}>
            Details
          </Button>
        </Space>
      ) : (
        <div className='mt-8px text-12px' data-testid='kel-approval-resolved'>
          {resolvedWords(item)}
        </div>
      )}
      {notice ? (
        <div className='mt-8px text-11px text-t-secondary' data-testid='kel-approval-notice'>
          {notice}
        </div>
      ) : null}
      <Modal
        title={kind === 'access' ? 'Access request' : 'Approval request'}
        visible={details}
        footer={null}
        onCancel={() => setDetails(false)}
        autoFocus={false}
        style={{ width: 440 }}
        unmountOnExit
      >
        <div className='text-12px leading-20px' data-testid='kel-approval-details-body'>
          <Typography.Paragraph>
            <Typography.Text bold>
              {kind === 'access' ? 'What Kel wants access to' : 'What Kel wants to do'}
            </Typography.Text>
            <br />
            {item.target || (item.summary ? `It wants to ${item.summary}.` : headline(item, kind))}
          </Typography.Paragraph>
          {item.what ? (
            <Typography.Paragraph>
              <Typography.Text bold>What for</Typography.Text>
              <br />
              {item.what}
            </Typography.Paragraph>
          ) : null}
          {item.why ? (
            <Typography.Paragraph>
              <Typography.Text bold>Why</Typography.Text>
              <br />
              {item.why}
            </Typography.Paragraph>
          ) : null}
          {item.benefit ? (
            <Typography.Paragraph>
              <Typography.Text bold>What approving allows</Typography.Text>
              <br />
              {item.benefit}
            </Typography.Paragraph>
          ) : null}
          <Typography.Paragraph>
            <Typography.Text bold>If you say no</Typography.Text>
            <br />
            {item.fallback || 'Kel stops this step and keeps everything else as it is.'}
          </Typography.Paragraph>
          <Typography.Paragraph type='secondary'>
            {pending
              ? 'Nothing happens until you decide. Your choice applies everywhere in Kel.'
              : 'This decision is settled; the card stays here so history makes sense.'}
          </Typography.Paragraph>
        </div>
      </Modal>
    </div>
  );
};

export default KelApprovalCard;
