import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ComposerMenuPortal from '@renderer/components/chat/SendBox/ComposerMenuPortal';
import GuidInputCard from '@renderer/pages/guid/components/GuidInputCard';
import ScaleControl from '@renderer/components/settings/ScaleControl';

const setFontScale = vi.fn(async () => undefined);
vi.mock('@renderer/hooks/context/ThemeContext', () => ({
  useThemeContext: () => ({ fontScale: 1.15, setFontScale, theme: 'dark' }),
}));
vi.mock('@renderer/components/media/FilePreview', () => ({ default: () => null }));
vi.mock('@renderer/components/media/UploadProgressBar', () => ({ default: () => null }));
vi.mock('@renderer/pages/guid/components/GuidWorkspaceFootnote', () => ({ default: () => null }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => (key === 'settings.scaleReset' ? 'Reset' : key) }) }));
afterEach(() => {
  cleanup();
  setFontScale.mockClear();
});

const anchorAt = (rect: Partial<DOMRect>) => {
  const anchor = document.createElement('div');
  anchor.getBoundingClientRect = () => ({ left: 388, top: 786, width: 920, height: 60, right: 1308, bottom: 846, x: 388, y: 786, toJSON: () => ({}), ...rect }) as DOMRect;
  document.body.appendChild(anchor);
  return anchor;
};

describe('Composer menus render outside the blurred composer (VS-3)', () => {
  it('portals the menu to <body>, above the composer, inset past the + and at the Figma width', () => {
    const anchor = anchorAt({});
    const { container } = render(
      <div className='sendbox-panel'>
        <ComposerMenuPortal anchor={anchor} inset={40} width={340}>
          <div role='listbox'>Commands</div>
        </ComposerMenuPortal>
      </div>
    );
    const layer = screen.getByTestId('composer-menu-layer');
    expect(container.contains(layer)).toBe(false);
    expect(layer.parentElement).toBe(document.body);
    expect(layer.style.position).toBe('fixed');
    expect(layer.style.left).toBe('428px');
    expect(layer.style.width).toBe('340px');
    expect(layer.style.bottom).toBe(`${window.innerHeight - 786 + 8}px`);
    anchor.remove();
  });

  it('keeps the Home slash menu out of the composer surface', () => {
    render(
      <GuidInputCard
        input='/'
        onInputChange={vi.fn()}
        onKeyDown={vi.fn()}
        onPaste={vi.fn()}
        onFocus={vi.fn()}
        onBlur={vi.fn()}
        placeholder="What's up?"
        isInputActive={false}
        isFileDragging={false}
        activeBorderColor=''
        inactiveBorderColor=''
        activeShadow=''
        dragHandlers={{}}
        files={[]}
        onRemoveFile={vi.fn()}
        actionRow={null}
        slashCommandMenu={<div data-testid='slash-menu'>Commands</div>}
        workspaceDir=''
        onSelectWorkspace={vi.fn()}
        onClearWorkspace={vi.fn()}
      />
    );
    const menu = screen.getByTestId('slash-menu');
    expect(menu.closest('.kel-shell-composer')).toBeNull();
    expect(menu.closest('[data-testid="composer-menu-layer"]')).not.toBeNull();
    // Home shows no usage chips before a conversation exists (FIX-0010).
    expect(screen.queryByLabelText('Conversation usage')).toBeNull();
  });
});

describe('Zoom reads like the other text-size rows (FIX-0016)', () => {
  it('shows − value + Reset with no slider and keeps the zoom step', () => {
    const { container } = render(<ScaleControl variant='stepper' />);
    expect(container.querySelector('.arco-slider')).toBeNull();
    expect(screen.getByTestId('zoom-value').textContent).toBe('115%');
    expect(screen.getByRole('button', { name: 'Reset' })).toBeTruthy();
    fireEvent.click(screen.getByTestId('text-larger'));
    expect(setFontScale).toHaveBeenCalledTimes(1);
    expect((setFontScale.mock.calls[0] as unknown as [number])[0]).toBeGreaterThan(1.15);
  });
});
