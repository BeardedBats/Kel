import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SWRConfig, useSWRConfig } from 'swr';
import type { AcpConfigOptionDto } from '@/common/types/platform/acpTypes';
import ShellConversationModeLabel from '@renderer/components/kel/ShellConversationModeLabel';

describe('Confirmed Chat mode label', () => {
  it('does not invent a mode when the runtime has no catalog', () => {
    render(<SWRConfig value={{ provider: () => new Map() }}><ShellConversationModeLabel conversationId='no-catalog' /></SWRConfig>);
    expect(screen.queryByTestId('chat-mode-label')).toBeNull();
  });

  it('follows confirmed catalog changes and hides unmatched values', async () => {
    let update: ReturnType<typeof useSWRConfig>['mutate'];
    const Harness = () => {
      update = useSWRConfig().mutate;
      return <ShellConversationModeLabel conversationId='confirmed' />;
    };
    render(<SWRConfig value={{ provider: () => new Map() }}><Harness /></SWRConfig>);
    const catalog = (value: string) => [{ id: 'mode', category: 'mode', type: 'select', current_value: value,
      options: [{ value: 'plan', name: 'Plan Mode' }, { value: 'read', name: 'Read Only' }],
    }] as AcpConfigOptionDto[];
    await act(async () => { await update!(['acp-config-options', 'confirmed'], catalog('plan'), false); });
    expect(screen.getByTestId('chat-mode-label').textContent).toBe('Planning');
    await act(async () => { await update!(['acp-config-options', 'confirmed'], catalog('read'), false); });
    expect(screen.getByTestId('chat-mode-label').textContent).toBe('Read Only');
    await act(async () => { await update!(['acp-config-options', 'confirmed'], catalog('unknown'), false); });
    expect(screen.queryByTestId('chat-mode-label')).toBeNull();
  });
});
