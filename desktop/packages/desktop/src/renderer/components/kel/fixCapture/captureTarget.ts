/**
 * Fix Capture (V2.0 preflight) — reading one clicked element into durable context.
 *
 * These are deliberately pure functions so the capture itself can be tested without a running app:
 * what text an element shows, how a stable locator is built, and how the target rectangle maps onto
 * the captured screenshot. Never stores form-control values (a fix must not archive a secret).
 */
export interface CapturedElement {
  tag: string;
  role: string | null;
  /** Visible words of the element, bounded. Never a form-control value. */
  text: string;
  /** aria-label / title / placeholder / name — the words a person sees about a control. */
  label: string | null;
  selector: string;
  rect: { x: number; y: number; width: number; height: number };
}

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

const MAX_TEXT = 160;
const MAX_LABEL = 80;
const MAX_SELECTOR = 220;
const SELECTOR_DEPTH = 4;

const FORM_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT']);

export const collapse = (value: string | null | undefined): string => String(value ?? '').replace(/\s+/g, ' ').trim();

export const shortPreview = (value: string | null | undefined, limit = 90): string => {
  const text = collapse(value);
  return text.length > limit ? `${text.slice(0, limit - 1).trimEnd()}…` : text;
};

/** Visible words of an element; form controls contribute their label instead of their value. */
export function elementText(element: Element | null): string {
  if (!element) return '';
  if (FORM_TAGS.has(element.tagName)) return '';
  const raw = (element as HTMLElement).innerText ?? element.textContent ?? '';
  const text = collapse(raw);
  return text.length > MAX_TEXT ? `${text.slice(0, MAX_TEXT - 1).trimEnd()}…` : text;
}

export function elementLabel(element: Element | null): string | null {
  if (!element) return null;
  const read = (name: string) => element.getAttribute(name) ?? '';
  const label = collapse(
    read('aria-label') || read('title') || read('placeholder') || read('name') || read('alt') || ''
  );
  if (!label) return null;
  return label.length > MAX_LABEL ? `${label.slice(0, MAX_LABEL - 1).trimEnd()}…` : label;
}

const escapeAttribute = (value: string): string => value.replace(/["\\]/g, '\\$&');

const looksGenerated = (value: string): boolean =>
  /^[0-9a-f]{8,}$/i.test(value) || /^[0-9a-f-]{16,}$/i.test(value) || /\d{6,}/.test(value);

const nodeSegment = (element: Element): string => {
  const parent = element.parentElement;
  if (!parent) return element.tagName.toLowerCase();
  const sameTag = Array.from(parent.children).filter((child) => child.tagName === element.tagName);
  if (sameTag.length <= 1) return element.tagName.toLowerCase();
  return `${element.tagName.toLowerCase()}:nth-of-type(${sameTag.indexOf(element) + 1})`;
};

/** A stable-enough locator: testid first, then a real id, then labelled, then a short path. */
export function buildSelector(element: Element | null): string {
  if (!element) return '';
  const testId = collapse(element.getAttribute('data-testid'));
  if (testId) return clip(`[data-testid="${escapeAttribute(testId)}"]`);
  const id = collapse(element.getAttribute('id'));
  if (id && !looksGenerated(id)) return clip(`#${id}`);
  const aria = collapse(element.getAttribute('aria-label'));
  if (aria) return clip(`${element.tagName.toLowerCase()}[aria-label="${escapeAttribute(aria)}"]`);
  const path: string[] = [];
  let node: Element | null = element;
  for (let depth = 0; node && depth < SELECTOR_DEPTH; depth += 1) {
    path.unshift(nodeSegment(node));
    if (node.parentElement === document.body || !node.parentElement) break;
    node = node.parentElement;
  }
  return clip(path.join(' > '));
}

const clip = (value: string): string => (value.length > MAX_SELECTOR ? value.slice(0, MAX_SELECTOR) : value);

export function describeElement(element: Element | null): CapturedElement | null {
  if (!element) return null;
  const box = element.getBoundingClientRect();
  return {
    tag: element.tagName.toLowerCase(),
    role: collapse(element.getAttribute('role')) || null,
    text: elementText(element),
    label: elementLabel(element),
    selector: buildSelector(element),
    rect: {
      x: Math.round(box.left),
      y: Math.round(box.top),
      width: Math.round(box.width),
      height: Math.round(box.height),
    },
  };
}

/**
 * Map a DOM rectangle (CSS pixels) into the captured image's pixel space. `image` is the PNG's own
 * size, so this stays correct at any device scale factor without guessing.
 */
export function imageRect(rect: Rect, content: { width: number; height: number }, image: { width: number; height: number }): Rect {
  const scaleX = content.width > 0 ? image.width / content.width : 1;
  const scaleY = content.height > 0 ? image.height / content.height : 1;
  return {
    x: Math.round(rect.x * scaleX),
    y: Math.round(rect.y * scaleY),
    width: Math.round(rect.width * scaleX),
    height: Math.round(rect.height * scaleY),
  };
}

/**
 * Where the floating panel goes: beside the target, never on top of it when there is room.
 * `gap` keeps a little air between the panel and the highlighted area.
 */
export function panelPlacement(
  target: Rect,
  viewport: { width: number; height: number },
  panel: { width: number; height: number },
  gap = 12
): { top: number; left: number; side: 'right' | 'left' | 'below' | 'above' } {
  const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), Math.max(min, max));
  const left = target.x + target.width + gap;
  if (left + panel.width <= viewport.width - 8) {
    return { left, top: clamp(target.y, 8, viewport.height - panel.height - 8), side: 'right' };
  }
  const right = target.x - panel.width - gap;
  if (right >= 8) {
    return { left: right, top: clamp(target.y, 8, viewport.height - panel.height - 8), side: 'left' };
  }
  const below = target.y + target.height + gap;
  if (below + panel.height <= viewport.height - 8) {
    return { left: clamp(target.x, 8, viewport.width - panel.width - 8), top: below, side: 'below' };
  }
  return {
    left: clamp(target.x, 8, viewport.width - panel.width - 8),
    top: clamp(target.y - panel.height - gap, 8, viewport.height - panel.height - 8),
    side: 'above',
  };
}
