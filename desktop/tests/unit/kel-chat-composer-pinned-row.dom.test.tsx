/**
 * FIX-0021 for the chat composer (/conversation/<id>), the same rule as the home composer: typing
 * several lines never moves or changes the +, the model pill, the mic or send. Only the text grows,
 * upward, keeping its left edge. Before this, the SendBox switched to a second layout at the first
 * wrap: the text jumped to full width and the controls moved to a new row, which re-mounted the model
 * pill (it showed its grey "Kel model: …" loading chip). jsdom has no layout, so this pins the
 * structure the geometry rests on (same nodes, same row, same order, one mount) and the CSS that
 * bottom-aligns the row; the packaged build's off-screen check measures the pixels.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import React, { useState } from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@renderer/components/media/UploadProgressBar', () => ({ default: () => null }));
vi.mock('@renderer/pages/guid/components/KelMicButton', () => ({
  default: () => <button type='button' data-testid='kel-mic-toggle' aria-label='Record a message' />,
}));
vi.mock('@/renderer/pages/conversation/Preview', () => ({
  usePreviewContext: () => ({ setSendBoxHandler: () => {}, domSnippets: [], removeDomSnippet: () => {}, clearDomSnippets: () => {} }),
}));
vi.mock('@/renderer/hooks/chat/useInputFocusRing', () => ({
  useInputFocusRing: () => ({ activeBorderColor: 'blue', inactiveBorderColor: 'grey', activeShadow: 'none' }),
}));
vi.mock('@renderer/pages/conversation/Messages/hooks', () => ({ useMessageList: () => [] }));
vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string, opts?: { defaultValue?: string }) => opts?.defaultValue ?? key, i18n: { language: 'en' } }),
}));

import SendBox from '@/renderer/components/chat/SendBox';
import { LayoutContext } from '@/renderer/hooks/context/LayoutContext';

const css = readFileSync(path.resolve(__dirname, '../../packages/desktop/src/renderer/styles/kel-shell.css'), 'utf8');

afterEach(cleanup);

let pillMounts = 0;
const Pill: React.FC = () => {
  React.useEffect(() => {
    pillMounts += 1;
  }, []);
  return (
    <button type='button' data-testid='kel-model-pill' className='kel-desktop-model-trigger'>
      <span>ChatGPT Luna</span>
    </button>
  );
};

const Harness: React.FC = () => {
  const [value, setValue] = useState('');
  return (
    <LayoutContext.Provider value={{ isMobile: false } as never}>
      <SendBox
        value={value}
        onChange={setValue}
        onSend={async () => {}}
        defaultMultiLine={false}
        lockMultiLine={false}
        tools={<button type='button' data-testid='file-upload-btn' aria-label='Add files' />}
        rightTools={<Pill />}
      />
    </LayoutContext.Provider>
  );
};

const snapshot = () => {
  const textarea = screen.getByTestId('sendbox-input') as HTMLTextAreaElement;
  const row = textarea.closest('.sendbox-input-row') as HTMLElement;
  const plus = screen.getByTestId('file-upload-btn');
  const pill = screen.getByTestId('kel-model-pill');
  const mic = screen.getByTestId('kel-mic-toggle');
  const send = row.querySelector('.sendbox-inline-actions > :last-child') as HTMLElement;
  const children = Array.from(row.children) as HTMLElement[];
  return {
    textarea,
    row,
    rowClass: row.className,
    plus,
    pill,
    pillLabel: pill.textContent,
    pillClass: pill.className,
    mic,
    send,
    order: children.map((child) => child.className),
    textColumn: children.indexOf(textarea.closest('.sendbox-highlight-container') as HTMLElement),
    textContainerClass: (textarea.closest('.sendbox-highlight-container') as HTMLElement).className,
  };
};

describe('FIX-0021 the chat composer keeps its controls on one pinned row', () => {
  it('1 line and 5 lines: the same +, pill, mic and send, in the same row and order; the text keeps its column', async () => {
    pillMounts = 0;
    render(<Harness />);
    const textarea = screen.getByTestId('sendbox-input') as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'one line' } });
    });
    const one = snapshot();
    expect(one.row.classList.contains('sendbox-input-row--pinned')).toBe(true);
    expect(one.row.contains(one.plus) && one.row.contains(one.pill) && one.row.contains(one.mic)).toBe(true);
    // The text sits between the + (left) and the actions (right).
    expect(one.textColumn).toBe(1);

    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'line one of a longer message\nline two\nline three\nline four\nline five' } });
    });
    const five = snapshot();

    // Same elements — nothing re-mounted or moved to another row.
    expect(five.row).toBe(one.row);
    expect(five.textarea).toBe(one.textarea);
    expect(five.plus).toBe(one.plus);
    expect(five.pill).toBe(one.pill);
    expect(five.mic).toBe(one.mic);
    expect(five.send).toBe(one.send);
    expect(pillMounts).toBe(1);
    // The pill looks and reads the same (no grey "Kel model: …" chip).
    expect(five.pillLabel).toBe('ChatGPT Luna');
    expect(five.pillClass).toBe(one.pillClass);
    // The row, its order and the text's column (its left edge) are unchanged; no second row appears.
    expect(five.rowClass).toBe(one.rowClass);
    expect(five.order).toEqual(one.order);
    expect(five.textColumn).toBe(one.textColumn);
    expect(five.textContainerClass).toBe(one.textContainerClass);
    expect(document.querySelector('.sendbox-actions')).toBeNull();
    // The text grows instead of switching layouts.
    expect(textarea.style.whiteSpace).toBe('pre-wrap');
  });

  it('bottom-aligns the row so the controls centre on the last text line (25 px line, 28 px +, 36 px send)', () => {
    expect(css).toMatch(/\.kel-v2-shell \.sendbox-input-row--pinned > \.sendbox-tools \{ margin-bottom: 4px; \}/);
    expect(css).toMatch(/\.kel-v2-shell \.sendbox-input-row--pinned > \.sendbox-highlight-container \{ margin-bottom: 5\.5px !important; \}/);
    expect(css).toMatch(/\.kel-v2-shell \.sendbox-input-row--pinned textarea \{ padding-block: 0 !important; min-height: 25px !important; \}/);
  });
});
