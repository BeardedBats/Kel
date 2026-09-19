/**
 * Campaign C AUD-MAJOR-002: the shared sender-guard truth table.
 *
 * The guard is the single boundary decision for every privileged IPC channel; these cases pin
 * the exact acceptance set (packaged main frame; dev server only when allowed) and the
 * fail-closed behaviour for subframes, foreign origins, and missing/malformed metadata.
 */
import { describe, expect, it } from 'vitest';
import { assertTrustedSender, isTrustedSender, SENDER_REFUSAL_MESSAGE } from '@/common/senderGuard';

const mainFrame = { url: 'file:///C:/kel/apps/renderer/index.html' };
const packagedMain = { senderFrame: mainFrame, sender: { mainFrame } };

const devFrame = { url: 'http://localhost:5173/index.html' };
const devMain = { senderFrame: devFrame, sender: { mainFrame: devFrame } };

const subframe = { url: 'file:///C:/kel/apps/renderer/artifact-preview.html' };
const subframeOfPackagedWindow = { senderFrame: subframe, sender: { mainFrame } };

const foreignFrame = { url: 'https://evil.example/login' };
const foreignMain = { senderFrame: foreignFrame, sender: { mainFrame: foreignFrame } };

describe('sender guard (Campaign C AUD-MAJOR-002)', () => {
  it('accepts the packaged main frame', () => {
    expect(isTrustedSender(packagedMain)).toBe(true);
    expect(isTrustedSender(packagedMain, { allowDevServer: true })).toBe(true);
  });

  it('accepts the dev-server main frame only when allowDevServer is set', () => {
    expect(isTrustedSender(devMain)).toBe(false);
    expect(isTrustedSender(devMain, { allowDevServer: true })).toBe(true);
  });

  it('refuses a subframe even when the top frame is trusted', () => {
    expect(isTrustedSender(subframeOfPackagedWindow)).toBe(false);
    expect(isTrustedSender(subframeOfPackagedWindow, { allowDevServer: true })).toBe(false);
  });

  it('refuses a main frame from a foreign origin', () => {
    expect(isTrustedSender(foreignMain)).toBe(false);
    expect(isTrustedSender(foreignMain, { allowDevServer: true })).toBe(false);
  });

  it('fails closed when sender metadata is missing', () => {
    expect(isTrustedSender(undefined)).toBe(false);
    expect(isTrustedSender(null)).toBe(false);
    expect(isTrustedSender({ sender: { mainFrame } })).toBe(false);
    expect(isTrustedSender({ senderFrame: mainFrame })).toBe(false);
    expect(isTrustedSender({ senderFrame: null, sender: { mainFrame } })).toBe(false);
    expect(isTrustedSender({ senderFrame: mainFrame, sender: null })).toBe(false);
  });

  it('fails closed on malformed metadata (no url, mismatched frame identity)', () => {
    const noUrl = {};
    expect(isTrustedSender({ senderFrame: noUrl, sender: { mainFrame: noUrl } })).toBe(false);
    expect(
      isTrustedSender({ senderFrame: { url: 'file:///x' }, sender: { mainFrame: { url: 'file:///x' } } })
    ).toBe(false);
    expect(isTrustedSender({ senderFrame: { url: '' }, sender: { mainFrame: { url: '' } } })).toBe(false);
  });

  it('assertTrustedSender throws the shared refusal for untrusted senders only', () => {
    expect(() => assertTrustedSender(packagedMain)).not.toThrow();
    expect(() => assertTrustedSender(devMain, { allowDevServer: true })).not.toThrow();
    expect(() => assertTrustedSender(subframeOfPackagedWindow)).toThrow(SENDER_REFUSAL_MESSAGE);
    expect(() => assertTrustedSender(foreignMain)).toThrow(SENDER_REFUSAL_MESSAGE);
    expect(() => assertTrustedSender(undefined)).toThrow(SENDER_REFUSAL_MESSAGE);
  });
});
