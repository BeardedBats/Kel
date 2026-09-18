/**
 * Leading-mark resolution semantics (Visual BATCH 5).
 *
 * The sidebar row hides a leading mark that merely restates the single default assistant — the
 * same backend logo repeated on every row, or a generic robot/message glyph — because it costs
 * 30px of title width and distinguishes nothing. Marks that identify a genuinely different
 * assistant (an assigned or preset avatar) must keep working. This pins the `decorative` flag at
 * the resolver so the row can rely on it (visual batch 5; findings 03 §4 / 04 §4.2).
 *
 * The two asset utilities are mocked: this test is about the resolver's branch -> decorative
 * mapping, not about logo/avatar URL parsing (which has its own semantics), and mocking keeps the
 * module graph free of Electron/SWR imports in the node test project.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  resolveAssistantAvatar: vi.fn(),
  resolveAgentLogo: vi.fn(),
}));

vi.mock('@renderer/utils/model/assistantAvatar', () => ({
  resolveAssistantAvatar: mocks.resolveAssistantAvatar,
}));

vi.mock('@renderer/utils/model/agentLogo', () => ({
  resolveAgentLogo: mocks.resolveAgentLogo,
}));

import { resolveConversationLeadingMark } from '@renderer/pages/conversation/utils/conversationAssistantIdentity';

import type { TChatConversation } from '@/common/config/storage';

const conversation = (over: Record<string, unknown> = {}): TChatConversation =>
  ({ id: 'c1', name: 'Thread', type: 'acp', ...over }) as unknown as TChatConversation;

describe('conversation leading mark — decorative semantics (visual batch 5)', () => {
  beforeEach(() => {
    mocks.resolveAssistantAvatar.mockReset();
    mocks.resolveAgentLogo.mockReset();
    mocks.resolveAssistantAvatar.mockReturnValue({ kind: 'fallback' });
    mocks.resolveAgentLogo.mockReturnValue(null);
  });

  it('marks the repeated backend logo as decorative', () => {
    mocks.resolveAgentLogo.mockReturnValue('https://kel.local/logo.png');
    const mark = resolveConversationLeadingMark(conversation(), undefined, { acp: 'https://kel.local/logo.png' });
    expect(mark).toMatchObject({ kind: 'image', decorative: true });
  });

  it('marks the generic robot and message glyphs as decorative', () => {
    const withAssistant = conversation({ assistant: { id: 'a1', name: 'Alpha' } });
    expect(resolveConversationLeadingMark(withAssistant, undefined, {})).toMatchObject({
      kind: 'assistant_fallback',
      decorative: true,
    });
    expect(resolveConversationLeadingMark(conversation(), undefined, {})).toMatchObject({
      kind: 'fallback',
      decorative: true,
    });
    expect(
      resolveConversationLeadingMark(conversation(), { isFallback: true, name: 'Kel' } as never, {})
    ).toMatchObject({ kind: 'assistant_fallback', decorative: true });
  });

  it('keeps a genuinely assigned or preset avatar non-decorative', () => {
    mocks.resolveAssistantAvatar.mockReturnValue({ kind: 'emoji', value: '🦐' });
    const assigned = resolveConversationLeadingMark(conversation({ assistant: { id: 'a1', name: 'Alpha' } }), undefined, {});
    expect(assigned).toMatchObject({ kind: 'emoji' });
    expect(assigned.decorative).toBeUndefined();

    mocks.resolveAssistantAvatar.mockReturnValue({ kind: 'image', value: 'https://kel.local/av.png' });
    const assignedImage = resolveConversationLeadingMark(
      conversation({ assistant: { id: 'a1', name: 'Alpha' } }),
      undefined,
      {}
    );
    expect(assignedImage).toMatchObject({ kind: 'image' });
    expect(assignedImage.decorative).toBeUndefined();

    const preset = resolveConversationLeadingMark(
      conversation(),
      { isFallback: false, isEmoji: true, logo: '🦐', name: 'Kel' } as never,
      {}
    );
    expect(preset).toMatchObject({ kind: 'emoji' });
    expect(preset.decorative).toBeUndefined();
  });
});
