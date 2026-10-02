import { beforeEach, describe, expect, it } from 'vitest';
import { parseEngineFailure, hasWorkFailureOwner, friendlyReason } from '@/renderer/pages/conversation/Messages/components/KelEngineFailureCard';
import type { TMessage } from '@/common/chat/chatLib';
import { lastHandoffViews, resetHandoffMemory } from '@renderer/components/kel/workCards/handoffMemory';
import type { KelHandoff } from '@renderer/components/kel/kelApi';

describe('parseEngineFailure', () => {
  it('extracts the reason from the legacy planning failure sentence', () => {
    expect(parseEngineFailure('Kel could not plan this request: Invalid structured result')).toBe(
      'Invalid structured result'
    );
  });

  it('extracts the reason from the hand-off start failure sentence', () => {
    expect(
      parseEngineFailure("I wasn't able to get that started — the model timed out. You can retry it from the card above.")
    ).toBe('the model timed out');
  });

  it('leaves ordinary replies alone', () => {
    expect(parseEngineFailure('The sky is usually blue.')).toBeNull();
    expect(parseEngineFailure('Here is why Kel could not plan this request: it was vague.')).toBeNull();
  });
});

describe('one failure per request', () => {
  beforeEach(() => {
    resetHandoffMemory();
    lastHandoffViews.set('submission', {phase:'failed_to_start', error:'timed out'} as KelHandoff);
  });
  const user = (id: string) => ({ id, type: 'text', position: 'right', conversation_id: 'chat' });
  const card = { id: 'work', type: 'acp_tool_call', position: 'left', conversation_id: 'chat', content: { update: { tool_call_id: 'kel-work:submission' } } };
  const failure = { id: 'failure', type: 'text', position: 'left', conversation_id: 'chat', content: {
    content: "I wasn't able to get that started — timed out. You can retry it from the card above." } };
  it('lets the current handoff card own its failure', () => {
    expect(hasWorkFailureOwner([user('request'), card, failure] as TMessage[], 'failure')).toBe(true);
  });
  it('keeps failures without a matching visible card', () => {
    for (const rows of [[user('request'), failure], [card, user('next'), failure],
      [user('request'), { ...card, hidden: true }, failure],
      [user('request'), { ...card, conversation_id: 'other' }, failure]]) {
      expect(hasWorkFailureOwner(rows as TMessage[], 'failure')).toBe(false);
    }
  });
  it('gives a specific setup step without sending image requests to model settings', () => {
    expect(friendlyReason('No image tool is available.')).toContain('Connect Codex');
    expect(friendlyReason('This project needs a test command')).toContain('test command');
    expect(friendlyReason('Timed out')).toBe('This took too long. Try again.');
  });
  it('keeps a separate planning failure even when this turn also has work', () => {
    const standalone = { ...failure, content: { content: 'Kel could not plan this request: Invalid structured result' } };
    expect(hasWorkFailureOwner([user('request'), card, standalone] as TMessage[], 'failure')).toBe(false);
  });
  it('keeps errors visible until a matching failed card is known', () => {
    for (const view of [undefined, {phase:'running',error:'timed out'}, {phase:'failed_to_start',error:'another error'}]) {
      resetHandoffMemory();
      if (view) lastHandoffViews.set('submission',view as KelHandoff);
      expect(hasWorkFailureOwner([user('request'),card,failure] as TMessage[], 'failure')).toBe(false);
    }
  });
});
