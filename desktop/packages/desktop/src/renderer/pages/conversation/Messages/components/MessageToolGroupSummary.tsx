import { Button, Message, Tooltip } from '@arco-design/web-react';
import { IconDown } from '@arco-design/web-react/icon';
import { Download } from '@icon-park/react';
import React, { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ipcBridge } from '@/common';
import { getAcpImageFileName } from '@/common/chat/acpToolCallOutput';
import type { NormalizedToolCall, ToolMessage } from '@/common/chat/normalizeToolCall';
import { normalizeToolMessages } from '@/common/chat/normalizeToolCall';
import LocalImageView from '@/renderer/components/media/LocalImageView';
import { downloadFileFromPath } from '@/renderer/utils/file/download';
import './MessageToolGroupSummary.css';

const ToolIcon: React.FC<{ kind?: string }> = ({ kind }) => (
  <svg aria-hidden='true' viewBox='0 0 16 16' fill='none' width='16' height='16'>
    {kind === 'execute' || kind === 'exec' ? <>
      <rect x='2' y='3' width='12' height='10' rx='1.5' stroke='currentColor' />
      <path d='m4.5 6 2 2-2 2M8 10h3' stroke='currentColor' strokeLinecap='round' strokeLinejoin='round' />
    </> : kind === 'edit' ? <>
      <path d='m3 11.5 7.9-7.9 1.5 1.5-7.9 7.9-2 .5.5-2Z' stroke='currentColor' strokeLinejoin='round' />
      <path d='m10 4.5 1.5 1.5' stroke='currentColor' />
    </> : <>
      <circle cx='7' cy='7' r='4' stroke='currentColor' />
      <path d='m10 10 3 3' stroke='currentColor' strokeLinecap='round' />
    </>}
  </svg>
);

const statusText = (status: NormalizedToolCall['status'], mobile = false): string => {
  switch (status) {
    case 'completed': return 'Success';
    case 'running': return mobile ? 'Running' : 'Executing';
    case 'error': return 'Failed';
    case 'canceled': return 'Stopped';
    default: return 'Pending';
  }
};

const ToolItemDetail: React.FC<{ item: NormalizedToolCall }> = ({ item }) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [fullItem, setFullItem] = useState<NormalizedToolCall | null>(null);
  const [loadingFull, setLoadingFull] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const displayItem = fullItem ?? item;
  const hasDetail = displayItem.input || displayItem.output || item.truncated || item.imagePath;
  const [messageApi, messageContext] = Message.useMessage();
  const handleDownloadImage = useCallback(
    async (path: string) => {
      try {
        await downloadFileFromPath(path, getAcpImageFileName(path));
        messageApi.success(t('acp.image.download_success'));
      } catch (error) {
        console.error('[MessageToolGroupSummary] Failed to download image:', error);
        messageApi.error(t('acp.image.download_error'));
      }
    },
    [messageApi, t]
  );

  const loadFullItem = async () => {
    if (!item.truncated || fullItem || loadingFull || !item.conversationId || !item.messageId) return;
    setLoadingFull(true);
    setLoadError(false);
    try {
      const message = await ipcBridge.database.getConversationMessage.invoke({
        conversation_id: item.conversationId,
        message_id: item.messageId,
      });
      const next = normalizeToolMessages([message as ToolMessage]).find((candidate) => candidate.key === item.key);
      if (next) setFullItem(next);
    } catch {
      setLoadError(true);
    } finally {
      setLoadingFull(false);
    }
  };

  const toggleExpanded = () => {
    const nextExpanded = !expanded;
    setExpanded(nextExpanded);
    if (nextExpanded) void loadFullItem();
  };

  return (
    <div className='kel-tool-call' data-status={item.status}>
      {messageContext}
      <button className='kel-tool-call__summary' type='button' aria-expanded={hasDetail ? expanded : undefined}
        disabled={!hasDetail} onClick={toggleExpanded}>
        <span className='kel-tool-call__icon'><ToolIcon kind={item.kind} /></span>
        <span className='kel-tool-call__copy'>
          <span className='kel-tool-call__title kel-tool-call__title--desktop'>{displayItem.name}</span>
          <span className='kel-tool-call__title kel-tool-call__title--mobile'>{displayItem.name.replace(/^Execute:\s*/i, '')}</span>
          {displayItem.description && displayItem.description !== displayItem.name &&
            <span className='kel-tool-call__description'>{displayItem.description}</span>}
        </span>
        <span className='kel-tool-call__status kel-tool-call__status--desktop'>{statusText(item.status)}</span>
        <span className='kel-tool-call__status kel-tool-call__status--mobile'>{statusText(item.status, true)}</span>
        {hasDetail && <IconDown className={`kel-tool-call__chevron${expanded ? ' kel-tool-call__chevron--open' : ''}`} style={{ fontSize: 12 }} />}
      </button>
      {expanded && hasDetail && (
        <div className='tool-detail-panel m-l-20px m-t-4px'>
          {loadingFull && <div className='tool-detail-label'>Loading...</div>}
          {loadError && <div className='tool-detail-label'>Failed to load full output</div>}
          {displayItem.input && (
            <div className='tool-detail-section'>
              <div className='tool-detail-label'>Input</div>
              <pre className='tool-detail-content'>{displayItem.input}</pre>
            </div>
          )}
          {displayItem.output && (
            <div className='tool-detail-section'>
              <div className='tool-detail-label'>Output</div>
              <pre className='tool-detail-content'>{displayItem.output}</pre>
            </div>
          )}
        </div>
      )}
      {item.imagePath && (
        <div className='group relative m-l-20px m-t-8px overflow-hidden rounded border bg-1 p-2 max-w-280px'>
          <LocalImageView
            src={item.imagePath}
            alt={getAcpImageFileName(item.imagePath)}
            className='max-w-full max-h-320px object-contain rounded'
          />
          <Tooltip content={t('acp.image.download')}>
            <Button
              aria-label={t('acp.image.download_aria')}
              className='!absolute end-10px top-10px !h-28px !w-28px !p-0 opacity-0 shadow-sm transition-opacity group-hover:opacity-90 focus:opacity-100'
              type='secondary'
              size='mini'
              shape='circle'
              icon={<Download theme='outline' size='14' />}
              onClick={() => void handleDownloadImage(item.imagePath)}
            />
          </Tooltip>
        </div>
      )}
    </div>
  );
};

const MessageToolGroupSummary: React.FC<{ messages: ToolMessage[] }> = ({ messages }) => {
  const tools = useMemo(() => normalizeToolMessages(messages), [messages]);

  return (
    <div className='tool-group-summary'>
      {tools.map((item) => <ToolItemDetail key={item.key} item={item} />)}
    </div>
  );
};

export default React.memo(MessageToolGroupSummary);
