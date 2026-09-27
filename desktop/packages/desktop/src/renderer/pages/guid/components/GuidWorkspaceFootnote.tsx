/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { ipcBridge } from '@/common';
import { Tooltip } from '@arco-design/web-react';
import { Down } from '@icon-park/react';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import styles from '../index.module.css';
import { KelDesktopProjectMenu } from '@renderer/components/kel/KelDesktopProjectMenu';
import { kelProjects } from '@renderer/components/kel/kelApi';
import {
  GENERAL_PROJECT_ID,
  GENERAL_PROJECT_NAME,
  announceProjectsChanged,
  liveProjects,
  setActiveProject,
  useProjects,
} from '@renderer/components/kel/activeProject';

const FolderIcon = ({ size = 12 }: { size?: number }) => (
  <svg
    width={size}
    height={size}
    fill='none'
    stroke='currentColor'
    strokeWidth='1.8'
    viewBox='0 0 24 24'
    style={{ lineHeight: 0, flexShrink: 0 }}
  >
    <path d='M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z' />
  </svg>
);

/**
 * D-54: the composer's project line is a second view of the header switcher. It names the project
 * a new chat starts in (the active project, or General when all projects are shown); choosing a row
 * or a folder makes that project active.
 */
const GuidWorkspaceFootnote: React.FC = () => {
  const view = useProjects();
  const target = view.newChatProject;
  const name = target?.name ?? GENERAL_PROJECT_NAME;
  const root = target?.root ?? '';
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({});
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const resize = () => setOpen(false);
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  const choose = useCallback(async (id: string) => {
    setOpen(false);
    setError('');
    try {
      await setActiveProject(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kel could not switch projects.');
    }
  }, []);

  const handleBrowse = useCallback(() => {
    setOpen(false);
    setError('');
    ipcBridge.dialog.showOpen
      .invoke({ properties: ['openDirectory', 'createDirectory'] })
      .then(async (dirs) => {
        if (!dirs || !dirs[0]) return;
        const project = await kelProjects.forFolder(dirs[0]);
        announceProjectsChanged();
        await setActiveProject(project.id);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Kel could not use that folder.');
      });
  }, []);

  const openDropdown = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const desktop = window.innerWidth >= 768;
    // Above the trigger, aligned to its left edge.
    setDropdownStyle({
      position: 'fixed',
      left: desktop ? Math.max(20, Math.min(rect.left, window.innerWidth - 340)) : rect.left,
      bottom: window.innerHeight - rect.top + 6,
      minWidth: desktop ? 320 : 230,
      maxHeight: Math.max(120, rect.top - 26),
      overflowY: 'auto',
      zIndex: desktop ? 440 : 9999,
    });
    setOpen(true);
    void view.refresh();
  }, [view.refresh]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const node = e.target as Node;
      if (triggerRef.current && !triggerRef.current.contains(node) && dropdownRef.current && !dropdownRef.current.contains(node)) {
        setOpen(false);
      }
    };
    const keyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyDown);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', keyDown);
    };
  }, [open]);

  const dropdownEl = open
    ? createPortal(
        <div ref={dropdownRef} className='kel-desktop-project-popover' style={dropdownStyle}>
          <KelDesktopProjectMenu
            projects={liveProjects(view.projects).map(({ id, name: projectName, root: projectRoot }) => ({
              id,
              name: projectName,
              root: projectRoot ?? null,
            }))}
            selected={target?.id ?? GENERAL_PROJECT_ID}
            onSelect={(project) => void choose(project.id)}
            onBrowse={handleBrowse}
          />
        </div>,
        document.body
      )
    : null;

  const trigger = (
    <button
      ref={triggerRef}
      type='button'
      className={root ? styles.workspacePillMain : styles.workspaceEmptyBtn}
      data-testid='workspace-selector-btn'
      aria-haspopup='dialog'
      aria-expanded={open}
      onClick={() => (open ? setOpen(false) : openDropdown())}
    >
      <FolderIcon size={14} />
      <span className={root ? styles.workspacePillName : undefined}>{name}</span>
      <Down theme='outline' size='12' fill='currentColor' style={{ flexShrink: 0, transform: 'translateY(1px)' }} />
    </button>
  );

  return (
    <div className={styles.workspaceFootnote} data-testid='kel-composer-project'>
      {root ? (
        <Tooltip content={root} position='top'>
          <div className={styles.workspacePill}>{trigger}</div>
        </Tooltip>
      ) : (
        trigger
      )}
      {dropdownEl}
      {error && (
        <span className='kel-meta' role='alert'>
          {error}
        </span>
      )}
    </div>
  );
};

export default GuidWorkspaceFootnote;
