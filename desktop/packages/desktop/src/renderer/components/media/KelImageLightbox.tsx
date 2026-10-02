import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Message } from '@arco-design/web-react';

interface KelImageLightboxProps {
  src: string;
  name: string;
  detail?: string;
  onCopy?: () => Promise<void>;
  onDownload?: () => Promise<void>;
  onClose: () => void;
}

const KelImageLightbox: React.FC<KelImageLightboxProps> = ({ src, name, onDownload, onClose }) => {
  const panel = useRef<HTMLElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  const [zoomed, setZoomed] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let activeElement = document.activeElement;
    while (activeElement?.shadowRoot?.activeElement) activeElement = activeElement.shadowRoot.activeElement;
    const previousFocus = activeElement instanceof HTMLElement ? activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeButton.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        close.current();
      } else if (event.key === 'Tab') {
        const controls = Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), [tabindex="0"]') ?? []);
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && (document.activeElement === first || !panel.current?.contains(document.activeElement))) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && (document.activeElement === last || !panel.current?.contains(document.activeElement))) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    window.addEventListener('keydown', onKeyDown, true);
    return () => {
      window.removeEventListener('keydown', onKeyDown, true);
      document.body.style.overflow = previousOverflow;
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, []);

  useEffect(() => {
    setZoomed(false);
    viewport.current?.scrollTo?.(0, 0);
  }, [src]);

  const save = async () => {
    if (saving) return;
    setSaving(true);
    try {
      if (onDownload) await onDownload();
      else {
        const link = document.createElement('a');
        link.href = src;
        link.download = name;
        document.body.appendChild(link);
        try { link.click(); } finally { link.remove(); }
      }
    } catch {
      Message.error('Could not save image');
    } finally {
      setSaving(false);
    }
  };

  return createPortal(
    <div className='kel-image-lightbox' role='presentation' onMouseDown={(event) => {
      if (event.target === event.currentTarget) close.current();
    }}>
      <section ref={panel} className='kel-image-lightbox__panel' role='dialog' aria-modal='true' aria-label='Image preview'>
        <div className='kel-image-lightbox__bar'>
          <span className='kel-image-lightbox__name'>Image</span>
          <div className='kel-image-lightbox__actions'>
            <button type='button' aria-label={zoomed ? 'Fit image' : 'Zoom image'} aria-pressed={zoomed} onClick={() => {
              setZoomed(!zoomed);
              viewport.current?.scrollTo?.(0, 0);
            }}>{zoomed ? 'Fit' : 'Zoom'}</button>
            <button type='button' aria-label='Save image' aria-busy={saving} disabled={saving} onClick={() => void save()}>Save</button>
            <button type='button' aria-label='Close image preview' onClick={() => close.current()} ref={closeButton}>Close</button>
          </div>
        </div>
        <div ref={viewport} className={`kel-image-lightbox__image${zoomed ? ' is-zoomed' : ''}`} tabIndex={zoomed ? 0 : undefined} role={zoomed ? 'region' : undefined} aria-label={zoomed ? 'Zoomed image. Use arrow keys to scroll.' : undefined}>
          <img src={src} alt='Image' draggable={false} />
        </div>
      </section>
    </div>,
    document.body
  );
};

export default KelImageLightbox;
