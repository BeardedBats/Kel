/**
 * CP-10a stage 3 (D-77): rename, pin, archive, unarchive and delete are written to Kel's engine first
 * (`/api/chat-state`), then to aioncore, whose row stays the chat's handle and the sidebar's list.
 *
 * Each wrapped call asks the engine only in the desktop app (the preload's `kelAPI`); an engine that
 * refuses fails the action, so the two never silently drift apart. Calls that do not change what the
 * engine keeps (a workspace, a model, a sort order) go straight to aioncore.
 */
export type ChatStateChange = {
  action?: 'set' | 'delete-archived';
  donor?: string;
  title?: string;
  archived?: boolean;
  pinned?: boolean;
  deleted?: boolean;
};

type Provider<Data, Params> = {
  provider: (handler: (params: Params) => Promise<Data>) => void;
  invoke: Params extends undefined ? () => Promise<Data> : (params: Params) => Promise<Data>;
};

type KelBridge = { request?: (route: string, body?: unknown) => Promise<unknown> };

const kelBridge = (): KelBridge | undefined =>
  (globalThis as unknown as { window?: { kelAPI?: KelBridge } }).window?.kelAPI;

/** Tell the engine first; null when this call changes nothing the engine keeps. */
export async function recordChatState(change: ChatStateChange | null): Promise<void> {
  if (!change) return;
  const request = kelBridge()?.request;
  if (!request) return; // WebUI / tests: no engine bridge in this page
  await request('/api/chat-state', { action: 'set', ...change });
}

export function withChatState<Data, Params>(
  inner: Provider<Data, Params>,
  change: (params: Params) => ChatStateChange | null
): Provider<Data, Params> {
  return {
    provider: () => {},
    invoke: (async (params?: Params) => {
      await recordChatState(change(params as Params));
      return (inner.invoke as (p?: Params) => Promise<Data>)(params);
    }) as Provider<Data, Params>['invoke'],
  };
}

/** What a conversation update changes that the engine keeps: the name, or the pin. */
export function updateChange(params: {
  id: string;
  updates?: { name?: unknown; extra?: { pinned?: unknown } | null };
}): ChatStateChange | null {
  const change: ChatStateChange = { donor: params.id };
  const name = params.updates?.name;
  if (typeof name === 'string' && name.trim()) change.title = name.trim();
  const pinned = params.updates?.extra?.pinned;
  if (typeof pinned === 'boolean') change.pinned = pinned;
  return change.title !== undefined || change.pinned !== undefined ? change : null;
}
