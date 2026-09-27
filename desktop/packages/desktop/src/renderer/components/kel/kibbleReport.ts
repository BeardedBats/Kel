/**
 * ST-02 — "Report issue" saves a Kibble fix on this computer instead of the donor report form
 * (which sent nothing in Kel builds and still said it had). The diagnostics become the fix's note;
 * the fix starts OPEN like any other Kibble capture.
 */
import { kelDogfood } from './kelApi';

declare const __APP_VERSION__: string | undefined;

export type KibbleReportInput = {
  /** One plain line naming what failed, e.g. `MCP server "github" failed its check`. */
  title: string;
  /** Where the report came from (a feedback module tag such as `mcp-tools`). */
  area?: string;
  /** Diagnostic fields; objects are written as compact JSON. */
  details?: Record<string, unknown>;
};

const MAX_FIELD = 2000;

const fieldText = (value: unknown): string => {
  if (value === undefined || value === null) return '';
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  return text.length > MAX_FIELD ? `${text.slice(0, MAX_FIELD)}…` : text;
};

export const buildKibbleReportNote = ({ title, area, details = {} }: KibbleReportInput): string => {
  const lines = [title.trim() || 'Reported issue'];
  if (area) lines.push(`Area: ${area}`);
  for (const [key, value] of Object.entries(details)) {
    const text = fieldText(value);
    if (text) lines.push(`${key}: ${text}`);
  }
  return lines.join('\n');
};

const currentRoute = (): string | null => {
  if (typeof window === 'undefined') return null;
  const hash = window.location.hash.replace(/^#/, '');
  return hash || window.location.pathname || null;
};

/** Save the report as a Kibble fix. Resolves with the fix id; rejects with Kel's own sentence. */
export const saveReportToKibble = async (input: KibbleReportInput): Promise<string> => {
  const saved = await kelDogfood.save({
    transcript: buildKibbleReportNote(input),
    route: currentRoute(),
    page_title: typeof document === 'undefined' ? null : document.title || null,
    version: typeof __APP_VERSION__ === 'string' ? __APP_VERSION__ : null,
  });
  return saved.id;
};
