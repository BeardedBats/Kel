import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import KelGeneratedImage, { parseKelImageReference } from '@renderer/components/media/KelGeneratedImage';
import MarkdownView from '@renderer/components/Markdown';

vi.mock('@renderer/components/media/LocalImageView', () => ({
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}));
vi.mock('@renderer/components/Markdown/ShadowView', () => ({ default: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock('@renderer/components/Markdown/CodeBlock', () => ({ default: () => null }));
vi.mock('@renderer/components/Markdown/LocalFileLink', () => ({ default: ({ children }: { children: React.ReactNode }) => <span>{children}</span> }));
vi.mock('@renderer/pages/conversation/Preview/context/PreviewContext', () => ({ useOptionalPreviewContext: () => null }));
vi.mock('@renderer/utils/platform', () => ({ openExternalUrl: vi.fn(async () => {}) }));

const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6iucAAAAASUVORK5CYII=';
const receipt = { base64: png, media_type: 'image/png' as const, width: 1, height: 1, sha256: 'a'.repeat(64) };

afterEach(() => { cleanup(); delete window.kelAPI; vi.restoreAllMocks(); });

describe('checked image delivery', () => {
  it('addresses a checked artifact without accepting paths, queries or encoded traversal', () => {
    expect(parseKelImageReference('kel-image://job-ab12/image')).toEqual({ job: 'job-ab12', milestone: 'image' });
    for (const src of ['kel-image://../image', 'kel-image://job/../image', 'kel-image://job/%2e%2e',
      'kel-image://job/image?path=C:/secret.png', 'kel-image://job/image#other', 'C:/secret.png', 'https://example.com/image.png']) {
      expect(parseKelImageReference(src)).toBeNull();
    }
  });

  it('loads, opens and saves the image bytes using the checked receipt', async () => {
    const imageArtifact = vi.fn(async () => receipt);
    window.kelAPI = { imageArtifact } as unknown as Window['kelAPI'];
    render(<KelGeneratedImage src='kel-image://job-ab12/image' alt='Generated infographic' />);
    const image = await screen.findByRole('img', { name: 'Generated infographic' });
    expect(imageArtifact).toHaveBeenCalledWith('job-ab12', 'image');
    expect(image.getAttribute('src')).toBe('data:image/png;base64,' + png);
    fireEvent.click(screen.getByRole('button', { name: 'Open image', exact: true }));
    expect(screen.getByRole('dialog', { name: 'Preview kel-image-job-ab12-image.png' })).toBeTruthy();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Open generated image' }));
    let saved: { href: string; name: string } | undefined;
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      saved = { href: this.href, name: this.download };
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save image' }));
    expect(saved).toEqual({ href: 'data:image/png;base64,' + png, name: 'kel-image-job-ab12-image.png' });
  });

  it('renders the published Markdown reference through the checked image bridge', async () => {
    const imageArtifact = vi.fn(async () => receipt);
    window.kelAPI = { imageArtifact } as unknown as Window['kelAPI'];
    render(<MarkdownView>{'Your image is ready.\n\n![Generated infographic](kel-image://job-ab12/image)'}</MarkdownView>);
    expect(await screen.findByRole('img', { name: 'Generated infographic' })).toBeTruthy();
    expect(imageArtifact).toHaveBeenCalledWith('job-ab12', 'image');
    expect(screen.getByRole('button', { name: 'Save image' })).toBeTruthy();
  });

  it('shows a plain failure and can retry without showing prompt text as an image', async () => {
    const imageArtifact = vi.fn().mockRejectedValueOnce(new Error('Image generation is not set up.')).mockResolvedValueOnce(receipt);
    window.kelAPI = { imageArtifact } as unknown as Window['kelAPI'];
    render(<KelGeneratedImage src='kel-image://job-ab12/image' />);
    expect((await screen.findByRole('alert')).textContent).toContain('Image generation is not set up.');
    expect(screen.queryByRole('img')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('img', { name: 'Generated image' })).toBeTruthy();
    await waitFor(() => expect(imageArtifact).toHaveBeenCalledTimes(2));
  });

  it('rejects text and invalid references before creating a visible image', async () => {
    const imageArtifact = vi.fn(async () => ({ ...receipt, base64: 'Here is a prompt.' }));
    window.kelAPI = { imageArtifact } as unknown as Window['kelAPI'];
    const mounted = render(<KelGeneratedImage src='kel-image://job-ab12/image' />);
    expect((await screen.findByRole('alert')).textContent).toContain('Kel could not load the checked image.');
    expect(screen.queryByRole('img')).toBeNull();
    mounted.rerender(<KelGeneratedImage src='kel-image://../image' />);
    expect(await screen.findByText('This image reference is invalid.')).toBeTruthy();
    expect(imageArtifact).toHaveBeenCalledTimes(1);
  });

  it('rejects image receipts beyond the delivery size and dimension limits', async () => {
    for (const extra of [
      { width: 8193 }, { height: 8193 }, { width: 8192, height: 8192 },
      { base64: png + 'A'.repeat(6_666_669 - png.length) },
    ]) {
      window.kelAPI = { imageArtifact: vi.fn(async () => ({ ...receipt, ...extra })) } as unknown as Window['kelAPI'];
      const mounted = render(<KelGeneratedImage src='kel-image://job-ab12/image' />);
      expect((await screen.findByRole('alert')).textContent).toContain('Kel could not load the checked image.');
      expect(screen.queryByRole('img')).toBeNull();
      mounted.unmount();
    }
  });
});
