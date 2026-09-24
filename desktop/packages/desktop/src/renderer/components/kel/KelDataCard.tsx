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

const summaryLine = (summary: BackupSummary): string => {
  const parts: string[] = [];
  if (typeof summary.conversations === 'number') parts.push(`${summary.conversations} chats`);
  if (typeof summary.messages === 'number') parts.push(`${summary.messages} messages`);
  if (typeof summary.transcripts === 'number') parts.push(`${summary.transcripts} transcripts`);
  if (typeof summary.vetting_sessions === 'number') parts.push(`${summary.vetting_sessions} vetting sessions`);
  return parts.length ? parts.join(' · ') : 'nothing backed up yet';
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

  const createBackup = useCallback(async () => {
    if (!backupTarget.trim()) return;
    setBusy(true);
    try {
      const created = await api<{ folder: string; summary: BackupSummary }>({ action: 'create', target: backupTarget.trim() });
      Message.success(`Backup created (${summaryLine(created.summary)}).`);
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
      Modal.confirm({
        title: 'Restore this backup?',
        content: (
          <div>
            <p>
              This replaces Kel's current data ({summaryLine(details.summary)} in the backup) with the
              backup from {details.folder}.
            </p>
            <p className='text-t-secondary'>
              Your current data is kept beside the data folder as <code>.pre-restore-…</code> and Kel
              must be restarted to finish. Credentials are not part of backups — reconnect them after.
            </p>
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
    <div className='kel-h2'>Data &amp; backup</div>
    <div className='kel-phone-only kel-shell-system-mobile-rows'>
      <button type='button' className='kel-shell-system-mobile-row' onClick={() => pathError ? void loadPath() : void openFolder()} disabled={!dataPath && !pathError}>Data folder <span aria-hidden='true'>›</span></button>
      <button type='button' className='kel-shell-system-mobile-row' onClick={() => setFolderDialog('backup')}>Back up now <span aria-hidden='true'>›</span></button>
      <button type='button' className='kel-shell-system-mobile-restore' onClick={() => setFolderDialog('restore')}>Restore from this backup</button>
    </div>
    <div className='kel-shell-preference-row kel-desktop-only'><div><div>Data folder</div><p className='kel-meta' data-testid='data-folder-path'>{dataPath ? dataPath.root : pathError ? 'Kel could not read the data folder path.' : 'Loading…'}</p></div>
      {pathError ? <Button onClick={loadPath}>Try again</Button> : <Button onClick={() => void openFolder()} disabled={!dataPath} data-testid='open-data-folder'>Show in folder</Button>}
    </div>
    <div className='kel-shell-preference-row kel-desktop-only'><div><div>Backup</div><p className='kel-meta'>Saves a copy of everything above to a folder you choose.</p></div><Button onClick={() => setFolderDialog('backup')} data-testid='backup-now'>Back up now</Button></div>
    <div className='kel-shell-preference-row kel-desktop-only'><div><div>Restore</div><p className='kel-meta'>Restores a backup folder. Current data is kept; Kel restarts.</p></div><Button onClick={() => setFolderDialog('restore')} data-testid='restore-inspect'>Restore from this backup</Button></div>
    <Modal title={folderDialog === 'backup' ? 'Back up now' : 'Restore from this backup'} visible={folderDialog !== null} onCancel={() => setFolderDialog(null)} okText={folderDialog === 'backup' ? 'Back up now' : 'Inspect backup'} confirmLoading={busy} okButtonProps={{ disabled: !(folderDialog === 'backup' ? backupTarget : restoreSource).trim() }} onOk={() => folderDialog === 'backup' ? createBackup() : restoreBackup()}>
      <Input aria-label={folderDialog === 'backup' ? 'Backup folder' : 'Restore folder'} value={folderDialog === 'backup' ? backupTarget : restoreSource} onChange={folderDialog === 'backup' ? setBackupTarget : setRestoreSource} placeholder='Folder path' />
    </Modal>
  </div>;
};
export default KelDataCard;
