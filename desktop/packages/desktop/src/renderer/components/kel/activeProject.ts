/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * D-54: the active Kel project. The engine owns it (one value, the same on every device); this module
 * reads it with the project list, shares one copy between every view in the window, and re-reads it
 * when the window regains focus or another view changes it. '*' means "All projects".
 */

import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { kelProjects, kelState, KEL_ALL_CONVERSATIONS, type KelProject } from './kelApi';

export type { KelProject } from './kelApi';

/** "All projects": no one project is active. New chats then start in General. */
export const ALL_PROJECTS = '*';
/** General, the engine's default project. */
export const GENERAL_PROJECT_ID = 'default';
export const GENERAL_PROJECT_NAME = 'General';
export const ALL_PROJECTS_LABEL = 'All projects';

const CHANGE_EVENT = 'kel:active-project';
/** The pre-D-54 per-device choice; imported once into the engine, then removed. */
const LEGACY_KEY = 'kel.activeWorkspace_v1';

type Snapshot = { projects: KelProject[] | null; active: string; loaded: boolean };

let snapshot: Snapshot = { projects: null, active: ALL_PROJECTS, loaded: false };
let inflight: Promise<void> | null = null;
/** A read asked for while another is running; it starts when that one ends, so it sees every write. */
let followUp: Promise<void> | null = null;
/** Bumped by each local write of the active project, so an older read cannot undo it. */
let writes = 0;
const listeners = new Set<() => void>();

const emit = () => listeners.forEach((listener) => listener());

/** Archived projects keep their chats but are not offered as a place to start new ones. */
export const isLiveProject = (project: KelProject) => !project.archived && project.kind !== 'system';

/** The name a person sees for a project, marked when it is archived. */
export const projectLabel = (project: Pick<KelProject, 'name' | 'archived'>) =>
  project.archived ? `${project.name} (archived)` : project.name;

/** Live projects, General first, the rest by name. */
export const liveProjects = (projects: KelProject[] | null | undefined): KelProject[] =>
  (projects ?? [])
    .filter(isLiveProject)
    .sort((a, b) =>
      a.id === GENERAL_PROJECT_ID ? -1 : b.id === GENERAL_PROJECT_ID ? 1 : a.name.localeCompare(b.name)
    );

const readLegacyChoice = (): string | null => {
  try {
    const raw = localStorage.getItem(LEGACY_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { id?: unknown };
    return typeof parsed?.id === 'string' ? parsed.id : null;
  } catch {
    return null;
  }
};

const dropLegacyChoice = () => {
  try {
    localStorage.removeItem(LEGACY_KEY);
  } catch {
    // Storage can be unavailable; nothing else reads the old key.
  }
};

/**
 * One-time import of the old per-device workspace: only when the engine has no active project yet
 * and the stored id is still a live project the person made. The key is removed either way.
 */
const importLegacyChoice = async (projects: KelProject[], active: string): Promise<string> => {
  const legacy = readLegacyChoice();
  if (legacy === null) {
    dropLegacyChoice();
    return active;
  }
  dropLegacyChoice();
  if (active !== ALL_PROJECTS) return active;
  const project = projects.find((item) => item.id === legacy);
  if (!project || !isLiveProject(project) || (project.kind && project.kind !== 'user')) return active;
  try {
    await kelProjects.setActive(project.id);
    return project.id;
  } catch {
    return active;
  }
};

/** Read the list and the active project from the engine (one read shared by every caller). */
export const refreshProjects = (): Promise<void> => {
  if (inflight) {
    followUp ??= inflight.then(() => {
      followUp = null;
      return refreshProjects();
    });
    return followUp;
  }
  const startedAt = writes;
  inflight = (async () => {
    try {
      const listed = await kelProjects.list({ include_archived: true });
      let active = listed.active;
      if (active === undefined) {
        // Older list payloads leave the active project to /api/state.
        const state = await kelState(KEL_ALL_CONVERSATIONS).catch((): null => null);
        active = state?.active_project;
      }
      const resolved = await importLegacyChoice(listed.projects, active || ALL_PROJECTS);
      snapshot = { projects: listed.projects, active: startedAt === writes ? resolved : snapshot.active, loaded: true };
    } catch {
      snapshot = { projects: snapshot.projects ?? [], active: snapshot.active, loaded: true };
    } finally {
      inflight = null;
      emit();
    }
  })();
  return inflight;
};

const onWindowFocus = (): void => {
  void refreshProjects();
};
const onVisibility = (): void => {
  if (document.visibilityState === 'visible') void refreshProjects();
};
const onActiveChange = (): void => {
  void refreshProjects();
};

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  if (listeners.size === 1) {
    window.addEventListener('focus', onWindowFocus);
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener(CHANGE_EVENT, onActiveChange);
  }
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      window.removeEventListener('focus', onWindowFocus);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener(CHANGE_EVENT, onActiveChange);
    }
  };
};

const getSnapshot = () => snapshot;

/** Make a project (or '*') active: the engine first, then every open view hears about it. */
export const setActiveProject = async (id: string): Promise<void> => {
  await kelProjects.setActive(id);
  writes += 1;
  snapshot = { ...snapshot, active: id };
  emit();
  window.dispatchEvent(new CustomEvent<string>(CHANGE_EVENT, { detail: id }));
};

/** Tell every open view the project list changed (created, renamed, archived…). */
export const announceProjectsChanged = () => {
  window.dispatchEvent(new CustomEvent<string>(CHANGE_EVENT, { detail: snapshot.active }));
};

export type ProjectsView = {
  /** Every project the engine lists, archived included; null until the first read. */
  projects: KelProject[] | null;
  /** The active project id, or '*' for all projects. */
  active: string;
  /** The active project's row; null for "All projects" (or before the first read). */
  activeProject: KelProject | null;
  /** Where a new chat starts: the active project, or General when all projects are shown. */
  newChatProject: KelProject | null;
  loaded: boolean;
  refresh: () => Promise<void>;
};

export const useProjects = (): ProjectsView => {
  const current = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  useEffect(() => {
    if (!snapshot.loaded && !inflight) void refreshProjects();
  }, []);
  return useMemo(() => {
    const activeProject =
      current.active === ALL_PROJECTS ? null : (current.projects ?? []).find((p) => p.id === current.active) ?? null;
    const general = (current.projects ?? []).find((p) => p.id === GENERAL_PROJECT_ID) ?? null;
    return {
      projects: current.projects,
      active: current.active,
      activeProject,
      newChatProject: activeProject ?? general,
      loaded: current.loaded,
      refresh: refreshProjects,
    };
  }, [current]);
};

/** The label for the active choice: the project's name, or "All projects". */
export const activeProjectLabel = (view: Pick<ProjectsView, 'active' | 'activeProject'>) =>
  view.active === ALL_PROJECTS ? ALL_PROJECTS_LABEL : view.activeProject ? projectLabel(view.activeProject) : '';

// ---------------------------------------------------------------------------------------------
// One chat's project (header chip, composer footer). A chat Kel has not seen yet is "pending": the
// engine answers with the project its first message will land in.
// ---------------------------------------------------------------------------------------------
type ChatProjectAnswer = { id: string | null; row: Partial<KelProject> | null; pending: boolean };
const chatProjectCache = new Map<string, Promise<ChatProjectAnswer>>();

const readChatProject = (donor: string): Promise<ChatProjectAnswer> => {
  const cached = chatProjectCache.get(donor);
  if (cached) return cached;
  const request = kelProjects
    .of({ donor })
    .then((answer): ChatProjectAnswer => {
      const project = answer?.project;
      if (project && typeof project === 'object') return { id: project.id, row: project, pending: Boolean(answer.pending) };
      return { id: typeof project === 'string' ? project : null, row: null, pending: Boolean(answer?.pending) };
    })
    .catch((): ChatProjectAnswer => {
      chatProjectCache.delete(donor);
      return { id: null, row: null, pending: false };
    });
  chatProjectCache.set(donor, request);
  return request;
};

/** Forget cached chat projects (a pending chat follows the active project). */
export const forgetChatProjects = () => chatProjectCache.clear();

export type ConversationProject = {
  /** The chat's project, merged with the engine's list row when there is one. */
  project: (Partial<KelProject> & { id: string; name: string }) | null;
  pending: boolean;
  loaded: boolean;
};

export const useConversationProject = (conversationId: string | undefined | null): ConversationProject => {
  const { projects } = useProjects();
  const [answer, setAnswer] = useState<ChatProjectAnswer | null>(null);
  const load = useCallback((): (() => void) => {
    if (!conversationId) {
      setAnswer(null);
      return () => undefined;
    }
    let cancelled = false;
    void readChatProject(conversationId).then((next) => {
      if (!cancelled) setAnswer(next);
    });
    return () => {
      cancelled = true;
    };
  }, [conversationId]);
  useEffect(() => load(), [load]);
  useEffect(() => {
    if (!conversationId) return undefined;
    const onChange = () => {
      chatProjectCache.delete(conversationId);
      load();
    };
    window.addEventListener(CHANGE_EVENT, onChange);
    return () => window.removeEventListener(CHANGE_EVENT, onChange);
  }, [conversationId, load]);
  return useMemo((): ConversationProject => {
    if (!answer || !answer.id) return { project: null, pending: Boolean(answer?.pending), loaded: answer !== null };
    const listed = (projects ?? []).find((p) => p.id === answer.id);
    const name = listed?.name ?? answer.row?.name ?? (answer.id === GENERAL_PROJECT_ID ? GENERAL_PROJECT_NAME : '');
    return {
      project: { ...(answer.row ?? {}), ...(listed ?? {}), id: answer.id, name },
      pending: answer.pending,
      loaded: true,
    };
  }, [answer, projects]);
};

/**
 * A chat made from another chat (a fork, or "new chat here") stays in the source chat's project.
 * Best effort: without an answer the engine places the new chat in the active project.
 */
export const bindToSourceProject = async (sourceConversationId: string, newConversationId: string): Promise<void> => {
  try {
    const source = await readChatProject(sourceConversationId);
    if (source.id) await kelProjects.bind(newConversationId, source.id);
  } catch {
    // Non-fatal: the chat still opens.
  }
};

/** Test seam: forget everything read so far. */
export const resetProjectsForTests = () => {
  snapshot = { projects: null, active: ALL_PROJECTS, loaded: false };
  inflight = null;
  followUp = null;
  chatProjectCache.clear();
  emit();
};
