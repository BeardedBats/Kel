/**
 * The Figma icons and status dots of the Office explorations (page "Office — D-66 explorations",
 * frames 4a–4d), exported from the file as-is. Dots are 16px slots holding the 20px glow SVG.
 */
import React from 'react';
import dotWorking from '@renderer/assets/figma/work-cards/dot-working.svg';
import dotReview from '@renderer/assets/figma/work-cards/dot-review.svg';
import dotNeeds from '@renderer/assets/figma/work-cards/dot-needs.svg';
import dotFailed from '@renderer/assets/figma/work-cards/dot-failed.svg';
import dotDone from '@renderer/assets/figma/work-cards/dot-done.svg';
import dotNext from '@renderer/assets/figma/work-cards/dot-next.svg';
import iconCheck from '@renderer/assets/figma/work-cards/icon-check.svg';
import iconCheck14 from '@renderer/assets/figma/work-cards/icon-check14.svg';
import iconWarning from '@renderer/assets/figma/work-cards/icon-warning.svg';
import iconStopMuted from '@renderer/assets/figma/work-cards/icon-stop-muted.svg';
import iconChatSrc from '@renderer/assets/figma/work-cards/icon-chat.svg';
import iconWarningAmberSrc from '@renderer/assets/figma/work-cards/icon-warning-amber.svg';
import type { OfficeState } from './officeApi';

export { default as iconClose } from '@renderer/assets/figma/work-cards/icon-close.svg';
export { default as iconChev } from '@renderer/assets/figma/work-cards/icon-chev.svg';
export { default as iconStop } from '@renderer/assets/figma/work-cards/icon-stop.svg';
export { default as iconLoader } from '@renderer/assets/figma/work-cards/icon-loader.svg';
export { default as iconFile } from '@renderer/assets/figma/work-cards/icon-file.svg';
export { default as iconRemove } from '@renderer/assets/figma/work-cards/icon-remove.svg';
export { default as iconUndo } from '@renderer/assets/figma/work-cards/icon-undo.svg';
export { default as iconFolder } from '@renderer/assets/figma/work-cards/icon-folder.svg';
export { default as stepPending } from '@renderer/assets/figma/work-cards/step-pending.svg';
// D-70 (Figma row 5): scoping, quick picks, the in-thread line and the done card.
export { default as iconChat } from '@renderer/assets/figma/work-cards/icon-chat.svg';
export { default as iconCheck12Light } from '@renderer/assets/figma/work-cards/icon-check12-light.svg';
export { default as iconSparkle } from '@renderer/assets/figma/work-cards/icon-sparkle.svg';
export { default as iconChevronDown } from '@renderer/assets/figma/work-cards/icon-chevron-down.svg';
export { default as iconFolder13 } from '@renderer/assets/figma/work-cards/icon-folder13.svg';
// VIS-6 (Figma 5a): the step paused work stopped at carries the amber warning.
export { default as iconWarningAmber } from '@renderer/assets/figma/work-cards/icon-warning-amber.svg';
export { iconCheck, iconCheck14, iconWarning, iconStopMuted, dotNext, dotDone, dotReview, dotFailed };

export type DotTone = 'working' | 'review' | 'needs' | 'done' | 'failed' | 'next';

const DOTS: Record<DotTone, string> = {
  working: dotWorking,
  review: dotReview,
  needs: dotNeeds,
  done: dotDone,
  failed: dotFailed,
  next: dotNext,
};

/** The Figma status dot: a 16px slot; glow dots draw their 20px SVG 2px outside it. */
export const StatusDot: React.FC<{ tone: DotTone; className?: string }> = ({ tone, className }) => (
  <span className={`kel-wc-dot${tone === 'next' ? ' kel-wc-dot--flat' : ''}${className ? ` ${className}` : ''}`} aria-hidden='true'>
    <img src={DOTS[tone]} alt='' />
  </span>
);

export const dotToneFor = (state: OfficeState | string): DotTone => {
  switch (state) {
    case 'in_review':
      return 'review';
    case 'needs_you':
      return 'needs';
    case 'done':
      return 'done';
    case 'failed':
      return 'failed';
    case 'stopped':
      return 'next';
    default:
      return 'working';
  }
};

/** The lead icon before a state label: a dot while running, a check, warning or stop when finished. */
export const StateIcon: React.FC<{ state: OfficeState | string; size?: 'card' | 'detail'; uncertain?: boolean }> = ({
  state,
  size = 'card',
  uncertain = false,
}) => {
  // LIVE-10: work Kel couldn't fully check carries the amber caution, not the red failure.
  if (state === 'failed' && uncertain)
    return (
      <span className='kel-wc-icon kel-wc-icon--14' aria-hidden='true'>
        <img src={iconWarningAmberSrc} alt='' />
      </span>
    );
  if (state === 'scoping')
    return (
      <span className='kel-wc-icon kel-wc-icon--check-card' aria-hidden='true'>
        <img src={iconChatSrc} alt='' />
      </span>
    );
  if (state === 'done')
    return (
      <span className={`kel-wc-icon kel-wc-icon--check-${size}`} aria-hidden='true'>
        <img src={size === 'card' ? iconCheck : iconCheck14} alt='' />
      </span>
    );
  if (state === 'failed')
    return (
      <span className='kel-wc-icon kel-wc-icon--14' aria-hidden='true'>
        <img src={iconWarning} alt='' />
      </span>
    );
  if (state === 'stopped')
    return (
      <span className='kel-wc-icon kel-wc-icon--14' aria-hidden='true'>
        <img src={iconStopMuted} alt='' />
      </span>
    );
  return <StatusDot tone={dotToneFor(state)} />;
};
