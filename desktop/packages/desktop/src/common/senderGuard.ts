/**
 * One sender-validation primitive for every privileged IPC channel (Campaign C AUD-MAJOR-002).
 *
 * A privileged channel may only be driven by the application's own top-level renderer frame:
 * the sending frame must be the main frame of its webContents (`senderFrame === sender.mainFrame`)
 * and must be loaded from the packaged renderer (`file:`) or - when `allowDevServer` is set - the
 * development server (`http://localhost:`). Subframes (artifact-preview iframes), foreign origins,
 * and missing or malformed sender metadata are refused. Fails closed: no frame, no url, no pass.
 */

export const SENDER_REFUSAL_MESSAGE = 'Unknown Kel window';

/** The Electron event fields the guard reads (works for `ipcMain.handle` and sendSync events). */
export interface GuardableSenderEvent {
  senderFrame?: { url?: string | null } | null;
  sender?: { mainFrame?: unknown } | null;
}

export interface SenderGuardOptions {
  /** Accept the dev-server origin (`http://localhost:*`) in addition to packaged `file:`. */
  allowDevServer?: boolean;
}

export const isTrustedSender = (
  event: GuardableSenderEvent | null | undefined,
  options?: SenderGuardOptions
): boolean => {
  const frame = event?.senderFrame;
  const mainFrame = event?.sender?.mainFrame;
  if (!frame || !mainFrame || frame !== mainFrame) return false;
  const url = typeof frame.url === 'string' ? frame.url : '';
  if (url.startsWith('file:')) return true;
  return options?.allowDevServer === true && url.startsWith('http://localhost:');
};

/** Throw the shared refusal for untrusted senders (use on `ipcMain.handle`-style channels). */
export const assertTrustedSender = (
  event: GuardableSenderEvent | null | undefined,
  options?: SenderGuardOptions
): void => {
  if (!isTrustedSender(event, options)) throw new Error(SENDER_REFUSAL_MESSAGE);
};
