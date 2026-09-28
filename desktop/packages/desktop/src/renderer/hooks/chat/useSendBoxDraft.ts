import { useCallback } from 'react';
import useSWR from 'swr';
import type { FileOrFolderItem } from '@/renderer/utils/file/fileTypes';
export type { FileOrFolderItem } from '@/renderer/utils/file/fileTypes';

type Draft =
  | {
      _type: 'acp';
      content: string;
      atPath: Array<string | FileOrFolderItem>;
      uploadFile: string[];
    }
  | {
      _type: 'codex';
      content: string;
      atPath: Array<string | FileOrFolderItem>;
      uploadFile: string[];
    }
  | {
      _type: 'aionrs';
      content: string;
      atPath: Array<string | FileOrFolderItem>;
      uploadFile: string[];
    };

/**
 * 当前支持的对话类型以及对应的草稿对象
 */
type DraftConversationType = Draft['_type'];
type SendBoxDraftStore = {
  [K in DraftConversationType]: Map<string, Extract<Draft, { _type: K }>>;
};

const store: SendBoxDraftStore = {
  acp: new Map(),
  codex: new Map(),
  aionrs: new Map(),
};

// Drafts survive a restart: the in-memory maps stay the source of truth and are mirrored into
// localStorage on every change. Keyed per conversation so switching chats never mixes drafts.
const DRAFT_STORAGE_KEY = 'kel.sendbox.drafts.v1';
const DRAFT_PERSIST_LIMIT = 20000;

const persistDrafts = () => {
  try {
    const snapshot: Record<string, Record<string, unknown>> = {};
    for (const type of Object.keys(store) as DraftConversationType[]) {
      const entries: Record<string, unknown> = {};
      for (const [id, draft] of store[type].entries()) {
        const payload = JSON.stringify(draft);
        if (payload.length <= DRAFT_PERSIST_LIMIT) entries[id] = draft;
      }
      snapshot[type] = entries;
    }
    window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(snapshot));
  } catch {
    /* drafts are best-effort and must never break the composer */
  }
};

const hydrateDrafts = () => {
  try {
    const raw = window.localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as Record<string, Record<string, unknown>>;
    for (const type of Object.keys(store) as DraftConversationType[]) {
      const entries = parsed[type];
      if (!entries || typeof entries !== 'object') continue;
      for (const [id, draft] of Object.entries(entries)) {
        store[type].set(id, draft as never);
      }
    }
  } catch {
    /* ignore corrupt or stale drafts */
  }
};

hydrateDrafts();

/**
 * Adds a prompt without discarding text the user has already typed.
 */
export const appendPromptToDraft = (draft: string, prompt: string): string => {
  if (!prompt) return draft;
  if (!draft) return prompt;
  return `${draft}${draft.endsWith('\n') ? '' : '\n'}${prompt}`;
};

const setDraft = <K extends DraftConversationType>(
  type: K,
  conversation_id: string,
  draft: Extract<Draft, { _type: K }> | undefined
) => {
  // TODO import ts-pattern for exhaustive check
  switch (type) {
    case 'acp':
      if (draft) {
        store.acp.set(conversation_id, draft as Extract<Draft, { _type: 'acp' }>);
      } else {
        store.acp.delete(conversation_id);
      }
      break;
    case 'codex':
      if (draft) {
        store.codex.set(conversation_id, draft as Extract<Draft, { _type: 'codex' }>);
      } else {
        store.codex.delete(conversation_id);
      }
      break;
    case 'aionrs':
      if (draft) {
        store.aionrs.set(conversation_id, draft as Extract<Draft, { _type: 'aionrs' }>);
      } else {
        store.aionrs.delete(conversation_id);
      }
      break;
    default:
      break;
  }
  persistDrafts();
};

const getDraft = <K extends DraftConversationType>(
  type: K,
  conversation_id: string
): Extract<Draft, { _type: K }> | undefined => {
  // TODO import ts-pattern for exhaustive check
  switch (type) {
    case 'acp':
      return store.acp.get(conversation_id) as Extract<Draft, { _type: K }>;
    case 'codex':
      return store.codex.get(conversation_id) as Extract<Draft, { _type: K }>;
    case 'aionrs':
      return store.aionrs.get(conversation_id) as Extract<Draft, { _type: K }>;
    default:
      return undefined;
  }
};

/**
 * Plain-text access to a draft outside a SendBox (the Home composer keeps its unsent text here
 * under its own id, so it survives navigation and restart like a conversation draft — CH-6).
 * An empty text removes the draft.
 */
export const readDraftText = (draft_id: string): string => getDraft('acp', draft_id)?.content ?? '';

export const writeDraftText = (draft_id: string, content: string): void => {
  const current = getDraft('acp', draft_id);
  if (!content) {
    if (current) setDraft('acp', draft_id, undefined);
    return;
  }
  if (current?.content === content) return;
  setDraft('acp', draft_id, { _type: 'acp', atPath: [], uploadFile: [], ...current, content });
};

/**
 * 获得一种类型下的会话草稿操作的 React Hook
 */
export const getSendBoxDraftHook = <K extends DraftConversationType>(
  type: K,
  initialValue: Extract<Draft, { _type: K }>
) => {
  function useDraft(conversation_id: string) {
    const swrRet = useSWR([`/send-box/${type}/draft/${conversation_id}`, conversation_id], ([_, id]) => {
      return getDraft(type, id);
    });

    const mutateDraft = useCallback(
      (draft: (k: Extract<Draft, { _type: K }>) => typeof k | undefined): void => {
        swrRet
          .mutate(
            (prev) => {
              const newDraft = draft(prev ?? initialValue);
              setDraft(type, conversation_id, newDraft);
              return newDraft;
            },
            { revalidate: false }
          )
          .catch((error) => {
            console.error('Failed to mutate draft:', error);
          });
      },
      [conversation_id]
    );

    return {
      get data() {
        return swrRet.data;
      },
      mutate: mutateDraft,
    };
  }

  return useDraft;
};
