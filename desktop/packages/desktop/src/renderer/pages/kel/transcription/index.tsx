/**
 * Transcription — Kel's first-class audio input source.
 *
 * Ported behaviour from the donor app (folders above recents, drag-to-folder, record/upload,
 * rename/copy/download, append recording) with Kel-native surfaces: provider machinery stays
 * behind the engine's `/api/transcription` action family, and transcripts can be sent to chat or
 * routed into a live Vetting Session through the existing ingestion service.
 */
import AionModal from '@renderer/components/base/AionModal';
import { KelButton } from '@renderer/components/kel/KelPrimitives';
import { kelRequest as request } from '@renderer/components/kel/kelApi';
import rambleBrand from '@renderer/assets/figma/kel-mark.png';
import transcriptFileIcon from '@renderer/assets/figma/refresh/transcript-file.svg';
import transcriptAudioIcon from '@renderer/assets/figma/refresh/transcript-audio.svg';
import transcriptCombineIcon from '@renderer/assets/figma/refresh/transcript-combine.svg';
import transcriptMicIcon from '@renderer/assets/figma/refresh/transcript-mic.svg';
import transcriptPlusIcon from '@renderer/assets/figma/refresh/transcript-plus.svg';
import transcriptCheckIcon from '@renderer/assets/figma/refresh/transcript-check.svg';
import transcriptSettingsIcon from '@renderer/assets/figma/refresh/transcript-settings.svg';
import rambleMobileMenuIcon from '@renderer/assets/figma/refresh/ramble-mobile-menu.svg';
import rambleMobileFolderIcon from '@renderer/assets/figma/refresh/ramble-mobile-folder.svg';
import rambleMobileMicIcon from '@renderer/assets/figma/refresh/ramble-mobile-mic.svg';
import rambleMobilePlusIcon from '@renderer/assets/figma/refresh/ramble-mobile-plus.svg';
import rambleMobileBackIcon from '@renderer/assets/figma/refresh/ramble-mobile-back.svg';
import rambleMobileMoreIcon from '@renderer/assets/figma/refresh/ramble-mobile-more.svg';
import rambleMobileEditIcon from '@renderer/assets/figma/refresh/ramble-mobile-edit.svg';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Button, Input, Message, Modal, Select } from '@arco-design/web-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { KelCard, KelEmpty, KelStatusChip } from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { decodeFileToWav, friendlyMicError, startMicCapture, type MicCapture } from '@renderer/utils/transcription/audio';
import styles from './index.module.css';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';
import KelBottomNav from '@renderer/components/kel/KelBottomNav';
import rambleIcon from '@renderer/assets/figma/refresh/ramble_hero.svg';

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
  const embedded = useLocation().pathname === '/transcription/library';
  const layout = useLayoutContext();
  const [creatingFolder, setCreatingFolder] = useState(false);
  const folderCreatePending = useRef(false);
  const folderRenamePending = useRef(false);
  const cancelFolderRename = useRef(false);
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
  useEffect(() => {
    if (!review.open || !layout?.isMobile) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setReview({ open: false, mode: 'answers', text: '', editing: false, busy: false });
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [review.open, layout?.isMobile]);
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
      if (embedded) {
        setSelectedId((current) =>
          current && data.transcripts.some((item) => item.id === current)
            ? current
            : [...data.transcripts].sort((a, b) => b.created - a.created)[0]?.id || null
        );
      }
      setLoadError(null);
    } catch (error) {
      setLoadError(error);
    }
  }, [embedded]);

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
    if (folderCreatePending.current) return;
    folderCreatePending.current = true;
    setCreatingFolder(true);
    try {
      const folder = await transcription<Folder>({ action: 'folder_create', name: 'New Folder' });
      setLibrary((current) => ({ ...current, folders: [...current.folders, folder] }));
      setExpanded((current) => new Set(current).add(folder.id));
      setFolderDraft(folder.name);
      setFolderEditing(folder.id);
    } catch (error) {
      Message.error(failMessage(error));
    } finally {
      folderCreatePending.current = false;
      setCreatingFolder(false);
    }
  }, []);

  const renameFolder = useCallback(
    async (id: string, name: string) => {
      if (folderRenamePending.current) return;
      const trimmed = name.trim();
      if (!trimmed || library.folders.find((folder) => folder.id === id)?.name === trimmed) {
        setFolderEditing(null);
        return;
      }
      folderRenamePending.current = true;
      try {
        await transcription({ action: 'folder_rename', id, name: trimmed });
        setLibrary((current) => ({ ...current, folders: current.folders.map((folder) => folder.id === id ? { ...folder, name: trimmed } : folder) }));
        setFolderEditing((current) => current === id ? null : current);
      } catch (error) {
        Message.error(failMessage(error));
      } finally {
        folderRenamePending.current = false;
      }
    },
    [library.folders]
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
      if (layout?.isMobile) Message.success('Muse is connected. New recordings and uploads use it.');
      else { const readiness = await transcription<ProviderStatus>({ action: 'status' }); setStatus(readiness); Message.success(readiness.live_capable ? 'Key saved. Transcription is ready to test.' : `Key saved. ${readiness.detail}`); }
      await refresh();
    } catch (error) {
      Message.error(failMessage(error));
    }
  }, [keyDraft, refresh, layout?.isMobile]);

  const clearKey = useCallback(async () => {
    try {
      await transcription({ action: 'clear_key' });
      setSettingsOpen(false);
      Message.success(layout?.isMobile ? 'Back to practice mode.' : 'Kel’s saved key was removed.');
      await refresh();
    } catch (error) {
      Message.error(failMessage(error));
    }
  }, [refresh, layout?.isMobile]);

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
        className={`${styles.shell} kel-shell-ramble${embedded ? ' kel-shell-ramble--embedded' : ''}${!embedded && (selected || recState !== 'idle') ? ' kel-shell-ramble--detail' : ''}${!embedded && selected && recState === 'idle' ? ' kel-shell-ramble--selected' : ''}`}
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
        {!embedded && <aside className={styles.sidebar} aria-label='Transcript library'>
          <div className={styles.brandRow}>
            <div className='kel-shell-tool-brand'><img src={rambleBrand} alt='' width={30} height={31} /><span>Kel</span></div>
            <div className={styles.navigation} ref={layout?.setTitlebarMenuHost} data-testid='ramble-navigation' />
          </div>
          <div className='kel-shell-ramble-mobile-header'>
            <div><button type='button' className='kel-shell-ramble-menu-button' aria-label='Open navigation' onClick={() => window.dispatchEvent(new Event('kel-open-navigation'))}><img src={rambleMobileMenuIcon} alt='' /></button><span className='kel-shell-ramble-mobile-title'>Ramble</span></div>
            <button type='button' className='kel-shell-ramble-new-button' aria-label='New recording' disabled={recState !== 'idle'} onClick={() => void beginRecording()}><img src={rambleMobilePlusIcon} alt='' /></button>
          </div>
          <button type='button' className='kel-shell-new-chat kel-shell-ramble-new' onClick={() => void beginRecording()} disabled={recState !== 'idle'}>
            <span className='kel-shell-ramble-hero-icon'><img src={rambleIcon} alt='' /></span><span>New Recording</span>
          </button>
          <input
            type='search'
            className={`${styles.searchInput} kel-shell-ramble-search`}
            aria-label='Search transcripts'
            placeholder='Search Transcripts'
            value={recentSearch}
            onChange={(event) => setRecentSearch(event.target.value)}
            data-testid='transcript-search'
          />
          <div className={styles.foldersHeader}>
            <h2 className={styles.sectionTitle}>Folders</h2>
            <button type='button' className={styles.addFolder} aria-label='New folder' title='New folder' disabled={creatingFolder} onClick={() => void createFolder()} data-testid='folder-create'>+</button>
          </div>
          <div className={`${styles.scrollArea} kel-shell-ramble-folders`}>
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
                    className={`${styles.folderRow} kel-shell-ramble-folder-row ${dropFolder === folder.id ? styles.dropTarget : ''}`}
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
                    <img className='kel-shell-ramble-row-icon' src={rambleMobileFolderIcon} alt='' />
                    {folderEditing === folder.id ? (
                      <input
                        className={styles.renameInput}
                        aria-label='Folder name'
                        value={folderDraft}
                        onChange={(event) => setFolderDraft(event.target.value)}
                        onFocus={(event) => { cancelFolderRename.current = false; event.target.select(); }}
                        onBlur={() => {
                          if (!cancelFolderRename.current) void renameFolder(folder.id, folderDraft);
                        }}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') event.currentTarget.blur();
                          if (event.key === 'Escape') {
                            cancelFolderRename.current = true;
                            setFolderEditing(null);
                          }
                        }}
                        autoFocus
                        data-testid='folder-rename'
                      />
                    ) : (
                      <span className={styles.rowName} title={folder.name}>
                        {folder.name}<small className='kel-shell-ramble-mobile-meta'>{children.length} {children.length === 1 ? 'transcript' : 'transcripts'}</small>
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
          </div>
          <div className={styles.divider} />
          <div className={`${styles.sectionTitle} kel-shell-ramble-recordings-label`}><span className='kel-shell-ramble-desktop-label'>Recordings</span><span className='kel-shell-ramble-mobile-label'>Recordings</span></div>
          <div className={`${styles.scrollArea} kel-shell-ramble-recordings`} data-testid='recent-list'>
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
                <img className='kel-shell-ramble-row-icon' src={rambleMobileMicIcon} alt='' />
                <span className={styles.rowName} title={item.name}>
                  {item.name}<small className='kel-shell-ramble-mobile-meta'>{formatWhen(item.created)} · {item.status === 'complete' ? (item.duration_ms && item.duration_ms >= 60000 ? `${Math.round(item.duration_ms / 60000)} min` : formatDuration(item.duration_ms)) : item.status}</small>
                </span>
                <span className={styles.rowMeta}>
                  {item.status === 'complete' ? formatDuration(item.duration_ms) : item.status}
                </span>
              </button>
            ))}
          </div>
          <button type='button' className='kel-shell-ramble-mobile-record' disabled={recState !== 'idle'} onClick={() => void beginRecording()}>New recording</button>

          <div className='kel-shell-ramble-bottom'>
            <KelBottomNav />
          </div>

        </aside>}

        <main className={styles.workspace}>
          {!embedded && selected && recState === 'idle' && <button type='button' className='kel-shell-ramble-mobile-back' onClick={() => setSelectedId(undefined)}><img src={rambleMobileBackIcon} alt='' /><span>{selected.name}</span></button>}
          {loadError && <KelFailureCard error={loadError} onRetry={() => void refresh()} />}
          <header className={styles.pageHeader}>
            <h1 className='kel-h1'>{embedded ? 'Transcriptions' : 'Ramble'}</h1>
            <div className={styles.actionRow}>
              {!embedded && <Button onClick={() => setSettingsOpen(true)} data-testid='transcription-settings'>API Key</Button>}
              {recState === 'idle' && (
                <>
                  <Button className='kel-transcription-upload' icon={<img src={transcriptFileIcon} alt='' width='16' height='16' />} onClick={() => fileInputRef.current?.click()} data-testid='upload-button'>
                    Upload Audio
                  </Button>
                  <Button
                    className='kel-transcription-record-more'
                    icon={<img src={transcriptPlusIcon} alt='' width='16' height='16' />}
                    disabled={selected?.source_type !== 'recording'}
                    onClick={() => {
                      if (selected) void beginRecording(selected.id);
                    }}
                    data-testid='record-more'
                  >
                    Record More
                  </Button>
                  <Button type='primary' className='kel-transcription-record' icon={<img src={transcriptMicIcon} alt='' width='16' height='16' />} onClick={() => void beginRecording()} data-testid='record-button'>
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
          </header>

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
                <div className={`${styles.documentHeader} kel-shell-transcript-header`}>
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
                    <h2 className={styles.documentTitle} data-testid='transcript-name' onDoubleClick={() => { setRenaming(true); setNameDraft(selected.name); }}>
                      {selected.name}
                    </h2>
                  )}
                  {/* Saved / recording state reads beside the title, as in the standalone app. */}
                  <span className={styles.grow} />
                  <span className={styles.documentStatus} data-testid='transcript-status'>
                    <img src={transcriptCheckIcon} alt='' width='14' height='14' /> {statusCopy}<span className='kel-shell-ramble-mobile-duration'>{selected.duration_ms ? ` · ${selected.duration_ms >= 60000 ? Math.round(selected.duration_ms / 60000) + ' min' : formatDuration(selected.duration_ms)}` : ''}</span> {layout?.isMobile || embedded ? <img src={transcriptSettingsIcon} alt='' width='14' height='14' /> : <details className='kel-ramble-desktop-document-menu'>
                      <summary aria-label='Transcript actions'><img src={transcriptSettingsIcon} alt='' width='14' height='14' /></summary>
                      <div><button type='button' onClick={() => { setRenaming(true); setNameDraft(selected.name); }}>Rename</button><button type='button' onClick={() => void openReview('freethink')}>Vetting answers</button></div>
                    </details>}
                  </span>
                </div>
                <p className={styles.transcriptText} data-testid='transcript-text'>
                  {(selected.text || '').trim() || '(No speech was recognized.)'}
                </p>
                {/* Authoritative IA: the donor's four actions come first and keep the weight; Kel's
                    additions stay available but quieter, so the document footer still reads as before. */}
                <div className={styles.documentActions}>
                  <Button icon={<img src={transcriptFileIcon} alt='' width='16' height='16' />} onClick={() => void copyTranscript()} data-testid='copy-transcript'>
                    <span className='kel-shell-ramble-desktop-label'>Copy Transcript</span><span className='kel-shell-ramble-mobile-label'>Copy transcript</span>
                  </Button>
                  <Button icon={<img src={transcriptFileIcon} alt='' width='16' height='16' />} onClick={downloadText} data-testid='download-txt'>
                    <span className='kel-shell-ramble-desktop-label'>Download Transcript</span><span className='kel-shell-ramble-mobile-label'>Download</span>
                  </Button>
                  <Button icon={<img src={transcriptAudioIcon} alt='' width='16' height='16' />} disabled={!selected.has_audio} onClick={() => void downloadAudio()} data-testid='download-audio'>
                    <span className='kel-shell-ramble-desktop-label'>Download Audio</span><span className='kel-shell-ramble-mobile-label'>Audio</span>
                  </Button>
                  <Button
                    icon={<img src={transcriptCombineIcon} alt='' width='16' height='16' />}
                    className='kel-transcription-combine'
                    disabled={library.transcripts.length < 2}
                    onClick={() => {
                      setCombineSource('');
                      setCombineOpen(true);
                    }}
                    data-testid='combine-open'
                  >
                    Combine
                  </Button>
                  {!embedded && !layout?.isMobile && <Button className='kel-ramble-footer-record-more' icon={<img src={transcriptPlusIcon} alt='' width='16' height='16' />} disabled={recState !== 'idle' || selected.source_type !== 'recording'} onClick={() => void beginRecording(selected.id)} data-testid='footer-record-more'>Record More</Button>}
                  {!embedded && <details className='kel-shell-ramble-more'>
                    <summary aria-label='More transcript actions'><img src={rambleMobileMoreIcon} alt='' /></summary>
                    <div>
                      <button type='button' onClick={() => { setRenaming(true); setNameDraft(selected.name); }}>Rename</button>
                      <button type='button' onClick={() => fileInputRef.current?.click()}>Upload Audio</button>
                      <button type='button' onClick={() => setSettingsOpen(true)}>API Key</button>
                      <button type='button' disabled={selected.source_type !== 'recording'} onClick={() => void beginRecording(selected.id)}>Record More</button>
                      <button type='button' disabled={library.transcripts.length < 2} onClick={() => { setCombineSource(''); setCombineOpen(true); }}>Combine</button>
                      <button type='button' onClick={() => void openReview('freethink')} data-testid='open-vetting-review'>Vetting answers</button>
                    </div>
                  </details>}
                </div>

              </>
            )}
          </div>
        </main>
      </div>

      {dragging && <div className={styles.dropOverlay}>Drop audio or video to transcribe</div>}

      {/* The user's explicit decision: the standalone app's key sheet, in Kel's words — a plain
          "Meta API key" modal with no helper paragraph under the button. */}
      {!layout?.isMobile ? <AionModal visible={settingsOpen} className='kel-ramble-key-modal' variant='standard'
        header={{ title: 'Meta API key', subtitle: 'Ramble uses it to transcribe. It stays on this computer.', showClose: false }}
        footer={null} closable={false} onCancel={() => { setSettingsOpen(false); setKeyDraft(''); }} focusLock autoFocus style={{ width: 480 }}>
        <div className='kel-ramble-key-body'>
          <Input.Password id='meta-api-key' value={keyDraft} onChange={setKeyDraft} placeholder='Paste your Meta Model API key' aria-label='Meta API key' data-testid='key-input' />
          {status?.has_key && <p>A key is available. A new one replaces Kel’s saved key.</p>}
          <div className='kel-ramble-dialog-actions'>
            {status?.has_key && <button type='button' className='kel-btn kel-ramble-key-disconnect' onClick={() => void clearKey()} data-testid='key-clear'>Disconnect the key</button>}
            <span className='kel-grow' />
            <KelButton variant='quiet' onClick={() => { setSettingsOpen(false); setKeyDraft(''); }}>Cancel</KelButton>
            <button type='button' className='kel-btn kel-btn--primary' disabled={!keyDraft.trim()} onClick={() => void saveKey()} data-testid='key-save'>Save and Verify</button>
          </div>
        </div>
      </AionModal> : <>
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
      </>}
      {layout?.isMobile && review.open && createPortal(
        <div className='kel-ramble-vetting-layer'>
          <button type='button' className='kel-ramble-vetting-scrim' aria-label='Close vetting answers' onClick={() => setReview({ open: false, mode: 'answers', text: '', editing: false, busy: false })} />
          <section className='kel-ramble-vetting-sheet' role='dialog' aria-modal='true' aria-labelledby='kel-ramble-vetting-title' data-testid='ramble-vetting-sheet'>
            <div className='kel-ramble-vetting-handle' />
            <h2 id='kel-ramble-vetting-title'>Vetting answers</h2>
            {review.busy ? <p className='kel-ramble-vetting-message'>Checking the transcript…</p> : review.editing ? (
              <div className='kel-ramble-vetting-edit'>
                <label htmlFor='kel-ramble-vetting-text'>Transcript</label>
                <textarea id='kel-ramble-vetting-text' value={review.text} onChange={(event) => setReview((current) => ({ ...current, text: event.target.value }))} data-testid='review-edit-text' />
                <button type='button' onClick={() => void loadPreview(review.text, review.mode)} data-testid='review-recheck'>Check again</button>
              </div>
            ) : review.payload ? (
              <>
                <div className='kel-ramble-vetting-content'>
                  {(['requirements', 'concerns', 'unresolved'] as const).map((key) => {
                    const lines = review.payload?.buckets?.[key] || [];
                    if (!lines.length) return null;
                    return <div className='kel-ramble-vetting-group' key={key}>
                      <h3>{key === 'requirements' ? 'Requirements heard' : key === 'concerns' ? 'Concerns heard' : 'Still open'}</h3>
                      {lines.map((line) => <div className='kel-ramble-vetting-row' key={line}>
                        <span className='kel-ramble-vetting-dot' aria-hidden='true' />
                        <span>{line}</span>
                        <button type='button' aria-label={`Edit ${line}`} onClick={() => setReview((current) => ({ ...current, editing: true }))}><img src={rambleMobileEditIcon} alt='' /></button>
                      </div>)}
                    </div>;
                  })}
                  {review.payload.preview.length > 0 && <div className='kel-ramble-vetting-group'><h3>Answers heard</h3>{review.payload.preview.map((line) => <div className='kel-ramble-vetting-row' key={line.question_id}><span className='kel-ramble-vetting-dot' aria-hidden='true' /><span>{line.question_id.replace('Q', '')}: {line.answer}</span><button type='button' aria-label={`Edit answer ${line.question_id}`} onClick={() => setReview((current) => ({ ...current, editing: true }))}><img src={rambleMobileEditIcon} alt='' /></button></div>)}</div>}
                  {!review.payload.buckets?.requirements.length && !review.payload.buckets?.concerns.length && !review.payload.buckets?.unresolved.length && !review.payload.preview.length && <p className='kel-ramble-vetting-message'>Kel did not find answers in this transcript yet.</p>}
                  <button type='button' className='kel-ramble-vetting-process' onClick={() => void runReview({ acceptAll: false, thenProcess: true })} data-testid='review-process'>Process batch</button>
                </div>
                <div className='kel-ramble-vetting-footer'>
                  <button type='button' className='kel-ramble-vetting-accept' onClick={() => void runReview({ acceptAll: true, thenProcess: false })} data-testid='review-accept'>Accept all</button>
                  <button type='button' className='kel-ramble-vetting-recheck' onClick={() => void loadPreview(review.text, review.mode)} data-testid='review-recheck'>Check again</button>
                </div>
              </>
            ) : <p className='kel-ramble-vetting-message'>Open a design vetting session in chat to review this transcript.</p>}
          </section>
        </div>, document.body
      )}

      {!layout?.isMobile ? <AionModal visible={combineOpen} className='kel-ramble-merge-modal' variant='standard'
        header={{ title: 'Merge a transcript into this one', showClose: false }} footer={null} closable={false}
        onCancel={() => setCombineOpen(false)} focusLock autoFocus style={{ width: 520 }}>
        <div className='kel-ramble-merge-body'>
          <p>Choose a transcript</p>
          <div className='kel-ramble-merge-list' role='radiogroup' aria-label='Choose a transcript'>
            {library.transcripts.filter(row => row.id !== selected?.id).map(row => <button key={row.id} type='button' role='radio' aria-checked={combineSource === row.id} onKeyDown={(event) => { const direction = ['ArrowDown', 'ArrowRight'].includes(event.key) ? 1 : ['ArrowUp', 'ArrowLeft'].includes(event.key) ? -1 : 0; if (!direction) return; event.preventDefault(); const rows = library.transcripts.filter(item => item.id !== selected?.id); const next = (rows.findIndex(item => item.id === row.id) + direction + rows.length) % rows.length; setCombineSource(rows[next].id); event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('button')[next]?.focus(); }} onClick={() => setCombineSource(row.id)}>
              <img src={transcriptMicIcon} alt='' /><span>{row.name || 'Untitled'}</span><small>{formatWhen(row.created)}{row.duration_ms ? ` · ${formatDuration(row.duration_ms)}` : ''}</small><span className='kel-ramble-merge-check' aria-hidden='true'>{combineSource === row.id ? '✓' : ''}</span>
            </button>)}
          </div>
          <p>The chosen transcript’s text and audio are added to the end of this one. It then leaves the list.</p>
          <div className='kel-ramble-dialog-actions'>
            <KelButton variant='quiet' onClick={() => setCombineOpen(false)}>Cancel</KelButton>
            <button type='button' className='kel-btn kel-btn--primary' disabled={!combineSource} onClick={() => void runCombine()} data-testid='combine-confirm'>Merge</button>
          </div>
        </div>
      </AionModal> : <>
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

      </>}
      {!layout?.isMobile && <AionModal
        className='kel-ramble-vetting-modal' variant='standard'
        header={{ title: 'Use this transcript as vetting answers', subtitle: review.busy ? 'Checking the transcript…' : review.payload ? 'I pulled these answers from your transcript. Review them before applying.' : 'Open a design vetting session in chat to review this transcript.', showClose: false }}
        closable={false} focusLock autoFocus
        visible={review.open}
        footer={null}
        onCancel={() => setReview({ open: false, mode: 'answers', text: '', editing: false, busy: false })}
        style={{ width: 620 }}
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
                {review.payload.preview.length === 0 && !(review.mode === 'freethink' && review.payload.buckets && Object.values(review.payload.buckets).some(lines => lines.length > 0)) && (
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
                            <span className='kel-ramble-vetting-flag'>Check this one</span>
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
                          <div key={key} className='kel-ramble-desktop-vetting-group'>
                            <strong>
                              {key === 'requirements'
                                ? 'Requirements heard'
                                : key === 'concerns'
                                  ? 'Concerns heard'
                                  : 'Still open'}
                            </strong>
                            <ul style={{ paddingLeft: 18 }}>
                              {review.payload!.buckets![key].map((line) => (
                                <li key={line}><span>{line}</span><button type='button' aria-label={`Edit transcript for: ${line}`} onClick={() => setReview(current => ({ ...current, editing: true }))}><img src={rambleMobileEditIcon} alt='' /></button></li>
                              ))}
                            </ul>
                          </div>
                        )
                    )}
                  </>
                )}
              </>
            )}
            <div className='kel-ramble-desktop-vetting-actions'>
              {!review.editing && !review.payload.buckets && <Button onClick={() => setReview(current => ({ ...current, editing: true }))} data-testid='review-edit'>Edit transcript</Button>}
              <Button onClick={() => void loadPreview(review.text, review.mode)} data-testid='review-recheck'>Check again</Button>
              <Button type='primary' onClick={() => void runReview({ acceptAll: false, thenProcess: true })} data-testid='review-process'>Process batch</Button>
              <Button onClick={() => void runReview({ acceptAll: true, thenProcess: false })} data-testid='review-accept'>Accept all</Button>
            </div>
          </>
        )}
      </AionModal>}
    </div>
  );
};

export default TranscriptionPage;
