/**
 * D-80: the first launch of the one chat store archives every existing chat (nothing deleted) after a
 * backup, so the sidebar starts empty; the switch is recorded once, is safe to resume, and
 * `KEL_CHAT_STORE=legacy` skips it. CP-10a stage 3: rename, pin, archive and delete reach the engine
 * before aioncore.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { migrateToOneChatStore } from '@process/services/kel/chatStoreMigration';
import { ChatLinks } from '@process/services/kel/chatLinks';
import { rendererKelRequestRefusal } from '@process/services/kel/kelRequestGuard';
import { recordChatState, updateChange, withChatState } from '@/common/adapter/kelChatState';

type Chat = { id: string; name: string; extra?: Record<string, unknown>; archived: boolean; team?: boolean };

/** aioncore as far as the switch sees it: the plain list, the sidebar (active and archived), archive. */
function fakeDonor(chats: Chat[], options: { failArchiveAfter?: number; gone?: string[] } = {}) {
  const calls: string[] = [];
  let archivedCount = 0;
  const item = (chat: Chat) =>
    chat.team ? { type: 'team', team_id: chat.id } : { type: 'conversation', conversation: { id: chat.id, name: chat.name, extra: chat.extra } };
  const donor = async (route: string, _body?: unknown, method?: string): Promise<unknown> => {
    calls.push((method ?? 'GET') + ' ' + route);
    if (route === '/api/conversations?limit=10000')
      return { items: chats.filter((c) => !c.archived && !c.team).map((c) => ({ id: c.id, name: c.name, extra: c.extra })) };
    if (route === '/api/sidebar?limit=100')
      return { groups: [{ scope: { type: 'chats' }, items: chats.filter((c) => !c.archived).map(item), has_more: false }] };
    if (route === '/api/sidebar?archived=true&limit=100')
      return { groups: [{ scope: { type: 'chats' }, items: chats.filter((c) => c.archived).map(item), has_more: false }] };
    const archive = /^\/api\/sidebar\/(conversation|team)\/([^/]+)\/archive$/.exec(route);
    if (archive && method === 'POST') {
      const id = decodeURIComponent(archive[2]);
      if (options.gone?.includes(id)) throw new Error('Kel integration ' + route + ': 404 not found');
      if (options.failArchiveAfter !== undefined && archivedCount >= options.failArchiveAfter)
        throw new Error('Kel integration ' + route + ': 500 busy');
      const chat = chats.find((c) => c.id === id);
      if (chat) chat.archived = true;
      archivedCount += 1;
      return null;
    }
    throw new Error('unexpected donor call ' + route);
  };
  return { donor, calls, chats };
}

/** The engine's `/api/chat-store` with its rules: one backup, idempotent freeze, complete once. */
function fakeEngine(initial: { state?: string } = {}) {
  const calls: Array<{ action: unknown; body: Record<string, unknown> }> = [];
  const record: Record<string, unknown> = { state: initial.state ?? 'none' };
  const frozen = new Map<string, Record<string, unknown>>();
  let backups = 0;
  const engine = async (route: string, body?: unknown): Promise<unknown> => {
    const data = (body ?? {}) as Record<string, unknown>;
    calls.push({ action: data.action, body: data });
    if (route !== '/api/chat-store') throw new Error('unexpected engine route ' + route);
    if (data.action === 'status') return { ...record };
    if (data.action === 'backup') {
      if (!record.backup) {
        backups += 1;
        record.backup = 'C:/engine/chat-store-migration/' + backups;
        record.state = 'started';
      }
      return { ...record };
    }
    if (data.action === 'freeze') {
      for (const chat of data.chats as Array<Record<string, unknown>>) if (!frozen.has(chat.donor as string)) frozen.set(chat.donor as string, chat);
      return { frozen: frozen.size };
    }
    if (data.action === 'complete') {
      record.state = 'done';
      record.finished = 1789400000;
      return { ...record };
    }
    throw new Error('unknown action');
  };
  return { engine, calls, record, frozen, backups: () => backups };
}

const chatsBefore = (): Chat[] => [
  { id: 'a', name: 'First', extra: { kel_conversation_id: 'c-a' }, archived: false },
  { id: 'b', name: 'Second', archived: false },
  { id: 'pinned', name: 'Pinned', archived: false },
  { id: 'team-1', name: 'A team', archived: false, team: true },
  { id: 'old', name: 'Archived before', archived: true },
];

describe('D-80: the switch to the one chat store', () => {
  it('backs up first, freezes every chat, archives them all and records the switch last', async () => {
    const donor = fakeDonor(chatsBefore());
    const engine = fakeEngine();
    const outcome = await migrateToOneChatStore({
      engine: engine.engine,
      donor: donor.donor,
      donorDb: 'C:/Data/store/aionui-backend.db',
      override: null,
      log: () => {},
    });
    expect(outcome).toEqual({ state: 'done', archived: 4, backup: 'C:/engine/chat-store-migration/1', switchedAt: 1789400000 });
    expect(engine.calls.map((c) => c.action)).toEqual(['status', 'backup', 'freeze', 'complete']);
    expect(engine.calls[1].body.donor_db).toBe('C:/Data/store/aionui-backend.db');
    // Every chat is a chat from before the one store, the archived one too; the app's own link travels.
    expect([...engine.frozen.keys()].sort()).toEqual(['a', 'b', 'old', 'pinned']);
    expect(engine.frozen.get('a')).toMatchObject({ conversation: 'c-a', title: 'First' });
    // The sidebar is empty; every chat (the team too) is in Archived, and nothing was deleted.
    expect(donor.chats.every((c) => c.archived)).toBe(true);
    expect(donor.chats).toHaveLength(5);
    expect(donor.calls.some((c) => c.startsWith('DELETE'))).toBe(false);
    const firstArchive = donor.calls.findIndex((c) => c.startsWith('POST'));
    const freezeAt = engine.calls.findIndex((c) => c.action === 'freeze');
    expect(firstArchive).toBeGreaterThan(-1);
    expect(freezeAt).toBe(2);
    expect(donor.calls).toContain('POST /api/sidebar/team/team-1/archive');
  });

  it('does nothing on a launch after the switch', async () => {
    const donor = fakeDonor(chatsBefore());
    const engine = fakeEngine({ state: 'done' });
    engine.record.finished = 1789400000;
    const outcome = await migrateToOneChatStore({ engine: engine.engine, donor: donor.donor, donorDb: 'x', override: null, log: () => {} });
    expect(outcome).toEqual({ state: 'already', switchedAt: 1789400000 });
    expect(engine.calls.map((c) => c.action)).toEqual(['status']);
    expect(donor.calls).toEqual([]);
    expect(donor.chats.filter((c) => !c.archived)).toHaveLength(4);
  });

  it('a switch cut short finishes on the next launch with the first backup', async () => {
    const chats = chatsBefore();
    const engine = fakeEngine();
    const cut = await migrateToOneChatStore({
      engine: engine.engine,
      donor: fakeDonor(chats, { failArchiveAfter: 1 }).donor,
      donorDb: 'x',
      override: null,
      log: () => {},
    });
    expect(cut.state).toBe('failed');
    expect(engine.record.state).toBe('started');
    expect(chats.filter((c) => !c.archived).length).toBeGreaterThan(0);
    // The run that failed keeps the legacy links (KelService passes `legacy` to ChatLinks.open).
    const again = await migrateToOneChatStore({
      engine: engine.engine,
      donor: fakeDonor(chats).donor,
      donorDb: 'x',
      override: null,
      log: () => {},
    });
    expect(again).toMatchObject({ state: 'done', backup: 'C:/engine/chat-store-migration/1' });
    expect(engine.backups()).toBe(1);
    expect(chats.every((c) => c.archived)).toBe(true);
  });

  it('a chat already gone is not an error', async () => {
    const donor = fakeDonor(chatsBefore(), { gone: ['b'] });
    const chat = donor.chats.find((c) => c.id === 'b')!;
    const engine = fakeEngine();
    const listOnce = donor.donor;
    // The plain list still names it, but aioncore answers 404 and the sidebar no longer shows it.
    const outcome = await migrateToOneChatStore({
      engine: engine.engine,
      donor: async (route, body, method) => {
        if (route === '/api/sidebar?limit=100') chat.archived = true;
        return listOnce(route, body, method);
      },
      donorDb: 'x',
      override: null,
      log: () => {},
    });
    expect(outcome.state).toBe('done');
  });

  it('stops before recording the switch when the sidebar would not empty', async () => {
    const donor = fakeDonor(chatsBefore(), { failArchiveAfter: 0 });
    const engine = fakeEngine();
    const outcome = await migrateToOneChatStore({ engine: engine.engine, donor: donor.donor, donorDb: 'x', override: null, log: () => {} });
    expect(outcome.state).toBe('failed');
    expect(engine.calls.map((c) => c.action)).not.toContain('complete');
  });

  it('KEL_CHAT_STORE=legacy skips the switch; an engine without it is a failure, not a crash', async () => {
    const engine = fakeEngine();
    const skipped = await migrateToOneChatStore({ engine: engine.engine, donor: fakeDonor([]).donor, donorDb: 'x', override: 'legacy' });
    expect(skipped).toEqual({ state: 'skipped', reason: 'KEL_CHAT_STORE=legacy' });
    expect(engine.calls).toEqual([]);
    const old = await migrateToOneChatStore({
      engine: async () => {
        throw new Error('Unknown route');
      },
      donor: fakeDonor([]).donor,
      donorDb: 'x',
      override: null,
      log: () => {},
    });
    expect(old.state).toBe('failed');
  });

  it('an install with no chats switches at once', async () => {
    const engine = fakeEngine();
    const outcome = await migrateToOneChatStore({ engine: engine.engine, donor: fakeDonor([]).donor, donorDb: 'x', override: null, log: () => {} });
    expect(outcome).toMatchObject({ state: 'done', archived: 0 });
  });

  it('a run whose switch did not finish opens the links in legacy', async () => {
    const bodies: unknown[] = [];
    const links = await ChatLinks.open(
      'C:/nowhere',
      async (_route, body) => {
        bodies.push(body);
        return { mode: (body as { override?: string }).override ?? 'engine' };
      },
      {},
      'legacy'
    );
    expect(links.mode).toBe('legacy');
    expect(bodies[0]).toEqual({ action: 'mode', override: 'legacy' });
  });
});

describe('CP-10a stage 3: chat state reaches the engine first', () => {
  afterEach(() => {
    delete (globalThis as { window?: unknown }).window;
  });

  it('records rename, pin, archive and delete before aioncore is asked', async () => {
    const order: string[] = [];
    (globalThis as { window?: unknown }).window = {
      kelAPI: {
        request: async (route: string, body: unknown) => {
          order.push('engine ' + route + ' ' + JSON.stringify(body));
          return {};
        },
      },
    };
    const inner = {
      provider: () => {},
      invoke: async (params: { id: string; updates?: Record<string, unknown> }) => {
        order.push('aioncore ' + params.id);
        return true;
      },
    };
    const update = withChatState(inner, (p) => updateChange(p));
    await update.invoke({ id: 'chat', updates: { name: '  Friday plans ' } });
    await update.invoke({ id: 'chat', updates: { extra: { pinned: true } } });
    await update.invoke({ id: 'chat', updates: { extra: { workspace: 'C:/x' } } });
    expect(order).toEqual([
      'engine /api/chat-state {"action":"set","donor":"chat","title":"Friday plans"}',
      'aioncore chat',
      'engine /api/chat-state {"action":"set","donor":"chat","pinned":true}',
      'aioncore chat',
      'aioncore chat',
    ]);
    await recordChatState({ action: 'delete-archived' });
    expect(order[order.length - 1]).toBe('engine /api/chat-state {"action":"delete-archived"}');
  });

  it('an engine that refuses stops the change; a page without the engine bridge goes straight on', async () => {
    const aioncore = vi.fn(async () => true);
    const archive = withChatState({ provider: () => {}, invoke: aioncore }, () => ({ donor: 'chat', archived: true }));
    await archive.invoke();
    expect(aioncore).toHaveBeenCalledTimes(1);
    (globalThis as { window?: unknown }).window = {
      kelAPI: {
        request: async () => {
          throw new Error('Kel is not answering');
        },
      },
    };
    await expect(archive.invoke()).rejects.toThrow('Kel is not answering');
    expect(aioncore).toHaveBeenCalledTimes(1);
  });

  it('the page may write chat state but never run the switch', () => {
    expect(rendererKelRequestRefusal('/api/chat-state', { donor: 'chat', archived: true })).toBeNull();
    expect(rendererKelRequestRefusal('/api/chat-store', { action: 'complete' })).toBe('Unknown Kel action');
  });
});
