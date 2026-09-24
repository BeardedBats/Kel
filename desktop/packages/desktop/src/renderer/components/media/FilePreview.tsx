/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { Close } from '@icon-park/react';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { formatByteSize } from '@/renderer/services/i18n/format';
import { getFileExtension } from '@/renderer/services/FileService';
import { ipcBridge } from '@/common';
import { Tooltip } from '@arco-design/web-react';
import fileIcon from '@/renderer/assets/icons/file-icon.svg';
import KelImageLightbox from './KelImageLightbox';

const IMAGE_EXTS = new Set(['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']);

// Substring from the base64-encoded "Image not found" placeholder SVG returned by getImageBase64 on ENOENT.
// This is the aligned base64 encoding of ">Image not found<" within the SVG data URL.
const IMAGE_NOT_FOUND_B64_MARKER = 'kltYWdlIG5vdCBmb3VuZD';
const MAX_IMAGE_RETRIES = 5;
const IMAGE_RETRY_DELAY_MS = 800;

const isImageFile = (path: string): boolean => {
  const ext = path.toLowerCase().slice(path.lastIndexOf('.'));
  return IMAGE_EXTS.has(ext);
};

interface FilePreviewProps {
  path: string;
  onRemove: () => void;
  readonly?: boolean;
  /** Optional tooltip shown on the chip (e.g. "sent as a file path"). */
  hint?: string;
}

const FilePreview: React.FC<FilePreviewProps> = ({ path, onRemove, readonly = false, hint }) => {
  // Defensive check: ensure path is a string
  if (typeof path !== 'string') {
    console.error('[FilePreview] Invalid path type:', typeof path, path);
    return null;
  }

  const isImage = isImageFile(path);
  // 直接从路径中提取文件名，不清理时间戳后缀
  // Extract filename directly from path without cleaning timestamp suffix
  const file_name = path.split(/[\\/]/).pop() || '';
  const fileExt = getFileExtension(path).toUpperCase().replace('.', '');
  const { i18n } = useTranslation();
  const [imageUrl, setImageUrl] = useState<string>('');
  const [fileSize, setFileSize] = useState<string>('');
  const [imageDimensions, setImageDimensions] = useState<string>('');
  const [previewOpen, setPreviewOpen] = useState(false);

  useEffect(() => {
    if (!imageUrl) return;
    const image = new window.Image();
    image.onload = () => setImageDimensions(`${image.naturalWidth}×${image.naturalHeight}`);
    image.src = imageUrl;
    return () => { image.onload = null; };
  }, [imageUrl]);

  useEffect(() => {
    // 获取文件大小
    ipcBridge.fs.getFileMetadata
      .invoke({ path })
      .then((metadata) => {
        setFileSize(formatByteSize(metadata.size, i18n.language));
      })
      .catch((error) => {
        console.error('[FilePreview] Failed to get file metadata:', { path, error });
      });

    // 如果是图片，获取图片的base64
    // Retry when the file is not found yet (race condition: display message rendered
    // before the backend finishes copying the pasted image to the workspace).
    if (isImage) {
      let cancelled = false;
      let retryCount = 0;
      let retryTimer: ReturnType<typeof setTimeout>;

      const loadImage = () => {
        ipcBridge.fs.getImageBase64
          .invoke({ path })
          .then((base64) => {
            if (cancelled) return;
            if (!base64) {
              setImageUrl('');
              return;
            }
            if (base64.includes(IMAGE_NOT_FOUND_B64_MARKER) && retryCount < MAX_IMAGE_RETRIES) {
              retryCount++;
              retryTimer = setTimeout(loadImage, IMAGE_RETRY_DELAY_MS);
            } else {
              setImageUrl(base64);
            }
          })
          .catch((error) => {
            if (cancelled) return;
            console.error('[FilePreview] Failed to load image:', { path, error });
          });
      };

      loadImage();

      return () => {
        cancelled = true;
        clearTimeout(retryTimer);
      };
    }

    return undefined;
  }, [isImage, path]);

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRemove();
  };

  const withHint = (chip: React.ReactElement) => (hint ? <Tooltip content={hint}>{chip}</Tooltip> : chip);

  if (isImage) {
    return withHint(
      <div className='kel-attachment-chip'>
        <button type='button' className='kel-attachment-chip__open' onClick={() => setPreviewOpen(true)} disabled={!imageUrl} aria-label={`Preview ${file_name}`}>
          {imageUrl ? <img src={imageUrl} alt='' /> : <span className='kel-attachment-chip__placeholder' />}
          <span className='kel-attachment-chip__text'><span title={file_name}>{file_name}</span><small>{fileSize || '...'}</small></span>
        </button>
        {!readonly && (
          <button type='button' className='kel-attachment-chip__remove' onClick={handleRemove} aria-label={`Remove ${file_name}`}>
            <Close theme='filled' size='10' fill='var(--text-secondary)' />
          </button>
        )}
        {previewOpen && imageUrl && <KelImageLightbox src={imageUrl} name={file_name} detail={[fileSize, imageDimensions].filter(Boolean).join(' · ')} onClose={() => setPreviewOpen(false)} />}
      </div>
    );
  }

  return withHint(
    <div className='relative inline-block mb-10px'>
      <div
        className='h-60px flex items-center gap-12px px-12px rd-8px bg-bg-2 border border-solid'
        style={{ borderColor: 'var(--border-base)', boxShadow: '0 0 0 1px rgba(0,0,0,0.02)' }}
      >
        <div className='w-40px h-40px rd-8px flex items-center justify-center flex-shrink-0'>
          <img className='w-full h-full object-contain' src={fileIcon} alt='File Icon' />
        </div>
        <div className='flex flex-col gap-2px min-w-0'>
          <span className='text-14px text-t-primary max-w-150px truncate'>{file_name}</span>
          <span className='text-12px text-t-secondary'>
            {fileExt}: {fileSize || '...'}
          </span>
        </div>
      </div>
      {!readonly && (
        <div
          className='absolute -top-4px -end-4px w-16px h-16px rd-50% bg-white dark:bg-gray-700 cursor-pointer flex items-center justify-center shadow-md hover:shadow-lg transition-all z-10 border-1 border-solid border-gray-200 dark:border-gray-600'
          onClick={handleRemove}
        >
          <Close theme='filled' size='10' fill='var(--text-secondary)' />
        </div>
      )}
    </div>
  );
};

export default FilePreview;
