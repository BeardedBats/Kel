/**
 * Kel memory proposals — the review queue for saved project knowledge, in plain words.
 *
 * When Kel believes something the project saved has changed (a Design Vetting decision disagrees
 * with a stored rule, two saved choices conflict, or the source behind a record moved on), the
 * change waits here until you accept, reject or postpone it. Nothing is overwritten until you
 * accept, and the same unchanged evidence never asks twice after a rejection.
 */
import { Button, Message, Modal, Popover, Space, Typography } from '@arco-design/web-react';
import React, { useCallback, useEffect, useState } from 'react';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';
import './kel-desktop-chat-menus.css';

export type MemoryProposal = {
  id: string;
  kind: string;
  type: string;
  topic: string;
  summary: string;
  why: string;
  state: string;
  value: unknown;
  current: { summary?: string; value?: unknown; status?: string } | null;
  evidence: Record<string, unknown>;
  source_ref: string;
  created: number;
};

export const memoryRequest = <T,>(body: Record<string, unknown>): Promise<T> => {
  const api = (window as unknown as { kelAPI?: { request: (route: string, payload?: unknown) => Promise<unknown> } }).kelAPI;
  if (!api) return Promise.reject(new Error('Kel connection is unavailable'));
  return api.request('/api/memory', body) as Promise<T>;
};

const headlineWords = (kind: string): string => {
  switch (kind) {
    case 'vetting':
      return 'Kel thinks this project decision changed.';
    case 'conflict':
      return 'Two saved choices disagree.';
    case 'stale':
      return 'This knowledge may be out of date.';
    case 'repo_state':
      return 'The project files suggest an update.';
    default:
      return 'Kel suggests updating saved knowledge.';
  }
};

const sourceWords = (proposal: MemoryProposal): string => {
  switch (proposal.kind) {
    case 'vetting':
      return 'Your latest Design Vetting decisions';
    case 'conflict':
      return 'Two saved choices in this project';
    case 'stale': {
      const ref = proposal.source_ref || '';
      return ref.startsWith('file:') ? `The file ${ref.slice(5)} changed` : 'The source behind this knowledge';
    }
    case 'repo_state':
      return 'The state of the project';
    default:
      return 'Project activity';
  }
};

const currentWords = (proposal: MemoryProposal): string => {
  if (!proposal.current || !proposal.current.summary) return 'Nothing saved yet.';
  return proposal.current.summary;
};

type ReviewProps = {
  proposal: MemoryProposal;
  busy: boolean;
  onAct: (act: 'accept' | 'reject' | 'defer') => void;
  total?: number;
};

export const MemoryProposalReview: React.FC<ReviewProps> = ({ proposal, busy, onAct, total = 1 }) => {
  const desktop = !useLayoutContext()?.isMobile;
  const [details, setDetails] = useState(false);
  const [visible, setVisible] = useState(false);
  return (
    <div className='kel-memory-review w-360px max-w-[84vw] hairline-border rounded-8px p-12px bg-[var(--color-bg-2)]' data-testid='kel-memory-proposal'>
      <div className='kel-memory-review__head'>
      <Typography.Text bold className='text-13px'>
        {headlineWords(proposal.kind)}
      </Typography.Text>
      {desktop && <span className='kel-memory-review__count'>1 of {total}</span>}
      </div>
      <div className='kel-memory-review__lines mt-8px text-12px leading-18px'>
        <div className='kel-memory-review__label text-t-secondary'>Current</div>
        <div className='kel-memory-review__value mt-2px rounded-6px px-8px py-6px' style={{ background: 'var(--color-fill-2)' }} data-testid='kel-memory-current'>
          {currentWords(proposal)}
        </div>
        <div className='kel-memory-review__label mt-8px text-t-secondary'>Proposed</div>
        <div className='kel-memory-review__value mt-2px rounded-6px px-8px py-6px' style={{ background: 'var(--color-fill-2)' }} data-testid='kel-memory-proposed'>
          {proposal.summary}
        </div>
        <div className='kel-memory-review__why mt-8px text-t-secondary' data-testid='kel-memory-why'>
          <span className='kel-memory-review__label'>{desktop ? 'Why' : 'Why: '}</span><span>{proposal.why}</span>
        </div>
      </div>
      <Space className='kel-memory-review__actions mt-10px' wrap size={6}>
        <Button type='primary' size='small' disabled={busy} data-testid='kel-memory-accept' onClick={() => onAct('accept')}>
          Accept
        </Button>
        <Button size='small' disabled={busy} data-testid='kel-memory-reject' onClick={() => onAct('reject')}>
          Reject
        </Button>
        <Button size='small' disabled={busy} data-testid='kel-memory-defer' onClick={() => onAct('defer')}>
          {desktop ? 'Not now' : 'Defer'}
        </Button>
        <Button size='small' type='text' data-testid='kel-memory-details' onClick={() => setDetails(true)}>
          Review details
        </Button>
      </Space>
      <Modal
        title='Review details'
        visible={details}
        footer={null}
        onCancel={() => setDetails(false)}
        autoFocus={false}
        style={{ width: 440 }}
        unmountOnExit
      >
        <div className='text-12px leading-20px' data-testid='kel-memory-details-body'>
          <Typography.Paragraph>
            <Typography.Text bold>What this would change</Typography.Text>
            <br />
            {currentWords(proposal)}
            <br />
            <Typography.Text type='secondary'>becomes</Typography.Text>
            <br />
            {proposal.summary}
          </Typography.Paragraph>
          <Typography.Paragraph>
            <Typography.Text bold>Why</Typography.Text>
            <br />
            {proposal.why}
          </Typography.Paragraph>
          <Typography.Paragraph>
            <Typography.Text bold>Where it came from</Typography.Text>
            <br />
            {sourceWords(proposal)}
          </Typography.Paragraph>
          <Typography.Paragraph type='secondary'>
            Nothing changes about this project&apos;s saved knowledge until you accept.
          </Typography.Paragraph>
        </div>
      </Modal>
    </div>
  );
};

export const KelMemoryProposalControl: React.FC<{ conversationId?: string }> = ({ conversationId }) => {
  const desktop = !useLayoutContext()?.isMobile;
  const [rows, setRows] = useState<MemoryProposal[] | null>(null);
  const [cid, setCid] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [visible, setVisible] = useState(false);

  const refresh = useCallback(async (target?: string | null) => {
    const resolved = target ?? cid;
    try {
      const out = await memoryRequest<{ proposals?: MemoryProposal[] }>({
        action: 'proposals',
        conversation: resolved ?? undefined,
        state: 'open',
      });
      setRows((out?.proposals || []).filter((row) => row.state === 'pending'));
    } catch {
      setRows(null);
    }
  }, [cid]);

  useEffect(() => {
    let alive = true;
    (async () => {
      let resolved: string | null = null;
      if (conversationId) {
        try {
          const api = (window as unknown as { kelAPI?: { conversation?: (id: string) => Promise<unknown> } }).kelAPI;
          const value = (await api?.conversation?.(conversationId)) ?? null;
          resolved = typeof value === 'string' ? value : ((value as { id?: string } | null)?.id ?? null);
        } catch {
          resolved = null;
        }
      }
      if (!alive) return;
      setCid(resolved);
      await refresh(resolved);
    })();
    const timer = setInterval(() => {
      if (alive) void refresh();
    }, 8000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  const act = useCallback(
    async (proposal: MemoryProposal, kind: 'accept' | 'reject' | 'defer') => {
      setBusy(true);
      try {
        await memoryRequest({ action: `${kind}_proposal`, conversation: cid ?? undefined, id: proposal.id });
        Message.success(
          kind === 'accept'
            ? 'Updated what this project knows.'
            : kind === 'reject'
              ? 'Kel will keep things as they are.'
              : 'Postponed — Kel will not ask again until something changes.'
        );
        await refresh();
      } catch {
        Message.error('Kel could not save that just now.');
        await refresh();
      } finally {
        setBusy(false);
      }
    },
    [cid, refresh]
  );

  if (!rows || rows.length === 0) return null;
  const first = rows[0];
  const extra = rows.length - 1;

  return (
    <Popover
      className='kel-memory-popover'
      trigger='click'
      position={desktop ? 'br' : 'bl'}
      popupVisible={visible}
      onVisibleChange={setVisible}
      content={
        <div>
          <MemoryProposalReview proposal={first} total={rows.length} busy={busy} onAct={(kind) => void act(first, kind)} />
          {extra > 0 ? (
            <div className='kel-memory-review__more mt-6px text-11px text-t-secondary' data-testid='kel-memory-more'>
              and {extra} more waiting for review in Work
            </div>
          ) : null}
        </div>
      }
    >
      <button
        type='button'
        data-testid='kel-memory-pill'
        className='flex items-center gap-4px text-12px px-8px h-24px rounded-12px cursor-pointer'
        style={{ background: 'var(--color-fill-2)', color: 'var(--color-text-1)', border: '1px solid var(--color-border-2)' }}
      >
        <span>{`Review · ${rows.length}`}</span>
        <span className='kel-memory-review__chevron' aria-hidden='true'>⌄</span>
      </button>
    </Popover>
  );
};

export default KelMemoryProposalControl;
