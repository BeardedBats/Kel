import { afterEach, describe, expect, it, vi } from 'vitest';
import { startMicCapture } from '../../packages/desktop/src/renderer/utils/transcription/audio';

afterEach(() => vi.unstubAllGlobals());

describe('microphone initialization failure', () => {
  it('releases acquired tracks when AudioContext creation fails', async () => {
    const stop = vi.fn();
    const failure = new Error('AudioContext unavailable');
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) } });
    vi.stubGlobal('AudioContext', class { constructor() { throw failure; } });
    await expect(startMicCapture()).rejects.toBe(failure);
    expect(stop).toHaveBeenCalledOnce();
  });

  it('closes the context and releases tracks when node initialization fails', async () => {
    const stop = vi.fn();
    const close = vi.fn().mockResolvedValue(undefined);
    const disconnect = vi.fn();
    const failure = new Error('Processor unavailable');
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) } });
    vi.stubGlobal('AudioContext', class {
      close = close;
      createMediaStreamSource() { return { disconnect }; }
      createScriptProcessor() { throw failure; }
    });
    await expect(startMicCapture()).rejects.toBe(failure);
    expect(stop).toHaveBeenCalledOnce();
    expect(close).toHaveBeenCalledOnce();
    expect(disconnect).toHaveBeenCalledOnce();
  });
});
