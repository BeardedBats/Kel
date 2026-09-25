import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { KelApprovalCard, type ApprovalItem } from '@renderer/components/kel/KelApprovalCard';

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const pending: ApprovalItem = {
  id: 'approval-1', kind: 'action', state: 'pending', title: 'Kel needs your OK to continue',
  summary: 'run npm run build', target: 'npm run build', context_title: 'Website Redesign', repeatable: true,
};

describe('Kel approval card', () => {
  it('keeps the decision tied to the engine approval and prevents a second submission', async () => {
    let resolve!: () => void;
    const request = vi.fn((route: string) => route.startsWith('/api/approvals?')
      ? Promise.resolve({ items: [pending] })
      : new Promise<void>((done) => { resolve = done; }));
    (window as unknown as { kelAPI: unknown }).kelAPI = {
      conversation: vi.fn(async () => 'engine-conversation'), request,
    };
    render(<KelApprovalCard kind='action' refId='approval-1' conversationId='host-conversation' />);
    const approve = await screen.findByTestId('kel-approval-approve');
    expect(screen.getByTestId('kel-approval-target').textContent).toBe('npm run build');
    expect(screen.getByTestId('kel-approval-body').textContent).toBe('It wants to run a build command in Website Redesign.');
    fireEvent.click(approve);
    fireEvent.click(approve);
    expect(request).toHaveBeenCalledWith('/api/approvals', {
      kind: 'action', id: 'approval-1', allow: true, conversation: 'engine-conversation',
    });
    expect(request.mock.calls.filter(([route]) => route === '/api/approvals')).toHaveLength(1);
    resolve();
    await waitFor(() => expect(approve.hasAttribute('disabled')).toBe(false));
  });

  it('shows a settled decision without live approval buttons', async () => {
    (window as unknown as { kelAPI: unknown }).kelAPI = {
      conversation: vi.fn(async () => 'engine-conversation'),
      request: vi.fn(async () => ({ items: [{ ...pending, state: 'approved' }] })),
    };
    render(<KelApprovalCard kind='action' refId='approval-1' conversationId='host-conversation' />);
    expect((await screen.findByTestId('kel-approval-resolved')).textContent).toContain('Kel is continuing');
    expect(screen.getByText('Approved', { exact: true })).toBeTruthy();
    expect(screen.queryByTestId('kel-approval-approve')).toBeNull();
  });
});
