/**
 * Kel in-chat approvals — the decision card that appears in the conversation where Kel is waiting.
 *
 * Pending: plain-language buttons (Allow once / Allow for this project / Deny, or Approve / Deny).
 * Resolved: the same card stays in history as a plain sentence ("Allowed once"), so old active
 * buttons never linger. Every action goes through the Kel engine's durable approval records —
 * the card is a presentation surface only, and it reads live state, so chat and Work agree.
 */
import { Modal, Typography } from '@arco-design/web-react';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

export type ApprovalItem = {
  id: string;
  kind: 'access' | 'action';
  state: 'pending' | 'allowed_once' | 'allowed_project' | 'approved' | 'denied' | 'expired';
  created?: number | null;
  resolved_at?: number | null;
  job_id?: string | null;
  title: string;
  target?: string | null;
  context_title?: string | null;
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
      return 'Allowed once. Kel is continuing.';
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

const actionTarget = (item: ApprovalItem): string | null => {
  if (item.target) return item.target;
  const summary = item.summary || '';
  return summary.startsWith('run ') ? summary.slice(4) : null;
};

const actionDescription = (item: ApprovalItem): string => {
  const target = actionTarget(item);
  if (target) {
    const action = /\bbuild\b/i.test(target) ? 'a build command' : 'a command';
    const context = item.context_title ? ` in ${item.context_title}` : '';
    return `It wants to run ${action}${context}.`;
  }
  return item.summary ? `It wants to ${item.summary}.` : '';
};

const approvalDetailAction = (item: ApprovalItem, kind: 'access' | 'action'): string => {
  if (kind === 'access') return item.target || item.what || headline(item, kind);
  const target = actionTarget(item);
  if (!target) return item.what || item.summary || headline(item, kind);
  const context = item.context_title ? ` in ${item.context_title}` : '';
  return `Run ${target}${context}.`;
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
  const [mobile, setMobile] = useState(() => Boolean(window.matchMedia?.('(max-width: 767px)').matches));
  const inFlight = useRef(false);

  useEffect(() => {
    const query = window.matchMedia?.('(max-width: 767px)');
    if (!query) return;
    const onChange = () => setMobile(query.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    if (!details || !mobile) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') setDetails(false); };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [details, mobile]);

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
      await kelApprovalRequest({ kind, id: refId, allow, conversation: engineCid || conversationId, ...extra });
      await refresh();
      setDetails(false);
    } catch (error) {
      // Audit APR-06: every failure used to be reported as "already settled" — an incorrect claim
      // about the state of the user's approval. The engine's sentence is the truth when it arrived;
      // a transport failure says so instead of guessing, and the refresh still self-corrects.
      const detail = String((error as Error)?.message || '').trim();
      const unreachable = !detail
        || /fetch failed|failed to fetch|NetworkError|ECONNREFUSED|ECONNRESET|socket|timed out|timeout|invoking remote method/i.test(detail);
      setNotice(unreachable
        ? 'Kel could not reach its engine just now, so that decision was not recorded — it refreshed the latest state.'
        : detail);
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
      <div className='kel-approval-card kel-approval-card--resolved'
        data-testid='kel-approval-card'>
        <span data-testid='kel-approval-resolved'>This request is no longer active.</span>
      </div>
    );
  }

  const pending = item.state === 'pending';
  const target = kind === 'action' ? actionTarget(item) : item.target;

  return (
    <div className={`kel-approval-card kel-approval-card--${pending ? 'pending' : 'resolved'} kel-approval-card--${kind}`}
      data-testid='kel-approval-card'>
      {pending ? <>
        <div className='kel-approval-card__heading'>
          <svg aria-hidden='true' className='kel-approval-card__shield' viewBox='0 0 16 16' fill='none'>
            <path d='M8 1.5 13 3.3v4.1c0 3.2-2 5.5-5 7.1-3-1.6-5-3.9-5-7.1V3.3L8 1.5Z' stroke='currentColor' strokeWidth='1.3' strokeLinejoin='round' />
          </svg>
          <strong data-testid='kel-approval-headline'>
            <span className='kel-approval-card__headline-desktop'>{headline(item, kind)}</span>
            <span className='kel-approval-card__headline-mobile'>{kind === 'action' ? 'Kel needs your OK' : headline(item, kind)}</span>
          </strong>
        </div>
        <div className='kel-approval-card__body' data-testid='kel-approval-body'>
          {kind === 'action' && item.summary ? <div>{actionDescription(item)}</div> : null}
          {item.what ? <div>{item.what}</div> : null}
          {item.why ? <div data-testid='kel-approval-why'>{item.why}</div> : null}
        </div>
        {target ? <div className='kel-approval-card__target' data-testid='kel-approval-target'>{target}</div> : null}
        <div className='kel-approval-card__actions'>
          <button className='kel-approval-card__details' type='button' data-testid='kel-approval-details'
            onClick={() => setDetails(true)}>Details</button>
          <div className='kel-approval-card__decisions'>
          {kind === 'access' ? (
            <>
              <button type='button' disabled={busy} data-testid='kel-approval-allow-once'
                onClick={() => void act(true, { grant_kind: 'once' })}>
                Allow once
              </button>
              <button type='button' disabled={busy} data-testid='kel-approval-allow-project'
                onClick={() => void act(true, { grant_kind: 'project' })}>
                Allow for this project
              </button>
            </>
          ) : (
            <>
              <button className='kel-approval-card__approve' type='button' disabled={busy} data-testid='kel-approval-approve'
                onClick={() => void act(true)}>
                Approve
              </button>
              {item.repeatable ? (
                <button className='kel-approval-card__remember' type='button' disabled={busy} data-testid='kel-approval-remember'
                  onClick={() => void act(true, { remember: true })}>
                  <span className='kel-approval-card__remember-desktop'>Always allow for this project</span>
                  <span className='kel-approval-card__remember-mobile'>Always allow here</span>
                </button>
              ) : null}
            </>
          )}
          <button className='kel-approval-card__deny' type='button' disabled={busy} data-testid='kel-approval-deny'
            onClick={() => void act(false)}>
            Deny
          </button>
          </div>
        </div>
      </> : (
        <div className='kel-approval-card__settled'>
          <span className='kel-approval-card__check' aria-hidden='true'>✓</span>
          <strong data-testid='kel-approval-resolved'>{resolvedWords(item)}</strong>
          <span className='kel-approval-card__status'>{item.state === 'denied' ? 'Denied' : item.state === 'expired' ? 'Expired' : item.state === 'approved' ? 'Approved' : 'Allowed'}</span>
        </div>
      )}
      {notice ? (
        <div className='mt-8px text-11px text-t-secondary' data-testid='kel-approval-notice'>
          {notice}
        </div>
      ) : null}
      {mobile && details ? createPortal(
        <div className='kel-mobile-model-picker kel-mobile-approval-details' data-testid='kel-mobile-approval-details'>
          <button type='button' className='kel-mobile-model-picker__scrim' aria-label='Close approval details' onClick={() => setDetails(false)} />
          <section className='kel-mobile-model-picker__sheet kel-mobile-approval-details__sheet' role='dialog' aria-modal='true' aria-label={kind === 'access' ? 'Access request' : 'Approval request'}>
            <div className='kel-mobile-model-picker__handle' aria-hidden='true' />
            <h2>
              <svg aria-hidden='true' viewBox='0 0 18 18' fill='none'><path d='M9 1.7 14.6 3.8v4.5c0 3.3-2.1 5.9-5.6 7.7-3.5-1.8-5.6-4.4-5.6-7.7V3.8L9 1.7Z' stroke='currentColor' strokeWidth='1.4' strokeLinejoin='round' /></svg>
              {kind === 'access' ? 'Access request' : 'Approval request'}
            </h2>
            <div className='kel-mobile-approval-details__content' data-testid='kel-approval-details-body'>
              <div><strong>{kind === 'access' ? 'What Kel wants access to' : 'What Kel wants to do'}</strong><p>{approvalDetailAction(item, kind)}</p></div>
              <div><strong>Why</strong><p>{item.why || (kind === 'action' ? 'Building runs scripts from this project, so Kel asks first.' : 'Kel asks before using this access.')}</p></div>
              <div><strong>If you say no</strong><p>{item.fallback || 'Kel stops this step and tells you what it could not check.'}</p></div>
              {pending && item.repeatable ? <button type='button' className='kel-mobile-approval-details__remember' disabled={busy} onClick={() => void act(true, { remember: true })}>Always allow for this project</button> : null}
            </div>
            {pending ? <div className='kel-mobile-approval-details__foot'>
              <button type='button' className='kel-mobile-approval-details__approve' disabled={busy} onClick={() => void act(true)}>Approve</button>
              <button type='button' className='kel-mobile-approval-details__deny' disabled={busy} onClick={() => void act(false)}>Deny</button>
            </div> : null}
          </section>
        </div>, document.body
      ) : null}
      {!mobile && <Modal
        className={kind === 'action' ? 'kel-shell-approval-details-modal' : undefined}
        title={kind === 'access' ? 'Access request' : <span className='kel-shell-approval-details-title'><svg aria-hidden='true' viewBox='0 0 16 16' fill='none'><path d='M8 1.5 13 3.3v4.1c0 3.2-2 5.5-5 7.1-3-1.6-5-3.9-5-7.1V3.3L8 1.5Z' stroke='currentColor' strokeWidth='1.3' strokeLinejoin='round' /></svg>Approval request</span>}
        visible={details}
        footer={null}
        onCancel={() => setDetails(false)}
        autoFocus={false}
        style={{ width: kind === 'action' ? 560 : 440 }}
        unmountOnExit
      >
        {kind === 'action' ? <div className='kel-shell-approval-details' data-testid='kel-approval-details-body'>
          <p className='kel-shell-approval-details-subtitle'>Nothing happens until you decide.</p>
          <div><strong>What Kel wants to do</strong><p>{approvalDetailAction(item, kind)}</p></div>
          <div><strong>What for</strong><p>{item.what || `To continue this work${item.context_title ? ` in ${item.context_title}` : ''}.`}</p></div>
          <div><strong>Why</strong><p>{item.why || (actionTarget(item) ? 'A command can run project code, so Kel asks first.' : 'This step needs your approval before Kel can continue.')}</p></div>
          <div><strong>What approving allows</strong><p>{item.benefit || (actionTarget(item) ? 'This one command, this one time.' : 'This one step, this one time.')}</p></div>
          <div><strong>If you say no</strong><p>{item.fallback || 'Kel stops this step and tells you what it could not check.'}</p></div>
          {pending ? <div className='kel-shell-approval-details-actions'>
            <button type='button' disabled={busy} onClick={() => void act(false)}>Deny</button>
            {item.repeatable ? <button type='button' disabled={busy} onClick={() => void act(true, { remember: true })}>Always allow for this project</button> : null}
            <button type='button' disabled={busy} onClick={() => void act(true)}>Approve</button>
          </div> : null}
        </div> : <div className='text-12px leading-20px' data-testid='kel-approval-details-body'>
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
        </div>}
      </Modal>}
    </div>
  );
};

export default KelApprovalCard;
