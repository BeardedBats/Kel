/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * D-54 "All projects" (`/projects/list`): every project the person has, what it holds, and the few
 * things that change one — its name, folder and test command — plus archive and restore. The engine
 * owns all of it; this page only asks. Deep link: `?edit=<id>&focus=folder|test`.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ipcBridge } from '@/common';
import ShellWorkspaceLink, { NewProjectForm } from '@renderer/components/kel/ShellWorkspaceLink';
import { KelButton, KelCard, KelEmpty, KelLoading } from '@renderer/components/kel/KelPrimitives';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { kelProjects, type KelProject } from '@renderer/components/kel/kelApi';
import {
  GENERAL_PROJECT_ID,
  announceProjectsChanged,
  refreshProjects,
  setActiveProject,
  useProjects,
} from '@renderer/components/kel/activeProject';

const folderName = (path: string) => path.split(/[\\/]/).filter(Boolean).pop() || path;
const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`;
/** A project that still holds chats or work cannot be deleted, only archived. */
const holdsSomething = (project: KelProject) => (project.conversations ?? 0) > 0 || (project.open_work ?? 0) > 0;

type Focus = 'folder' | 'test' | null;

export default function KelProjectsList() {
  const navigate = useNavigate();
  const { search } = useLocation();
  const params = useMemo(() => new URLSearchParams(search), [search]);
  const editId = params.get('edit');
  const focus = (['folder', 'test'].includes(params.get('focus') ?? '') ? params.get('focus') : null) as Focus;
  const view = useProjects();
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<{ text: string; alert?: boolean } | null>(null);
  const [renaming, setRenaming] = useState<{ id: string; name: string } | null>(null);
  const [testing, setTesting] = useState<{ id: string; argv: string[] } | null>(null);
  const [archiving, setArchiving] = useState<string | null>(null);

  useEffect(() => {
    void refreshProjects();
  }, []);

  const projects = useMemo(() => (view.projects ?? []).filter((project) => project.kind !== 'system'), [view.projects]);
  const live = projects
    .filter((project) => !project.archived)
    .sort((a, b) => (a.id === GENERAL_PROJECT_ID ? -1 : b.id === GENERAL_PROJECT_ID ? 1 : a.name.localeCompare(b.name)));
  const archived = projects.filter((project) => project.archived);

  // A deep link opens the named project's editor (the test command) or points at its folder button.
  const openedFor = useRef<string | null>(null);
  useEffect(() => {
    if (!editId || !view.loaded || openedFor.current === `${editId}:${focus}`) return;
    const project = projects.find((item) => item.id === editId);
    if (!project) return;
    openedFor.current = `${editId}:${focus}`;
    if (focus === 'test') setTesting({ id: project.id, argv: project.test_command?.length ? [...project.test_command] : [''] });
    document.getElementById(`kel-project-${project.id}`)?.scrollIntoView?.({ block: 'center' });
  }, [editId, focus, projects, view.loaded]);

  const act = useCallback(async (label: string, fn: () => Promise<unknown>, done?: string) => {
    setBusy(label);
    setNote(null);
    try {
      await fn();
      await refreshProjects();
      announceProjectsChanged();
      if (done) setNote({ text: done });
      return true;
    } catch (err) {
      setNote({ text: `${label} didn't work. ${failureSentence(err, 'Kel did not answer — try again.')}`, alert: true });
      return false;
    } finally {
      setBusy(null);
    }
  }, []);

  const open = async (project: KelProject) => {
    if (await act('Open', () => setActiveProject(project.id))) void navigate('/projects/knowledge');
  };

  const chooseFolder = async (project: KelProject) => {
    let folder: string | undefined;
    try {
      folder = (await ipcBridge.dialog.showOpen.invoke({ properties: ['openDirectory', 'createDirectory'] }))?.[0];
    } catch {
      setNote({ text: 'The folder picker could not open. Try again.', alert: true });
      return;
    }
    if (!folder) return;
    await act(
      'Set folder',
      () => kelProjects.update(project.id, { root: folder }),
      project.root
        ? `${project.name} now uses ${folderName(folder)}. Kel will ask again before it changes files there.`
        : `${project.name} now uses ${folderName(folder)}.`
    );
  };

  const saveName = async () => {
    if (!renaming) return;
    const name = renaming.name.trim();
    if (!name) {
      setNote({ text: 'Give the project a name.', alert: true });
      return;
    }
    if (await act('Rename', () => kelProjects.update(renaming.id, { name }), `Renamed to ${name}.`)) setRenaming(null);
  };

  const saveTest = async (clear = false) => {
    if (!testing) return;
    const argv = testing.argv.map((arg) => arg.trim()).filter(Boolean);
    if (!clear && argv.length === 0) {
      setNote({ text: 'Add the command, one part per box — for example "npm", "test".', alert: true });
      return;
    }
    const ok = await act(
      clear ? 'Remove test command' : 'Save test command',
      () => kelProjects.update(testing.id, { test_command: clear ? null : argv }),
      clear ? 'Test command removed.' : 'Test command saved.'
    );
    if (ok) setTesting(null);
  };

  const row = (project: KelProject) => {
    const isGeneral = project.id === GENERAL_PROJECT_ID;
    const isActive = view.active === project.id;
    const editingName = renaming?.id === project.id;
    const editingTest = testing?.id === project.id;
    return (
      <div
        className='kel-project-list-row'
        id={`kel-project-${project.id}`}
        key={project.id}
        data-testid={`kel-project-row-${project.id}`}
        data-editing={editId === project.id || undefined}
      >
        <div className='kel-row'>
          {editingName ? (
            <form
              className='kel-row'
              onSubmit={(event) => {
                event.preventDefault();
                void saveName();
              }}
            >
              <input
                className='kel-input'
                aria-label='Project name'
                autoFocus
                maxLength={120}
                value={renaming.name}
                onChange={(event) => setRenaming({ id: project.id, name: event.target.value })}
              />
              <KelButton variant='primary' disabled={busy !== null} onClick={() => void saveName()}>
                Save
              </KelButton>
              <KelButton variant='quiet' onClick={() => setRenaming(null)}>
                Cancel
              </KelButton>
            </form>
          ) : (
            <span className='kel-strong'>{project.name}</span>
          )}
          {isActive && <span className='kel-chip kel-chip--ok'>Active</span>}
          <span className='kel-grow' />
          {!project.archived && (
            <KelButton variant={isActive ? 'quiet' : 'primary'} disabled={busy !== null} onClick={() => void open(project)}>
              Open
            </KelButton>
          )}
        </div>
        <div className='kel-row kel-meta'>
          <span title={project.root ?? undefined}>{project.root ? folderName(project.root) : 'No folder'}</span>
          <span>·</span>
          {project.test_command?.length ? (
            <span className='kel-chip' title={project.test_command.join(' ')}>
              {`Tests: ${project.test_command.join(' ')}`}
            </span>
          ) : (
            <span>No test command</span>
          )}
          <span>·</span>
          <span>{plural(project.conversations ?? 0, 'chat', 'chats')}</span>
        </div>
        {project.archived ? (
          <div className='kel-row'>
            <KelButton
              variant='secondary'
              disabled={busy !== null}
              onClick={() => void act('Restore', () => kelProjects.restore(project.id), `${project.name} is back.`)}
            >
              Restore
            </KelButton>
            {!holdsSomething(project) && (
              <KelButton
                variant='danger'
                disabled={busy !== null}
                onClick={() => void act('Delete', () => kelProjects.remove(project.id), `${project.name} was deleted.`)}
              >
                Delete
              </KelButton>
            )}
          </div>
        ) : (
          <div className='kel-row'>
            {!isGeneral && (
              <KelButton variant='quiet' disabled={busy !== null} onClick={() => setRenaming({ id: project.id, name: project.name })}>
                Rename
              </KelButton>
            )}
            <span className={editId === project.id && focus === 'folder' ? 'kel-project-list-focus' : undefined}>
              <KelButton variant='quiet' disabled={busy !== null} onClick={() => void chooseFolder(project)}>
                {project.root ? 'Change folder' : 'Set folder'}
              </KelButton>
            </span>
            <KelButton
              variant='quiet'
              disabled={busy !== null}
              onClick={() => setTesting(editingTest ? null : { id: project.id, argv: project.test_command?.length ? [...project.test_command] : [''] })}
            >
              Test command
            </KelButton>
            {!isGeneral && (
              <KelButton variant='quiet' disabled={busy !== null} onClick={() => setArchiving(project.id)}>
                Archive
              </KelButton>
            )}
          </div>
        )}
        {archiving === project.id && (
          <div className='kel-row' role='group' aria-label={`Archive ${project.name}`}>
            <span className='kel-meta'>
              {`Archive ${project.name}? Its chats stay openable, and Kel will ask again before using its folder.`}
            </span>
            <span className='kel-grow' />
            <KelButton
              variant='danger'
              disabled={busy !== null}
              onClick={() =>
                void act('Archive', () => kelProjects.archive(project.id), `${project.name} is archived.`).then(() => setArchiving(null))
              }
            >
              Archive
            </KelButton>
            <KelButton variant='quiet' onClick={() => setArchiving(null)}>
              Cancel
            </KelButton>
          </div>
        )}
        {editingTest && testing && (
          <div className='kel-project-list-test' role='group' aria-label={`Test command for ${project.name}`}>
            <p className='kel-meta'>The command Kel runs to check its work here, one part per box (for example “npm”, “test”).</p>
            <div className='kel-row'>
              {testing.argv.map((arg, index) => (
                <span className='kel-row' key={index}>
                  <input
                    className='kel-input'
                    aria-label={`Command part ${index + 1}`}
                    autoFocus={index === 0}
                    value={arg}
                    onChange={(event) =>
                      setTesting((current) =>
                        current && { ...current, argv: current.argv.map((value, i) => (i === index ? event.target.value : value)) }
                      )
                    }
                  />
                  {testing.argv.length > 1 && (
                    <KelButton
                      variant='quiet'
                      ariaLabel={`Remove part ${index + 1}`}
                      onClick={() => setTesting((current) => current && { ...current, argv: current.argv.filter((_, i) => i !== index) })}
                    >
                      ×
                    </KelButton>
                  )}
                </span>
              ))}
              <KelButton variant='quiet' onClick={() => setTesting((current) => current && { ...current, argv: [...current.argv, ''] })}>
                Add part
              </KelButton>
            </div>
            <div className='kel-row'>
              <KelButton variant='primary' disabled={busy !== null} onClick={() => void saveTest()}>
                Save
              </KelButton>
              {project.test_command?.length ? (
                <KelButton variant='quiet' disabled={busy !== null} onClick={() => void saveTest(true)}>
                  Remove test command
                </KelButton>
              ) : null}
              <KelButton variant='quiet' onClick={() => setTesting(null)}>
                Cancel
              </KelButton>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className='kel-scope'>
      <a className='kel-skip' href='#kel-projects-list-main'>
        Skip to main content
      </a>
      <main className='kel-page kel-projects-list' id='kel-projects-list-main' tabIndex={-1}>
        <div className='kel-page__head'>
          <div>
            <ShellWorkspaceLink />
            <h1 className='kel-h1'>Projects</h1>
          </div>
          <span className='kel-grow' />
          <KelButton variant='primary' onClick={() => setCreating(true)}>
            New project
          </KelButton>
        </div>
        <p className='kel-meta'>Your active project is the same on every device.</p>
        {note && (
          <p className='kel-meta' role={note.alert ? 'alert' : 'status'}>
            {note.text}
          </p>
        )}

        {creating && (
          <KelCard title='New project'>
            <NewProjectForm
              onCancel={() => setCreating(false)}
              onCreated={(project) => {
                setCreating(false);
                void act('Create', () => setActiveProject(project.id), `${project.name} is ready and active.`);
              }}
            />
          </KelCard>
        )}

        {!view.loaded ? (
          <KelLoading rows={3} />
        ) : (
          <KelCard title='All projects'>
            {live.length === 0 ? (
              <KelEmpty title='No projects yet.' why='A project keeps its chats, knowledge and folder together.' />
            ) : (
              live.map(row)
            )}
          </KelCard>
        )}

        {view.loaded && archived.length > 0 && <KelCard title='Archived'>{archived.map(row)}</KelCard>}
      </main>
    </div>
  );
}
