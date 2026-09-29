/**
 * D-80: the one-time switch to the one chat store, with a fresh start.
 *
 * Nick needs none of his earlier chats. On the first launch of a build with the one store, every chat
 * that exists is archived — moved to Settings → Archived, nothing deleted — so the sidebar starts
 * empty, and the engine's `chat_store` becomes `engine`. In order:
 *
 * 1. `backup`   the engine copies its database, aioncore's database and the old link files into
 *               `<engine>/chat-store-migration/<stamp>/` (reused, never retaken, by a resumed switch);
 * 2. `freeze`   the engine marks every chat that exists now (active and archived) as a chat from
 *               before the one store, archived (`chat_state`);
 * 3. archive    each active chat (and team) in aioncore, the list the sidebar shows;
 * 4. check      the sidebar is empty, else the switch stops here and the next launch finishes it;
 * 5. `complete` the engine records the switch (the marker) and sets `chat_store = engine`.
 *
 * Every step is idempotent, so a switch cut short (Kel closed, a crash, a busy aioncore) is finished
 * on the next launch; until it is, this run keeps the legacy chat links. `KEL_CHAT_STORE=legacy`
 * skips the switch altogether (the rollback path).
 */
import type { ChatStoreMode } from './chatLinks';

export type EngineCall = (route: string, body?: unknown) => Promise<unknown>;
export type DonorCall = (route: string, body?: unknown, method?: string) => Promise<unknown>;

export type ChatStoreMigrationDeps = {
  engine: EngineCall;
  /** aioncore's HTTP API (the `core` helper in KelService: returns `data` or the payload). */
  donor: DonorCall;
  /** aioncore's database file, copied into the backup before anything changes. */
  donorDb: string;
  /** `KEL_CHAT_STORE` for this run. */
  override: ChatStoreMode | null;
  log?: (line: string) => void;
};

export type ChatStoreMigrationOutcome =
  | { state: 'done'; archived: number; backup: string; switchedAt: number }
  | { state: 'already'; switchedAt: number }
  | { state: 'skipped'; reason: string }
  | { state: 'failed'; error: string; archived: number };

type DonorChat = { id: string; name?: unknown; extra?: { kel_conversation_id?: unknown } | null };
type SidebarItem = { type?: string; conversation?: DonorChat; team_id?: string };
type SidebarGroup = { items?: SidebarItem[] };

/** Rounds of "archive what the sidebar shows": each round clears up to 100 items per group. */
const MAX_ROUNDS = 50;

const notFound = (error: unknown): boolean => String(error).includes(': 404 ');

async function activeChats(donor: DonorCall): Promise<DonorChat[]> {
  const page = (await donor('/api/conversations?limit=10000')) as { items?: DonorChat[] } | DonorChat[] | null;
  const items = Array.isArray(page) ? page : (page?.items ?? []);
  return items.filter((item): item is DonorChat => typeof item?.id === 'string' && item.id.length > 0);
}

/** Every item the active sidebar shows (first window of each group): what Nick would still see. */
async function sidebarItems(donor: DonorCall): Promise<Array<{ type: 'conversation' | 'team'; id: string }>> {
  const read = (await donor('/api/sidebar?limit=100')) as { groups?: SidebarGroup[] } | null;
  const out = new Map<string, { type: 'conversation' | 'team'; id: string }>();
  for (const group of read?.groups ?? [])
    for (const item of group.items ?? []) {
      if (item?.type === 'conversation' && item.conversation?.id)
        out.set('c:' + item.conversation.id, { type: 'conversation', id: item.conversation.id });
      else if (item?.type === 'team' && item.team_id) out.set('t:' + item.team_id, { type: 'team', id: item.team_id });
    }
  return [...out.values()];
}

async function archive(donor: DonorCall, type: 'conversation' | 'team', id: string): Promise<boolean> {
  try {
    await donor(`/api/sidebar/${type}/${encodeURIComponent(id)}/archive`, undefined, 'POST');
    return true;
  } catch (error) {
    if (notFound(error)) return false; // gone already
    throw error;
  }
}

export async function migrateToOneChatStore(deps: ChatStoreMigrationDeps): Promise<ChatStoreMigrationOutcome> {
  const log = deps.log ?? ((line: string) => console.log(line));
  if (deps.override === 'legacy') return { state: 'skipped', reason: 'KEL_CHAT_STORE=legacy' };
  let status: { state?: unknown; finished?: unknown };
  try {
    status = ((await deps.engine('/api/chat-store', { action: 'status' })) ?? {}) as typeof status;
  } catch (error) {
    return { state: 'failed', error: 'This engine cannot switch chat stores: ' + String(error), archived: 0 };
  }
  if (status.state === 'done') return { state: 'already', switchedAt: Number(status.finished) || 0 };
  let archived = 0;
  try {
    const backup = (await deps.engine('/api/chat-store', { action: 'backup', donor_db: deps.donorDb })) as {
      backup?: unknown;
    };
    if (typeof backup?.backup !== 'string' || !backup.backup) throw new Error('the backup was not made');
    log('[KEL-CHAT-STORE] backup: ' + backup.backup);
    const active = await activeChats(deps.donor);
    // Archived chats are frozen too: they are chats from before the one store as well.
    const archivedAlready = await archivedChats(deps.donor);
    const everyChat = new Map<string, DonorChat>();
    for (const chat of [...active, ...archivedAlready]) if (!everyChat.has(chat.id)) everyChat.set(chat.id, chat);
    await deps.engine('/api/chat-store', {
      action: 'freeze',
      chats: [...everyChat.values()].map((chat) => ({
        donor: chat.id,
        conversation: typeof chat.extra?.kel_conversation_id === 'string' ? chat.extra.kel_conversation_id : undefined,
        title: typeof chat.name === 'string' ? chat.name : undefined,
      })),
    });
    for (const chat of active) if (await archive(deps.donor, 'conversation', chat.id)) archived += 1;
    // Whatever the sidebar still shows (teams, chats the plain list left out) goes the same way.
    for (let round = 0; ; round += 1) {
      const left = await sidebarItems(deps.donor);
      if (!left.length) break;
      if (round >= MAX_ROUNDS) throw new Error(left.length + ' chats are still in the sidebar');
      let moved = 0;
      for (const item of left) if (await archive(deps.donor, item.type, item.id)) moved += 1;
      archived += moved;
      if (!moved) throw new Error(left.length + ' chats could not be archived');
    }
    const done = (await deps.engine('/api/chat-store', { action: 'complete', archived })) as { finished?: unknown };
    log('[KEL-CHAT-STORE] switched to the one chat store; archived ' + archived + ' chats');
    return { state: 'done', archived, backup: backup.backup, switchedAt: Number(done?.finished) || Date.now() / 1000 };
  } catch (error) {
    log('[KEL-CHAT-STORE] the switch did not finish; it continues next launch: ' + String(error));
    return { state: 'failed', error: String(error), archived };
  }
}

/** Archived chats, read through the archived sidebar (paged per group). Read failures leave them out. */
async function archivedChats(donor: DonorCall): Promise<DonorChat[]> {
  const out: DonorChat[] = [];
  try {
    const read = (await donor('/api/sidebar?archived=true&limit=100')) as {
      groups?: Array<SidebarGroup & { scope?: { type?: string; project_id?: string; key?: string }; has_more?: boolean; next_cursor?: string }>;
    } | null;
    for (const group of read?.groups ?? []) {
      const take = (items?: SidebarItem[]) => {
        for (const item of items ?? []) if (item?.type === 'conversation' && item.conversation?.id) out.push(item.conversation);
      };
      take(group.items);
      const scope = group.scope;
      const token =
        scope?.type === 'project' && scope.project_id
          ? 'project:' + scope.project_id
          : scope?.type === 'dir' && scope.key
            ? 'dir:' + scope.key
            : scope?.type === 'chats' || scope?.type === 'pinned'
              ? scope.type
              : null;
      let cursor = group.next_cursor;
      for (let page = 0; group.has_more && token && cursor && page < 50; page += 1) {
        const params = new URLSearchParams({ scope: token, cursor, limit: '100', archived: 'true' });
        const next = (await donor('/api/sidebar/items?' + params.toString())) as
          | { items?: SidebarItem[]; has_more?: boolean; next_cursor?: string }
          | null;
        take(next?.items);
        if (!next?.has_more) break;
        cursor = next.next_cursor;
      }
    }
  } catch {
    // The archived list is only read to mark those chats as legacy too; the switch goes on without it.
  }
  return out;
}
