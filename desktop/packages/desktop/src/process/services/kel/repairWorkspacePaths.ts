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
  extra?: { workspace?: unknown; custom_workspace?: unknown; is_temporary_workspace?: unknown } | null;
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
