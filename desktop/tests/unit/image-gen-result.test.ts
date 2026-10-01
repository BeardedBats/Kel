import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

const { complete } = vi.hoisted(() => ({ complete: vi.fn() }));
vi.mock('@/common/api/ClientFactory', () => ({
  ClientFactory: { createRotatingClient: vi.fn(async () => ({ createChatCompletion: complete })) },
}));

import { executeImageGeneration } from '@/common/chat/imageGenCore';

describe('image generation requires an image result', () => {
  let workspace: string;
  const provider = { id: 'fixture', name: 'Fixture', platform: 'openai', base_url: '', api_key: '', use_model: 'fixture-image' };

  beforeEach(() => {
    workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-image-result-'));
    complete.mockReset();
  });
  afterEach(() => {
    const resolved = path.resolve(workspace);
    if (path.dirname(resolved) !== path.resolve(os.tmpdir()) || !path.basename(resolved).startsWith('kel-image-result-')) {
      throw new Error('Refusing cleanup outside the owned image fixture');
    }
    fs.rmSync(resolved, { recursive: true, force: true });
  });

  it('does not mark a prose or prompt response successful', async () => {
    complete.mockResolvedValue({ choices: [{ message: { content: 'Here is a prompt to create your infographic.' } }] });
    const result = await executeImageGeneration({ prompt: 'Create an infographic.' }, provider, workspace);
    expect(result).toMatchObject({ success: false, error: 'Image generation returned no image.' });
    expect(result.imagePath).toBeUndefined();
    expect(fs.readdirSync(workspace)).toEqual([]);
  });

  it('does not mark an unusable image entry successful', async () => {
    complete.mockResolvedValue({ choices: [{ message: { content: 'Done.', images: [{ type: 'image_url', image_url: {} }] } }] });
    const result = await executeImageGeneration({ prompt: 'Create an infographic.' }, provider, workspace);
    expect(result).toMatchObject({ success: false, error: 'Image generation returned no usable image.' });
    expect(result.imagePath).toBeUndefined();
    expect(fs.readdirSync(workspace)).toEqual([]);
  });

  it('preserves a returned image as a local artifact', async () => {
    const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6iucAAAAASUVORK5CYII=';
    complete.mockResolvedValue({ choices: [{ message: { content: 'Created the image.', images: [{ type: 'image_url', image_url: { url: 'data:image/png;base64,' + png } }] } }] });
    const result = await executeImageGeneration({ prompt: 'Create an infographic.' }, provider, workspace);
    expect(result.success).toBe(true);
    expect(result.imagePath).toBeDefined();
    expect(fs.readFileSync(result.imagePath!)).toEqual(Buffer.from(png, 'base64'));
    expect(path.dirname(result.imagePath!)).toBe(workspace);
  });
});
