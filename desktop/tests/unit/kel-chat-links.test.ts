/**
 * CP-10a stage 1 (D-77): the main process reads and writes chat links through one place. `legacy`
 * is the old file behaviour; `engine` is the engine's `chat_links` table, and never rewrites the files.
 */
import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ChatLinks, chatStoreOverride } from '@process/services/kel/chatLinks';
import { donorsForMessages } from '@process/services/kel/reconcileHistory';
import { listConversationsForRepair } from '@process/services/kel/repairWorkspacePaths';

let root: string;

const record = (donor: string, cid: string) => {
  const folder = path.join(root, 'aion-session-map');
  fs.mkdirSync(folder, { recursive: true });
  const name = crypto.createHash('sha256').update(donor).digest('hex') + '.json';
  fs.writeFileSync(path.join(folder, name), JSON.stringify({ [donor]: cid }));
};
const writeLegacy = (value: Record<string, string>) =>
  fs.writeFileSync(path.join(root, 'aion-conversations.json'), JSON.stringify(value));
const readLegacy = () => JSON.parse(fs.readFileSync(path.join(root, 'aion-conversations.json'), 'utf8'));
const snapshot = () => {
  const out: Record<string, string> = {};
  const walk = (dir: string) => {
    for (const name of fs.readdirSync(dir)) {
      const full = path.join(dir, name);
      if (fs.statSync(full).isDirectory()) walk(full);
      else out[path.relative(root, full)] = fs.readFileSync(full, 'utf8');
    }
  };
  walk(root);
  return out;
};

/** A stand-in for the engine's `/api/chat-link` with the table's rules that matter here. */
function fakeEngine(mode: 'legacy' | 'engine' | 'missing', table: Record<string, string> = {}) {
  const calls: Array<{ route: string; body?: unknown }> = [];
  let override: string | null = null;
  const engine = async (route: string, body?: unknown): Promise<unknown> => {
    calls.push({ route, body });
    if (mode === 'missing') throw new Error('Not found');
    const data = (body || {}) as Record<string, unknown>;
    if (route === '/api/chat-link' && data.action === 'mode') {
      override = (data.override as string | null) ?? null;
      return { mode: override || mode };
    }
    if (data.action === 'import') {
      for (const [donor, cid] of Object.entries(data.links as Record<string, string>)) table[donor] ??= cid;
      return { links: { ...table }, conflicts: [{ donor: 'x' }] };
    }
    if (data.action === 'link') {
      table[data.donor as string] ??= data.conversation as string;
      return { conversation: table[data.donor as string] };
    }
    if (data.action === 'retire') {
      delete table[data.donor as string];
      return { ok: true };
    }
    const donor = new URL(route, 'http://x').searchParams.get('donor');
    if (donor) return { mode, conversation: table[donor] ?? null };
    return { mode, links: { ...table } };
  };
  return { engine, calls, table };
}

beforeEach(() => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-links-'));
});
afterEach(() => {
  fs.rmSync(root, { recursive: true, force: true });
});

describe('chat links: the switch', () => {
  it('reads KEL_CHAT_STORE and hands it to the engine for this run', async () => {
    expect(chatStoreOverride({ KEL_CHAT_STORE: ' Engine ' })).toBe('engine');
    expect(chatStoreOverride({ KEL_CHAT_STORE: 'both' })).toBeNull();
    const fake = fakeEngine('legacy');
    const links = await ChatLinks.open(root, fake.engine, { KEL_CHAT_STORE: 'engine' });
    expect(links.mode).toBe('engine');
    expect(fake.calls[0].body).toEqual({ action: 'mode', override: 'engine' });
    const plain = await ChatLinks.open(root, fakeEngine('legacy').engine, {});
    expect(plain.mode).toBe('legacy');
  });

  it('falls back to the legacy files when the engine has no link table', async () => {
    record('chat', 'c-record');
    const links = await ChatLinks.open(root, fakeEngine('missing').engine, { KEL_CHAT_STORE: 'engine' });
    expect(links.mode).toBe('legacy');
    expect(links.get('chat')).toBe('c-record');
  });
});

describe('chat links: legacy is the old behaviour', () => {
  it('folds C, then the session records, then the donor rows, and writes C back whole', async () => {
    writeLegacy({ a: 'c-legacy', b: 'c-legacy-b' });
    record('a', 'c-record');
    const links = await ChatLinks.open(root, fakeEngine('legacy').engine, {});
    expect(links.get('a')).toBe('c-record');
    await links.foldDonorLinks([
      { id: 'a', extra: { kel_conversation_id: 'c-extra' } },
      { id: 'z', extra: null },
    ]);
    expect(links.get('a')).toBe('c-extra');
    expect(links.donorFor('c-legacy-b')).toBe('b');
    record('late', 'c-late');
    expect(await links.lookup('late')).toBe('c-late');
    await links.refresh();
    expect(links.get('late')).toBe('c-late');
    await links.drop('b', 'gone');
    await links.adopt('new', 'c-new');
    links.persist();
    // B-9, kept as it was: a later refresh lets the session record win over the donor's link again.
    expect(readLegacy()).toEqual({ a: 'c-record', late: 'c-late', new: 'c-new' });
  });

  it('keeps every chat past the first 20', async () => {
    const donors = Array.from({ length: 45 }, (_, index) => ({
      id: 'd' + index,
      extra: { kel_conversation_id: 'c' + index },
    }));
    const links = await ChatLinks.open(root, fakeEngine('legacy').engine, {});
    await links.foldDonorLinks(donors);
    expect(links.entries()).toHaveLength(45);
  });
});

describe('chat links: the engine table', () => {
  it('reads the table, adds only adoptions to C, and never rewrites the other files', async () => {
    writeLegacy({ old: 'c-old' });
    record('a', 'c-record');
    const before = snapshot();
    const fake = fakeEngine('engine', { a: 'c-winner' });
    const links = await ChatLinks.open(root, fake.engine, {});
    expect(links.mode).toBe('engine');
    expect(links.entries()).toEqual([]);
    const donors = Array.from({ length: 30 }, (_, index) => ({
      id: 'd' + index,
      extra: { kel_conversation_id: 'c' + index },
    }));
    const folded = await links.foldDonorLinks([{ id: 'a', extra: { kel_conversation_id: 'c-extra' } }, ...donors]);
    expect(folded.conflicts).toBe(1);
    expect(fake.calls.find((call) => (call.body as { action?: string })?.action === 'import')?.body).toMatchObject({
      links: { a: 'c-extra', d29: 'c29' },
    });
    expect(links.get('a')).toBe('c-winner');
    expect(links.get('d25')).toBe('c25');
    links.persist();
    expect(snapshot()).toEqual(before, 'nothing was adopted: C is not even rewritten');

    fake.table.fresh = 'c-fresh'; // the ACP host linked a new chat
    expect(await links.lookup('fresh')).toBe('c-fresh');
    expect(donorsForMessages(links, [{ conversation_id: 'c-fresh' }])).toEqual(['fresh']);

    await links.adopt('adopted', 'c-adopted');
    await links.drop('d3', 'app chat gone');
    expect(fake.table.d3).toBeUndefined();
    links.persist();
    expect(readLegacy()).toEqual({ old: 'c-old', adopted: 'c-adopted' });
    const after = snapshot();
    delete after['aion-conversations.json'];
    const expected = { ...before };
    delete expected['aion-conversations.json'];
    expect(after).toEqual(expected);
  });

  it('a restart reads the same links back', async () => {
    const fake = fakeEngine('engine');
    const first = await ChatLinks.open(root, fake.engine, {});
    const donors = Array.from({ length: 25 }, (_, index) => ({
      id: 'd' + index,
      extra: { kel_conversation_id: 'c' + index },
    }));
    await first.foldDonorLinks(donors);
    const again = await ChatLinks.open(root, fake.engine, {});
    await again.foldDonorLinks(donors);
    expect(Object.fromEntries(again.entries())).toEqual(Object.fromEntries(first.entries()));
    expect(again.entries()).toHaveLength(25);
  });
});

describe('chat links: archived chats', () => {
  it('asks aioncore for archived chats within its page limit, so they keep their links', async () => {
    const routes: string[] = [];
    await listConversationsForRepair(async (route) => {
      routes.push(route);
      return route.startsWith('/api/conversations?') ? { items: [] } : { groups: [] };
    });
    const limit = Number(new URLSearchParams(routes[1].split('?')[1]).get('limit'));
    expect(limit).toBeGreaterThan(0);
    expect(limit).toBeLessThanOrEqual(100); // aioncore: "limit out of range [1,100]"
  });
});
