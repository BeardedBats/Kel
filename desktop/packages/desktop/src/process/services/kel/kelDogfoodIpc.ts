/**
 * Fix Capture — window screenshot custody (V2.0 preflight).
 *
 * The renderer can describe a clicked element, but only the main process can read the window's
 * pixels. This handler captures the Kel window (never the desktop, never another app), writes the
 * PNG into `<data-root>/dogfood/tmp/`, and hands the renderer a data-root-relative path plus the
 * window metrics. The engine then commits that file under the fix id when the fix is saved — so a
 * screenshot either belongs to a saved fix or is a stale temporary, never a half-record.
 *
 * Same privileged-channel guard as the other Kel IPC families.
 */
import { BrowserWindow, ipcMain, screen } from 'electron';
import { randomUUID } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { assertTrustedSender } from '../../../common/senderGuard';

export interface KelDogfoodCapture {
  /** Data-root-relative path of the temporary capture, e.g. `dogfood/tmp/<uuid>.png`. */
  screenshot: string;
  /** The captured image in pixels (the PNG's own size). */
  image: { width: number; height: number };
  /** The window's content size in CSS pixels — what a DOM rect is measured against. */
  content: { width: number; height: number };
  /** The display the window sits on (scale only; never a screen grab). */
  display: { scale: number };
  captured_at: number;
}

export interface KelDogfoodIpcDeps {
  /** The engine data root (the same directory the engine is launched against). */
  dataRoot: () => string;
}

const SCREENSHOT_FOLDER = ['dogfood', 'screenshots'];
const MAX_SCREENSHOT_BYTES = 12 * 1024 * 1024;

/** Resolve `relpath` and require it to be a PNG directly inside `<data-root>/dogfood/screenshots`. */
const resolveScreenshot = (root: string, relpath: string): string => {
  const base = path.resolve(path.join(root, ...SCREENSHOT_FOLDER));
  const target = path.resolve(root, String(relpath || ''));
  if (path.dirname(target) !== base) throw new Error('That image is not a Kel screenshot');
  if (path.extname(target).toLowerCase() !== '.png') throw new Error('That image is not a Kel screenshot');
  return target;
};

export const registerKelDogfoodIpc = (deps: KelDogfoodIpcDeps): void => {
  ipcMain.handle('kel:dogfood-capture', async (event): Promise<KelDogfoodCapture> => {
    assertTrustedSender(event, { allowDevServer: true });
    const win = BrowserWindow.fromWebContents(event.sender);
    if (!win) throw new Error('Kel could not read its own window.');

    // capturePage() reads this window's contents only — never the desktop, never another app.
    const image = await win.webContents.capturePage();
    const png = image.toPNG();
    if (!png?.length) throw new Error('Kel could not capture the window.');

    const root = path.resolve(deps.dataRoot());
    const tmpDir = path.join(root, 'dogfood', 'tmp');
    fs.mkdirSync(tmpDir, { recursive: true });
    const file = path.join(tmpDir, `${randomUUID()}.png`);
    fs.writeFileSync(file, png);

    const [contentWidth, contentHeight] = win.getContentSize();
    const display = screen.getDisplayMatching(win.getBounds());
    return {
      screenshot: path.relative(root, file).split(path.sep).join('/'),
      image: { width: image.getSize().width, height: image.getSize().height },
      content: { width: contentWidth, height: contentHeight },
      display: { scale: display.scaleFactor },
      captured_at: Date.now(),
    };
  });

  // Showing a saved screenshot in the Dogfood Fixes view: a bounded, validated read of one PNG
  // inside the dogfood folder. No other path can be read through this channel.
  ipcMain.handle('kel:dogfood-screenshot', (event, relpath: string): { data_url: string } => {
    assertTrustedSender(event, { allowDevServer: true });
    const root = path.resolve(deps.dataRoot());
    const file = resolveScreenshot(root, relpath);
    const stat = fs.statSync(file);
    if (stat.size > MAX_SCREENSHOT_BYTES) throw new Error('That screenshot is too large to show');
    return { data_url: `data:image/png;base64,${fs.readFileSync(file).toString('base64')}` };
  });
};
