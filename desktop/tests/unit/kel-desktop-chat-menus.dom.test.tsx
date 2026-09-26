import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { MemoryProposalReview, type MemoryProposal } from '@renderer/components/kel/KelMemoryProposal';
import FileAttachButton from '@renderer/components/media/FileAttachButton';
import AgentModeSelector from '@renderer/components/agent/AgentModeSelector';

const processed = vi.hoisted(() => vi.fn());
vi.mock('@renderer/services/FileService', () => ({ FileService: { processDroppedFiles: processed } }));
vi.mock('@renderer/hooks/context/ConversationContext', () => ({ useConversationContextSafe: () => null }));
vi.mock('@renderer/utils/platform', () => ({ isElectronDesktop: () => true }));
const proposal: MemoryProposal = { id: 'fixture-only', kind: 'conflict', type: 'rule', topic: 'deploy', summary: 'Deploy on Thursdays.', why: 'The new choice differs.', state: 'pending', value: null, current: { summary: 'Deploy on Fridays.' }, evidence: {}, source_ref: '', created: 0 };

describe('Desktop chat menus', () => {
  it('shows only supplied permission modes and retains the local selection callback', async () => {
    const select = vi.fn();
    render(<MemoryRouter><AgentModeSelector compact initialMode='plan' onModeSelect={select} dynamicModes={[
      { value: 'plan', label: 'Plan Mode', description: 'Kel plans only. Nothing changes.' },
      { value: 'read', label: 'Read Only', description: 'Kel can read. It cannot change anything.' },
    ]} /></MemoryRouter>);
    fireEvent.click(screen.getByTestId('mode-selector'));
    expect(await screen.findByText('Kel plans only. Nothing changes.')).toBeTruthy();
    expect(screen.queryByText('Full Access')).toBeNull();
    fireEvent.click(screen.getByTestId('aionrs-mode-option-read'));
    expect(select).toHaveBeenCalledWith('read');
  });
  it('keeps reviewing separate from changing saved knowledge', () => {
    const act = vi.fn();
    render(<MemoryRouter><MemoryProposalReview proposal={proposal} busy={false} total={2} onAct={act} /></MemoryRouter>);
    expect(screen.getByText('1 of 2')).toBeTruthy();
    fireEvent.click(screen.getByTestId('kel-memory-details'));
    expect(screen.getByTestId('kel-memory-details-body')).toBeTruthy();
    expect(act).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Not now', exact: true }));
    expect(act).toHaveBeenCalledWith('defer');
  });
  it('blocks all changes while a memory action is pending', () => {
    const act = vi.fn();
    render(<MemoryRouter><MemoryProposalReview proposal={proposal} busy total={2} onAct={act} /></MemoryRouter>);
    for (const id of ['accept', 'reject', 'defer']) fireEvent.click(screen.getByTestId('kel-memory-' + id));
    expect(act).not.toHaveBeenCalled();
  });
  it('offers both desktop file paths and attaches uploaded files without sending a turn', async () => {
    const pick = vi.fn(); const attach = vi.fn();
    const metadata = { name: 'fixture.txt', path: '/fixture.txt' };
    processed.mockResolvedValue([metadata]);
    render(<MemoryRouter><FileAttachButton openFileSelector={pick} onLocalFilesAdded={attach} /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'Attach files and tools' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Add files', exact: true }));
    expect(pick).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole('button', { name: 'Attach files and tools' }));
    expect(await screen.findByRole('button', { name: 'Upload from device', exact: true })).toBeTruthy();
    fireEvent.change(screen.getByTestId('aionrs-file-upload-input'), { target: { files: [new File(['fixture'], 'fixture.txt')] } });
    await waitFor(() => expect(attach).toHaveBeenCalledWith([metadata]));
    expect(processed).toHaveBeenCalledOnce();
  });
});
