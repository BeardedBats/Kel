/**
 * V2.0 preflight — Fix Capture pins (node).
 *
 * The feature promises a short list of behaviours: one hotkey, one click, one thought, and nothing
 * recorded unless Save Fix is pressed. These tests hold that contract, plus the capture helpers that
 * turn a clicked element into context a coding session can use.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  buildSelector,
  collapse,
  describeElement,
  elementLabel,
  elementText,
  imageRect,
  panelPlacement,
  shortPreview,
} from '@renderer/components/kel/fixCapture/captureTarget';
import {
  fixCaptureReducer,
  initialFixCaptureState,
  isCapturing,
  type FixCaptureEvent,
  type FixCaptureState,
} from '@renderer/components/kel/fixCapture/fixCaptureMachine';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const layer = read('desktop/packages/desktop/src/renderer/components/kel/fixCapture/FixCaptureLayer.tsx');
const machine = read('desktop/packages/desktop/src/renderer/components/kel/fixCapture/fixCaptureMachine.ts');
const captureCss = read('desktop/packages/desktop/src/renderer/components/kel/fixCapture/fixCapture.module.css');
const dogfoodPage = read('desktop/packages/desktop/src/renderer/pages/kel/dogfood/index.tsx');
const layout = read('desktop/packages/desktop/src/renderer/components/layout/Layout.tsx');
const palette = read('desktop/packages/desktop/src/renderer/components/kel/KelCommandPalette.tsx');
const engine = read('runtime/kel/dogfood.py');
const engineService = read('runtime/kel/service.py');
const dogfoodIpc = read('desktop/packages/desktop/src/process/services/kel/kelDogfoodIpc.ts');
const hook = read('desktop/packages/desktop/src/renderer/components/kel/fixCapture/useFixCapture.ts');
const searchPopover = read(
  'desktop/packages/desktop/src/renderer/pages/conversation/GroupedHistory/ConversationSearchPopover.tsx'
);
const bridgeService = read('desktop/packages/desktop/src/process/services/kel/KelService.ts');
const preload = read('desktop/packages/desktop/src/preload/main.ts');
const kelApiSource = read('desktop/packages/desktop/src/renderer/components/kel/kelApi.ts');

const element = (markup: string): Element => {
  const host = document.createElement('div');
  host.innerHTML = markup;
  return host.firstElementChild as Element;
};

const run = (state: FixCaptureState, events: FixCaptureEvent[]): FixCaptureState =>
  events.reduce(fixCaptureReducer, state);

describe('Fix Capture — the hotkey', () => {
  it('is Ctrl+Shift+F through the app shortcut helper, never the spacebar', () => {
    expect(layer).toContain("isPrimaryApplicationShortcut(event, { key: 'f', shiftKey: true, targetGuard: 'embedded-editor' })");
    expect(layer).not.toMatch(/Space|spacebar/i);
    expect(machine).not.toMatch(/spacebar/i);
  });

  it('begins a capture, stops a recording, and always cancels on Escape', () => {
    expect(layer).toContain("if (phaseRef.current === 'idle') api.current.begin();");
    expect(layer).toContain("else if (phaseRef.current === 'recording') api.current.stop();");
    expect(layer).toContain("if (event.key === 'Escape' && phaseRef.current !== 'idle' && phaseRef.current !== 'saved')");
  });

  it('is mounted once by the shell, next to the command palette', () => {
    expect(layout).toContain('<FixCaptureLayer />');
    expect(layout).toContain("import FixCaptureLayer from '@renderer/components/kel/fixCapture/FixCaptureLayer';");
  });
});

describe('Fix Capture — the hotkey conflict, resolved deliberately', () => {
  it('claims Ctrl+Shift+F in the capture phase, ahead of the donor conversation search', () => {
    // Both bind the chord. Fix Capture listens on window in the capture phase and stops the event,
    // so the search handler (document capture) never sees it; the search keeps its own trigger and
    // the Ctrl+K palette path. Its raw binding stays in the source — that is the documented trade.
    expect(layer).toContain("window.addEventListener('keydown', onKeyDown, true);");
    expect(layer).toContain('event.stopPropagation();');
    expect(searchPopover).toContain(
      "document.addEventListener('keydown', handleGlobalSearchShortcut, true);"
    );
    expect(searchPopover).toContain("key: 'f',");
    expect(searchPopover).toContain('shiftKey: true,');
  });
});

describe('Fix Capture — the state machine', () => {
  const begin = (): FixCaptureState =>
    run(initialFixCaptureState, [
      { type: 'begin', route: '/providers', pageTitle: 'Kel', conversation: 'c-1' },
    ]);

  it('walks idle → selecting → preparing → recording → stopping → review → saving → saved', () => {
    const target = describeElement(element('<button aria-label="Set up">Set up</button>'))!;
    const state = run(begin(), [
      { type: 'pick', target },
      { type: 'capture', screenshot: null },
      { type: 'started' },
      { type: 'stop' },
      { type: 'stopped', text: 'the button does nothing' },
      { type: 'save' },
      { type: 'saved', id: 'FIX-0001' },
    ]);
    expect(state.phase).toBe('saved');
    expect(state.savedId).toBe('FIX-0001');
    expect(state.draft).toBe('the button does nothing');
    expect(state.route).toBe('/providers');
    expect(state.conversation).toBe('c-1');
  });

  it('cancels from every active phase and leaves nothing behind', () => {
    const target = describeElement(element('<div>card</div>'))!;
    for (const events of [
      [] as FixCaptureEvent[],
      [{ type: 'pick', target }] as FixCaptureEvent[],
      [{ type: 'pick', target }, { type: 'started' }] as FixCaptureEvent[],
      [{ type: 'pick', target }, { type: 'started' }, { type: 'stop' }] as FixCaptureEvent[],
      [{ type: 'pick', target }, { type: 'started' }, { type: 'stop' }, { type: 'stopped', text: 'x' }] as FixCaptureEvent[],
    ]) {
      const state = run(begin(), [...events, { type: 'cancel' }]);
      expect(state.phase).toBe('idle');
      expect(state.target).toBeNull();
      expect(state.draft).toBe('');
      expect(state.savedId).toBeNull();
    }
  });

  it('keeps the target and drops the words on Record Again', () => {
    const target = describeElement(element('<div>panel</div>'))!;
    const state = run(begin(), [
      { type: 'pick', target },
      { type: 'capture', screenshot: { screenshot: 'dogfood/tmp/a.png', image: { width: 2, height: 2 }, content: { width: 1, height: 1 }, display: { scale: 1 }, captured_at: 1 } },
      { type: 'started' },
      { type: 'stop' },
      { type: 'stopped', text: 'first attempt' },
      { type: 'again' },
    ]);
    expect(state.phase).toBe('recording');
    expect(state.target?.tag).toBe('div');
    expect(state.draft).toBe('');
    expect(state.live).toBe('');
    expect(state.seconds).toBe(0);
    expect(state.screenshot?.screenshot).toBe('dogfood/tmp/a.png');
  });

  it('treats a missing microphone as a typed capture, not a dead end', () => {
    const target = describeElement(element('<div>card</div>'))!;
    const state = run(begin(), [
      { type: 'pick', target },
      { type: 'capture', screenshot: null, note: 'A screenshot is not available on this surface.' },
      { type: 'mic-failed', note: 'The microphone did not start — type what happened instead.' },
    ]);
    expect(state.phase).toBe('review');
    expect(state.note).toContain('type what happened instead');
    expect(state.target?.tag).toBe('div');
  });

  it('never leaves saving or saved through an ordinary cancel', () => {
    expect(isCapturing('idle')).toBe(false);
    expect(isCapturing('saved')).toBe(false);
    const saving = run(begin(), [{ type: 'pick' as never, target: describeElement(element('<i>x</i>'))! }, { type: 'started' }, { type: 'stop' }, { type: 'stopped', text: 'y' }, { type: 'save' }]);
    expect(saving.phase).toBe('saving');
    expect(fixCaptureReducer(saving, { type: 'cancel' }).phase).toBe('saving');
  });
});

describe('Fix Capture — the preload exposes what the client calls', () => {
  it('wires capture and screenshot end to end (preload ↔ main ↔ client)', () => {
    // The renderer's declared shape is not the preload's implementation: a member can be declared,
    // called, and still missing from the bridge. This pin walks the whole path.
    expect(preload).toContain("capture: () => ipcRenderer.invoke('kel:dogfood-capture')");
    expect(preload).toContain(
      "screenshot: (relpath: string) => ipcRenderer.invoke('kel:dogfood-screenshot', relpath)"
    );
    expect(dogfoodIpc).toContain("ipcMain.handle('kel:dogfood-capture'");
    expect(dogfoodIpc).toContain("ipcMain.handle('kel:dogfood-screenshot'");
    expect(kelApiSource).toContain('api.dogfood.capture');
    expect(kelApiSource).toContain('api.dogfood.screenshot');
  });
});

describe('Fix Capture — the desktop bridge admits the route', () => {
  it('accepts every dogfood route the client uses, and nothing more', () => {
    // The main process keeps a route allowlist for `kel:request`; a new family has to be let in.
    // This pin reads the shipped regex itself and tries the routes the client actually sends.
    const allowSource = bridgeService.match(/!\/\^\\\/api\\\/\(([\s\S]*?)\)\$\/\.test\(/)?.[1];
    expect(allowSource, 'the kel:request allowlist must be findable').toBeTruthy();
    expect(allowSource).toContain('dogfood');
    const allow = new RegExp(`^/api/(${allowSource})$`);
    for (const route of [
      '/api/dogfood',
      '/api/dogfood?status=OPEN',
      '/api/dogfood?action=get&id=FIX-0007',
    ]) {
      expect(allow.test(route), `${route} must pass the bridge allowlist`).toBe(true);
    }
    expect(allow.test('/api/dogfood?action=save')).toBe(false);
    expect(allow.test('/api/secret')).toBe(false);
  });
});

describe('Fix Capture — reading the clicked element', () => {
  it('captures the visible words, the label and a locator', () => {
    const button = element('<button data-testid="kel-work-allow" aria-label="Approve this">Approve</button>');
    const target = describeElement(button)!;
    expect(target.tag).toBe('button');
    expect(target.text).toBe('Approve');
    expect(target.label).toBe('Approve this');
    expect(target.selector).toBe('[data-testid="kel-work-allow"]');
    expect(elementText(button)).toBe('Approve');
  });

  it('never stores a form-control value', () => {
    const input = element('<input type="password" value="sk-secret" aria-label="Anthropic API key" />');
    expect(elementText(input)).toBe('');
    expect(elementLabel(input)).toBe('Anthropic API key');
  });

  it('prefers a real id over a generated one, then falls back to a short path', () => {
    expect(buildSelector(element('<section id="providers-list"></section>'))).toBe('#providers-list');
    expect(buildSelector(element('<div id="a1b2c3d4e5f60718"></div>'))).toContain('div');
    const nested = element('<div><ul><li><span>deep</span></li></ul></div>');
    const span = nested.querySelector('span')!;
    expect(buildSelector(span)).toBe('div > ul > li > span');
  });

  it('maps a DOM rect into the captured image, whatever the scale', () => {
    expect(imageRect({ x: 10, y: 20, width: 30, height: 40 }, { width: 100, height: 200 }, { width: 200, height: 400 })).toEqual({
      x: 20,
      y: 40,
      width: 60,
      height: 80,
    });
    expect(imageRect({ x: 1, y: 1, width: 1, height: 1 }, { width: 0, height: 0 }, { width: 10, height: 10 })).toEqual({
      x: 1,
      y: 1,
      width: 1,
      height: 1,
    });
  });

  it('places the panel beside the target and never on top of it when there is room', () => {
    const panel = { width: 340, height: 250 };
    const viewport = { width: 1280, height: 800 };
    expect(panelPlacement({ x: 100, y: 100, width: 120, height: 40 }, viewport, panel).side).toBe('right');
    expect(panelPlacement({ x: 1100, y: 100, width: 150, height: 40 }, viewport, panel).side).toBe('left');
    // No room on either side and plenty below → under the target.
    const below = panelPlacement({ x: 20, y: 60, width: 1240, height: 40 }, viewport, panel);
    expect(below.side).toBe('below');
    expect(below.top).toBeGreaterThanOrEqual(60 + 40);
    // Nothing below either (the target sits near the bottom edge) → above it.
    const above = panelPlacement({ x: 20, y: 740, width: 1240, height: 40 }, viewport, panel);
    expect(above.side).toBe('above');
    expect(above.top + panel.height).toBeLessThanOrEqual(740);
    const clamped = panelPlacement({ x: 1270, y: 790, width: 8, height: 8 }, viewport, panel);
    expect(clamped.left).toBeGreaterThanOrEqual(8);
    expect(clamped.top).toBeGreaterThanOrEqual(8);
  });

  it('keeps previews short and single-line', () => {
    expect(shortPreview('  a\n\nb   c  ')).toBe('a b c');
    expect(shortPreview('x'.repeat(200)).length).toBeLessThanOrEqual(90);
    expect(collapse(undefined)).toBe('');
  });
});

describe('Fix Capture — where it is reachable from', () => {
  it('lives at /dogfood, offered by the palette, not by the sider', () => {
    expect(read('desktop/packages/desktop/src/renderer/components/layout/Router.tsx')).toContain(
      "import('@renderer/pages/kel/dogfood')"
    );
    expect(palette).toContain("path: '/dogfood'");
    expect(read('desktop/packages/desktop/src/renderer/components/layout/Sider/index.tsx')).not.toContain('/dogfood');
  });

  it('shows the four statuses and nothing resembling an issue tracker', () => {
    const statuses = read('desktop/packages/desktop/src/renderer/components/kel/kelApi.ts');
    expect(statuses).toContain("export const FIX_STATUSES = ['OPEN', 'BATCHED', 'FIXED', 'DISMISSED'] as const;");
    // Not the words (the surfaces explain what they deliberately do not have) — the fields. A fix
    // carries Nick's words and captured context, and nothing that would make this a tracker.
    for (const field of ['assignee', 'priority', 'due_date', 'sprint', 'labels']) {
      expect(engine).not.toMatch(new RegExp(`${field}\\s*[:=]`));
      expect(dogfoodPage).not.toMatch(new RegExp(`${field}\\s*[:=]`));
    }
  });

  it('never prints internal ids in the person-facing detail line', () => {
    expect(dogfoodPage).toContain("if (fix.project_id) bits.push('in a project');");
    expect(dogfoodPage).toContain("if (fix.conversation) bits.push('from a conversation');");
    expect(dogfoodPage).not.toContain('project ${');
  });

  it('says the prompt never starts development by itself', () => {
    expect(dogfoodPage).toContain('it never\n                starts development on its own');
  });
});

describe('Fix Capture — honest failure copy', () => {
  it('turns a device error into a sentence and offers the typed path', () => {
    expect(hook).toContain('friendlyMicError(error)');
    expect(hook).toContain('You can type what happened instead.');
  });

  it('quotes the engine (never the transport) when the transcript itself fails to start', () => {
    expect(hook).toContain(
      "failureSentence(error, 'Kel could not start the transcript — type what happened instead.')"
    );
  });
});

describe('Fix Capture — storage and styling rules', () => {
  it('keeps fixes and screenshots under the engine data root', () => {
    expect(engine).toContain("self.dogfood = self.root / 'dogfood'");
    expect(engine).toContain("self.screenshots = self.dogfood / 'screenshots'");
    expect(engine).toContain("self.tmp = self.dogfood / 'tmp'");
    expect(engine).toContain("self.prompts = self.dogfood / 'prompts'");
    expect(engineService).toContain("if path=='/api/dogfood':return self._dogfood_action(data)");
    expect(dogfoodIpc).toContain("path.join(root, 'dogfood', 'tmp')");
  });

  it('refuses screenshots outside the dogfood folder', () => {
    expect(engine).toContain("raise PolicyError('That screenshot is not inside Kel data.')");
    expect(dogfoodIpc).toContain('const resolveScreenshot = (root: string, relpath: string): string => {');
    expect(dogfoodIpc).toContain("throw new Error('That image is not a Kel screenshot');");
  });

  it('never uses accent rails (the Kel visual rule: no single-side colored borders)', () => {
    // Neutral full-perimeter borders and neutral between-row dividers are the house style; what the
    // rule forbids is a coloured edge or an accent rail on one side. The capture surfaces take the
    // stricter form: no single-side border at all.
    expect(captureCss).not.toMatch(/border-(left|right|top|bottom)\s*:/);
    for (const css of [captureCss, read('desktop/packages/desktop/src/renderer/pages/kel/dogfood/index.module.css')]) {
      expect(css).not.toMatch(
        /border-(left|right|top|bottom)\s*:\s*[^;]*(accent|run-|wait-|ok-|uncertain-|failed-|blocked-|#[0-9a-fA-F]{3})/
      );
      expect(css).not.toMatch(/(-left|-right|-top|-bottom)-color\s*:/);
    }
  });

  it('keeps its layering inside the app ladder', () => {
    expect(captureCss).toContain('z-index: 450');
    expect(captureCss).toContain('z-index: 452');
    expect(captureCss).not.toMatch(/z-index:\s*(9|1)\d{3}/);
  });

  it('carries exactly the ten instructions the prompt must give a coding session', () => {
    for (let index = 1; index <= 10; index += 1) {
      // Quote-agnostic: the source mixes ' and " because the instructions contain apostrophes.
      expect(engine).toMatch(new RegExp(`['"]${index}\\. `));
    }
    expect(engine).toContain('Return the exact Fix ids you verified as repaired');
    expect(engine).toContain('Do not mark a fix resolved merely because code changed');
  });
});
