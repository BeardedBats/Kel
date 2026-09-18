/**
 * Capability recommendation helpers: only real actions map to requests; unknown ids drop.
 */
import { describe, expect, it } from 'vitest';
import {
  capabilityActionRequest,
  capabilityCardActions,
  capabilityConfirmation,
  type CapabilityRecommendation,
} from '@/renderer/components/kel/capabilityRecommendation';

const rec = (over: Partial<CapabilityRecommendation> = {}): CapabilityRecommendation => ({
  capability: 'web',
  label: 'Web',
  reason: 'Web is disabled for this conversation.',
  actions: ['allow_once', 'enable', 'keep_disabled'],
  ...over,
});

describe('capabilityCardActions', () => {
  it("maps the engine's three real actions, in order", () => {
    expect(capabilityCardActions(rec())).toEqual([
      { id: 'allow_once', label: 'Allow once' },
      { id: 'enable', label: 'Enable for this chat' },
      { id: 'keep_disabled', label: 'Keep it off' },
    ]);
  });

  it('drops unknown action ids instead of inventing UI', () => {
    expect(capabilityCardActions(rec({ actions: ['allow_once', 'deploy_everything'] }))).toEqual([
      { id: 'allow_once', label: 'Allow once' },
    ]);
  });

  it('renders nothing without a recommendation or without actions', () => {
    expect(capabilityCardActions(null)).toEqual([]);
    expect(capabilityCardActions(rec({ actions: [] }))).toEqual([]);
  });
});

describe('capabilityActionRequest', () => {
  it('allow_once grants a single-use allowance for the conversation', () => {
    expect(capabilityActionRequest('allow_once', 'chat-1', 'web')).toEqual({
      route: '/api/capabilities',
      body: { action: 'allow_once', conversation: 'chat-1', capability: 'web' },
    });
  });

  it('enable turns the capability on for the conversation only', () => {
    expect(capabilityActionRequest('enable', 'chat-1', 'web')).toEqual({
      route: '/api/capabilities',
      body: { action: 'set', conversation: 'chat-1', capability: 'web', state: 'on' },
    });
  });

  it('keep it off changes no state at all', () => {
    expect(capabilityActionRequest('keep_disabled', 'chat-1', 'web')).toBeNull();
  });
});

describe('capabilityConfirmation', () => {
  it('states the scope in plain words', () => {
    expect(capabilityConfirmation('allow_once', 'Web')).toContain('Web');
    expect(capabilityConfirmation('enable', 'Web')).toBe('Web is on for this conversation.');
    expect(capabilityConfirmation('keep_disabled', 'Web')).toBe('Web stays off for this conversation.');
  });
});
