import kelMark from '@renderer/assets/figma/kel-mark.png';
import KelEngineFailureCard, { parseEngineFailure } from './KelEngineFailureCard';
import { KelMessageNote } from './KelMessageDetails';
import { KelMessageCard } from '@renderer/components/kel/workCards/KelMessageCard';
import { KelUsageChips } from '@renderer/components/kel/usage/KelUsageChips';
import { isKelNoteMeta } from '@/common/chat/kelMessageMeta';
import moreIcon from '@renderer/assets/figma/chat/more.svg';
/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import type { IMessageText } from '@/common/chat/chatLib';
import { parseFileMarker, resolveMessageFilePath } from './fileMarker';
import SessionMentionAction from './SessionMentionAction';
import { parseSessionMessageBlock, parseSessionsBlock } from './sessionMarkers';
import { useConversationContextSafe } from '@/renderer/hooks/context/ConversationContext';
import { useLayoutContext } from '@/renderer/hooks/context/LayoutContext';
import { useLocalFilePreview } from '@/renderer/pages/conversation/Preview/hooks/useLocalFilePreview';
import { iconColors } from '@/renderer/styles/colors';
import { Dropdown, Menu, Message, Tooltip } from '@arco-design/web-react';
import { Copy, Edit, Refresh } from '@icon-park/react';
import classNames from 'classnames';
import React, { useCallback, useMemo, useRef, useState } from 'react';
import { useMessageArrival, useStreamFade } from '@renderer/motion';
import { useTranslation } from 'react-i18next';
import { copyText } from '@/renderer/utils/ui/clipboard';
import { emitter } from '@/renderer/utils/emitter';
import CollapsibleContent from '@renderer/components/chat/CollapsibleContent';
import FilePreview from '@renderer/components/media/FilePreview';
import HorizontalFileList from '@renderer/components/media/HorizontalFileList';
import MarkdownView from '@renderer/components/Markdown';
import { stripThinkTags, hasThinkTags } from '@renderer/utils/chat/thinkTagFilter';
import { buildTurnClipboardText } from '@renderer/utils/chat/turnCopy';
import { stripSkillSuggest, hasSkillSuggest } from '@renderer/utils/chat/skillSuggestParser';
import { isForkEnabled } from '@/common/chat/forkConversation';
import { useForkConversation } from '@/renderer/hooks/chat/useForkConversation';
import ForkBranchIcon from '@renderer/components/base/ForkBranchIcon';
import { findByAttribute, useMenuKeyboard } from '@/renderer/hooks/ui/useMenuKeyboard';

/**
 * Format a timestamp for message display.
 * Desktop uses "h:mm AM"; phone keeps "HH:mm". Older dates add "MM-DD".
 */
export const formatMessageTime = (timestamp: number, twelveHour = true): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const hours = twelveHour ? (date.getHours() % 12 || 12).toString() : date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const time = `${hours}:${minutes}${twelveHour ? ` ${date.getHours() < 12 ? 'AM' : 'PM'}` : ''}`;

  if (
    date.getFullYear() !== now.getFullYear() ||
    date.getMonth() !== now.getMonth() ||
    date.getDate() !== now.getDate()
  ) {
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${month}-${day} ${time}`;
  }
  return time;
};
import MessageCronBadge from './MessageCronBadge';
import { resolveAgentLogo, useAgentLogos } from '@/renderer/utils/model/agentLogo';
import TeammateMessageAvatar from './TeammateMessageAvatar';
import { useTeammateColor } from '@/renderer/pages/team/identity/TeamIdentityContext';

const CODE_STYLE = { marginTop: 4, marginBlock: 4 };

// D-59: replies carry Copy (and Fork when available) only; the old thumbs up/down wrote to local
// storage and changed nothing, so they are gone.
export const ReplyActions: React.FC<{
  onCopy: () => void;
  directCopy?: React.ReactNode;
  onFork?: () => void;
  /** D-75.2: answer the last reply again. */
  onRegenerate?: () => void;
}> = ({ onCopy, directCopy, onFork, onRegenerate }) => {
  const { t } = useTranslation();
  // VIS-10: keyboard like the project chip (focus in, arrows, Escape back to ⋯, closes on page change).
  const [open, setOpen] = React.useState(false);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const menuId = React.useId();
  useMenuKeyboard({
    open,
    onClose: () => setOpen(false),
    getMenu: () => findByAttribute('data-kel-reply-menu', menuId),
    triggerRef,
  });
  return <>
    {directCopy}
    {onRegenerate && <Tooltip content='Answer again'>
      <button type='button' aria-label='Answer again' className='kel-shell-message-action' style={{ lineHeight: 0 }}
        onClick={onRegenerate} data-testid='message-regenerate-button'>
        <Refresh theme='outline' size='16' fill={iconColors.secondary} />
      </button>
    </Tooltip>}
    <Dropdown trigger='click' position='bl' popupVisible={open} onVisibleChange={setOpen} droplist={<Menu data-kel-reply-menu={menuId} aria-label='Reply actions'>
      <Menu.Item key='copy' onClick={() => { setOpen(false); onCopy(); }}>{t('common.copy', { defaultValue: 'Copy' })}</Menu.Item>
      {onRegenerate && <Menu.Item key='regenerate' onClick={() => { setOpen(false); onRegenerate(); }}>Answer again</Menu.Item>}
      {onFork && <Menu.Item key='fork' onClick={() => { setOpen(false); onFork(); }}>{t('messages.fork.action')}</Menu.Item>}
    </Menu>}>
      <button ref={triggerRef} type='button' aria-label='More reply actions' aria-haspopup='menu' aria-expanded={open} className='kel-shell-message-action'>
        <img src={moreIcon} alt='' width={16} height={16} />
      </button>
    </Dropdown>
  </>;
};

type TeamContextResetNotice = {
  kind: 'context_reset';
  member_name: string;
  runtime_status: 'ready' | 'failed';
};

export const parseTeamContextResetNotice = (content: string): TeamContextResetNotice | null => {
  try {
    const value = JSON.parse(content) as Record<string, unknown>;
    if (
      value.kind === 'context_reset' &&
      typeof value.member_name === 'string' &&
      (value.runtime_status === 'ready' || value.runtime_status === 'failed')
    ) {
      return value as TeamContextResetNotice;
    }
  } catch {
    // Ordinary teammate/system text is not a semantic notice.
  }
  return null;
};

const useFormatContent = (content: string) => {
  return useMemo(() => {
    try {
      const json = JSON.parse(content);
      const isJson = typeof json === 'object';
      return {
        json: isJson,
        data: isJson ? json : content,
      };
    } catch {
      return { data: content };
    }
  }, [content]);
};

const MessageText: React.FC<{
  message: IMessageText;
  showCopyRow?: boolean;
  isLastMessage?: boolean;
  hasForkAnchor?: boolean;
  /** Render the existing actions after an adjacent desktop tool group. */
  actionsOnly?: boolean;
  /** All text segments of this message's turn, in order — the copy button
   * copies the whole reply, not just the segment it happens to sit on. */
  turnTexts?: string[];
}> = ({ message, showCopyRow = true, isLastMessage = false, hasForkAnchor = false, actionsOnly = false, turnTexts }) => {
  const logos = useAgentLogos();
  // Filter think tags from content before rendering
  // 在渲染前过滤 think 标签
  const contentToRender = useMemo(() => {
    let content = message.content.content;
    if (typeof content === 'string') {
      if (hasThinkTags(content)) {
        content = stripThinkTags(content);
      }
      // Strip any inline [SKILL_SUGGEST] blocks (now handled via separate skill_suggest message type)
      if (hasSkillSuggest(content)) {
        content = stripSkillSuggest(content);
      }
      return content;
    }
    return content;
  }, [message.content.content]);

  const { t } = useTranslation();
  const layout = useLayoutContext();
  const isUserMessage = message.position === 'right';
  const engineFailure = !isUserMessage && typeof message.content.content === 'string' ? parseEngineFailure(message.content.content) : null;
  // Delivered-but-not-yet-consumed marker for messages sent mid-turn to a
  // supporting backend (claude/codex). The message already reached the
  // server (it's rendered); this only answers "has the agent picked it up
  // yet" — an IM delivered/read style badge, never a ghost/dashed bubble.
  const isPendingDelivery = isUserMessage && message.status === 'pending';
  const isTeammateMessage = message.position === 'left' && message.content.teammateMessage === true;
  const senderName = message.content.senderName;
  const senderAgentType = message.content.senderAgentType;
  const senderConversationId = message.content.senderConversationId;
  const { text, files } = useMemo(
    () => parseFileMarker(contentToRender, isUserMessage),
    [contentToRender, isUserMessage]
  );
  // Cross-session markers. Both live on USER messages: the sender-side
  // `[[AION_SESSIONS]]` block is appended to the user's own message, and a
  // delivery is persisted as a user message too. Not parsing them would show
  // raw marker text in a bubble.
  const { text: textWithoutMentions, sessions: mentionedSessions } = useMemo(
    () => (isUserMessage ? parseSessionsBlock(text) : { text, sessions: [] }),
    [isUserMessage, text]
  );
  const { text: visibleText, source: deliverySource } = useMemo(
    () => (isUserMessage ? parseSessionMessageBlock(textWithoutMentions) : { text: textWithoutMentions, source: null }),
    [isUserMessage, textWithoutMentions]
  );
  const contextResetNotice = useMemo(
    () => (isTeammateMessage && senderName === 'team_system' ? parseTeamContextResetNotice(text) : null),
    [isTeammateMessage, senderName, text]
  );
  const renderedText = contextResetNotice
    ? t(
        contextResetNotice.runtime_status === 'ready'
          ? 'team.systemNotice.contextResetSuccess'
          : 'team.systemNotice.contextResetRuntimeFailed',
        { memberName: contextResetNotice.member_name }
      )
    : visibleText;
  const { data, json } = useFormatContent(renderedText);
  const shouldRenderPlainText = isUserMessage || Boolean(contextResetNotice);
  const conversationContext = useConversationContextSafe();
  const forkConversation = useForkConversation(conversationContext?.conversation_id);
  const handleLocalFileLink = useLocalFilePreview(conversationContext?.workspace);
  const teammateColor = useTeammateColor(isTeammateMessage ? senderConversationId : undefined);
  const resolvedFiles = useMemo(
    () => files.map((file_path) => resolveMessageFilePath(file_path, conversationContext?.workspace)),
    [conversationContext?.workspace, files]
  );

  // D-78 §10.1: a message that arrives while Nick watches — his words fly from the composer, Kel's mark
  // flies from Thinking to the reply's avatar, and a streamed reply's new words fade out of a blur.
  const turnRef = useRef<HTMLDivElement>(null);
  const [markdownBody, setMarkdownBody] = useState<HTMLDivElement | null>(null);
  const onMarkdownBody = useCallback((el?: HTMLDivElement | null) => setMarkdownBody(el ?? null), []);
  useMessageArrival(turnRef, isUserMessage ? 'user' : isTeammateMessage || message.content.cronMeta ? 'other' : 'kel');
  useStreamFade(markdownBody, !isUserMessage);

  // D-75.2: Nick can edit a message he sent; Kel answers again from there.
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState('');

  // 过滤空内容，避免渲染空DOM
  if (!message.content.content || (typeof message.content.content === 'string' && !message.content.content.trim())) {
    return null;
  }

  // CH-3/D-55: "You stopped this reply." and "Restarting … with that change" are notes about the
  // conversation, shown as one quiet line rather than as a Kel reply with its actions.
  const kelMeta = isUserMessage ? undefined : message.content.kel_meta;
  if (kelMeta && isKelNoteMeta(kelMeta)) {
    return actionsOnly ? null : <KelMessageNote text={renderedText} />;
  }

  const handleCopy = () => {
    const baseText = shouldRenderPlainText ? renderedText : json ? JSON.stringify(data, null, 2) : renderedText;
    const fileList = files.length ? `Files:\n${files.map((path) => `- ${path}`).join('\n')}\n\n` : '';
    // An AI turn split by tool calls / thinking stores several text messages;
    // the row sits on the last one but must copy the whole reply.
    const textToCopy = turnTexts?.length ? buildTurnClipboardText(turnTexts) : fileList + baseText;
    copyText(textToCopy)
      .then(() => {
        // The same Kel toast every other copy uses, instead of a one-off banner.
        Message.success('Copied');
      })
      .catch(() => {
        Message.error(t('common.copyFailed'));
      });
  };

  const copyButton = (
    <Tooltip content={t('common.copy', { defaultValue: 'Copy' })}>
      <button
        type='button'
        aria-label={t('common.copy', { defaultValue: 'Copy' })}
        className='kel-shell-message-action'
        onClick={handleCopy}
        style={{ lineHeight: 0 }}
      >
        <Copy theme='outline' size='16' fill={iconColors.secondary} />
      </button>
    </Tooltip>
  );

  // Fork entry point: only when the agent declares the capability, and only on
  // messages the backend can actually fork at (any message for at_turn/codex,
  // the last message otherwise) — see `isForkEnabled`.
  const showForkButton = isForkEnabled(conversationContext?.forkCapability, {
    isLastMessage,
    hasTurnAnchor: hasForkAnchor,
  });
  const forkButton = showForkButton ? (
    <Tooltip content={t('messages.fork.action')}>
      <button
        type='button'
        aria-label={t('messages.fork.action')}
        className='kel-shell-message-action'
        onClick={() => void forkConversation(message.msg_id ?? message.id)}
        style={{ lineHeight: 0 }}
        data-testid='message-fork-button'
      >
        <ForkBranchIcon size={16} fill={iconColors.secondary} />
      </button>
    </Tooltip>
  ) : null;

  // D-75.2: edit and "Answer again" belong to Kel's own chat (not team, scheduled or read-only views).
  const canRewrite = conversationContext?.type === 'acp' && !conversationContext?.hideSendBox && !isTeammateMessage
    && !message.content.cronMeta && !deliverySource && !engineFailure && Boolean(conversationContext?.conversation_id);
  const regenerate = canRewrite && isLastMessage && !isUserMessage ? () => {
    emitter.emit('kel.message.rewrite', { kind: 'regenerate', conversationId: conversationContext!.conversation_id, messageId: message.id });
  } : undefined;
  const startEdit = () => {
    setDraft(renderedText);
    setEditing(true);
  };
  const submitEdit = () => {
    const next = draft.trim();
    setEditing(false);
    if (!next || next === renderedText.trim()) return;
    emitter.emit('kel.message.rewrite', {
      kind: 'edit', conversationId: conversationContext!.conversation_id, messageId: message.id,
      text: renderedText, newText: next, files,
    });
  };
  const editButton = canRewrite && isUserMessage && !isPendingDelivery ? (
    <Tooltip content='Edit'>
      <button type='button' aria-label='Edit message' className='kel-shell-message-action' style={{ lineHeight: 0 }}
        onClick={startEdit} data-testid='message-edit-button'>
        <Edit theme='outline' size='16' fill={iconColors.secondary} />
      </button>
    </Tooltip>
  ) : null;

  const kelReplyActions = (
    <ReplyActions key={message.id} onCopy={handleCopy}
      directCopy={layout?.isMobile ? copyButton : null}
      onRegenerate={regenerate}
      onFork={showForkButton ? () => void forkConversation(message.msg_id ?? message.id) : undefined} />
  );

  const cronMeta = message.content.cronMeta;
  const displaySenderName = senderName === 'team_system' ? t('team.systemNotice.sender') : senderName;
  const fallbackBackendLogo = senderAgentType ? resolveAgentLogo(logos, { backend: senderAgentType }) : null;
  const actionsRow = showCopyRow && !editing && (
    <div
      className={classNames('kel-shell-message-actions h-32px flex items-center mt-4px gap-8px', {
        'flex-row-reverse': isUserMessage,
      })}
      data-reply-message-id={message.id}
    >
      {!isUserMessage && !isTeammateMessage && !cronMeta ? kelReplyActions : <>{copyButton}{editButton}{forkButton}</>}
    </div>
  );

  return (
    <>
      {actionsOnly ? actionsRow : <div ref={turnRef} className={classNames('kel-shell-message-turn min-w-0 flex flex-col group', isUserMessage ? 'items-end' : 'items-start')}>
        {message.created_at && <div className='kel-shell-message-meta'>
          {!isUserMessage && !isTeammateMessage && (layout?.isMobile
            ? <img src={kelMark} alt='Kel' width={22} height={22} />
            : <span className='kel-shell-message-avatar'><img src={kelMark} alt='Kel' width={22} height={23} /></span>)}
          <time dateTime={new Date(message.created_at).toISOString()}>{formatMessageTime(message.created_at, !layout?.isMobile)}</time>
        </div>}
        {cronMeta && <MessageCronBadge meta={cronMeta} />}
        {isTeammateMessage && displaySenderName && (
          <div className='flex items-center gap-6px mb-4px'>
            <TeammateMessageAvatar
              senderName={displaySenderName}
              senderConversationId={senderConversationId}
              backendLogo={fallbackBackendLogo}
            />
            <span
              className='text-12px'
              style={teammateColor ? { color: teammateColor } : { color: 'var(--text-secondary)' }}
            >
              {displaySenderName}
            </span>
          </div>
        )}
        {deliverySource && (
          <div
            className={classNames('mb-4px flex items-center gap-4px text-12px text-t-secondary', {
              'self-end': isUserMessage,
            })}
          >
            <SessionMentionAction
              id={deliverySource.fromId}
              name={deliverySource.fromName || deliverySource.fromId}
              label={t('conversation.crossSession.fromBadge', {
                name: deliverySource.fromName || deliverySource.fromId,
                defaultValue: 'From conversation {{name}}',
              })}
            />
            {deliverySource.workspace && deliverySource.workspace !== 'same' && (
              <span
                className='px-4px rounded-4px'
                style={{ background: 'var(--color-fill-2)' }}
                title={deliverySource.workspace}
              >
                {t('conversation.crossSession.otherWorkspace', { defaultValue: 'different workspace' })}
              </span>
            )}
          </div>
        )}
        {mentionedSessions.length > 0 && (
          <div className={classNames('mb-4px flex flex-wrap gap-4px', { 'self-end': isUserMessage })}>
            {mentionedSessions.map((session) => (
              <SessionMentionAction
                key={session.id}
                id={session.id}
                name={session.name}
                label={`@@${session.name}`}
                title={session.workspace}
                chip
              />
            ))}
          </div>
        )}
        {files.length > 0 && (
          <div className={classNames('mt-6px min-w-0 max-w-full', { 'self-end': isUserMessage })}>
            {resolvedFiles.length === 1 ? (
              <div className='flex items-center'>
                <FilePreview path={resolvedFiles[0]} onRemove={() => undefined} readonly />
              </div>
            ) : (
              <HorizontalFileList>
                {resolvedFiles.map((path) => (
                  <FilePreview key={path} path={path} onRemove={() => undefined} readonly />
                ))}
              </HorizontalFileList>
            )}
          </div>
        )}
        <div
          className={classNames('kel-shell-message-text min-w-0 [&>p:first-child]:mt-0px [&>p:last-child]:mb-0px', {
            'bg-aou-2 p-6px md:p-8px': isUserMessage || cronMeta,
            'bg-3 p-6px md:p-8px': isTeammateMessage,
            'w-full': !(isUserMessage || cronMeta || isTeammateMessage),
          })}
          style={{
            ...(isUserMessage || cronMeta
              ? { borderRadius: '8px 0 8px 8px', color: 'var(--text-primary)' }
              : isTeammateMessage
                ? {
                    borderRadius: '0 8px 8px 8px',
                    ...(teammateColor ? { border: `1px solid ${teammateColor}` } : {}),
                  }
                : undefined),
          }}
        >
          {/* JSON 内容使用折叠组件 Use CollapsibleContent for JSON content */}
          {engineFailure ? (
            <KelEngineFailureCard reason={engineFailure} messageId={message.id} conversationId={message.conversation_id} />
          ) : editing ? (
            <div className='kel-message-edit flex flex-col gap-6px' data-testid='message-edit-form'>
              <textarea
                aria-label='Edit your message'
                className='kel-message-edit-input'
                value={draft}
                autoFocus
                rows={Math.min(8, Math.max(2, draft.split('\n').length))}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') setEditing(false);
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault();
                    submitEdit();
                  }
                }}
              />
              <div className='flex justify-end gap-6px'>
                <button type='button' className='kel-message-edit-cancel' onClick={() => setEditing(false)}>Cancel</button>
                <button type='button' className='kel-message-edit-send' onClick={submitEdit}
                  disabled={!draft.trim() || draft.trim() === renderedText.trim()}>Send</button>
              </div>
            </div>
          ) : shouldRenderPlainText ? (
            <div className='whitespace-pre-wrap [overflow-wrap:anywhere]' data-testid='message-text-content'>
              {renderedText}
            </div>
          ) : json ? (
            <CollapsibleContent maxHeight={200} defaultCollapsed={true}>
              <div data-testid='message-text-content'>
                <MarkdownView
                  codeStyle={CODE_STYLE}
                  onLocalFileLink={handleLocalFileLink}
                >{`\`\`\`json\n${JSON.stringify(data, null, 2)}\n\`\`\``}</MarkdownView>
              </div>
            </CollapsibleContent>
          ) : (
            <div data-testid='message-text-content'>
              <MarkdownView codeStyle={CODE_STYLE} onLocalFileLink={handleLocalFileLink} onRef={onMarkdownBody}>
                {data}
              </MarkdownView>
            </div>
          )}
        </div>
        {/* CP-14: who answered and what the checks found, only when the person asks. */}
        {/* D-70: a scoping card, or a result's done card when its work has a top card. */}
        {kelMeta && !engineFailure && <KelMessageCard meta={kelMeta} conversationId={message.conversation_id} />}
        {/* D-72: what this reply used — cost (or "Included in your plan"), tokens, time, model. */}
        {kelMeta?.usage && !engineFailure && !actionsOnly ? <KelUsageChips usage={kelMeta.usage} /> : null}
        {isPendingDelivery && (
          <div className='text-12px text-t-secondary mt-4px select-none' data-testid='message-status-badge'>
            {t('messages.delivery.pending', { defaultValue: 'Unread' })}
          </div>
        )}
        {/* Keep reply actions visible on mobile, where hover cannot reveal them.
            For replies split across text messages, only the last shows the row. */}
        {actionsRow}
      </div>}
    </>
  );
};

export default MessageText;
