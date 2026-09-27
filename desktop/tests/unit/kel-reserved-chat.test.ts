/**
 * ST-04: a new, unused chat has a reserved engine id but no row in `state.conversations` until its
 * first message. The Work drawer must treat it as a chat of the default project and name it,
 * never fail or show a bare id.
 */
import { describe, expect, it } from 'vitest';
import { conversationOptions, projectOfConversation } from '@renderer/components/chat/KelWorkPanel';

const conversations = [
  { id: 'c-garden', title: 'Garden plan', project_id: 'p-home' },
  { id: 'c-taxes', title: 'Taxes', project_id: 'default' },
];

describe('reserved chats in the Work drawer', () => {
  it('reads the project of a chat that exists', () => {
    expect(projectOfConversation(conversations, 'c-garden')).toBe('p-home');
  });

  it('places a reserved chat (no row yet) in the default project', () => {
    expect(projectOfConversation(conversations, '5d0c1f9e-2a7b-4c7e-9b1a-6f1d2e3c4b5a')).toBe('default');
    expect(projectOfConversation(undefined, 'anything')).toBe('default');
    expect(projectOfConversation([], 'anything')).toBe('default');
  });

  it('names a reserved chat in the picker instead of showing its id', () => {
    const reserved = '5d0c1f9e-2a7b-4c7e-9b1a-6f1d2e3c4b5a';
    expect(conversationOptions(conversations, reserved)).toEqual([
      { value: reserved, label: 'New chat' },
      { value: 'c-garden', label: 'Garden plan' },
      { value: 'c-taxes', label: 'Taxes' },
    ]);
    expect(conversationOptions(undefined, reserved)).toEqual([{ value: reserved, label: 'New chat' }]);
  });

  it('lists existing chats unchanged when the open chat has its row', () => {
    expect(conversationOptions(conversations, 'c-taxes')).toEqual([
      { value: 'c-garden', label: 'Garden plan' },
      { value: 'c-taxes', label: 'Taxes' },
    ]);
  });
});
