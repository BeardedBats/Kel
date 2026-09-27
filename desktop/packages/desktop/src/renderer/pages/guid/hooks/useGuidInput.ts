/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { GENERAL_PROJECT_ID, announceProjectsChanged, setActiveProject, useProjects } from '@renderer/components/kel/activeProject';
import { kelProjects } from '@renderer/components/kel/kelApi';
import { type ChatFileRef, chatFileRefPath, localFileRef, uploadFileRef } from '@/common/types/chatFile';
import { useDragUpload } from '@/renderer/hooks/file/useDragUpload';
import { usePasteService } from '@/renderer/hooks/file/usePasteService';
import { allSupportedExts, type FileMetadata } from '@/renderer/services/FileService';
import { measureCaretTop, scrollCaretToLastLine } from '../utils/caretUtils';
import { readDraftText, writeDraftText } from '@/renderer/hooks/chat/useSendBoxDraft';
import { useCallback, useEffect, useState } from 'react';

/** The Home (new chat) composer's draft id in the shared draft store (CH-6, JR-43). */
export const HOME_DRAFT_ID = 'kel-home-new-chat';

export type GuidInputResult = {
  input: string;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  files: ChatFileRef[];
  setFiles: React.Dispatch<React.SetStateAction<ChatFileRef[]>>;
  /** The folder of the project a new chat starts in ('' when that project has no folder). */
  dir: string;
  /** D-54: the project a new chat starts in — the active project, or General for "All projects". */
  projectId: string;
  isInputFocused: boolean;
  loading: boolean;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  handleFilesPasted: (pastedFiles: FileMetadata[]) => void;
  /** Device uploads (blob → managed dir): sent as `upload` refs. */
  handleFilesUploaded: (uploadedPaths: string[]) => void;
  /** Backend-machine picker paths (native/server-fs): sent as `local` refs. */
  handleFilesPicked: (pickedPaths: string[]) => void;
  handleRemoveFile: (targetPath: string) => void;
  handleTextareaFocus: () => void;
  handleTextareaBlur: () => void;
  onPaste: ReturnType<typeof usePasteService>['onPaste'];
  isFileDragging: boolean;
  dragHandlers: ReturnType<typeof useDragUpload>['dragHandlers'];
};

type UseGuidInputOptions = {
  locationState: { workspace?: string } | null;
};

/**
 * Hook that manages input state, file handling, and drag/paste for the Guid page.
 */
export const useGuidInput = ({ locationState }: UseGuidInputOptions): GuidInputResult => {
  // CH-6: unsent Home text survives navigation and restart; sending clears the input, which clears
  // the stored draft with it.
  const [input, setInput] = useState(() => readDraftText(HOME_DRAFT_ID));
  useEffect(() => {
    writeDraftText(HOME_DRAFT_ID, input);
  }, [input]);
  const [files, setFiles] = useState<ChatFileRef[]>([]);
  // D-54: new chats start in the engine's active project (General when all projects are shown);
  // the folder is that project's own, never a separate per-page choice.
  const { newChatProject } = useProjects();
  const dir = newChatProject?.root ?? '';
  const projectId = newChatProject?.id ?? GENERAL_PROJECT_ID;
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [loading, setLoading] = useState(false);

  // A caller that opens Home "in a folder" (e.g. the tabs add button) makes that folder's project
  // active, so the header, the footer and the new chat all agree.
  const requestedFolder = locationState?.workspace;
  useEffect(() => {
    if (!requestedFolder) return;
    let cancelled = false;
    void kelProjects
      .forFolder(requestedFolder)
      .then(async (project) => {
        if (cancelled) return;
        announceProjectsChanged();
        await setActiveProject(project.id);
      })
      .catch((error: unknown) => console.warn('[Kel] Could not open that folder as a project:', error));
    return () => {
      cancelled = true;
    };
  }, [requestedFolder]);

  // Handle pasted files (append mode to support multiple pastes)
  // Do NOT clear dir here: paste/drag should coexist with a selected workspace,
  // matching the dialog-upload path (handleFilesUploaded).
  const handleFilesPasted = useCallback((pastedFiles: FileMetadata[]) => {
    // Paste/drag bytes are uploaded to the managed dir by the paste/drag hooks →
    // `upload` refs.
    const refs = pastedFiles.map((file) => uploadFileRef(file.path));
    setFiles((prevFiles) => [...prevFiles, ...refs]);
  }, []);

  // Device uploads (browser input → managed dir): append as `upload` refs.
  const handleFilesUploaded = useCallback((uploadedPaths: string[]) => {
    setFiles((prevFiles) => [...prevFiles, ...uploadedPaths.map(uploadFileRef)]);
  }, []);

  // Backend-machine picker (native dialog / server-fs browse): append as `local`
  // refs — the path is already absolute on the backend host, sent as-is.
  const handleFilesPicked = useCallback((pickedPaths: string[]) => {
    setFiles((prevFiles) => [...prevFiles, ...pickedPaths.map(localFileRef)]);
  }, []);

  const handleRemoveFile = useCallback((targetPath: string) => {
    setFiles((prevFiles) => prevFiles.filter((ref) => chatFileRefPath(ref) !== targetPath));
  }, []);

  // Use drag upload hook (drag treated like paste, appends to existing files)
  const { isFileDragging, dragHandlers } = useDragUpload({
    supportedExts: allSupportedExts,
    onFilesAdded: handleFilesPasted,
  });

  // Use shared PasteService integration (paste appends to existing files)
  const { onPaste, onFocus } = usePasteService({
    supportedExts: allSupportedExts,
    onFilesAdded: handleFilesPasted,
    onTextPaste: (text: string) => {
      const textarea = document.activeElement as HTMLTextAreaElement | null;
      if (textarea && textarea.tagName === 'TEXTAREA') {
        const start = textarea.selectionStart ?? textarea.value.length;
        const end = textarea.selectionEnd ?? start;
        const current_value = textarea.value;
        const newValue = current_value.slice(0, start) + text + current_value.slice(end);
        setInput(newValue);

        setTimeout(() => {
          const newPos = start + text.length;
          textarea.setSelectionRange(newPos, newPos);
          const caretTop = measureCaretTop(textarea, newPos);
          scrollCaretToLastLine(textarea, caretTop);
        }, 0);
      } else {
        setInput((prev) => prev + text);
      }
    },
  });

  const handleTextareaFocus = useCallback(() => {
    onFocus();
    setIsInputFocused(true);
  }, [onFocus]);

  const handleTextareaBlur = useCallback(() => {
    setIsInputFocused(false);
  }, []);

  return {
    input,
    setInput,
    files,
    setFiles,
    dir,
    projectId,
    isInputFocused,
    loading,
    setLoading,
    handleFilesPasted,
    handleFilesUploaded,
    handleFilesPicked,
    handleRemoveFile,
    handleTextareaFocus,
    handleTextareaBlur,
    onPaste,
    isFileDragging,
    dragHandlers,
  };
};
