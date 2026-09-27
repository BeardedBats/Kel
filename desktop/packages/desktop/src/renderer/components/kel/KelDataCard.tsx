/** Kel data & backup — where Kel keeps things, plus simple local backup/restore. */
import React, { useCallback, useEffect, useState } from 'react';
import { Button, Input, Message, Modal } from '@arco-design/web-react';
import { ipcBridge } from '@/common';

type DataPath = { root: string; database: string };
type BackupSummary = Record<string, number>;
type BackupDetails = { folder: string; created?: number; notes?: string; summary: BackupSummary };

const api = <T,>(body: Record<string, unknown>): Promise<T> => {
  const bridge = (window as unknown as { kelAPI?: { request: (route: string, payload?: unknown) => Promise<T> } }).kelAPI;
  if (!bridge) return Promise.reject(new Error('Kel connection is unavailable'));
  return bridge.request('/api/backup', body);
};

const requestPath = (): Promise<DataPath> => {
  const bridge = (window as unknown as { kelAPI?: { request: (route: string, payload?: unknown) => Promise<DataPath> } }).kelAPI;
  if (!bridge) return Promise.reject(new Error('Kel connection is unavailable'));
  return bridge.request('/api/data-path', {});
};

const SUMMARY_WORDS: Array<[string, string, string]> = [
  ['conversations', 'chat', 'chats'],
  ['messages', 'message', 'messages'],
  ['projects', 'project', 'projects'],
  ['jobs', 'piece of work', 'pieces of work'],
  ['transcripts', 'transcript', 'transcripts'],
  ['memories', 'memory', 'memories'],
  ['connections', 'connection', 'connections'],
  ['vetting_sessions', 'vetting session', 'vetting sessions'],
];
export const summaryLine = (summary: BackupSummary, empty = 'nothing backed up yet'): string => {
  const parts = SUMMARY_WORDS.filter(([key]) => typeof summary[key] === 'number').map(
    ([key, one, many]) => `${summary[key]} ${summary[key] === 1 ? one : many}`
  );
  return parts.length ? parts.join(' · ') : empty;
};

/** JR-45: what a backup covers and what it never carries, said before anything is copied. */
export const BACKUP_INCLUDES =
  'Includes your chats, projects, work, memories, transcripts and their audio, attachments, skills and settings.';
export const BACKUP_EXCLUDES =
  'Not included: saved credentials — model provider keys, the transcription key and connection credentials. Add them again after a restore.';

const pickFolder = async (): Promise<string | null> => {
  const picked = await ipcBridge.dialog.showOpen.invoke({ properties: ['openDirectory', 'createDirectory'] });
  return picked && picked[0] ? picked[0] : null;
};
const folderName = (path: string): string => path.split(/[\\/]/).filter(Boolean).pop() || path;
const backupDate = (created?: number): string => {
  if (!created || !Number.isFinite(created)) return 'Selected backup';
  const date = new Date(created > 1_000_000_000_000 ? created : created * 1000);
  return Number.isNaN(date.getTime()) ? 'Selected backup' : `Backup from ${date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
};

export const KelDataCard: React.FC = () => {
  const [dataPath, setDataPath] = useState<DataPath | null>(null);
  const [backupTarget, setBackupTarget] = useState('');
  const [restoreSource, setRestoreSource] = useState('');
  const [busy, setBusy] = useState(false);
  const [folderDialog, setFolderDialog] = useState<'backup' | 'restore' | null>(null);

  const [pathError, setPathError] = useState(false);
  const loadPath = useCallback(() => {
    setPathError(false);
    requestPath()
      .then(setDataPath)
      .catch(() => {
        setDataPath(null);
        setPathError(true);
      });
  }, []);

  const plainError = (error: unknown): string => {
    const raw = String((error as Error)?.message || error);
    if (/locked|busy|EBUSY|WinError/i.test(raw)) {
      return 'Kel could not read its files just now. Close any other Kel window and try again.';
    }
    if (/not a kel backup|description|existing folder/i.test(raw)) return raw;
    return 'Kel could not finish that just now. Try again.';
  };

  useEffect(() => {
    loadPath();
  }, [loadPath]);

  const copyPath = useCallback(async () => {
    if (!dataPath) return;
    try {
      await navigator.clipboard.writeText(dataPath.root);
      Message.success('Data folder path copied.');
    } catch {
      Message.error('Kel could not copy to the clipboard. Select the text and copy manually.');
    }
  }, [dataPath]);

  const openFolder = useCallback(async () => {
    if (!dataPath) return;
    try {
      await ipcBridge.shell.showItemInFolder.invoke(dataPath.database);
    } catch {
      Message.error('Kel could not open the folder.');
    }
  }, [dataPath]);

  const chooseFolder = useCallback(async (which: 'backup' | 'restore') => {
    try {
      const folder = await pickFolder();
      if (!folder) return;
      if (which === 'backup') setBackupTarget(folder);
      else setRestoreSource(folder);
    } catch {
      Message.error('Kel could not open the folder picker. Try again.');
    }
  }, []);

  const createBackup = useCallback(async () => {
    if (!backupTarget.trim()) return;
    setBusy(true);
    try {
      const created = await api<{ folder: string; summary: BackupSummary; skipped?: string[] }>({
        action: 'create',
        target: backupTarget.trim(),
      });
      // ST-13: the dialog closes on success and the toast names the folder that was written.
      setFolderDialog(null);
      Message.success({
        content: `Backed up to ${folderName(created.folder)} (${summaryLine(created.summary)}).${
          created.skipped?.length ? ' Some files in use were skipped — the backup description lists them.' : ''
        }`,
        duration: 6000,
      });
    } catch (error) {
      Message.error(plainError(error));
    } finally {
      setBusy(false);
    }
  }, [backupTarget]);

  const restoreBackup = useCallback(async () => {
    if (!restoreSource.trim()) return;
    setBusy(true);
    try {
      const details = await api<BackupDetails>({ action: 'inspect', source: restoreSource.trim() });
      // What is there now, so the confirmation can say what gets replaced (best effort, read-only).
      const inventory = await api<{ tables: Record<string, number | null>; summary?: BackupSummary }>({
        action: 'inventory',
      }).catch((): null => null);
      // `summary` counts sidebar chats the way a backup does; `tables` (older engines) counts records.
      const current: BackupSummary = {};
      for (const [key] of SUMMARY_WORDS) {
        const value = inventory?.summary?.[key] ?? inventory?.tables?.[key];
        if (typeof value === 'number') current[key] = value;
      }
      setFolderDialog(null);
      Modal.confirm({
        className: 'kel-shell-restore-confirm-modal',
        title: 'Restore this backup?',
        content: (
          <div className='kel-shell-restore-confirm-copy' data-testid='restore-confirm-copy'>
            <p className='kel-shell-restore-confirm-summary'>{backupDate(details.created)} · {summaryLine(details.summary)}</p>
            <p>
              <strong>This replaces everything Kel has now</strong>
              {inventory ? ` (${summaryLine(current, 'no chats yet')})` : ''} — chats, projects, work, memories,
              transcripts, attachments, skills and settings — with the backup&apos;s copy.
            </p>
            <p>Your current data is kept beside the data folder first. Kel finishes the restore the next time it starts.</p>
            <p>Saved credentials are not in backups: add your model keys, the transcription key and connection credentials again after.</p>
          </div>
        ),
        okText: 'Restore',
        cancelText: 'Keep current data',
        onOk: async () => {
          try {
            await api<{ restart_required: boolean }>({ action: 'restore', source: details.folder });
            Message.success('Ready to restore. Close and reopen Kel to finish.');
          } catch (error) {
            Message.error(plainError(error));
          }
        },
      });
    } catch (error) {
      Message.error(plainError(error));
    } finally {
      setBusy(false);
    }
  }, [restoreSource]);

  return <div className='kel-card kel-shell-data-card'>
    <div className='kel-h2'><span className='kel-desktop-only'>Data and backup</span><span className='kel-phone-only'>Data &amp; backup</span></div>
    <div className='kel-phone-only kel-shell-system-mobile-rows'>
      <button type='button' className='kel-shell-system-mobile-row' onClick={() => pathError ? void loadPath() : void openFolder()} disabled={!dataPath && !pathError}>Data folder <span aria-hidden='true'>›</span></button>
      <button type='button' className='kel-shell-system-mobile-row' onClick={() => setFolderDialog('backup')}>Back up now <span aria-hidden='true'>›</span></button>
      <button type='button' className='kel-shell-system-mobile-restore' onClick={() => setFolderDialog('restore')}>Restore from this backup</button>
    </div>
    <div className='kel-shell-preference-row kel-desktop-only'><div><div>Data folder</div><p className='kel-meta' data-testid='data-folder-path'>{dataPath ? dataPath.root : pathError ? 'Kel could not read the data folder path.' : 'Loading…'}</p></div>
      {pathError ? <Button onClick={loadPath}>Try again</Button> : <Button onClick={() => void openFolder()} disabled={!dataPath} data-testid='open-data-folder'>Show in folder</Button>}
    </div>
    <div className='kel-shell-preference-row kel-desktop-only'><div><div>Back up</div><p className='kel-meta'>Save a copy of your chats, projects and settings to a folder. Credentials are not included.</p></div><Button type='primary' onClick={() => setFolderDialog('backup')} data-testid='backup-now'>Back up now</Button></div>
    <div className='kel-shell-preference-row kel-desktop-only'><div><div>Restore</div><p className='kel-meta'>Replace current data with a backup</p></div><Button onClick={() => setFolderDialog('restore')} data-testid='restore-inspect'>Restore...</Button></div>
    <Modal
      title={folderDialog === 'backup' ? 'Back up now' : 'Restore from a backup'}
      visible={folderDialog !== null}
      unmountOnExit
      onCancel={() => setFolderDialog(null)}
      okText={folderDialog === 'backup' ? 'Back up now' : 'Check this backup'}
      confirmLoading={busy}
      okButtonProps={{ disabled: !(folderDialog === 'backup' ? backupTarget : restoreSource).trim() }}
      onOk={() => (folderDialog === 'backup' ? createBackup() : restoreBackup())}
    >
      <div className='kel-shell-backup-dialog' data-testid='backup-dialog'>
        {folderDialog === 'backup' ? (
          <>
            <p className='kel-meta' data-testid='backup-includes'>{BACKUP_INCLUDES}</p>
            <p className='kel-meta' data-testid='backup-excludes'>{BACKUP_EXCLUDES}</p>
            <p className='kel-meta'>Kel makes a new dated folder inside the folder you choose.</p>
          </>
        ) : (
          <p className='kel-meta'>
            Choose a folder Kel made with Back up now. Kel checks it and shows what it holds before anything is replaced.
          </p>
        )}
        <div className='kel-shell-backup-folder'>
          <Input
            readOnly
            aria-label={folderDialog === 'backup' ? 'Backup folder' : 'Restore folder'}
            value={folderDialog === 'backup' ? backupTarget : restoreSource}
            placeholder='No folder chosen'
          />
          <Button
            onClick={() => void chooseFolder(folderDialog === 'restore' ? 'restore' : 'backup')}
            data-testid='backup-choose-folder'
          >
            Choose folder…
          </Button>
        </div>
      </div>
    </Modal>
  </div>;
};
export default KelDataCard;
