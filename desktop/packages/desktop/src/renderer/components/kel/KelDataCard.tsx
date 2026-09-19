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

  return (
    <div className='kel-card'>
      <div className='text-14px text-t-primary leading-22px font-500'>Data & backup</div>
      <div className='text-14px text-t-secondary leading-20px mt-2px'>
        Where Kel keeps your chats, projects, transcripts and settings on this computer — plus simple backup and
        restore. Credentials are never included in backups.
      </div>

      <div className='kel-divider' />

      <div className='flex flex-col gap-8px'>
        <div className='text-14px text-t-primary font-500'>Data folder</div>
        <div className='flex items-center gap-8px flex-wrap'>
          <code className='text-12px text-t-secondary break-all' data-testid='data-folder-path'>
            {dataPath ? dataPath.root : pathError ? 'Kel could not read the data folder path.' : 'Loading…'}
          </code>
          {pathError && (
            <Button size='small' onClick={() => loadPath()} data-testid='retry-data-path'>
              Try again
            </Button>
          )}
          <Button size='small' onClick={() => void copyPath()} disabled={!dataPath} data-testid='copy-data-path'>
            Copy path
          </Button>
          <Button size='small' onClick={() => void openFolder()} disabled={!dataPath} data-testid='open-data-folder'>
            Show in folder
          </Button>
        </div>
      </div>

      <div className='kel-divider' />

      <div className='flex flex-col gap-8px'>
        <div className='text-14px text-t-primary font-500'>Backup</div>
        <div className='text-14px text-t-secondary'>Saves a copy of everything above to a folder you choose.</div>
        <div className='flex items-center gap-8px flex-wrap'>
          <Input
            value={backupTarget}
            onChange={setBackupTarget}
            placeholder='Folder to save the backup in (for example D:\Kel backups)'
            data-testid='backup-target'
            style={{ maxWidth: 420 }}
          />
          <Button type='primary' size='small' disabled={!backupTarget.trim() || busy} onClick={() => void createBackup()} data-testid='backup-now'>
            Back up now
          </Button>
        </div>
      </div>

      <div className='kel-divider' />

      <div className='flex flex-col gap-8px'>
        <div className='text-14px text-t-primary font-500'>Restore</div>
        <div className='text-14px text-t-secondary'>Brings back a backup folder. Your current data is kept and Kel restarts to finish.</div>
        <div className='flex items-center gap-8px flex-wrap'>
          <Input
            value={restoreSource}
            onChange={setRestoreSource}
            placeholder='Backup folder to restore from'
            data-testid='restore-source'
            style={{ maxWidth: 420 }}
          />
          <Button size='small' disabled={!restoreSource.trim() || busy} onClick={() => void restoreBackup()} data-testid='restore-inspect'>
            Restore from this backup
          </Button>
        </div>
      </div>
    </div>
  );
};

export default KelDataCard;
