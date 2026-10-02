import React, { useEffect, useMemo, useRef, useState } from 'react';
import LocalImageView from './LocalImageView';
import KelImageLightbox from './KelImageLightbox';

const IMAGE_REFERENCE = /^kel-image:\/\/([A-Za-z0-9][A-Za-z0-9_-]{0,127})\/([A-Za-z0-9][A-Za-z0-9_-]{0,127})$/;
const MAX_BASE64_LENGTH = 6_666_668;

export const parseKelImageReference = (src: string): { job: string; milestone: string } | null => {
  const match = IMAGE_REFERENCE.exec(src);
  return match ? { job: match[1], milestone: match[2] } : null;
};

/** Only checked engine artifacts enter this view. Model text never supplies a local path. */
const KelGeneratedImage: React.FC<{ src: string; alt?: string }> = ({ src, alt }) => {
  const reference = useMemo(() => parseKelImageReference(src), [src]);
  const [picture, setPicture] = useState<{ url: string; width: number; height: number } | null>(null);
  const [error, setError] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const openButton = useRef<HTMLButtonElement>(null);
  const name = 'kel-image.png';

  useEffect(() => {
    let active = true;
    setPicture(null);
    setError('');
    setPreviewOpen(false);
    const load = async () => {
      if (!reference) throw new Error('This image reference is invalid.');
      if (!window.kelAPI?.imageArtifact) throw new Error('Open this image in the Kel desktop app.');
      const image = await window.kelAPI.imageArtifact(reference.job, reference.milestone);
      if (image.media_type !== 'image/png' || typeof image.base64 !== 'string' ||
          image.base64.length > MAX_BASE64_LENGTH || !image.base64.startsWith('iVBORw0KGgo') ||
          !/^[A-Za-z0-9+/]+={0,2}$/.test(image.base64) ||
          !Number.isInteger(image.width) || image.width < 1 || image.width > 8192 ||
          !Number.isInteger(image.height) || image.height < 1 || image.height > 8192 ||
          image.width * image.height > 16 * 1024 * 1024 ||
          !/^[a-f0-9]{64}$/i.test(image.sha256)) {
        throw new Error('Kel could not load the checked image.');
      }
      if (active) setPicture({ url: 'data:image/png;base64,' + image.base64, width: image.width, height: image.height });
    };
    void load().catch((failure: unknown) => {
      if (active) setError(failure instanceof Error ? failure.message : 'Kel could not open this image.');
    });
    return () => { active = false; };
  }, [reference, attempt]);

  if (error) return <span className='kel-generated-image' role='alert'>
    <span>Kel could not load this image. Try again here.</span>
    {reference && <button type='button' className='kel-btn kel-btn--quiet' onClick={() => setAttempt(value => value + 1)}>Try again</button>}
    <details><summary>Details</summary><span>{error}</span></details>
  </span>;
  if (!picture) return <span role='status'>Loading image…</span>;

  const save = () => {
    const link = document.createElement('a');
    link.href = picture.url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };
  return <span className='kel-generated-image' data-testid='kel-generated-image'>
    <button type='button' aria-label='Open generated image' onClick={() => setPreviewOpen(true)} ref={openButton}
      className='kel-generated-image__preview'>
      <LocalImageView src={picture.url} alt={alt || 'Generated image'} className='max-w-full max-h-[520px] object-contain rounded-8px' />
    </button>
    <span className='kel-generated-image__actions'>
      <button type='button' className='kel-btn kel-btn--quiet' onClick={() => setPreviewOpen(true)}>Open image</button>
      <button type='button' className='kel-btn kel-btn--quiet' onClick={save}>Save image</button>
    </span>
    {previewOpen && <KelImageLightbox src={picture.url} name={name}
      onClose={() => { setPreviewOpen(false); openButton.current?.focus(); }} />}
  </span>;
};

export default KelGeneratedImage;
