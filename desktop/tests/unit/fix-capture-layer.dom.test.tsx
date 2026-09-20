/**
 * V2.0 preflight — Fix Capture through the real layer (jsdom).
 *
 * The microphone and the engine are stubbed, the capture logic is not: pressing the hotkey, clicking
 * the target, watching the live transcript, stopping, recording again, saving, and cancelling all run
 * through the shipped hook and reducer.
 */
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mic = vi.hoisted(() => ({
  onPcm: null as ((pcm: string) => void) | null,
  cancel: vi.fn(),
  stop: vi.fn(() => Promise.resolve({ base64: 'QUJD', durationMs: 2500, wav: new Uint8Array() })),
  /** Set to make the next microphone start fail, like a machine with no audio device. */
  failWith: null as string | null,
}));

vi.mock('@renderer/utils/transcription/audio', () => ({
  startMicCapture: (onPcm?: (pcm: string) => void) => {
    if (mic.failWith) return Promise.reject(new Error(mic.failWith));
    mic.onPcm = onPcm ?? null;
    return Promise.resolve({ stop: mic.stop, cancel: mic.cancel });
  },
  // Stands in for the shipped mic-error copy (the real helper turns device errors into sentences).
  friendlyMicError: () => 'No microphone was found on this computer.',
}));

import FixCaptureLayer from '@renderer/components/kel/fixCapture/FixCaptureLayer';

type Call = { route: string; body: Record<string, unknown> };

const calls: Call[] = [];
let captureResult: Record<string, unknown> | null = null;
let streamText = 'the button jumps when I click it';

const stubBridge = () => {
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request: (route: string, body?: Record<string, unknown>) => {
      calls.push({ route, body: body ?? {} });
      if (route !== '/api/transcription') {
        return Promise.resolve({ id: 'FIX-0001', status: 'OPEN', transcript: body?.transcript ?? '' });
      }
      switch (body?.action) {
        case 'stream_start':
          return Promise.resolve({ session_id: 'session-1', live: true });
        case 'stream_chunk':
          return Promise.resolve({ text: '' });
        case 'stream_status':
          return Promise.resolve({ text: 'the button jumps' });
        case 'stream_finish':
          return Promise.resolve({ text: streamText, duration_ms: 2500 });
        case 'quick_transcribe':
          return Promise.resolve({ text: 'from the whole recording' });
        default:
          return Promise.resolve({});
      }
    },
    dogfood: {
      capture: () => Promise.resolve(captureResult),
      screenshot: () => Promise.resolve({ data_url: 'data:image/png;base64,AA==' }),
    },
    revealArtifact: () => Promise.resolve({ ok: true }),
  };
};

const hotkey = () =>
  fireEvent.keyDown(window, { key: 'f', code: 'KeyF', ctrlKey: true, shiftKey: true, bubbles: true });

const renderLayer = () =>
  render(
    <MemoryRouter initialEntries={['/guid']}>
      <button type='button' data-testid='app-target'>
        Set up
      </button>
      <FixCaptureLayer />
    </MemoryRouter>
  );

const findCall = (action: string) => calls.find((entry) => entry.body?.action === action);

beforeEach(() => {
  calls.length = 0;
  captureResult = null;
  streamText = 'the button jumps when I click it';
  mic.cancel.mockClear();
  mic.stop.mockClear();
  mic.failWith = null;
  stubBridge();
});

afterEach(() => {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Fix Capture — the capture itself', () => {
  it('opens on Ctrl+Shift+F and Esc cancels without saving anything', async () => {
    renderLayer();
    expect(screen.queryByTestId('fix-capture-overlay')).toBeNull();
    hotkey();
    await waitFor(() => expect(screen.getByTestId('fix-capture-overlay')).toBeTruthy());
    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('fix-capture-overlay')).toBeNull());
    expect(findCall('save')).toBeUndefined();
    expect(findCall('stream_start')).toBeUndefined();
  });

  it('selects the clicked element, starts recording, and shows the live transcript', async () => {
    renderLayer();
    hotkey();
    await waitFor(() => expect(screen.getByTestId('fix-capture-overlay')).toBeTruthy());
    fireEvent.click(screen.getByTestId('app-target'));
    // The capture UI leaves the screen before the window is captured, then the session starts.
    await waitFor(() => expect(findCall('stream_start')).toBeTruthy());
    const panel = await screen.findByTestId('fix-capture-panel');
    expect(panel.getAttribute('data-phase')).toBe('recording');
    expect(screen.getByText('Recording fix…')).toBeTruthy();
    // PCM chunks flow through Kel's own transcription family.
    mic.onPcm?.('AAAA');
    await waitFor(() => expect(findCall('stream_chunk')).toBeTruthy());
    // The live transcript arrives from the engine's own status read.
    await waitFor(
      () => expect(screen.getByTestId('fix-capture-live').textContent).toContain('the button jumps'),
      { timeout: 3000 }
    );
  });

  it('stops on the hotkey and hands the transcript to review', async () => {
    renderLayer();
    hotkey();
    await waitFor(() => expect(screen.getByTestId('fix-capture-overlay')).toBeTruthy());
    fireEvent.click(screen.getByTestId('app-target'));
    await waitFor(() => expect(findCall('stream_start')).toBeTruthy());
    await waitFor(() =>
      expect(screen.getByTestId('fix-capture-panel').getAttribute('data-phase')).toBe('recording')
    );
    hotkey();
    await waitFor(() => expect(findCall('stream_finish')).toBeTruthy());
    const transcript = (await screen.findByTestId('fix-capture-transcript')) as HTMLTextAreaElement;
    await waitFor(() => expect(transcript.value).toBe('the button jumps when I click it'));
    expect(mic.stop).toHaveBeenCalled();
    expect(screen.getByTestId('fix-capture-panel').getAttribute('data-phase')).toBe('review');
  });

  it('Record Again keeps the target and the capture but replaces the words', async () => {
    captureResult = {
      screenshot: 'dogfood/tmp/one.png',
      image: { width: 2560, height: 1600 },
      content: { width: 1280, height: 800 },
      display: { scale: 2 },
      captured_at: 1,
    };
    renderLayer();
    hotkey();
    await waitFor(() => expect(screen.getByTestId('fix-capture-overlay')).toBeTruthy());
    fireEvent.click(screen.getByTestId('app-target'));
    await waitFor(() => expect(findCall('stream_start')).toBeTruthy());
    hotkey();
    await waitFor(() =>
      expect(screen.getByTestId('fix-capture-panel').getAttribute('data-phase')).toBe('review')
    );
    streamText = 'second try says it better';
    fireEvent.click(screen.getByTestId('fix-capture-again'));
    await waitFor(() =>
      expect(calls.filter((entry) => entry.body?.action === 'stream_start').length).toBe(2)
    );
    await waitFor(() =>
      expect(screen.getByTestId('fix-capture-panel').getAttribute('data-phase')).toBe('recording')
    );
    hotkey();
    await waitFor(() =>
      expect(screen.getByTestId('fix-capture-panel').getAttribute('data-phase')).toBe('review')
    );
    const transcript = (await screen.findByTestId('fix-capture-transcript')) as HTMLTextAreaElement;
    await waitFor(() => expect(transcript.value).toBe('second try says it better'));
  });

  it('saves exactly one fix with the captured context, then says so', async () => {
    captureResult = {
      screenshot: 'dogfood/tmp/one.png',
      image: { width: 2560, height: 1600 },
      content: { width: 1280, height: 800 },
      display: { scale: 2 },
      captured_at: 1,
    };
    renderLayer();
    hotkey();
    await waitFor(() => expect(screen.getByTestId('fix-capture-overlay')).toBeTruthy());
    fireEvent.click(screen.getByTestId('app-target'));
    await waitFor(() => expect(findCall('stream_start')).toBeTruthy());
    hotkey();
    await waitFor(() =>
      expect(screen.getByTestId('fix-capture-panel').getAttribute('data-phase')).toBe('review')
    );
    fireEvent.click(screen.getByTestId('fix-capture-save'));
    await waitFor(() => expect(findCall('save')).toBeTruthy());
    const payload = findCall('save')?.body ?? {};
    expect(payload.transcript).toBe('the button jumps when I click it');
    expect(payload.screenshot).toBe('dogfood/tmp/one.png');
    expect(payload.route).toBe('/guid');
    expect(payload.conversation).toBeNull();
    expect(payload.element).toMatchObject({ tag: 'button' });
    expect(payload.window).toMatchObject({ width: 1280, height: 800, scale: 2 });
    expect(calls.filter((entry) => entry.body?.action === 'save').length).toBe(1);
    await waitFor(() => expect(screen.getByText('Saved as FIX-0001.')).toBeTruthy());
  });

  it('keeps the fix honest when there is no microphone: type instead of record', async () => {
    mic.failWith = 'NotFoundError: no audio device';
    renderLayer();
    hotkey();
    await waitFor(() => expect(screen.getByTestId('fix-capture-overlay')).toBeTruthy());
    fireEvent.click(screen.getByTestId('app-target'));
    const note = await screen.findByTestId('fix-capture-note', {}, { timeout: 3000 });
    // No raw device error reaches the person; the note offers the typed path instead.
    expect(note.textContent).toContain('type what happened instead');
    expect(note.textContent).not.toContain('NotFoundError');
    const transcript = (await screen.findByTestId('fix-capture-transcript')) as HTMLTextAreaElement;
    fireEvent.change(transcript, { target: { value: 'typed: the toast overlaps the title' } });
    fireEvent.click(screen.getByTestId('fix-capture-save'));
    await waitFor(() => expect(findCall('save')).toBeTruthy());
    expect(findCall('save')?.body.transcript).toBe('typed: the toast overlaps the title');
  });

  it('a click outside cancels a review: nothing is saved, nothing is left behind', async () => {
    renderLayer();
    hotkey();
    await waitFor(() => expect(screen.getByTestId('fix-capture-overlay')).toBeTruthy());
    fireEvent.click(screen.getByTestId('app-target'));
    await waitFor(() =>
      expect(screen.getByTestId('fix-capture-panel').getAttribute('data-phase')).toBe('recording')
    );
    fireEvent.mouseDown(document.body);
    await waitFor(() => expect(screen.queryByTestId('fix-capture-panel')).toBeNull());
    expect(findCall('save')).toBeUndefined();
    expect(mic.cancel).toHaveBeenCalled();
  });
});
