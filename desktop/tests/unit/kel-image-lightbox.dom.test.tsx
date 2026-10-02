import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import KelImageLightbox from '@renderer/components/media/KelImageLightbox';

describe('image lightbox', () => {
  it('shows simple image actions and closes on Escape or the scrim', () => {
    const onClose = vi.fn();
    render(<KelImageLightbox src='data:image/png;base64,AA==' name='sample.png' detail='1.2 MB · 1920×1080' onClose={onClose} />);
    expect(screen.getByRole('dialog', { name: 'Image preview' })).toBeTruthy();
    expect(screen.queryByText('sample.png')).toBeNull();
    expect(screen.queryByText('1.2 MB · 1920×1080')).toBeNull();
    expect(screen.getByRole('button', { name: 'Zoom image' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Save image' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Copy image' })).toBeNull();
    fireEvent.mouseDown(screen.getByRole('img', { name: 'Image' }));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.mouseDown(document.querySelector('.kel-image-lightbox')!);
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it('toggles zoom without replacing the image or panel', () => {
    render(<KelImageLightbox src='data:image/png;base64,AA==' name='sample.png' onClose={vi.fn()} />);
    const image = screen.getByRole('img');
    const dialog = screen.getByRole('dialog');
    fireEvent.click(screen.getByRole('button', { name: 'Zoom image' }));
    expect(screen.getByRole('button', { name: 'Fit image' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('region').classList.contains('is-zoomed')).toBe(true);
    expect(screen.getByRole('img')).toBe(image);
    expect(screen.getByRole('dialog')).toBe(dialog);
    fireEvent.click(screen.getByRole('button', { name: 'Fit image' }));
    expect(screen.queryByRole('region')).toBeNull();
  });

  it('keeps keyboard focus inside and restores the opener and page scrolling', () => {
    const opener = document.createElement('button');
    document.body.appendChild(opener);
    opener.focus();
    const previousOverflow = document.body.style.overflow;
    const { unmount } = render(<KelImageLightbox src='data:image/png;base64,AA==' name='sample.png' onClose={vi.fn()} />);
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Close image preview' }));
    fireEvent.keyDown(window, { key: 'Tab' });
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Zoom image' }));
    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Close image preview' }));
    unmount();
    expect(document.activeElement).toBe(opener);
    expect(document.body.style.overflow).toBe(previousOverflow);
    opener.remove();
  });

  it('awaits the existing binary save callback and keeps repeated saves disabled', async () => {
    let finish!: () => void;
    const onDownload = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
    render(<KelImageLightbox src='data:image/png;base64,AA==' name='sample.png' onDownload={onDownload} onClose={vi.fn()} />);
    const save = screen.getByRole('button', { name: 'Save image' }) as HTMLButtonElement;
    fireEvent.click(save);
    fireEvent.click(save);
    expect(onDownload).toHaveBeenCalledTimes(1);
    expect(save.disabled).toBe(true);
    finish();
    await waitFor(() => expect(save.disabled).toBe(false));
  });

  it('preserves the original image bytes and filename in the fallback download', () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.href).toBe('data:image/png;base64,AA==');
      expect(this.download).toBe('sample.png');
    });
    render(<KelImageLightbox src='data:image/png;base64,AA==' name='sample.png' onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Save image' }));
    expect(click).toHaveBeenCalledTimes(1);
    expect(document.querySelector('a[download]')).toBeNull();
    click.mockRestore();
  });
});
