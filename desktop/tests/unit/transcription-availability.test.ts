import { afterEach, expect, it, vi } from 'vitest';
import { microphoneUnavailableReason } from '../../packages/desktop/src/renderer/utils/transcription/availability';

afterEach(() => vi.unstubAllGlobals());

it('explains insecure connections without requesting microphone permission', () => {
  const getUserMedia = vi.fn();
  vi.stubGlobal('window', { isSecureContext: false });
  vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
  expect(microphoneUnavailableReason()).toContain('Use Kel on the desktop, or upload an audio file.');
  expect(getUserMedia).not.toHaveBeenCalled();
});

it('keeps unsupported browser capture separate from provider setup', () => {
  vi.stubGlobal('window', { isSecureContext: true });
  vi.stubGlobal('navigator', {});
  expect(microphoneUnavailableReason()).toContain('This browser cannot record audio.');
});

it('accepts capture APIs without claiming a device or recording exists', () => {
  const getUserMedia = vi.fn();
  vi.stubGlobal('window', { isSecureContext: true });
  vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
  vi.stubGlobal('AudioContext', class {});
  expect(microphoneUnavailableReason()).toBeNull();
  expect(getUserMedia).not.toHaveBeenCalled();
});
