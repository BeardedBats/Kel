/**
 * CP-10a stage 1 (D-77): the one place the main process asks which Kel conversation an app chat
 * belongs to.
 *
 * `legacy` is exactly the old behaviour: `aion-conversations.json` (C), then every
 * `aion-session-map` record (D), then the donor rows' `extra.kel_conversation_id` (E) on top, kept in
 * memory and written back to C.
 *
 * `engine` reads the engine's `chat_links` table (`/api/chat-link`), which folds D, C and E once and
 * settles a chat whose links disagree by one rule (the side whose conversation has messages wins).
 * C is only ever added to (a chat adopted here), never rewritten or pruned, so switching back to
 * `legacy` finds the files as they were.
 *
 * The switch is the engine setting `chat_store`; `KEL_CHAT_STORE` overrides it for this run and is
 * handed to the engine, so the ACP host (which asks the engine) answers the same way.
 */
import fs from 'fs';
import path from 'path';

export type ChatStoreMode = 'legacy' | 'engine';
export type EngineCall = (route: string, body?: unknown) => Promise<unknown>;
export type DonorRow = { id: string; extra?: { kel_conversation_id?: unknown } | null };

const MODES: ChatStoreMode[] = ['legacy', 'engine'];

export function chatStoreOverride(env: NodeJS.ProcessEnv = process.env): ChatStoreMode | null {
  const value = String(env.KEL_CHAT_STORE || '')
    .trim()
    .toLowerCase();
  return (MODES as string[]).includes(value) ? (value as ChatStoreMode) : null;
}

function readJson(file: string): Record<string, string> {
  if (!fs.existsSync(file)) return {};
  const value = JSON.parse(fs.readFileSync(file, 'utf8').replace(/^﻿/, ''));
  return value && typeof value === 'object' ? (value as Record<string, string>) : {};
}

function linksOf(value: unknown): Record<string, string> {
  const links = (value as { links?: unknown } | null)?.links;
  const out: Record<string, string> = {};
  if (links && typeof links === 'object')
    for (const [donor, cid] of Object.entries(links as Record<string, unknown>))
      if (typeof cid === 'string' && cid) out[donor] = cid;
  return out;
}

export class ChatLinks {
  /** donor id -> engine conversation id: the snapshot every reader in the main process uses. */
  readonly map: Record<string, string> = {};
  private readonly mapPath: string;
  private readonly liveMapDir: string;
  /** C as read at start-up, plus chats adopted since (engine mode only ever adds to it). */
  private readonly fileMap: Record<string, string>;
  private fileMapChanged = false;

  private constructor(
    readonly root: string,
    readonly mode: ChatStoreMode,
    private readonly engine: EngineCall
  ) {
    this.mapPath = path.join(root, 'aion-conversations.json');
    this.liveMapDir = path.join(root, 'aion-session-map');
    this.fileMap = readJson(this.mapPath);
    if (mode === 'legacy') {
      Object.assign(this.map, this.fileMap);
      this.mergeSessionRecords();
    }
  }

  /**
   * The switch for this run: `KEL_CHAT_STORE` (handed to the engine for this engine process), else
   * the engine's `chat_store` setting. An engine without the link table means legacy.
   */
  static async open(root: string, engine: EngineCall, env: NodeJS.ProcessEnv = process.env): Promise<ChatLinks> {
    let mode: ChatStoreMode = 'legacy';
    try {
      const answer = (await engine('/api/chat-link', { action: 'mode', override: chatStoreOverride(env) })) as {
        mode?: unknown;
      };
      if (answer?.mode === 'engine') mode = 'engine';
    } catch {
      if (chatStoreOverride(env) === 'engine')
        console.warn('[Kel] This engine has no chat link table; using the legacy chat links.');
    }
    return new ChatLinks(root, mode, engine);
  }

  /** Legacy only: fold every session record (D) over the map (a record wins over C). */
  private mergeSessionRecords(): void {
    if (!fs.existsSync(this.liveMapDir)) return;
    for (const file of fs.readdirSync(this.liveMapDir).filter((name) => name.endsWith('.json')))
      Object.assign(this.map, readJson(path.join(this.liveMapDir, file)));
  }

  private replace(links: Record<string, string>): void {
    for (const key of Object.keys(this.map)) if (!(key in links)) delete this.map[key];
    Object.assign(this.map, links);
  }

  /**
   * Start-up: the donor rows' own links (E), read from the full paged list so chats past the first
   * 20 keep their link. Legacy: E wins. Engine: the engine folds D, C and E and settles conflicts.
   */
  async foldDonorLinks(donors: DonorRow[]): Promise<{ conflicts: number }> {
    const extra: Record<string, string> = {};
    for (const donor of donors) {
      const cid = donor.extra?.kel_conversation_id;
      if (typeof cid === 'string' && cid) extra[donor.id] = cid;
    }
    if (this.mode === 'legacy') {
      Object.assign(this.map, extra);
      return { conflicts: 0 };
    }
    const result = (await this.engine('/api/chat-link', { action: 'import', links: extra })) as {
      conflicts?: unknown[];
    };
    this.replace(linksOf(result));
    return { conflicts: Array.isArray(result?.conflicts) ? result.conflicts.length : 0 };
  }

  get(donorId: string): string | undefined {
    return this.map[donorId];
  }

  donorFor(cid: string): string | undefined {
    return Object.keys(this.map).find((donorId) => this.map[donorId] === cid);
  }

  entries(): Array<[string, string]> {
    return Object.entries(this.map);
  }

  /** Pick up links made since (the ACP host's new chats). */
  async refresh(): Promise<void> {
    if (this.mode === 'legacy') {
      this.mergeSessionRecords();
      return;
    }
    this.replace(linksOf(await this.engine('/api/chat-link')));
  }

  /** `kel:conversation`: the conversation one app chat links to, or null. */
  async lookup(donorId: string): Promise<string | null> {
    if (this.map[donorId]) return this.map[donorId];
    if (this.mode === 'legacy') {
      if (fs.existsSync(this.liveMapDir))
        for (const file of fs.readdirSync(this.liveMapDir).filter((name) => name.endsWith('.json'))) {
          const live = readJson(path.join(this.liveMapDir, file));
          if (live[donorId]) return live[donorId];
        }
      return null;
    }
    const answer = (await this.engine('/api/chat-link?donor=' + encodeURIComponent(donorId))) as {
      conversation?: unknown;
    };
    if (typeof answer?.conversation !== 'string' || !answer.conversation) return null;
    this.map[donorId] = answer.conversation;
    return answer.conversation;
  }

  /** A new app chat made here for an engine conversation (adoption). */
  async adopt(donorId: string, cid: string): Promise<string> {
    if (this.mode === 'engine') {
      const answer = (await this.engine('/api/chat-link', {
        action: 'link',
        donor: donorId,
        conversation: cid,
        source: 'adopt',
      })) as { conversation?: unknown };
      this.map[donorId] = typeof answer?.conversation === 'string' ? answer.conversation : cid;
      this.fileMap[donorId] = cid; // kept for a switch back to legacy
      this.fileMapChanged = true;
    } else {
      this.map[donorId] = cid;
    }
    return this.map[donorId];
  }

  /** The app chat is gone. Legacy drops the pair from C; engine retires the link (the row is kept). */
  async drop(donorId: string, reason: string): Promise<void> {
    if (this.mode === 'engine') await this.engine('/api/chat-link', { action: 'retire', donor: donorId, reason });
    delete this.map[donorId];
  }

  /** Write C: legacy writes the whole map (as before); engine writes only what C had plus adoptions. */
  persist(): void {
    if (this.mode === 'engine' && !this.fileMapChanged) return;
    const value = this.mode === 'legacy' ? this.map : this.fileMap;
    fs.writeFileSync(this.mapPath + '.tmp', JSON.stringify(value));
    fs.renameSync(this.mapPath + '.tmp', this.mapPath);
  }
}
