import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import KelImageLightbox from '@renderer/components/media/KelImageLightbox';

describe('image lightbox', () => {
  it('shows file details and closes on Escape or the scrim', () => {
    const onClose = vi.fn();
    render(
      <KelImageLightbox src='data:image/png;base64,AA==' name='sample.png' detail='1.2 MB · 1920×1080' onClose={onClose} />
    );
    expect(screen.getByRole('dialog', { name: 'Preview sample.png' })).toBeTruthy();
    expect(screen.getByText('1.2 MB · 1920×1080')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Copy image' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Download image' })).toBeTruthy();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.mouseDown(document.querySelector('.kel-image-lightbox')!);
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
