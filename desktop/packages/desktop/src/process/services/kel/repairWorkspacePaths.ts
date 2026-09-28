/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * Chats keep the folder they run in (`extra.workspace`). Kel-created scratch folders live under the
 * engine root (`<engine>/aion-workspaces/<id>`); a data root that moved (the 2026-09-24
 * consolidation left 22 chats pointing at the removed `KelV2Runs` root) or a deleted scratch folder
 * makes the chat fail with "failed to run in this workspace path". This repair re-homes Kel-created
 * scratch folders under the current engine root. Folders the person chose themselves are never
 * moved or recreated — those need the person to pick a folder again.
 */

import * as fs from 'fs';
import * as path from 'path';

export type WorkspaceDonorConversation = {
  id: string;
  extra?: {
    workspace?: unknown;
    custom_workspace?: unknown;
    is_temporary_workspace?: unknown;
    kel_conversation_id?: unknown;
  } | null;
};

export type WorkspaceRepair = { id: string; from: string; to: string };

/** Kel-owned scratch folder names: `aion-workspaces/<id>` or an `*-temp-<id>` folder. */
const isKelScratchFolder = (workspace: string): boolean => {
  const parts = workspace.split(/[\\/]+/).filter(Boolean);
  const name = parts[parts.length - 1] ?? '';
  const parent = parts[parts.length - 2] ?? '';
  return parent.toLowerCase() === 'aion-workspaces' || /-temp-[0-9a-z]+$/i.test(name);
};

/** The repairs needed for `conversations` (pure: no disk writes). */
export const planWorkspaceRepairs = (
  conversations: WorkspaceDonorConversation[],
  engineRoot: string,
  exists: (target: string) => boolean = fs.existsSync
): WorkspaceRepair[] => {
  const repairs: WorkspaceRepair[] = [];
  for (const conversation of conversations) {
    const workspace = conversation.extra?.workspace;
    if (typeof workspace !== 'string' || !workspace.trim()) continue;
    if (conversation.extra?.custom_workspace === true) continue;
    if (!isKelScratchFolder(workspace)) continue;
    if (exists(workspace)) continue;
    const name = workspace.split(/[\\/]+/).filter(Boolean).pop() as string;
    // A missing folder already under the current root is simply recreated in place.
    repairs.push({ id: conversation.id, from: workspace, to: path.join(engineRoot, 'aion-workspaces', name) });
  }
  return repairs;
};

/** Creates each target folder and points the chat at it. Returns the repairs that were applied. */
export const applyWorkspaceRepairs = async (
  repairs: WorkspaceRepair[],
  update: (id: string, workspace: string) => Promise<unknown>
): Promise<WorkspaceRepair[]> => {
  const applied: WorkspaceRepair[] = [];
  for (const repair of repairs) {
    try {
      fs.mkdirSync(repair.to, { recursive: true });
      await update(repair.id, repair.to);
      applied.push(repair);
    } catch (error) {
      console.warn('[Kel] Could not re-home a chat folder', repair.id, error);
    }
  }
  return applied;
};

type ConversationPage = { items?: WorkspaceDonorConversation[]; has_more?: boolean } | null | undefined;
type SidebarGroupPage = {
  scope?: { type?: string; project_id?: string; key?: string };
  items?: Array<{ type?: string; conversation?: WorkspaceDonorConversation }>;
  has_more?: boolean;
  next_cursor?: string;
};

const sidebarScopeToken = (scope: SidebarGroupPage['scope']): string | null => {
  if (!scope?.type) return null;
  if (scope.type === 'project' && scope.project_id) return `project:${scope.project_id}`;
  if (scope.type === 'dir' && scope.key) return `dir:${scope.key}`;
  if (scope.type === 'chats' || scope.type === 'pinned') return scope.type;
  return null;
};

const conversationsOf = (items: SidebarGroupPage['items']): WorkspaceDonorConversation[] =>
  (items ?? []).flatMap((item) => (item?.type === 'conversation' && item.conversation?.id ? [item.conversation] : []));

/**
 * Every donor conversation the repair should look at: all active chats (the donor's
 * `page_size` is ignored and caps a page at 20, so `limit` asks for all of them) and the
 * ARCHIVED ones too, read through the archived sidebar and paged per group — an archived chat
 * that points at a removed root is just as broken once it is restored. Read failures are
 * tolerated: whatever could be read is still repaired.
 */
export const listConversationsForRepair = async (
  get: (route: string) => Promise<unknown>,
  // aioncore's sidebar refuses a limit above 100 ("limit out of range [1,100]"); 200 lost every
  // archived chat, and with it their chat links.
  pageLimit = 100
): Promise<WorkspaceDonorConversation[]> => {
  const byId = new Map<string, WorkspaceDonorConversation>();
  const add = (items: WorkspaceDonorConversation[]) => {
    for (const item of items) if (item?.id && !byId.has(item.id)) byId.set(item.id, item);
  };
  try {
    const active = (await get('/api/conversations?limit=10000')) as ConversationPage;
    add(active?.items ?? []);
  } catch (error) {
    console.warn('[Kel] Could not list chats for the folder repair', error);
  }
  try {
    const archived = (await get(`/api/sidebar?archived=true&limit=${pageLimit}`)) as { groups?: SidebarGroupPage[] } | null;
    for (const group of archived?.groups ?? []) {
      add(conversationsOf(group.items));
      const token = sidebarScopeToken(group.scope);
      let cursor = group.next_cursor;
      let more = Boolean(group.has_more && cursor && token);
      // A bounded walk: never more than 50 extra pages per group, whatever the backend says.
      for (let page = 0; more && page < 50; page += 1) {
        const params = new URLSearchParams({ scope: token as string, cursor: cursor as string, limit: String(pageLimit), archived: 'true' });
        const next = (await get(`/api/sidebar/items?${params.toString()}`)) as SidebarGroupPage | null;
        add(conversationsOf(next?.items));
        cursor = next?.next_cursor;
        more = Boolean(next?.has_more && cursor);
      }
    }
  } catch (error) {
    console.warn('[Kel] Could not list archived chats for the folder repair', error);
  }
  return [...byId.values()];
};
