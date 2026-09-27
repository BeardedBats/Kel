/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { saveReportToKibble } from '@/renderer/components/kel/kibbleReport';
import { Message } from '@arco-design/web-react';
import { Comment } from '@icon-park/react';
import classNames from 'classnames';
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';

type FeedbackButtonProps = {
  /** The area the report is about (a feedback module tag such as `mcp-tools`). */
  module?: string;
  /** Short diagnostic labels written into the Kibble note. */
  feedbackTags?: Record<string, string>;
  /** Structured context written into the Kibble note. */
  feedbackExtra?: Record<string, unknown>;
  /** Additional classes appended to the default pill styling. */
  className?: string;
  label?: string;
  /** The first line of the Kibble note; defaults to the button label. */
  reportTitle?: string;
};

/**
 * Inline "Report issue" chip shown near errors. It saves the diagnostics as a Kibble fix on this
 * computer (ST-02) and says so only once the fix is really saved.
 */
const FeedbackButton: React.FC<FeedbackButtonProps> = ({
  module,
  feedbackTags,
  feedbackExtra,
  className,
  label,
  reportTitle,
}) => {
  const { t } = useTranslation();
  const [saving, setSaving] = useState(false);
  const text = label ?? t('settings.oneClickFeedback');

  const handleClick = useCallback(
    async (event: React.MouseEvent<HTMLElement>) => {
      event.stopPropagation();
      if (saving) return;
      setSaving(true);
      try {
        await saveReportToKibble({
          title: reportTitle ?? text,
          area: module,
          details: { ...feedbackTags, ...feedbackExtra },
        });
        Message.success('Saved to Kibble.');
      } catch (error) {
        const reason = error instanceof Error && error.message ? error.message : '';
        Message.error(reason ? `Kel could not save this to Kibble. ${reason}` : 'Kel could not save this to Kibble.');
      } finally {
        setSaving(false);
      }
    },
    [feedbackExtra, feedbackTags, module, reportTitle, saving, text]
  );

  return (
    <button
      type='button'
      onClick={(event) => void handleClick(event)}
      disabled={saving}
      aria-busy={saving || undefined}
      className={classNames(
        'inline-flex items-center gap-3px cursor-pointer select-none b-none',
        'px-8px py-4px rd-16px',
        'bg-transparent hover:bg-fill-2 text-t-primary',
        'text-13px leading-18px transition-colors duration-150',
        className
      )}
    >
      <Comment theme='outline' size='14' fill='currentColor' className='flex-shrink-0 pt-4px' />
      <span>{text}</span>
    </button>
  );
};

export default FeedbackButton;
