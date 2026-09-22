import { ipcBridge } from '@/common';
import { Button, Result, Spin } from '@arco-design/web-react';
import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import useSWR from 'swr';
import ChatConversation from './components/ChatConversation';
import { usePreviewContext } from '@/renderer/pages/conversation/Preview';
import { previewScopeKey } from '@/renderer/pages/conversation/Preview/context/previewScope';
import { setCurrentProject } from '@/renderer/pages/conversation/explorer/currentProjectStore';
import { setCurrentConversation } from '@/renderer/pages/conversation/explorer/currentConversationStore';
import { useAutoTitle } from '@/renderer/hooks/chat/useAutoTitle';
import { getConversationOrNull } from '@/renderer/pages/conversation/utils/conversationCache';
import { getSnapshotConversationProjectId } from '@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync';

const ChatConversationIndex: React.FC = () => {
  const { id } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { closePreviewIfScopeChanged } = usePreviewContext();
  const { syncTitleFromHistory } = useAutoTitle();
  const notFoundHandledIdRef = useRef<string | undefined>(undefined);
  const defaultConversationTitle = t('conversation.welcome.newConversation');

  const { data, isLoading, mutate } = useSWR(id ? `conversation/${id}` : null, () => {
    return getConversationOrNull(id!);
  });

  // Close preview only when the isolation scope changes, not on every
  // conversation switch. Same-scope conversations keep the preview open. The
  // scope is `previewScopeKey` = project (falling back to workspace until the
  // backend populates project_id). The ref lives in PreviewContext (app-root
  // level) so it survives remounts.
  useEffect(() => {
    if (!data) return;
    const workspace = (data.extra as { workspace?: string } | undefined)?.workspace ?? null;
    closePreviewIfScopeChanged(previewScopeKey(data.project_id ?? null, workspace));
  }, [data, closePreviewIfScopeChanged]);

  // Publish the active project SYNCHRONOUSLY on conversation switch, from the
  // in-memory list snapshot (every row carries project_id) — before the async
  // `conversation.get` resolves. Without this the module store held the previous
  // conversation's project until the fetch landed (~120-280ms, seconds when the
  // conversation is cold / mid-backfill), so the Explorer painted the old
  // project's tree. A known conversation publishes its project id immediately
  // (covers never-opened rows — the snapshot is the full list); an unknown one
  // (brand-new / not yet in the snapshot) publishes null — an empty placeholder,
  // never a stale project. Runs before paint (layout effect) so no stale frame.
  useLayoutEffect(() => {
    if (!id) return;
    setCurrentProject(getSnapshotConversationProjectId(id) ?? null);
  }, [id]);

  // Post-resolve authoritative correction: once `conversation.get` lands, publish
  // its project_id (also the backfill path — a workspace conversation's
  // project_id flips None→Some server-side and re-flows here via the refetch
  // below). `setCurrentProject` dedups, so when the sync effect already set the
  // right value this is a no-op.
  useEffect(() => {
    if (data) setCurrentProject(data.project_id ?? null);
  }, [data]);

  // Publish the active conversation id so the Layout-level Explorer's "add to
  // chat" can target this conversation's send box. Cleared when leaving the
  // conversation route (id falsy) so a stale target can't leak.
  useEffect(() => {
    setCurrentConversation(data?.id ?? null);
  }, [data]);

  // Refetch this conversation when the backend reports it changed. This is also
  // the project_id backfill path: opening a workspace conversation lazily
  // backfills its project_id server-side (project_id None→Some), and the first
  // GET can land on the pre-backfill row (project_id null). The backend emits a
  // `conversation.listChanged` (action 'updated') once when the backfill lands;
  // this listener refetches → the now-populated project_id flows to
  // `setCurrentProject` above → the Explorer host appears. Responsive, no poll.
  useEffect(() => {
    if (!id) return;

    return ipcBridge.conversation.listChanged.on((event) => {
      if (event.conversation_id !== id || (event.action !== 'updated' && event.action !== 'created')) {
        return;
      }

      void mutate();
    });
  }, [id, mutate]);

  useEffect(() => {
    if (!data || data.name !== defaultConversationTitle) {
      return;
    }

    void syncTitleFromHistory(data.id);
  }, [data, defaultConversationTitle, syncTitleFromHistory]);

  // 会话不存在（例如从历史栈回到已删除会话）时，说明发生了什么并留在该路由上。
  // Conversation does not exist (e.g. a deep link to a deleted one, or an id from another
  // install): say so on the route itself. Measured before this change: a deep link to an unknown
  // id showed a toast and silently replaced the route with home, so the visitor could not tell
  // whether they mis-clicked or the conversation was gone. One pass per id.
  const [missingId, setMissingId] = useState<string | undefined>(undefined);
  useEffect(() => {
    if (!id || isLoading || data || notFoundHandledIdRef.current === id) return;
    notFoundHandledIdRef.current = id;
    setMissingId(id);
  }, [id, isLoading, data]);

  if (isLoading) return <Spin loading></Spin>;
  if (!data && missingId) {
    return (
      <div className='flex h-full w-full items-center justify-center p-6'>
        <Result
          status='404'
          title={t('conversation.notFound')}
          subTitle={missingId}
          extra={
            <Button type='primary' onClick={() => navigate('/guid')}>
              {t('conversation.welcome.newConversation')}
            </Button>
          }
        />
      </div>
    );
  }
  return <ChatConversation conversation={data ?? undefined}></ChatConversation>;
};

export default ChatConversationIndex;
