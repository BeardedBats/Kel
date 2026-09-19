/**
 * Batch 6 (visual findings 16/17) — pins for the failure classifier and copy.
 *
 * The hard requirement under test: nothing a person can see may contain transport or
 * infrastructure text (TypeError / fetch failed / ECONN* / traceback / IPC envelopes / daemon
 * vocabulary). Raw detail is allowed only in the diagnostics text.
 */
import { describe, expect, it } from 'vitest';
import {
  classifyEngineFailure,
  diagnosticsText,
  engineStateCopy,
  failureCopy,
  failureSentence,
  stripTransportEnvelope,
} from '@renderer/components/kel/engineFailure';

describe('stripTransportEnvelope', () => {
  it('removes the Electron IPC envelope and Error prefixes', () => {
    expect(stripTransportEnvelope("Error invoking remote method 'kel:request': Error: Web is off for this conversation.")).toBe(
      'Web is off for this conversation.'
    );
    expect(stripTransportEnvelope("Error invoking remote method 'kel:request': TypeError: fetch failed")).toBe('fetch failed');
  });

  it('leaves plain engine sentences untouched', () => {
    expect(stripTransportEnvelope('That conversation is still running.')).toBe('That conversation is still running.');
  });
});

describe('classifyEngineFailure', () => {
  it('classifies transport failures', () => {
    expect(classifyEngineFailure(new Error('TypeError: fetch failed'))).toBe('engine-unreachable');
    expect(classifyEngineFailure(new Error('connect ECONNREFUSED 127.0.0.1:5173'))).toBe('engine-unreachable');
    expect(classifyEngineFailure(new Error('The operation was aborted due to timeout'))).toBe('engine-timeout');
    expect(classifyEngineFailure(new Error('Kel bridge unavailable — restart Kel and try again'))).toBe('bridge-unavailable');
  });

  it('keeps plain-language engine sentences as their own class', () => {
    expect(classifyEngineFailure(new Error('Web is off for this conversation'))).toBe('engine-sentence');
    expect(classifyEngineFailure('That approval was already resolved.')).toBe('engine-sentence');
  });

  it('routes everything unrecognisable to unexpected, never to a raw rendering', () => {
    expect(classifyEngineFailure(new Error('Traceback (most recent call last): File "x.py"'))).toBe('unexpected');
    expect(classifyEngineFailure(undefined)).toBe('unexpected');
  });
});

describe('copy never leaks infrastructure text', () => {
  const raws = [
    'TypeError: fetch failed',
    "Error invoking remote method 'kel:request': TypeError: fetch failed",
    'Traceback (most recent call last): File "service.py", line 1',
    'connect ECONNREFUSED 127.0.0.1:5173',
    'C:\\Users\\Nick\\AppData\\Local\\Programs\\Kel\\resources\\kel-engine\\KelEngine.exe did not start',
  ];

  it('every visible sentence is clean for every class', () => {
    for (const raw of raws) {
      const kind = classifyEngineFailure(raw);
      const copy = failureCopy(kind, stripTransportEnvelope(raw));
      const visible = `${copy.title} ${copy.detail}`.toLowerCase();
      expect(visible).not.toMatch(/typeerror|fetch failed|econnrefused|traceback|remote method|\bipc\b|\bdaemon\b|\bbroker\b|\.py\b/);
    }
  });

  it('the raw text survives only in the diagnostics bundle', () => {
    const text = diagnosticsText({ title: 'Kel is taking too long to answer', raw: 'TypeError: fetch failed', engineVersion: '1.6.0' });
    expect(text).toContain('TypeError: fetch failed');
    expect(text).toContain('engine: 1.6.0');
  });
});

describe('failureSentence', () => {
  it('maps transport failures to the local-engine sentence', () => {
    expect(failureSentence(new Error('TypeError: fetch failed'), 'x')).toBe(
      "Kel couldn't reach its local engine. Your work is preserved, and Kel will try to bring the engine back."
    );
  });

  it('passes engine sentences through', () => {
    expect(failureSentence(new Error('That recording is still transcribing.'), 'x')).toBe('That recording is still transcribing.');
  });

  it('falls back honestly for unexpected failures', () => {
    expect(failureSentence(new Error('Traceback (most recent call last)'), 'x')).toMatch(/unexpected problem/);
  });
});

describe('engineStateCopy', () => {
  it('says nothing while connected', () => {
    expect(engineStateCopy({ state: 'connected', attempts: 0, maxAttempts: 2, at: 0 })).toBeNull();
    expect(engineStateCopy(null)).toBeNull();
  });

  it('describes reconnecting, recovered and unrecoverable states truthfully', () => {
    expect(engineStateCopy({ state: 'reconnecting', attempts: 1, maxAttempts: 2, at: 0 })?.title).toBe('Kel is reconnecting');
    const recovered = engineStateCopy({ state: 'recovered', attempts: 1, maxAttempts: 2, at: 0 });
    expect(recovered?.tone).toBe('ok');
    expect(recovered?.detail).toMatch(/preserved/);
    const failed = engineStateCopy({ state: 'unrecoverable', attempts: 2, maxAttempts: 2, at: 0 });
    expect(failed?.tone).toBe('failed');
    expect(failed?.detail).toMatch(/2 attempts/);
  });
});
