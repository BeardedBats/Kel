import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { ipcBridge } from '@/common';
import workspaceIcon from '@renderer/assets/figma/chat-shell/workspace.svg';
import chevronIcon from '@renderer/assets/figma/chat-shell/workspace-chevron.svg';
import check from '@renderer/assets/figma/chat-pickers/project-check.svg';
import folder from '@renderer/assets/figma/chat-pickers/project-folder.svg';
import plus from '@renderer/assets/figma/chat-pickers/project-plus.svg';
import { kelProjects } from './kelApi';
import {
  ALL_PROJECTS,
  ALL_PROJECTS_LABEL,
  GENERAL_PROJECT_NAME,
  activeProjectLabel,
  announceProjectsChanged,
  liveProjects,
  projectLabel,
  setActiveProject,
  useConversationProject,
  useProjects,
} from './activeProject';

const folderName = (path: string) => path.split(/[\\/]/).filter(Boolean).pop() || path;

/**
 * Header project switcher (Figma page header, D-54). Lists the engine's live projects and "All
 * projects", marks the one in use, and offers "New project" and "Manage projects". The choice is
 * the engine's active project — the same on every device — and new chats start in it.
 *
 * Inside a chat (`conversationId`) the chip shows that chat's own project. Choosing another project
 * makes it active for new chats and opens a new chat there; the open chat stays where it is.
 */
export default function ShellWorkspaceLink({ conversationId }: { conversationId?: string }) {
  const navigate = useNavigate();
  const view = useProjects();
  const chat = useConversationProject(conversationId);
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [menuStyle, setMenuStyle] = useState<React.CSSProperties>({});
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const inChat = Boolean(conversationId);
  const selected = inChat ? chat.project?.id ?? null : view.active;
  // A chat whose project Kel cannot name yet still reads as a project, never as a folder.
  const label = inChat
    ? chat.project?.name
      ? projectLabel(chat.project)
      : 'Project'
    : activeProjectLabel(view) || (view.loaded ? ALL_PROJECTS_LABEL : 'Projects');
  const title = inChat ? chat.project?.root ?? undefined : view.activeProject?.root ?? undefined;

  const toggle = () => {
    if (open) {
      setOpen(false);
      return;
    }
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) setMenuStyle({ position: 'fixed', top: rect.bottom + 6, left: rect.left, zIndex: 1000 });
    setCreating(false);
    setError('');
    setOpen(true);
    void view.refresh();
  };

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!menuRef.current?.contains(target) && !triggerRef.current?.contains(target)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const choose = async (id: string, name: string) => {
    setError('');
    try {
      await setActiveProject(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kel could not switch projects.');
      return;
    }
    setOpen(false);
    if (inChat && chat.project && id !== chat.project.id) {
      const startsIn = id === ALL_PROJECTS ? GENERAL_PROJECT_NAME : name;
      void navigate('/guid', {
        state: { projectNote: `New chats start in ${startsIn}. This chat stays in ${chat.project.name || 'its project'}.` },
      });
    }
  };

  const rows = liveProjects(view.projects);

  const menu = open
    ? createPortal(
        <div
          ref={menuRef}
          className='kel-desktop-picker kel-workspace-menu'
          style={menuStyle}
          role='dialog'
          aria-label='Projects'
          data-testid='kel-workspace-menu'
        >
          {creating ? (
            <NewProjectForm
              onCancel={() => setCreating(false)}
              onCreated={(project) => {
                announceProjectsChanged();
                void choose(project.id, project.name);
              }}
            />
          ) : (
            <>
              <p className='kel-workspace-menu__label'>Projects</p>
              {!view.loaded && <p className='kel-workspace-menu__empty'>Loading…</p>}
              <button
                type='button'
                className='kel-desktop-picker__row'
                aria-pressed={!inChat && view.active === ALL_PROJECTS}
                onClick={() => void choose(ALL_PROJECTS, ALL_PROJECTS_LABEL)}
              >
                <img src={folder} alt='' />
                <span>{ALL_PROJECTS_LABEL}</span>
                {!inChat && view.active === ALL_PROJECTS && <img src={check} alt='' />}
              </button>
              {rows.map((project) => (
                <button
                  type='button'
                  key={project.id}
                  className='kel-desktop-picker__row'
                  aria-pressed={selected === project.id}
                  title={project.root ?? undefined}
                  onClick={() => void choose(project.id, project.name)}
                >
                  <img src={folder} alt='' />
                  <span>{project.name}</span>
                  {selected === project.id && <img src={check} alt='' />}
                </button>
              ))}
              {error && (
                <p className='kel-workspace-form__error' role='alert'>
                  {error}
                </p>
              )}
              <div className='kel-desktop-picker__divider' />
              <button type='button' className='kel-desktop-picker__row' onClick={() => setCreating(true)}>
                <img src={plus} alt='' />
                <span>New project</span>
              </button>
              <button
                type='button'
                className='kel-desktop-picker__row kel-workspace-menu__quiet'
                onClick={() => {
                  setOpen(false);
                  void navigate('/projects/list');
                }}
              >
                <span>Manage projects</span>
              </button>
            </>
          )}
        </div>,
        document.body
      )
    : null;

  return (
    <>
      <button
        ref={triggerRef}
        type='button'
        className='kel-shell-workspace-link'
        aria-haspopup='dialog'
        aria-expanded={open}
        onClick={toggle}
        title={title}
        data-testid='kel-project-chip'
      >
        <img src={workspaceIcon} alt='' />
        <span>{label}</span>
        <img src={chevronIcon} alt='' />
      </button>
      {menu}
    </>
  );
}

/** Name + optional folder. A project without a folder is fine until Kel needs to change code. */
export const NewProjectForm: React.FC<{
  onCancel: () => void;
  onCreated: (project: { id: string; name: string; root: string | null }) => void;
}> = ({ onCancel, onCreated }) => {
  const [name, setName] = useState('');
  const [root, setRoot] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const browse = async () => {
    try {
      const dirs = await ipcBridge.dialog.showOpen.invoke({ properties: ['openDirectory', 'createDirectory'] });
      if (dirs && dirs[0]) {
        setRoot(dirs[0]);
        if (!name.trim()) setName(folderName(dirs[0]));
      }
    } catch {
      setError('Kel could not open the folder picker.');
    }
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError('Give the project a name.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const { id } = await kelProjects.create({ name: trimmed, root: root || undefined });
      onCreated({ id, name: trimmed, root: root || null });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kel could not create that project.');
      setBusy(false);
    }
  };

  return (
    <form className='kel-workspace-form' onSubmit={(event) => void submit(event)}>
      <p className='kel-workspace-menu__label'>New project</p>
      <label className='kel-workspace-form__field'>
        <span>Name</span>
        <input autoFocus value={name} maxLength={120} placeholder='e.g. Website Redesign' onChange={(e) => setName(e.target.value)} />
      </label>
      <div className='kel-workspace-form__field'>
        <span>Folder</span>
        <button type='button' className='kel-workspace-form__folder' onClick={() => void browse()} title={root || undefined}>
          <img src={folder} alt='' />
          <span>{root ? folderName(root) : 'Choose a folder (optional)'}</span>
        </button>
      </div>
      {error && <p className='kel-workspace-form__error' role='alert'>{error}</p>}
      <div className='kel-workspace-form__actions'>
        <button type='button' className='kel-btn kel-btn--quiet' onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type='submit' className='kel-btn kel-btn--primary' disabled={busy || !name.trim()}>
          {busy ? 'Creating…' : 'Create'}
        </button>
      </div>
    </form>
  );
};
