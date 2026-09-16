/**
 * Microphone capture and WAV preparation for Kel's transcription pipeline.
 *
 * The donor app prepared audio in its Rust backend with a bundled FFmpeg sidecar. Kel keeps the
 * renderer as the only place that touches browser media APIs and prepares 24 kHz mono PCM16 WAV
 * here — the engine accepts WAV directly, so there is no external binary to ship.
 */
export const TARGET_RATE = 24000;

export function toBase64(bytes: Uint8Array): string {
  let binary = '';
  const step = 0x8000;
  for (let index = 0; index < bytes.length; index += step) {
    binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(index, index + step)) as unknown as number[]);
  }
  return btoa(binary);
}

export function floatToPcm16(input: Float32Array, sourceRate: number, targetRate = TARGET_RATE): Int16Array {
  const ratio = sourceRate / targetRate;
  const length = Math.max(1, Math.round(input.length / ratio));
  const output = new Int16Array(length);
  for (let index = 0; index < length; index += 1) {
    const position = index * ratio;
    const left = Math.floor(position);
    const right = Math.min(left + 1, input.length - 1);
    const mix = position - left;
    const sample = Math.max(-1, Math.min(1, input[left] * (1 - mix) + input[right] * mix));
    output[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output;
}

export function pcm16ToWav(pcm: Int16Array, rate = TARGET_RATE): Uint8Array {
  const buffer = new ArrayBuffer(44 + pcm.length * 2);
  const view = new DataView(buffer);
  const writeText = (offset: number, text: string) => {
    for (let index = 0; index < text.length; index += 1) view.setUint8(offset + index, text.charCodeAt(index));
  };
  writeText(0, 'RIFF');
  view.setUint32(4, 36 + pcm.length * 2, true);
  writeText(8, 'WAVE');
  writeText(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeText(36, 'data');
  view.setUint32(40, pcm.length * 2, true);
  for (let index = 0; index < pcm.length; index += 1) view.setInt16(44 + index * 2, pcm[index], true);
  return new Uint8Array(buffer);
}

export function pcmDurationMs(pcm: Int16Array, rate = TARGET_RATE): number {
  return Math.round((pcm.length / rate) * 1000);
}

export function friendlyMicError(error: unknown): string {
  const text = String((error as { name?: string; message?: string })?.name || (error as Error)?.message || error || '');
  if (/NotAllowed|Permission/i.test(text)) {
    return 'Kel needs microphone access to record audio. Allow the microphone for Kel, then try again.';
  }
  if (/NotFound|Devices/i.test(text)) {
    return 'No microphone was found on this computer.';
  }
  if (/NotReadable|Track/i.test(text)) {
    return 'The microphone is already in use by another app. Close it, then try again.';
  }
  return 'Kel could not start the microphone. Check your sound settings, then try again.';
}

export type MicCapture = {
  stop(): Promise<{ wav: Uint8Array; base64: string; durationMs: number }>;
  cancel(): void;
};

export async function startMicCapture(onPcm?: (base64: string) => void): Promise<MicCapture> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  const context = new AudioContext({ sampleRate: TARGET_RATE });
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const sink = context.createGain();
  sink.gain.value = 0;
  const parts: Int16Array[] = [];
  let stopped = false;
  processor.onaudioprocess = (event) => {
    if (stopped) return;
    const pcm = floatToPcm16(event.inputBuffer.getChannelData(0), context.sampleRate);
    parts.push(pcm);
    if (onPcm) {
      try {
        onPcm(toBase64(new Uint8Array(pcm.buffer.slice(0))));
      } catch {
        /* live feeding is best-effort; the final WAV is always captured */
      }
    }
  };
  source.connect(processor);
  processor.connect(sink);
  sink.connect(context.destination);
  const teardown = () => {
    try {
      processor.disconnect();
      source.disconnect();
      sink.disconnect();
    } catch {
      /* already torn down */
    }
    stream.getTracks().forEach((track) => track.stop());
    void context.close();
  };
  return {
    async stop() {
      if (stopped) throw new Error('The recording already stopped.');
      stopped = true;
      teardown();
      const total = parts.reduce((sum, part) => sum + part.length, 0);
      const merged = new Int16Array(total);
      let offset = 0;
      for (const part of parts) {
        merged.set(part, offset);
        offset += part.length;
      }
      const wav = pcm16ToWav(merged);
      return { wav, base64: toBase64(wav), durationMs: pcmDurationMs(merged) };
    },
    cancel() {
      stopped = true;
      teardown();
    },
  };
}

export async function decodeFileToWav(file: File): Promise<{ wav: Uint8Array; base64: string; durationMs: number }> {
  const buffer = await file.arrayBuffer();
  const context = new AudioContext();
  try {
    const decoded = await context.decodeAudioData(buffer.slice(0));
    const channels = decoded.numberOfChannels;
    const frames = decoded.length;
    const mixed = new Float32Array(frames);
    for (let channel = 0; channel < channels; channel += 1) {
      const data = decoded.getChannelData(channel);
      for (let index = 0; index < frames; index += 1) mixed[index] += data[index] / channels;
    }
    const pcm = floatToPcm16(mixed, decoded.sampleRate);
    const wav = pcm16ToWav(pcm);
    return { wav, base64: toBase64(wav), durationMs: pcmDurationMs(pcm) };
  } catch {
    throw new Error('That file could not be read as audio or video. Choose an MP3 or MP4 file.');
  } finally {
    void context.close();
  }
}
