import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Message } from '@arco-design/web-react';
import { Close, Copy, Download } from '@icon-park/react';

interface KelImageLightboxProps {
  src: string;
  name: string;
  detail?: string;
  onCopy?: () => Promise<void>;
  onDownload?: () => Promise<void>;
  onClose: () => void;
}

const KelImageLightbox: React.FC<KelImageLightboxProps> = ({ src, name, detail, onCopy, onDownload, onClose }) => {
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeButton.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      onClose();
    };
    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, [onClose]);

  const copy = async () => {
    if (onCopy) return onCopy();
    try {
      const picture = new Image();
      picture.src = src;
      await picture.decode();
      const canvas = document.createElement('canvas');
      canvas.width = picture.naturalWidth;
      canvas.height = picture.naturalHeight;
      const context = canvas.getContext('2d');
      if (!context) throw new Error('Canvas unavailable');
      context.drawImage(picture, 0, 0);
      const blob = await new Promise<Blob>((resolve, reject) =>
        canvas.toBlob((value) => value ? resolve(value) : reject(new Error('Image conversion failed')), 'image/png')
      );
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
      Message.success('Image copied');
    } catch (error) {
      console.error('Could not copy image', error);
      Message.error('Could not copy image');
    }
  };

  const download = () => {
    if (onDownload) { void onDownload(); return; }
    const link = document.createElement('a');
    link.href = src;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return createPortal(
    <div className='kel-image-lightbox' role='presentation' onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className='kel-image-lightbox__panel' role='dialog' aria-modal='true' aria-label={`Preview ${name}`}>
        <div className='kel-image-lightbox__bar'>
          <span className='kel-image-lightbox__name' title={name}>{name}</span>
          {detail && <span className='kel-image-lightbox__detail'>{detail}</span>}
          <div className='kel-image-lightbox__actions'>
            <button type='button' aria-label='Copy image' title='Copy image' onClick={() => void copy()}><Copy size='16' /></button>
            <button type='button' aria-label='Download image' title='Download image' onClick={download}><Download size='16' /></button>
            <button type='button' aria-label='Close preview' title='Close preview' onClick={onClose} ref={closeButton}><Close size='16' /></button>
          </div>
        </div>
        <div className='kel-image-lightbox__image'><img src={src} alt={name} /></div>
      </section>
    </div>,
    document.body
  );
};

export default KelImageLightbox;
