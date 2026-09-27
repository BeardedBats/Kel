/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * The active Kel workspace (an engine project: name + folder). The header switcher sets it; the
 * Home composer starts new chats in its folder. Stored per device, broadcast in-window.
 */

import { useEffect, useState } from 'react';

export type KelWorkspace = { id: string; name: string; root?: string | null };

const STORAGE_KEY = 'kel.activeWorkspace_v1';
const CHANGE_EVENT = 'kel:active-workspace';

export const readActiveWorkspace = (): KelWorkspace | null => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as KelWorkspace;
    return parsed && typeof parsed.id === 'string' && typeof parsed.name === 'string' ? parsed : null;
  } catch {
    return null;
  }
};

export const setActiveWorkspace = (workspace: KelWorkspace | null): void => {
  try {
    if (workspace) localStorage.setItem(STORAGE_KEY, JSON.stringify(workspace));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage can be unavailable; the in-window event still updates open views.
  }
  window.dispatchEvent(new CustomEvent<KelWorkspace | null>(CHANGE_EVENT, { detail: workspace }));
};

export const useActiveWorkspace = (): KelWorkspace | null => {
  const [workspace, setWorkspace] = useState<KelWorkspace | null>(() => readActiveWorkspace());
  useEffect(() => {
    const onChange = (event: Event) => setWorkspace((event as CustomEvent<KelWorkspace | null>).detail);
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setWorkspace(readActiveWorkspace());
    };
    window.addEventListener(CHANGE_EVENT, onChange);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(CHANGE_EVENT, onChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);
  return workspace;
};
