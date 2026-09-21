import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { LayoutContext } from '@renderer/hooks/context/LayoutContext';
import GuidInputCard from '@renderer/pages/guid/components/GuidInputCard';
import GuidActionRow from '@renderer/pages/guid/components/GuidActionRow';

vi.mock('@renderer/components/media/FilePreview', () => ({ default: ({ path, onRemove }: { path: string; onRemove: () => void }) => <button onClick={onRemove}>Remove {path}</button> }));
vi.mock('@renderer/components/media/UploadProgressBar', () => ({ default: () => null }));
vi.mock('@renderer/pages/guid/components/GuidWorkspaceFootnote', () => ({ default: () => null }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
afterEach(cleanup);

const inputProps = () => ({
  input: '', onInputChange: vi.fn(), onKeyDown: vi.fn(), onPaste: vi.fn(), onFocus: vi.fn(), onBlur: vi.fn(),
  placeholder: "What's up?", isInputActive: false, isFileDragging: false, activeBorderColor: '', inactiveBorderColor: '', activeShadow: '',
  dragHandlers: {}, files: [], onRemoveFile: vi.fn(), actionRow: null, workspaceDir: '', onSelectWorkspace: vi.fn(), onClearWorkspace: vi.fn(),
});
const actionProps = () => ({
  files: [], onFilesPicked: vi.fn(), onFilesUploaded: vi.fn(), modelSelectorNode: null, isGeminiMode: false, modelList: [],
  setCurrentModel: vi.fn(async () => undefined), currentAcpCachedModelInfo: null, selectedAcpModel: null, setSelectedAcpModel: vi.fn(),
  selectedMode: '', onModeSelect: vi.fn(), allSkills: [], disabledBuiltinSkills: [], enabledSkills: [], onToggleSkill: vi.fn(),
  mcpServers: [], selectedMcpServerIds: [], onToggleMcpServer: vi.fn(), loading: false, isButtonDisabled: false, onSend: vi.fn(),
});

describe('Figma composer preserves production input behavior', () => {
  it('hands draft changes and paste to the owner, and blocks Enter during IME composition', () => {
    const props = inputProps();
    render(<GuidInputCard {...props} />);
    const input = screen.getByTestId('guid-input');
    fireEvent.change(input, { target: { value: 'A draft' } });
    expect(props.onInputChange.mock.calls[0][0]).toBe('A draft');
    fireEvent.paste(input, { clipboardData: { getData: () => 'pasted' } });
    expect(props.onPaste).toHaveBeenCalledTimes(1);
    fireEvent.compositionStart(input);
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(props.onKeyDown).not.toHaveBeenCalled();
    fireEvent.compositionEnd(input);
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(props.onKeyDown).toHaveBeenCalledTimes(1);
  });
  it('keeps uploaded file removal connected to the owning draft', () => {
    const props = inputProps();
    render(<GuidInputCard {...props} files={['brief.txt']} />);
    fireEvent.click(screen.getByRole('button', { name: 'Remove brief.txt' }));
    expect(props.onRemoveFile).toHaveBeenCalledWith('brief.txt');
  });
  it('keeps send disabled when the owner requires it, and sends once when enabled', () => {
    const props = actionProps();
    const { rerender } = render(<GuidActionRow {...props} isButtonDisabled />);
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    expect(props.onSend).not.toHaveBeenCalled();
    rerender(<GuidActionRow {...props} />);
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    expect(props.onSend).toHaveBeenCalledTimes(1);
  });
  it('opens the mobile control sheet by a tap', () => {
    render(<LayoutContext.Provider value={{ isMobile: true, siderCollapsed: true, setSiderCollapsed: vi.fn() }}><GuidActionRow {...actionProps()} /></LayoutContext.Provider>);
    fireEvent.click(screen.getByRole('button', { name: 'Attach files and tools' }));
    expect(screen.getByRole('dialog')).toBeTruthy();
  });
});

