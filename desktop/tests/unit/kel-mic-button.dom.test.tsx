/**
 * V2-05 — mobile voice: the transport, and the failure nobody could see.
 *
 * A phone browser has no `window.kelAPI`. The mic button used to require it, so voice threw
 * "Kel is not connected" before a single request left the page — and that throw was swallowed into a
 * silent recording. These tests hold both halves: transcription goes through the same Kel transport as
 * every other call, and a stream_start that fails is said out loud in plain words instead of nowhere.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { Message } from '@arco-design/web-react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const startMicCapture = vi.fn();

vi.mock('@renderer/utils/transcription/audio', () => ({
  friendlyMicError: (error: unknown) => `mic: ${String(error)}`,
  startMicCapture: (...args: unknown[]) => startMicCapture(...args),
}));

import KelMicButton from '@renderer/pages/guid/components/KelMicButton';

const capture = {
  stop: vi.fn(async () => ({ base64: 'UklGRg==', durationMs: 1400 })),
  cancel: vi.fn(),
};

const jsonResponse = (body: Record<string, unknown>, ok = true) =>
  ({ ok, status: ok ? 200 : 500, json: async () => body, text: async () => JSON.stringify(body) }) as unknown as Response;

/** What the browser sends: the gateway path, never the desktop bridge. */
const calls = (): Array<{ url: string; action: string }> =>
  (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.map(([url, init]) => ({
    url: String(url),
    action: String(JSON.parse(String((init as RequestInit | undefined)?.body ?? '{}')).action ?? ''),
  }));

describe('mobile voice transport (V2-05)', () => {
  let info: ReturnType<typeof vi.spyOn>;
  let error: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // The phone: a real browser page with no preload bridge.
    delete (window as unknown as { kelAPI?: unknown }).kelAPI;
    startMicCapture.mockReset();
    startMicCapture.mockResolvedValue(capture);
    capture.stop.mockClear();
    capture.cancel.mockClear();
    globalThis.fetch = vi.fn(async () => jsonResponse({ session_id: 'sess-1', live: true })) as unknown as typeof fetch;
    info = vi.spyOn(Message, 'info').mockImplementation(() => undefined as never);
    error = vi.spyOn(Message, 'error').mockImplementation(() => undefined as never);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('records through the shared Kel transport even though the desktop bridge is absent', async () => {
    render(<KelMicButton onTranscript={() => undefined} />);
    screen.getByTestId('kel-mic-toggle').click();

    await waitFor(() => expect(screen.getByTestId('kel-mic').getAttribute('data-state')).toBe('recording'));
    expect(calls().map((call) => call.url)).toContain('/kel/api/transcription');
    expect(calls().map((call) => call.action)).toContain('stream_start');
  });

  it('says live typing is unavailable instead of swallowing a failed stream_start', async () => {
    globalThis.fetch = vi.fn(async () => jsonResponse({ error: 'transcription key missing' }, false)) as unknown as typeof fetch;

    render(<KelMicButton onTranscript={() => undefined} />);
    screen.getByTestId('kel-mic-toggle').click();

    await waitFor(() => expect(info).toHaveBeenCalled());
    expect(String(info.mock.calls[0]?.[0])).toMatch(/live typing is not available/i);
    // The recording is still the user's: capture runs, and the UI shows exactly that.
    await waitFor(() => expect(screen.getByTestId('kel-mic').getAttribute('data-state')).toBe('recording'));
  });

  it('transcribes on stop and hands the words to the composer', async () => {
    globalThis.fetch = vi.fn(async (url: string) => {
      const body = String(url).includes('transcription') ? {} : {};
      void body;
      return jsonResponse({ session_id: 'sess-1', live: true, text: 'Mobile Kel Muse verification, green baseball sixty-four.' });
    }) as unknown as typeof fetch;
    const onTranscript = vi.fn();

    render(<KelMicButton onTranscript={onTranscript} />);
    screen.getByTestId('kel-mic-toggle').click();
    await waitFor(() => expect(screen.getByTestId('kel-mic').getAttribute('data-state')).toBe('recording'));
    screen.getByTestId('kel-mic-toggle').click();

    await waitFor(() => expect(onTranscript).toHaveBeenCalledWith('Mobile Kel Muse verification, green baseball sixty-four.'));
    await waitFor(() => expect(calls().map((call) => call.action)).toContain('stream_finish'));
  });

  it('tells the user in plain words when the transcription path is dead — no jargon, no ids', async () => {
    globalThis.fetch = vi.fn(async () => jsonResponse({ error: 'unreachable' }, false)) as unknown as typeof fetch;
    const onTranscript = vi.fn();

    render(<KelMicButton onTranscript={onTranscript} />);
    screen.getByTestId('kel-mic-toggle').click();
    await waitFor(() => expect(screen.getByTestId('kel-mic').getAttribute('data-state')).toBe('recording'));
    screen.getByTestId('kel-mic-toggle').click();

    await waitFor(() => expect(error).toHaveBeenCalled());
    const sentence = String(error.mock.calls[error.mock.calls.length - 1]?.[0]);
    expect(sentence).toMatch(/recording|could not transcribe|not reachable/i);
    expect(sentence).not.toMatch(/\/kel|stream_|quick_|sess-|Bearer|fetch/i);
    expect(onTranscript).not.toHaveBeenCalled();
  });
});
