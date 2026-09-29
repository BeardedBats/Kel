/**
 * The Kel mark and wordmark at the top of the sidebar, as one real button: it always takes Nick to the
 * start page (home / new chat, #/guid). It is keyboard-focusable and never part of the window's drag
 * region, so a click is a click.
 */
import classNames from 'classnames';
import React from 'react';
import { useNavigate } from 'react-router-dom';
import brandMark from '@renderer/assets/figma/kel-mark.png';

export const KEL_HOME_PATH = '/guid';

export const KelBrandHome: React.FC<{ collapsed?: boolean; onPress?: () => void }> = ({ collapsed = false, onPress }) => {
  const navigate = useNavigate();
  return (
    <button
      type='button'
      className='kel-brand-home'
      aria-label='Kel home'
      title='Kel home'
      data-testid='kel-brand-home'
      onClick={() => {
        onPress?.();
        void navigate(KEL_HOME_PATH);
      }}
    >
      <span className={classNames('shrink-0 size-32px relative rd-0.5rem overflow-hidden', { '!size-24px': collapsed })}>
        {/* Canonical Kel mark — the same asset the About page loads. Never redrawn or replaced with a text glyph. */}
        <img src={brandMark} alt='' className='absolute inset-0 size-full object-contain' draggable={false} />
      </span>
      <span className='text-16px text-t-primary collapsed-hidden font-semibold'>Kel</span>
    </button>
  );
};

/**
 * A thin full-width strip along the top edge of the frameless window that moves the window when dragged,
 * like a normal title bar (double-click maximises and restores — Windows does that for a drag region).
 * It is rendered first in the shell so every control declared after it with `no-drag` stays clickable.
 */
export const KelWindowDragStrip: React.FC = () => (
  <div className='kel-window-drag-strip' data-testid='kel-window-drag-strip' aria-hidden='true' />
);

export default KelBrandHome;
