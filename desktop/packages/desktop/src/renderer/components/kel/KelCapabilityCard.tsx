/**
 * A capability conflict card: Kel was paused because a capability is off here.
 *
 * Renders exactly the actions the engine recommended (real capabilities, real effects — see
 * `runtime/kel/capabilities.recommendation`). Acting refreshes the Work panel; keeping it off
 * dismisses the card so it never nags.
 */
import React, { useState } from 'react';
import { Button, Message } from '@arco-design/web-react';
import {
  capabilityActionRequest,
  capabilityCardActions,
  capabilityConfirmation,
  type CapabilityCardActionId,
  type CapabilityRecommendation,
} from './capabilityRecommendation';

const request = async <T,>(route: string, body?: unknown): Promise<T> => {
  const bridge = (window as unknown as { kelAPI?: { request: (route: string, payload?: unknown) => Promise<T> } }).kelAPI;
  if (!bridge) throw new Error('Kel connection is unavailable');
  return bridge.request(route, body);
};

export const KelCapabilityCard: React.FC<{
  conversation: string;
  recommendation: CapabilityRecommendation;
  detail?: string;
  onDone?: () => void;
}> = ({ conversation, recommendation, detail, onDone }) => {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState('');
  const actions = capabilityCardActions(recommendation);
  if (!actions.length) return null;

  const act = async (id: CapabilityCardActionId) => {
    if (id === 'keep_disabled') {
      setDone(capabilityConfirmation(id, recommendation.label));
      onDone?.();
      return;
    }
    const call = capabilityActionRequest(id, conversation, recommendation.capability);
    if (!call) return;
    setBusy(true);
    try {
      await request(call.route, call.body);
      const line = capabilityConfirmation(id, recommendation.label);
      setDone(line);
      Message.success(line);
    } catch {
      Message.error('Kel could not change that just now.');
    } finally {
      setBusy(false);
      onDone?.();
    }
  };

  return (
    <section className='mt-8px p-12px bg-2 rd-12px' data-testid='kel-capability-card'>
      <div className='text-13px text-t-primary leading-20px'>
        {`Kel paused something that needs ${recommendation.label}.`}
      </div>
      {detail ? <div className='text-12px text-t-secondary leading-18px mt-2px'>{detail}</div> : null}
      <div className='text-12px text-t-secondary leading-18px mt-2px'>{recommendation.reason}</div>
      {done ? (
        <div className='text-12px text-t-secondary mt-6px' data-testid='kel-capability-done'>
          {done}
        </div>
      ) : (
        <div className='mt-8px flex flex-wrap gap-8px'>
          {actions.map((a) => (
            <Button
              key={a.id}
              size='small'
              disabled={busy}
              data-testid={'kel-capability-' + a.id}
              onClick={() => void act(a.id)}
            >
              {a.label}
            </Button>
          ))}
        </div>
      )}
    </section>
  );
};
