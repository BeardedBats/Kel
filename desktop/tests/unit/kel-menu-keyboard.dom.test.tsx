/**
 * VIS-10 / JR-26: the chat row menu, the composer's model picker and the attach menu work from the
 * keyboard like the project chip: a labelled trigger, focus moves into the menu, arrows move between
 * items, Escape closes and returns focus, and changing page closes the menu. (The reply ⋯ menu is gone:
 * FIX-0027 made its actions plain icon buttons.)
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/common', () => ({
  ipcBridge: { fs: { listAvailableSkills: { invoke: async () => [] } } },
}));
vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key, i18n: { language: 'en-US' } }),
}));
vi.mock('@/renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));
vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));
vi.mock('@/renderer/hooks/context/ConversationContext', () => ({ useConversationContextSafe: () => ({ conversation_id: 'c1' }) }));
vi.mock('@/renderer/utils/model/agentLogo', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/renderer/utils/model/agentLogo')>()),
  useAgentLogos: () => ({}),
}));
vi.mock('@/renderer/hooks/agent/usePresetAssistantInfo', () => ({ usePresetAssistantInfo: () => ({ info: null }) }));
vi.mock('@/renderer/components/kel/useKelLiveWork', () => ({ useKelLiveWork: () => 'idle' }));
vi.mock('@/renderer/pages/cron', () => ({ CronJobIndicator: () => null }));

import ConversationRow from '@renderer/pages/conversation/GroupedHistory/ConversationRow';
import FileAttachButton from '@renderer/components/media/FileAttachButton';
import { KelModelPill } from '@renderer/components/kel/KelModelControl';
import type { TChatConversation } from '@/common/config/storage';

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

let navigateTo: (path: string) => void = () => {};
const Navigator = () => {
  const navigate = useNavigate();
  navigateTo = (path) => void navigate(path);
  return null;
};
const inRouter = (node: React.ReactNode) =>
  render(
    <MemoryRouter initialEntries={['/conversation/c1']}>
      <Navigator />
      {node}
    </MemoryRouter>
  );

const press = (key: string, init: KeyboardEventInit = {}) => fireEvent.keyDown(document.activeElement ?? document.body, { key, ...init });

/** Opens with the trigger, then walks the shared contract: focus in, arrows, Escape, route change. */
const expectKeyboardMenu = async (trigger: HTMLElement, menuName: string, firstItem: string, secondItem: string) => {
  expect(trigger.getAttribute('aria-haspopup')).toBeTruthy();
  expect(trigger.getAttribute('aria-expanded')).toBe('false');
  fireEvent.click(trigger);
  await waitFor(() => expect(document.activeElement?.textContent).toContain(firstItem));
  expect(trigger.getAttribute('aria-expanded')).toBe('true');
  press('ArrowDown');
  expect(document.activeElement?.textContent).toContain(secondItem);
  press('ArrowUp');
  expect(document.activeElement?.textContent).toContain(firstItem);
  press('Escape');
  await waitFor(() => expect(trigger.getAttribute('aria-expanded')).toBe('false'));
  expect(document.activeElement).toBe(trigger);

  // Reopen, then leave the page: the menu does not follow.
  fireEvent.click(trigger);
  await waitFor(() => expect(trigger.getAttribute('aria-expanded')).toBe('true'));
  act(() => navigateTo('/settings/model'));
  await waitFor(() => expect(trigger.getAttribute('aria-expanded')).toBe('false'));
  void menuName;
};

describe('chat row menu', () => {
  const conversation = { id: 'c9', name: 'Garden plan', type: 'acp', extra: {} } as unknown as TChatConversation;
  const Row = () => {
    const [open, setOpen] = React.useState(false);
    return (
      <ConversationRow
        conversation={conversation}
        isGenerating={false}
        isWaitingConfirmation={false}
        hasUnread={false}
        isManualUnread={false}
        collapsed={false}
        tooltipEnabled={false}
        batchMode={false}
        checked={false}
        selected={false}
        menuVisible={open}
        onToggleChecked={vi.fn()}
        onConversationClick={vi.fn()}
        onOpenMenu={() => setOpen(true)}
        onMenuVisibleChange={(_id, visible) => setOpen(visible)}
        onEditStart={vi.fn()}
        onCreateCronTask={vi.fn()}
        onArchive={vi.fn()}
        onTogglePin={vi.fn()}
        onToggleManualUnread={vi.fn()}
        getJobStatus={() => 'none'}
      />
    );
  };

  it('has a labelled trigger and full keyboard support', async () => {
    inRouter(<Row />);
    const trigger = screen.getByRole('button', { name: 'Garden plan options' });
    await expectKeyboardMenu(trigger, 'Garden plan options', 'conversation.history.pin', 'conversation.history.markAsUnread');
  });

  it('opens from the keyboard on the row (Shift+F10 / context menu key) with focus inside', async () => {
    inRouter(<Row />);
    const row = document.getElementById('c-c9') as HTMLElement;
    row.focus();
    fireEvent.contextMenu(row);
    await waitFor(() => expect(document.activeElement?.textContent).toContain('conversation.history.pin'));
  });
});

describe('attach menu', () => {
  it('has a labelled trigger and full keyboard support', async () => {
    (window as unknown as { electronAPI?: unknown }).electronAPI = {};
    try {
      inRouter(<FileAttachButton openFileSelector={vi.fn()} onLocalFilesAdded={vi.fn()} />);
      await expectKeyboardMenu(screen.getByRole('button', { name: 'Attach files and tools' }), 'Attach files and tools', 'Add files', 'Upload from device');
    } finally {
      delete (window as unknown as { electronAPI?: unknown }).electronAPI;
    }
  });
});

describe('composer model picker', () => {
  it('has a labelled trigger and full keyboard support', async () => {
    const state = {
      default: null,
      conversation: null,
      providers: [
        { id: 'claude-code', label: 'Claude', available: true, note: null, options: [{ id: 'claude-native', label: 'Claude (built-in)', available: true, note: null }] },
      ],
    };
    (window as unknown as { kelAPI: unknown }).kelAPI = {
      request: vi.fn(async (_route: string, body?: Record<string, unknown>) => (body?.action === 'get' ? state : {})),
      conversation: vi.fn(async () => 'engine-1'),
    };
    inRouter(<KelModelPill conversationId='c1' />);
    const trigger = await screen.findByRole('button', { name: /Kel's model: Automatic/ });
    // The picker opens on its scope tabs; the first stop is "This chat", the next "Kel's model" (D-73.3).
    await expectKeyboardMenu(trigger, 'Model picker', 'This chat', "Kel's model");
  });
});
