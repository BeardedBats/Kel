import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { ipcBridge } from '@/common';
import workspaceIcon from '@renderer/assets/figma/chat-shell/workspace.svg';
import chevronIcon from '@renderer/assets/figma/chat-shell/workspace-chevron.svg';
import check from '@renderer/assets/figma/chat-pickers/project-check.svg';
import folder from '@renderer/assets/figma/chat-pickers/project-folder.svg';
import plus from '@renderer/assets/figma/chat-pickers/project-plus.svg';
import { kelRequest, kelState } from './kelApi';
import { setActiveWorkspace, useActiveWorkspace, type KelWorkspace } from './activeWorkspace';

type EngineProject = { id: string; name: string; root?: string | null };

/**
 * The engine also records a project for every chat's auto-created scratch folder, the OS temp dir and
 * Kel's own data tree. Those are plumbing, not workspaces a person made, so the switcher hides them.
 */
const isUserWorkspace = (project: EngineProject) => {
  if (project.id === 'default') return false;
  if (/-temp-[0-9a-z]+$/i.test(project.name)) return false;
  const root = project.root ?? '';
  if (/[\\/]AppData[\\/]Local[\\/]Temp$/i.test(root) || /^\/tmp$/.test(root)) return false;
  if (/[\\/]conversations[\\/]users[\\/]/i.test(root)) return false;
  if (/[\\/]Data[\\/](engine|store|host)([\\/]|$)/i.test(root)) return false;
  return true;
};

const folderName = (path: string) => path.split(/[\\/]/).filter(Boolean).pop() || path;

/**
 * Header "Workspace ⌄" switcher (Figma page header). Lists the engine's projects, marks the active
 * one, and offers "New workspace" (name + folder). The active workspace's folder is where new chats
 * start from Home.
 */
export default function ShellWorkspaceLink() {
  const navigate = useNavigate();
  const active = useActiveWorkspace();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [projects, setProjects] = useState<EngineProject[] | null>(null);
  const [menuStyle, setMenuStyle] = useState<React.CSSProperties>({});
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      const state = await kelState();
      setProjects(((state.projects ?? []) as EngineProject[]).filter(isUserWorkspace));
    } catch {
      setProjects([]);
    }
  }, []);

  const toggle = () => {
    if (open) {
      setOpen(false);
      return;
    }
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) setMenuStyle({ position: 'fixed', top: rect.bottom + 6, left: rect.left, zIndex: 1000 });
    setCreating(false);
    setOpen(true);
    void load();
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

  // Keep the stored name/folder in step with the engine (renamed or removed workspaces).
  useEffect(() => {
    if (!projects || !active) return;
    const current = projects.find((p) => p.id === active.id);
    if (!current) setActiveWorkspace(null);
    else if (current.name !== active.name || (current.root ?? null) !== (active.root ?? null))
      setActiveWorkspace({ id: current.id, name: current.name, root: current.root ?? null });
  }, [projects, active]);

  const choose = (workspace: KelWorkspace | null) => {
    setActiveWorkspace(workspace);
    setOpen(false);
  };

  const menu = open
    ? createPortal(
        <div
          ref={menuRef}
          className='kel-desktop-picker kel-workspace-menu'
          style={menuStyle}
          role='dialog'
          aria-label='Workspaces'
          data-testid='kel-workspace-menu'
        >
          {creating ? (
            <NewWorkspaceForm
              onCancel={() => setCreating(false)}
              onCreated={(workspace) => {
                choose(workspace);
                void load();
              }}
            />
          ) : (
            <>
              <p className='kel-workspace-menu__label'>Workspaces</p>
              {projects === null && <p className='kel-workspace-menu__empty'>Loading…</p>}
              {projects?.length === 0 && <p className='kel-workspace-menu__empty'>No workspaces yet.</p>}
              {projects?.map((project) => (
                <button
                  type='button'
                  key={project.id}
                  className='kel-desktop-picker__row'
                  aria-pressed={active?.id === project.id}
                  title={project.root ?? undefined}
                  onClick={() => choose({ id: project.id, name: project.name, root: project.root ?? null })}
                >
                  <img src={folder} alt='' />
                  <span>{project.name}</span>
                  {active?.id === project.id && <img src={check} alt='' />}
                </button>
              ))}
              {active && (
                <button type='button' className='kel-desktop-picker__row kel-workspace-menu__quiet' onClick={() => choose(null)}>
                  <span>No workspace</span>
                </button>
              )}
              <div className='kel-desktop-picker__divider' />
              <button type='button' className='kel-desktop-picker__row' onClick={() => setCreating(true)}>
                <img src={plus} alt='' />
                <span>New workspace</span>
              </button>
              <button
                type='button'
                className='kel-desktop-picker__row kel-workspace-menu__quiet'
                onClick={() => {
                  setOpen(false);
                  navigate('/projects');
                }}
              >
                <span>Open Projects</span>
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
        title={active?.root ?? undefined}
      >
        <img src={workspaceIcon} alt='' />
        <span>{active?.name ?? 'Workspace'}</span>
        <img src={chevronIcon} alt='' />
      </button>
      {menu}
    </>
  );
}

const NewWorkspaceForm: React.FC<{ onCancel: () => void; onCreated: (workspace: KelWorkspace) => void }> = ({
  onCancel,
  onCreated,
}) => {
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
      setError('Give the workspace a name.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const { id } = await kelRequest<{ id: string }>('/api/project', { name: trimmed, root: root || undefined });
      onCreated({ id, name: trimmed, root: root || null });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kel could not create that workspace.');
      setBusy(false);
    }
  };

  return (
    <form className='kel-workspace-form' onSubmit={(event) => void submit(event)}>
      <p className='kel-workspace-menu__label'>New workspace</p>
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
