/**
 * Chat polish from the 2026-09-27 audit: CH-7 Recipes in the slash menu, CH-17 one search
 * experience, short code blocks shown whole, Archive → Undo, Export confirms the file name.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

const bridge = vi.hoisted(() => ({
  archive: vi.fn(async () => undefined),
  unarchive: vi.fn(async () => undefined),
}));
vi.mock('@/common', () => ({
  ipcBridge: new Proxy(
    {},
    {
      get: (_target, ns: string) =>
        ns === 'sidebar'
          ? { archive: { invoke: bridge.archive }, unarchive: { invoke: bridge.unarchive } }
          : new Proxy({}, { get: () => ({ invoke: async () => null }) }),
    }
  ),
}));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), confirm: vi.fn() }));
vi.mock('@arco-design/web-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@arco-design/web-react')>();
  return {
    ...actual,
    Message: { ...actual.Message, success: toast.success, error: toast.error },
    Modal: { ...actual.Modal, confirm: toast.confirm },
  };
});
const i18n = vi.hoisted(() => {
  const t = (key: string, options?: { defaultValue?: string; count?: number }) =>
    key === 'common.viewMoreLines' ? `View ${options?.count} more lines` : (options?.defaultValue ?? key);
  return { t, value: { t, i18n: { language: 'en-US' } } };
});
vi.mock('react-i18next', () => ({ useTranslation: () => i18n.value }));
vi.mock('@/renderer/utils/chat/messagePagination', () => ({ loadAllConversationMessagesPaged: vi.fn(async () => []) }));
vi.mock('@/renderer/utils/file/download', () => ({ downloadTextContent: vi.fn() }));

import {
  buildRecipeSlashEntries,
  matchRecipeSlash,
  recipeRunValues,
  recipeSlug,
} from '@renderer/components/kel/recipeSlash';
import { openKelCommandPalette } from '@renderer/components/kel/KelCommandPalette';
import SiderSearchEntry from '@renderer/components/layout/Sider/SiderNav/SiderSearchEntry';
import CodeBlock from '@renderer/components/Markdown/CodeBlock';
import { useConversationActions } from '@renderer/pages/conversation/GroupedHistory/hooks/useConversationActions';
import { downloadTextContent } from '@/renderer/utils/file/download';
import type { TChatConversation } from '@/common/config/storage';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('CH-7 Recipes in the slash menu', () => {
  const entries = buildRecipeSlashEntries(
    [
      { recipe_id: 'r.fix', name: 'Fix a bug', description: 'Reproduce, diagnose and fix a bug.' } as never,
      { recipe_id: 'r.copy', name: 'Copy' },
      { recipe_id: 'r.audit', name: 'Audit & repair' },
    ],
    new Set(['copy'])
  );

  it('names each recipe as a command without shadowing an existing one', () => {
    expect(recipeSlug('Audit & repair')).toBe('audit-repair');
    expect(entries.map((entry) => entry.slug)).toEqual(['fix-a-bug', 'audit-repair']);
    expect(entries[0].description).toBe('Reproduce, diagnose and fix a bug.');
  });

  it('recognises a sent recipe line and what was typed after it', () => {
    expect(matchRecipeSlash('/fix-a-bug the login button does nothing', entries)).toEqual({
      entry: entries[0],
      rest: 'the login button does nothing',
    });
    expect(matchRecipeSlash('/unknown thing', entries)).toBeNull();
    expect(matchRecipeSlash('fix-a-bug', entries)).toBeNull();
  });

  it('fills the first required text input with the typed text and reports what is missing', () => {
    const inputs = [
      { name: 'symptom', type: 'text' as const, required: true, description: 'What is broken?' },
      { name: 'area', type: 'path' as const, required: false },
      { name: 'strict', type: 'bool' as const, required: true, default: false },
    ];
    expect(recipeRunValues(inputs, 'login fails')).toEqual({ values: { symptom: 'login fails', strict: false }, missing: [] });
    expect(recipeRunValues(inputs, '').missing.map((input) => input.name)).toEqual(['symptom']);
  });
});

describe('CH-17 one search experience', () => {
  it('the header/sidebar search opens the command palette in search mode', () => {
    const heard = vi.fn();
    window.addEventListener('kel:open-command-palette', heard);
    const onConversationSelect = vi.fn();
    render(
      <SiderSearchEntry isMobile collapsed={false} siderTooltipProps={{} as never} onConversationSelect={onConversationSelect} />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Search chats' }));
    expect(onConversationSelect).toHaveBeenCalled();
    expect(heard).toHaveBeenCalledTimes(1);
    expect((heard.mock.calls[0][0] as CustomEvent).detail).toEqual({ mode: 'search' });
    openKelCommandPalette();
    expect(heard).toHaveBeenCalledTimes(2);
    window.removeEventListener('kel:open-command-palette', heard);
  });
});

describe('code blocks', () => {
  const block = (lines: number) => Array.from({ length: lines }, (_, index) => `line ${index + 1}`).join('\n');

  it('shows a block of up to 12 lines whole', () => {
    render(<CodeBlock className='language-text'>{block(12)}</CodeBlock>);
    expect(screen.queryByText(/more lines/)).toBeNull();
  });

  it('collapses a longer block with a way to see the rest', () => {
    render(<CodeBlock className='language-text'>{block(20)}</CodeBlock>);
    expect(screen.getByText('View 12 more lines')).toBeTruthy();
  });
});

const conversation = { id: 'c1', name: 'Trip plan', extra: {} } as unknown as TChatConversation;
const actions = () =>
  renderHook(
    () =>
      useConversationActions({
        batchMode: false,
        selectedConversationIds: new Set(),
        setSelectedConversationIds: vi.fn(),
        toggleSelectedConversation: vi.fn(),
        markManualUnread: vi.fn(),
        clearManualUnread: vi.fn(),
        isManualUnread: () => false,
      }),
    { wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter> }
  );

describe('conversation actions', () => {
  it('Archive offers Undo, which moves the chat back', async () => {
    const { result } = actions();
    await act(async () => {
      await result.current.handleArchive(conversation);
    });
    expect(bridge.archive).toHaveBeenCalledWith({ item_type: 'conversation', item_id: 'c1' });
    const shown = toast.success.mock.calls[0][0] as { content: React.ReactElement };
    render(<>{shown.content}</>);
    expect(screen.getByText(/Archived/)).toBeTruthy();
    fireEvent.click(screen.getByTestId('archive-undo'));
    await waitFor(() => expect(bridge.unarchive).toHaveBeenCalledWith({ item_type: 'conversation', item_id: 'c1' }));
    await waitFor(() => expect(toast.success).toHaveBeenLastCalledWith(expect.objectContaining({ content: 'Moved back to your chats.' })));
  });

  it('Export confirms with the file name before saving', async () => {
    const { result } = actions();
    await act(async () => {
      await result.current.handleExport(conversation);
    });
    expect(downloadTextContent).not.toHaveBeenCalled();
    const confirm = toast.confirm.mock.calls[0][0] as { content: string; onOk: () => Promise<void> };
    expect(confirm.content).toContain('“Trip plan.md”');
    await act(async () => {
      await confirm.onOk();
    });
    expect(downloadTextContent).toHaveBeenCalledWith(expect.any(String), 'Trip plan.md', 'text/markdown;charset=utf-8');
  });
});
