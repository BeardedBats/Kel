/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * A skill suggestion the old scheduler left in a chat. D-57 retired that scheduler, so saving a
 * skill from here is gone; the card stays readable (name, description, preview) and can be
 * dismissed. `cron_job_id` is kept for the artifact's shape only.
 */
import { ipcBridge } from '@/common';
import { iconColors } from '@/renderer/styles/colors';
import { useUpdateConversationArtifactStatus } from '@renderer/pages/conversation/Messages/artifacts';
import { Button, Message } from '@arco-design/web-react';
import { Down, Lightning, Up } from '@icon-park/react';
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import MarkdownView from '@renderer/components/Markdown';
import type { SkillSuggestion } from '@renderer/utils/chat/skillSuggestParser';

interface SkillSuggestCardProps {
  artifact_id: string;
  conversation_id: string;
  suggestion: SkillSuggestion;
  cron_job_id: string;
}

const CODE_STYLE = { marginTop: 4, marginBlock: 4 };

const SkillSuggestCard: React.FC<SkillSuggestCardProps> = ({
  artifact_id,
  conversation_id,
  suggestion,
  cron_job_id,
}) => {
  const { t } = useTranslation();
  const updateArtifactStatus = useUpdateConversationArtifactStatus();
  const [dismissed, setDismissed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  void cron_job_id;

  if (dismissed) return null;

  return (
    <div
      data-testid='skill-suggest-card'
      className='mt-8px p-12px rd-8px bg-fill-0 b-1 b-solid'
      style={{ borderColor: 'color-mix(in srgb, var(--color-border-2) 70%, transparent)' }}
    >
      <div className='flex items-center gap-6px mb-8px'>
        <Lightning theme='filled' size={16} fill={iconColors.warning} />
        <span className='font-500 text-14px'>Skill suggested by an earlier scheduled task</span>
      </div>
      <div className='text-t-primary text-13px mb-4px'>{suggestion.name}</div>
      <div className='text-t-secondary text-12px mb-8px'>{suggestion.description}</div>

      {/* Expandable preview */}
      <div
        className='flex items-center gap-4px text-12px text-t-secondary cursor-pointer hover:text-t-primary mb-8px select-none'
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <Up size={12} /> : <Down size={12} />}
        <span>{t('cron.skill.preview')}</span>
      </div>
      {expanded && (
        <div className='mb-12px p-8px rd-4px bg-bg-3 max-h-240px overflow-y-auto text-12px'>
          <MarkdownView codeStyle={CODE_STYLE}>{`\`\`\`markdown\n${suggestion.content}\n\`\`\``}</MarkdownView>
        </div>
      )}

      <div className='flex gap-8px'>
        <Button
          size='small'
          onClick={async () => {
            try {
              await ipcBridge.conversation.updateArtifact.invoke({
                conversation_id,
                artifact_id,
                status: 'dismissed',
              });
              updateArtifactStatus(artifact_id, 'dismissed');
              setDismissed(true);
            } catch (error) {
              Message.error('Kel could not dismiss this just now.');
              console.error('[SkillSuggestCard] Failed to dismiss artifact:', error);
            }
          }}
        >
          {t('cron.skill.dismiss')}
        </Button>
      </div>
    </div>
  );
};

export default SkillSuggestCard;
