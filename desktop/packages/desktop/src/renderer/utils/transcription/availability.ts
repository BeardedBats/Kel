/** Capability check only. Never requests permission or starts a recording. */
export function microphoneUnavailableReason(): string | null {
  if (typeof window !== 'undefined' && window.isSecureContext === false) {
    return 'This connection cannot record audio. Use Kel on the desktop, or upload an audio file.';
  }
  if (typeof navigator === 'undefined' || typeof navigator.mediaDevices?.getUserMedia !== 'function' || typeof AudioContext !== 'function') {
    return 'This browser cannot record audio. Upload an audio file, or type your message.';
  }
  return null;
}
