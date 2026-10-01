/** A private main-process image worker; provider keys never reach Kel's renderer or engine. */
import { nativeImage } from 'electron';
import fs from 'node:fs/promises';
import path from 'node:path';
import { executeImageGeneration } from '@/common/chat/imageGenCore';
import { resolveImageGenerationMcpEnv } from '@/common/config/imageGenerationMcpEnv';
import type { ImageGenerationModelSetting } from '@/common/config/clientSettings';
import type { IProvider, TProviderWithModel } from '@/common/config/storage';

type Request = (route: string, body?: unknown, timeoutMs?: number) => Promise<any>;
type Backend = (route: string, body?: unknown, method?: string) => Promise<any>;
type Task = { run_id: string; token: string; prompt: string };
const MAX_BYTES = 5_000_000;
const ID = /^[a-zA-Z0-9_-]{1,128}$/;

export function startImageWorker(request: Request, backend: Backend, root: string): () => void {
  let stopped = false;
  let polling = false;
  let controller: AbortController | undefined;
  let selected: TProviderWithModel | undefined;
  let refreshed = 0;

  const refresh = async () => {
    if (Date.now() - refreshed < 10_000) return;
    refreshed = Date.now();
    selected = undefined;
    const [preferences, providers] = await Promise.all([
      backend('/api/settings/client'), backend('/api/providers'),
    ]);
    const choice = preferences?.['tools.imageGenerationModel'] as ImageGenerationModelSetting | undefined;
    if (choice?.switch !== true) return;
    const resolved = resolveImageGenerationMcpEnv(choice, (providers || []) as IProvider[]);
    if (resolved.ok && resolved.provider.enabled !== false) {
      selected = { ...resolved.provider, use_model: resolved.model };
    }
  };

  const execute = async (task: Task, provider: TProviderWithModel) => {
    if (!ID.test(task.run_id) || !ID.test(task.token) || typeof task.prompt !== 'string') return;
    const taskController = new AbortController();
    controller = taskController;
    const active = setInterval(() => {
      void request('/api/image-worker', { action: 'active', run_id: task.run_id, token: task.token }, 4000)
        .then((state) => { if (!state?.active) taskController.abort(); })
        .catch(() => taskController.abort());
    }, 2000);
    active.unref?.();
    const workspace = path.join(root, 'image-provider-work', task.run_id);
    try {
      await fs.mkdir(workspace, { recursive: true });
      const result = await executeImageGeneration({ prompt: task.prompt }, provider, workspace, undefined, taskController.signal);
      if (!result.success || !result.imagePath) throw new Error('missing_image');
      const realRoot = await fs.realpath(workspace);
      const imagePath = await fs.realpath(result.imagePath);
      const relative = path.relative(realRoot, imagePath);
      if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('invalid_image_path');
      const stat = await fs.stat(imagePath);
      if (!stat.isFile() || stat.size > MAX_BYTES) throw new Error('image_size');
      const image = nativeImage.createFromPath(imagePath);
      const size = image.getSize();
      if (image.isEmpty() || !size.width || !size.height || size.width > 8192 || size.height > 8192 ||
          size.width * size.height > 16 * 1024 * 1024)
        throw new Error('invalid_image');
      const png = image.toPNG();
      if (png.byteLength > MAX_BYTES) throw new Error('image_size');
      if (taskController.signal.aborted || stopped) return;
      await request('/api/image-worker', {
        action: 'result', run_id: task.run_id, token: task.token, base64: png.toString('base64'),
      });
    } catch {
      if (!stopped) await request('/api/image-worker', {
        action: 'result', run_id: task.run_id, token: task.token,
        error: 'The image tool did not deliver a usable image. No image was delivered. Check Settings > Tools, then retry.',
      }).catch((): undefined => undefined);
    } finally {
      clearInterval(active);
      if (controller === taskController) controller = undefined;
    }
  };

  const tick = async () => {
    if (polling || stopped) return;
    polling = true;
    try {
      await refresh();
      const provider = selected;
      const response = await request('/api/image-worker', {
        action: 'poll', ready: Boolean(provider), provider: provider?.id, model: provider?.use_model,
      }, 4000);
      if (response?.task && provider && !stopped) await execute(response.task as Task, provider);
    } catch {
      // An unavailable provider or engine never creates a receipt. Try the link on the next tick.
    } finally { polling = false; }
  };
  const timer = setInterval(() => void tick(), 3000);
  timer.unref?.();
  void tick();
  return () => { stopped = true; clearInterval(timer); controller?.abort(); };
}
