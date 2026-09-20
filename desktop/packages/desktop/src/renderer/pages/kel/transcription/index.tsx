/**
 * Transcription — Kel's first-class audio input source.
 *
 * Ported behaviour from the donor app (folders above recents, drag-to-folder, record/upload,
 * rename/copy/download, append recording) with Kel-native surfaces: provider machinery stays
 * behind the engine's `/api/transcription` action family, and transcripts can be sent to chat or
 * routed into a live Vetting Session through the existing ingestion service.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Input, Message, Modal, Select } from '@arco-design/web-react';
import { useNavigate } from 'react-router-dom';
import { KelCard, KelEmpty, KelStatusChip } from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { decodeFileToWav, friendlyMicError, startMicCapture, type MicCapture } from '@renderer/utils/transcription/audio';
import styles from './index.module.css';

/**
 * Batch 6 (TR-02 residual): every failure toast goes through the classifier, so transport and
 * infrastructure text never reaches a person. Engine sentences (already plain language) pass
 * through unchanged.
 */
const failMessage = (error: unknown): string => failureSentence(error, 'That did not go through — try again.');

type Folder = { id: string; name: string; created: number };
type Transcript = {
  id: string;
  name: string;
  text: string;
  created: number;
  updated: number;
  folder_id: string | null;
  source_type: string;
  source_filename: string | null;
  duration_ms: number | null;
  status: string;
  has_audio: boolean;
};
type Library = { folders: Folder[]; transcripts: Transcript[] };
type ProviderStatus = { mode: string; has_key: boolean; live_capable: boolean; label: string; detail: string };
type ReviewPayload = {
  session_id?: string;
  mode?: string;
  preview: { question_id: string; answer: string; note?: string; confidence: string }[];
  proposals?: { question_id: string; option: string; option_label?: string }[];
  unmatched?: { payload: string }[];
  potential_conflicts: { statement: string }[];
  buckets?: { requirements: string[]; concerns: string[]; unresolved: string[] };
};

async function request<T>(route: string, body?: unknown): Promise<T> {
  const api = window.kelAPI;
  if (!api) throw new Error('Kel is not connected');
  return (await api.request(route, body)) as T;
}

const transcription = <T,>(body: Record<string, unknown>) => request<T>('/api/transcription', body);

function formatWhen(seconds: number): string {
  const date = new Date(seconds * 1000);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  return sameDay
    ? date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
    : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatDuration(ms: number | null): string {
  if (!ms) return '';
  const total = Math.round(ms / 1000);
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return minutes ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

function downloadBlob(name: string, data: BlobPart, mime: string): void {
  const url = URL.createObjectURL(new Blob([data], { type: mime }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const TranscriptionPage: React.FC = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<ProviderStatus>();
  const [library, setLibrary] = useState<Library>({ folders: [], transcripts: [] });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState('');
  const [dragging, setDragging] = useState(false);
  const [dropFolder, setDropFolder] = useState<string | null>(null);
  const [folderDraft, setFolderDraft] = useState('');
  const [folderEditing, setFolderEditing] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState('');
  const [renaming, setRenaming] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [recState, setRecState] = useState<'idle' | 'recording' | 'working'>('idle');
  const [seconds, setSeconds] = useState(0);
  const [liveText, setLiveText] = useState('');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [keyDraft, setKeyDraft] = useState('');
  const [review, setReview] = useState<{ open: boolean; mode: 'answers' | 'freethink'; text: string; editing: boolean; busy: boolean; payload?: ReviewPayload }>(
    { open: false, mode: 'answers', text: '', editing: false, busy: false }
  );
  const captureRef = useRef<MicCapture | null>(null);
  const sessionRef = useRef<string | null>(null);
  const chainRef = useRef<Promise<unknown>>(Promise.resolve());
  const timerRef = useRef<number | null>(null);
  const pollRef = useRef<number | null>(null);
  const appendTargetRef = useRef<string | null>(null);
  const recEpochRef = useRef(0);
  const [combineOpen, setCombineOpen] = useState(false);
  const [combineSource, setCombineSource] = useState('');
  const [recentSearch, setRecentSearch] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const selected = useMemo(
    () => library.transcripts.find((item) => item.id === selectedId) || null,
    [library.transcripts, selectedId]
  );
  const recent = useMemo(
    () => [...library.transcripts].sort((a, b) => b.created - a.created),
    [library.transcripts]
  );
  // D4: search narrows the recents (and folder contents) client-side — one library, no second store.
  const visibleRecent = useMemo(() => {
    const needle = recentSearch.trim().toLowerCase();
    if (!needle) return recent;
    return recent.filter(
      (item) => item.name.toLowerCase().includes(needle) || (item.text || '').toLowerCase().includes(needle)
    );
  }, [recent, recentSearch]);

  const refresh = useCallback(async () => {
    try {
      const [state, data] = await Promise.all([
        transcription<ProviderStatus>({ action: 'status' }),
        transcription<Library>({ action: 'library' }),
      ]);
      setStatus(state);
      setLibrary(data);
      setLoadError(null);
    } catch (error) {
      setLoadError(error);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(
    () => () => {
      captureRef.current?.cancel();
      if (timerRef.current) window.clearInterval(timerRef.current);
      if (pollRef.current) window.clearInterval(pollRef.current);
    },
    []
  );

  const stopTimers = useCallback(() => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    if (pollRef.current) window.clearInterval(pollRef.current);
    timerRef.current = null;
    pollRef.current = null;
  }, []);

  const beginRecording = useCallback(
    async (appendTo?: string) => {
      if (recState !== 'idle') return;
      const epoch = (recEpochRef.current += 1);
      setRecState('working');
      setProgress('');
      appendTargetRef.current = appendTo || null;
      try {
        const capture = await startMicCapture((pcm) => {
          const session = sessionRef.current;
          if (!session) return;
          chainRef.current = chainRef.current
            .then(() => transcription<{ text?: string }>({ action: 'stream_chunk', session, pcm }))
            .catch(() => {});
        });
        if (epoch !== recEpochRef.current) {
          capture.cancel();
          return;
        }
        captureRef.current = capture;
        const started = await transcription<{ session_id: string | null; live: boolean }>({ action: 'stream_start' });
        if (epoch !== recEpochRef.current) {
          capture.cancel();
          if (started.live && started.session_id) {
            void transcription({ action: 'stream_finish', session: started.session_id }).catch(() => {});
          }
          return;
        }
        sessionRef.current = started.live ? started.session_id : null;
        setLiveText('');
        setSeconds(0);
        setRecState('recording');
        timerRef.current = window.setInterval(() => setSeconds((value) => value + 1), 1000);
        if (started.live && started.session_id) {
          pollRef.current = window.setInterval(() => {
            const session = sessionRef.current;
            if (!session) return;
            void transcription<{ text?: string }>({ action: 'stream_status', session })
              .then((state) => setLiveText(state.text || ''))
              .catch(() => {});
          }, 900);
        }
      } catch (error) {
        captureRef.current?.cancel();
        captureRef.current = null;
        setRecState('idle');
        const name = (error as { name?: string })?.name || '';
        const message = String((error as Error)?.message || error);
        if (/NotAllowed|NotFound|NotReadable|Overconstrained|Security|Permission/i.test(name + message)) {
          Message.error(friendlyMicError(error));
        } else {
          Message.error(failureSentence(error, 'The microphone did not start. Check the audio device and try again.'));
        }
      }
    },
    [recState]
  );

  const finishRecording = useCallback(
    async (keep: boolean) => {
      recEpochRef.current += 1;
      const capture = captureRef.current;
      captureRef.current = null;
      stopTimers();
      const session = sessionRef.current;
      sessionRef.current = null;
      if (!capture) {
        setRecState('idle');
        return;
      }
      if (!keep) {
        capture.cancel();
        if (session) void transcription({ action: 'stream_finish', session }).catch(() => {});
        setRecState('idle');
        setSeconds(0);
        setLiveText('');
        return;
      }
      setRecState('working');
      try {
        const recording = await capture.stop();
        await chainRef.current.catch(() => {});
        let text = '';
        if (session) {
          const finished = await transcription<{ text?: string; duration_ms?: number }>({
            action: 'stream_finish',
            session,
          });
          text = finished.text || '';
        }
        if (!text.trim() && recording.durationMs > 400) {
          const quick = await transcription<{ text?: string }>({
            action: 'quick_transcribe',
            filename: 'recording.wav',
            audio: recording.base64,
            duration_ms: recording.durationMs,
          });
          text = quick.text || '';
        }
        const saved = await transcription<Transcript>({
          action: 'save_recording',
          text,
          duration_ms: recording.durationMs,
          audio: recording.base64,
          append_to: appendTargetRef.current || undefined,
        });
        const appended = Boolean(appendTargetRef.current);
        appendTargetRef.current = null;
        await refresh();
        setSelectedId(saved.id);
        Message.success(appended ? 'Recording added to the transcript.' : 'Recording saved to Recents.');
      } catch (error) {
        Message.error(failMessage(error));
      } finally {
        setSeconds(0);
        setLiveText('');
        setRecState('idle');
      }
    },
    [refresh, stopTimers]
  );

  const uploadFile = useCallback(
    async (file: File) => {
      setBusy(true);
      try {
        setProgress('Preparing audio…');
        const prepared = await decodeFileToWav(file);
        setProgress('Transcribing…');
        const saved = await transcription<Transcript>({
          action: 'upload',
          filename: file.name,
          audio: prepared.base64,
        });
        setProgress('Saving transcript…');
        await refresh();
        setSelectedId(saved.id);
        Message.success('Transcript ready.');
      } catch (error) {
        Message.error(failMessage(error));
      } finally {
        setProgress('');
        setBusy(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    },
    [refresh]
  );

  useEffect(() => {
    if (recState === 'idle') return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        void finishRecording(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [recState, finishRecording]);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setDragging(false);
      const transcriptId = event.dataTransfer.getData('text/kel-transcript');
      const folderId = (event.target as HTMLElement).closest<HTMLElement>('[data-folder-id]')?.dataset.folderId;
      if (transcriptId && folderId) {
        void transcription({ action: 'assign', id: transcriptId, folder: folderId })
          .then(() => refresh())
          .catch((error) => Message.error(failMessage(error)));
        return;
      }
      const file = event.dataTransfer.files?.[0];
      if (file) void uploadFile(file);
    },
    [refresh, uploadFile]
  );

  const createFolder = useCallback(async () => {
    const name = folderDraft.trim();
    if (!name) return;
    try {
      const folder = await transcription<Folder>({ action: 'folder_create', name });
      setFolderDraft('');
      setExpanded((current) => new Set(current).add(folder.id));
      await refresh();
    } catch (error) {
      Message.error(failMessage(error));
    }
  }, [folderDraft, refresh]);

  const renameFolder = useCallback(
    async (id: string, name: string) => {
      setFolderEditing(null);
      if (!name.trim()) return;
      try {
        await transcription({ action: 'folder_rename', id, name: name.trim() });
        await refresh();
      } catch (error) {
        Message.error(failMessage(error));
      }
    },
    [refresh]
  );

  const deleteFolder = useCallback(
    async (folder: Folder) => {
      Modal.confirm({
        title: `Delete “${folder.name}”?`,
        content: 'Transcripts inside stay in Recent Transcriptions.',
        okText: 'Delete folder',
        cancelText: 'Keep',
        onOk: async () => {
          try {
            await transcription({ action: 'folder_delete', id: folder.id });
            await refresh();
          } catch (error) {
            Message.error(failMessage(error));
          }
        },
      });
    },
    [refresh]
  );

const saveName = useCallback(async () => {
    if (!selected) return;
    const name = nameDraft.trim();
    if (!name) {
      setRenaming(false);
      return;
    }
    try {
      await transcription({ action: 'rename', id: selected.id, name });
      setRenaming(false);
      await refresh();
    } catch (error) {
      Message.error(failMessage(error));
    }
  }, [nameDraft, refresh, selected]);

  const removeTranscript = useCallback(
    (item: Transcript) => {
      Modal.confirm({
        title: `Delete “${item.name}”?`,
        content: 'The transcript and its saved audio are removed. This cannot be undone.',
        okText: 'Delete',
        cancelText: 'Keep',
        onOk: async () => {
          try {
            await transcription({ action: 'delete', id: item.id });
            if (selectedId === item.id) setSelectedId(null);
            await refresh();
          } catch (error) {
            Message.error(failMessage(error));
          }
        },
      });
    },
    [refresh, selectedId]
  );

  const assignTo = useCallback(
    async (folderId: string | null) => {
      if (!selected) return;
      try {
        await transcription({ action: 'assign', id: selected.id, folder: folderId });
        if (folderId) setExpanded((current) => new Set(current).add(folderId));
        await refresh();
      } catch (error) {
        Message.error(failMessage(error));
      }
    },
    [refresh, selected]
  );

  const copyTranscript = useCallback(async () => {
    if (!selected) return;
    try {
      await navigator.clipboard.writeText(selected.text || '');
      Message.success('Transcript copied.');
    } catch {
      Message.error('Kel could not copy to the clipboard. Select the text and copy manually.');
    }
  }, [selected]);

  const downloadText = useCallback(() => {
    if (!selected) return;
    downloadBlob(`${selected.name || 'transcript'}.txt`, selected.text || '', 'text/plain;charset=utf-8');
  }, [selected]);

  const downloadAudio = useCallback(async () => {
    if (!selected) return;
    try {
      const exported = await transcription<{ name: string; mime: string; data: string }>(
        { action: 'export_audio', id: selected.id }
      );
      const binary = atob(exported.data);
      const bytes = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
      downloadBlob(exported.name, bytes, exported.mime || 'audio/wav');
    } catch (error) {
      Message.error(failMessage(error));
    }
  }, [selected]);

  const runCombine = useCallback(async () => {
    if (!selected || !combineSource) return;
    try {
      await transcription({ action: 'combine', id: selected.id, source: combineSource });
      setCombineOpen(false);
      setCombineSource('');
      await refresh();
      Message.success('Merged into this transcript.');
    } catch (error) {
      Message.error(failMessage(error));
    }
  }, [combineSource, refresh, selected]);

  const sendToChat = useCallback(() => {
    if (!selected) return;
    try {
      window.sessionStorage.setItem('kel.transcription.draft', selected.text || '');
    } catch {
      /* the draft is a convenience; chat still opens */
    }
    navigate('/guid');
  }, [navigate, selected]);

  const onRowDragStart = useCallback((event: React.DragEvent<HTMLElement>, item: Transcript) => {
    event.dataTransfer.setData('text/kel-transcript', item.id);
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  const folderDrop = useCallback(
    (folderId: string) => ({
      onDragOver: (event: React.DragEvent<HTMLElement>) => {
        if (event.dataTransfer.types.includes('text/kel-transcript')) {
          event.preventDefault();
          setDropFolder(folderId);
        }
      },
      onDragLeave: () => setDropFolder(null),
      onDrop: async (event: React.DragEvent<HTMLElement>) => {
        event.preventDefault();
        event.stopPropagation();
        setDropFolder(null);
        const id = event.dataTransfer.getData('text/kel-transcript');
        if (!id) return;
        try {
          await transcription({ action: 'assign', id, folder: folderId });
          setExpanded((current) => new Set(current).add(folderId));
          await refresh();
        } catch (error) {
          Message.error(failMessage(error));
        }
      },
    }),
    [refresh]
  );

  const saveKey = useCallback(async () => {
    const key = keyDraft.trim();
    if (!key) return;
    try {
      await transcription({ action: 'set_key', key });
      setKeyDraft('');
      setSettingsOpen(false);
      Message.success('Muse is connected. New recordings and uploads use it.');
      await refresh();
    } catch (error) {
      Message.error(failMessage(error));
    }
  }, [keyDraft, refresh]);

  const clearKey = useCallback(async () => {
    try {
      await transcription({ action: 'clear_key' });
      setSettingsOpen(false);
      Message.success('Back to practice mode.');
      await refresh();
    } catch (error) {
      Message.error(failMessage(error));
    }
  }, [refresh]);

  const loadPreview = useCallback(async (text: string, mode: 'answers' | 'freethink') => {
    try {
      const payload = await request<ReviewPayload>('/api/vetting', {
        action: 'transcript_preview',
        text,
        mode,
      });
      setReview((current) => ({ ...current, busy: false, payload, editing: false }));
    } catch (error) {
      setReview((current) => ({ ...current, busy: false }));
      Message.error(failMessage(error));
    }
  }, []);

  const openReview = useCallback(
    async (mode: 'answers' | 'freethink') => {
      if (!selected) return;
      setReview({ open: true, mode, text: selected.text || '', editing: false, busy: true });
      await loadPreview(selected.text || '', mode);
    },
    [loadPreview, selected]
  );

  const runReview = useCallback(
    async (options: { acceptAll: boolean; thenProcess: boolean }) => {
      if (!selected) return;
      setReview((current) => ({ ...current, busy: true }));
      try {
        const result = await request<{ applied?: { applied?: string[] }; accepted?: { applied?: string[] } }>(
          '/api/vetting',
          {
            action: 'transcript_apply',
            text: review.text,
            mode: review.mode,
            accept_all: options.acceptAll,
            then_process: options.thenProcess,
          }
        );
        const applied = result?.applied?.applied || [];
        const accepted = result?.accepted?.applied || [];
        Message.success(
          applied.length || accepted.length
            ? `Added to the vetting session: ${[...applied, ...accepted].join(', ')}.`
            : 'Applied to the vetting session.'
        );
        setReview({ open: false, mode: 'answers', text: '', editing: false, busy: false });
      } catch (error) {
        setReview((current) => ({ ...current, busy: false }));
        Message.error(failMessage(error));
      }
    },
    [review.mode, review.text, selected]
  );

const statusCopy =
    selected?.status === 'complete'
      ? 'Saved'
      : selected?.status === 'failed'
        ? 'Needs attention'
        : selected
          ? 'Processing'
          : '';

  return (
    <div className='relative h-full'>
      <div
        className={styles.shell}
        data-testid='transcription-page'
        onDragOver={(event) => {
          if (event.dataTransfer.types.includes('Files')) {
            event.preventDefault();
            setDragging(true);
          }
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <aside className={styles.sidebar} aria-label='Transcript library'>
          {/* Authoritative standalone IA (finding 6): the column keeps the donor's own title and a
              plain-text API Key entry — not a gear — because that is where a user looks for the
              transcription credential. */}
          <div className={styles.sidebarHeader}>
            <h1 className={styles.sidebarTitle}>Transcriptions</h1>
            <button
              type='button'
              className={styles.apiKeyAction}
              onClick={() => setSettingsOpen(true)}
              data-testid='transcription-settings'
            >
              API Key
            </button>
          </div>
          <div className={styles.sectionTitle}>Folders</div>
          <div className={styles.scrollArea}>
            {library.folders.length === 0 && (
              <div className={styles.rowMeta} style={{ padding: '2px 8px 6px' }}>
                Group recordings into folders — drag a transcript onto one.
              </div>
            )}
            {library.folders.map((folder) => {
              const children = visibleRecent.filter((item) => item.folder_id === folder.id);
              const open = expanded.has(folder.id);
              return (
                <div key={folder.id}>
                  <div
                    className={`${styles.folderRow} ${dropFolder === folder.id ? styles.dropTarget : ''}`}
                    {...folderDrop(folder.id)}
                    data-folder-id={folder.id}
                  >
                    <button
                      type='button'
                      className='border-none bg-transparent p-0 text-t-secondary'
                      aria-label={`${open ? 'Collapse' : 'Expand'} ${folder.name}`}
                      onClick={() =>
                        setExpanded((current) => {
                          const next = new Set(current);
                          if (next.has(folder.id)) next.delete(folder.id);
                          else next.add(folder.id);
                          return next;
                        })
                      }
                    >
                      {open ? '▾' : '▸'}
                    </button>
                    {folderEditing === folder.id ? (
                      <Input
                        size='small'
                        value={folderDraft}
                        onChange={setFolderDraft}
                        onBlur={() => void renameFolder(folder.id, folderDraft)}
                        onPressEnter={() => void renameFolder(folder.id, folderDraft)}
                        autoFocus
                        data-testid='folder-rename'
                      />
                    ) : (
                      <span className={styles.rowName} title={folder.name}>
                        {folder.name}
                      </span>
                    )}
                    <span className={styles.rowMeta}>{children.length}</span>
                    <button
                      type='button'
                      className='border-none bg-transparent p-0 text-t-secondary'
                      aria-label={`Rename ${folder.name}`}
                      onClick={() => {
                        setFolderEditing(folder.id);
                        setFolderDraft(folder.name);
                      }}
                    >
                      ✎
                    </button>
                    <button
                      type='button'
                      className='border-none bg-transparent p-0 text-t-secondary'
                      aria-label={`Delete ${folder.name}`}
                      onClick={() => void deleteFolder(folder)}
                    >
                      ✕
                    </button>
                  </div>
                  {open &&
                    children.map((item) => (
                      <button
                        key={item.id}
                        type='button'
                        draggable
                        onDragStart={(event) => onRowDragStart(event, item)}
                        className={`${styles.transcriptRow} ${selectedId === item.id ? styles.rowActive : ''}`}
                        style={{ paddingLeft: 26 }}
                        onClick={() => setSelectedId(item.id)}
                        data-testid='folder-transcript'
                      >
                        <span className={styles.rowName} title={item.name}>
                          {item.name}
                        </span>
                      </button>
                    ))}
                </div>
              );
            })}
            <div style={{ display: 'flex', gap: 6, padding: '4px 2px 6px' }}>
              <Input size='small' value={folderDraft} onChange={setFolderDraft} placeholder='New folder' data-testid='folder-name' />
              <Button size='small' onClick={() => void createFolder()} data-testid='folder-create'>
                Add
              </Button>
            </div>
          </div>
          <div className={styles.divider} />
          <div className={styles.sectionTitle}>Recent</div>
          <Input
            size='small'
            allowClear
            placeholder='Search transcripts'
            value={recentSearch}
            onChange={setRecentSearch}
            style={{ margin: '0 8px 6px', width: 'calc(100% - 16px)' }}
            data-testid='transcript-search'
          />
          <div className={styles.scrollArea} data-testid='recent-list'>
            {recent.length === 0 && (
              <div className={styles.rowMeta} style={{ padding: '2px 8px' }}>
                Nothing here yet.
              </div>
            )}
            {recent.length > 0 && visibleRecent.length === 0 && (
              <div className={styles.rowMeta} style={{ padding: '2px 8px' }}>
                No transcripts match that search.
              </div>
            )}
            {visibleRecent.map((item) => (
              <button
                key={item.id}
                type='button'
                draggable
                onDragStart={(event) => onRowDragStart(event, item)}
                className={`${styles.transcriptRow} ${selectedId === item.id ? styles.rowActive : ''}`}
                onClick={() => setSelectedId(item.id)}
                data-testid='transcript-row'
              >
                <span className={styles.rowName} title={item.name}>
                  {item.name}
                </span>
                <span className={styles.rowMeta}>
                  {item.status === 'complete' ? formatDuration(item.duration_ms) : item.status}
                </span>
              </button>
            ))}
          </div>
          {/* The connection state stays one quiet line; the entry point moved to the column header. */}
          <div className={styles.sidebarFooterNote} data-testid='transcription-mode'>
            {status?.label || 'Checking…'}
          </div>
        </aside>

        <main className={styles.workspace}>
          {loadError && <KelFailureCard error={loadError} onRetry={() => void refresh()} />}
          {/* Authoritative IA: actions sit top-right in the donor's order — Upload Audio · Record More ·
              Record — with Record last and primary. Record More is always present (disabled when there is
              nothing to append to) instead of appearing conditionally. */}
          <div className={styles.actionRow}>
            {recState === 'idle' && (
              <>
                <Button onClick={() => fileInputRef.current?.click()} data-testid='upload-button'>
                  Upload Audio
                </Button>
                <Button
                  disabled={selected?.source_type !== 'recording'}
                  onClick={() => {
                    if (selected) void beginRecording(selected.id);
                  }}
                  data-testid='record-more'
                >
                  Record More
                </Button>
                <Button type='primary' onClick={() => void beginRecording()} data-testid='record-button'>
                  Record
                </Button>
              </>
            )}
            <input
              ref={fileInputRef}
              type='file'
              accept='.mp3,.mp4,.wav,audio/*,video/mp4'
              style={{ display: 'none' }}
              data-testid='upload-input'
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadFile(file);
                event.target.value = '';
              }}
            />
            {progress && (
              <span className={styles.rowMeta} data-testid='progress-label' role='status'>
                {progress}
              </span>
            )}
          </div>

          {recState !== 'idle' && (
            <div className={styles.recordBar} data-testid='recording-bar' role='status' aria-live='polite'>
              <span className={styles.liveDot} />
              <strong style={{ fontSize: 13 }}>
                {recState === 'recording' ? `Recording ${formatDuration(seconds * 1000)}` : 'Finishing the transcript…'}
              </strong>
              {(liveText || '').trim() !== '' && (
                <span className='min-w-0 flex-1 truncate text-13px text-t-secondary' data-testid='live-text'>
                  {liveText}
                </span>
              )}
              {recState === 'recording' && (
                <>
                  <Button size='small' type='primary' onClick={() => void finishRecording(true)} data-testid='stop-button'>
                    Stop and save
                  </Button>
                  <Button size='small' onClick={() => void finishRecording(false)} data-testid='cancel-button'>
                    Cancel
                  </Button>
                </>
              )}
            </div>
          )}

          <div className={styles.workspaceScroll}>
            {!selected && (
              <KelEmpty
                title='Your transcripts live here'
                why='Record with the button above, or drop an MP3 or MP4 file anywhere on this page. Everything is saved automatically.'
                actionLabel='Upload audio'
                onAction={() => fileInputRef.current?.click()}
              />
            )}
            {selected && (
              <>
                <div className={styles.documentHeader}>
                  {renaming ? (
                    <Input
                      value={nameDraft}
                      onChange={setNameDraft}
                      onBlur={() => void saveName()}
                      onPressEnter={() => void saveName()}
                      autoFocus
                      style={{ maxWidth: 380 }}
                      data-testid='transcript-rename'
                    />
                  ) : (
                    <h2 className={styles.documentTitle} data-testid='transcript-name'>
                      {selected.name}
                    </h2>
                  )}
                  {/* Saved / recording state reads beside the title, as in the standalone app. */}
                  <span className={styles.documentStatus} data-testid='transcript-status'>
                    {statusCopy}
                  </span>
                  <span className={styles.grow} />
                  <button
                    type='button'
                    className={styles.secondaryAction}
                    onClick={() => {
                      setRenaming(true);
                      setNameDraft(selected.name);
                    }}
                    data-testid='rename-button'
                  >
                    Rename
                  </button>
                </div>
                <div className={styles.rowMeta}>
                  {selected.source_type === 'recording' ? 'Recording' : `Upload: ${selected.source_filename || 'audio'}`}
                  {' · '}
                  {formatDuration(selected.duration_ms)}
                  {' · '}
                  {formatWhen(selected.created)}
                  {selected.folder_id
                    ? ` · ${library.folders.find((folder) => folder.id === selected.folder_id)?.name || 'Folder'}`
                    : ''}
                </div>
                <Select
                  size='small'
                  value={selected.folder_id || ''}
                  onChange={(value) => void assignTo((value as string) || null)}
                  style={{ maxWidth: 260 }}
                  options={[
                    { value: '', label: 'Recent Transcriptions (unfiled)' },
                    ...library.folders.map((folder) => ({ value: folder.id, label: folder.name })),
                  ]}
                  data-testid='move-select'
                />
                <p className={styles.transcriptText} data-testid='transcript-text'>
                  {(selected.text || '').trim() || '(No speech was recognized.)'}
                </p>
                {/* Authoritative IA: the donor's four actions come first and keep the weight; Kel's
                    additions stay available but quieter, so the document footer still reads as before. */}
                <div className={styles.documentActions}>
                  <Button onClick={() => void copyTranscript()} data-testid='copy-transcript'>
                    Copy Transcript
                  </Button>
                  <Button onClick={downloadText} data-testid='download-txt'>
                    Download Transcript
                  </Button>
                  <Button disabled={!selected.has_audio} onClick={() => void downloadAudio()} data-testid='download-audio'>
                    Download Audio
                  </Button>
                  <Button
                    disabled={library.transcripts.length < 2}
                    onClick={() => {
                      setCombineSource('');
                      setCombineOpen(true);
                    }}
                    data-testid='combine-open'
                  >
                    Combine
                  </Button>
                </div>
                <div className={styles.secondaryActions}>
                  <button type='button' className={styles.secondaryAction} onClick={sendToChat} data-testid='send-to-chat'>
                    Send to chat
                  </button>
                  <button
                    type='button'
                    className={styles.secondaryAction}
                    onClick={() => void openReview('answers')}
                    data-testid='use-vetting'
                  >
                    Use as vetting answers
                  </button>
                  <button
                    type='button'
                    className={styles.secondaryAction}
                    onClick={() => void openReview('freethink')}
                    data-testid='think-out-loud'
                  >
                    Think out loud
                  </button>
                  <button
                    type='button'
                    className={styles.dangerAction}
                    onClick={() => removeTranscript(selected)}
                    data-testid='delete-transcript'
                  >
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </main>
      </div>

      {dragging && <div className={styles.dropOverlay}>Drop audio or video to transcribe</div>}

      {/* The user's explicit decision: the standalone app's key sheet, in Kel's words — a plain
          "Meta API key" modal with no helper paragraph under the button. */}
      <Modal
        title='Meta API key'
        visible={settingsOpen}
        footer={null}
        onCancel={() => setSettingsOpen(false)}
        style={{ maxWidth: 480 }}
      >
        <p className={styles.keySheetBody}>
          {status?.has_key
            ? 'Replace the key used for Muse transcription.'
            : 'Add a Model API key to begin transcribing.'}
        </p>
        {status && !status.has_key && (
          <div className={styles.keySheetForm}>
            <label className={styles.keySheetLabel} htmlFor='meta-api-key'>
              API key
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <Input.Password
                id='meta-api-key'
                value={keyDraft}
                onChange={setKeyDraft}
                placeholder='Paste your Meta Model API key'
                data-testid='key-input'
              />
              <Button type='primary' onClick={() => void saveKey()} disabled={!keyDraft.trim()} data-testid='key-save'>
                Save and Verify
              </Button>
            </div>
          </div>
        )}
        {status?.has_key && (
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <Button onClick={() => void clearKey()} data-testid='key-clear'>
              Disconnect the key
            </Button>
          </div>
        )}
      </Modal>

      <Modal
        title='Merge another transcript into this one'
        visible={combineOpen}
        footer={null}
        onCancel={() => setCombineOpen(false)}
        style={{ maxWidth: 480 }}
      >
        <p style={{ marginBottom: 8 }}>
          The other transcript's text and audio join this one, and it leaves the list.
        </p>
        <Select
          value={combineSource}
          onChange={(value) => setCombineSource((value as string) || '')}
          placeholder='Choose a transcript'
          style={{ width: '100%' }}
          options={library.transcripts
            .filter((row) => row.id !== selected?.id)
            .map((row) => ({ value: row.id, label: `${row.name || 'Untitled'} · ${formatWhen(row.created)}` }))}
          data-testid='combine-select'
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
          <Button onClick={() => setCombineOpen(false)}>Cancel</Button>
          <Button type='primary' disabled={!combineSource} onClick={() => void runCombine()} data-testid='combine-confirm'>
            Merge
          </Button>
        </div>
      </Modal>

      <Modal
        title='Use this transcript as vetting answers'
        visible={review.open}
        footer={null}
        onCancel={() => setReview({ open: false, mode: 'answers', text: '', editing: false, busy: false })}
        style={{ maxWidth: 640 }}
      >
        {review.busy && <p>Checking the transcript…</p>}
        {!review.busy && review.payload && (
          <>
            {review.editing ? (
              <Input.TextArea
                value={review.text}
                onChange={(value) => setReview((current) => ({ ...current, text: value }))}
                autoSize={{ minRows: 6 }}
                data-testid='review-edit-text'
              />
            ) : (
              <>
                {review.payload.preview.length === 0 && (
                  <p>
                    Kel did not find answers in this transcript yet. Try naming questions (“12: A”) or use Think
                    out loud.
                  </p>
                )}
                {review.payload.preview.length > 0 && (
                  <>
                    <p style={{ margin: '8px 0 4px', fontWeight: 600 }}>
                      I pulled these answers from your transcript:
                    </p>
                    <ul style={{ paddingLeft: 18 }} data-testid='review-list'>
                      {review.payload.preview.map((line) => (
                        <li key={line.question_id} style={{ marginBottom: 4 }}>
                          <strong>{line.question_id.replace('Q', '')}</strong> — {line.answer}
                          {line.note ? (
                            <>
                              {' '}
                              · <em>{line.note}</em>
                            </>
                          ) : null}
                          {line.confidence !== 'EXPLICIT' ? (
                            <span className={styles.rowMeta}> (check this one)</span>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {(review.payload.proposals || []).length > 0 && (
                  <p className={styles.rowMeta} data-testid='review-proposals'>
                    Suggested matches to confirm:{' '}
                    {(review.payload.proposals || []).map((item) => `${item.question_id.replace('Q', '')} → ${item.option}`).join(', ')}
                  </p>
                )}
                {review.payload.potential_conflicts.length > 0 && (
                  <p className={styles.rowMeta} data-testid='review-conflict'>
                    Possible conflict: {review.payload.potential_conflicts[0].statement}
                  </p>
                )}
                {review.mode === 'freethink' && review.payload.buckets && (
                  <>
                    {(['requirements', 'concerns', 'unresolved'] as const).map(
                      (key) =>
                        review.payload!.buckets![key].length > 0 && (
                          <div key={key} style={{ marginTop: 8 }}>
                            <strong style={{ fontSize: 13 }}>
                              {key === 'requirements'
                                ? 'Requirements heard'
                                : key === 'concerns'
                                  ? 'Concerns heard'
                                  : 'Still open'}
                            </strong>
                            <ul style={{ paddingLeft: 18 }}>
                              {review.payload!.buckets![key].map((line) => (
                                <li key={line}>{line}</li>
                              ))}
                            </ul>
                          </div>
                        )
                    )}
                  </>
                )}
              </>
            )}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12, flexWrap: 'wrap' }}>
              <Button onClick={() => setReview({ open: false, mode: 'answers', text: '', editing: false, busy: false })}>
                Close
              </Button>
              <Button onClick={() => setReview((current) => ({ ...current, editing: true }))} data-testid='review-edit'>
                Edit
              </Button>
              {review.editing && (
                <Button onClick={() => void loadPreview(review.text, review.mode)} data-testid='review-recheck'>
                  Check again
                </Button>
              )}
              <Button
                onClick={() => void runReview({ acceptAll: true, thenProcess: false })}
                data-testid='review-accept'
              >
                Accept all
              </Button>
              <Button
                type='primary'
                onClick={() => void runReview({ acceptAll: false, thenProcess: true })}
                data-testid='review-process'
              >
                Process batch
              </Button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
};

export default TranscriptionPage;
