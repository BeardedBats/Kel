/**
 * D4 — transcription surface policy pins.
 *
 * The transcription page is the human face of the engine's /api/transcription family. These pins
 * keep the hard rules attached to that surface:
 *   1. NO spacebar start/stop shortcut (Escape is the only recording shortcut, and it cancels).
 *   2. Core library actions stay wired to the engine's action family (record/upload/live/combine/
 *      exports/key setup).
 *   3. Search narrows the existing library client-side — a second document store must never appear.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoDesktop = path.resolve(here, '..', '..');
const page = readFileSync(
  path.join(repoDesktop, 'packages', 'desktop', 'src', 'renderer', 'pages', 'kel', 'transcription', 'index.tsx'),
  'utf8'
);

describe('transcription page policy (D4)', () => {
  it('never binds the spacebar while recording (Escape cancels; Space stays free)', () => {
    expect(page).not.toMatch(/event\.code\s*===\s*'Space'/);
    expect(page).not.toMatch(/event\.key\s*===\s*' '\s*\)/);
    expect(page).not.toMatch(/event\.key\s*===\s*'Space/);
    expect(page).not.toMatch(/addEventListener\('keypress'/);
    // Escape remains the only recording shortcut.
    expect(page).toMatch(/event\.key === 'Escape'/);
  });

  it('keeps the library actions wired to the engine family', () => {
    for (const needle of [
      "action: 'upload'",
      "action: 'save_recording'",
      "action: 'quick_transcribe'",
      "action: 'stream_start'",
      "action: 'stream_chunk'",
      "action: 'stream_status'",
      "action: 'stream_finish'",
      "action: 'combine'",
      "action: 'export_audio'",
      "action: 'set_key'",
      "action: 'clear_key'",
      "action: 'folder_create'",
      "action: 'assign'",
      "action: 'rename'",
      "action: 'delete'",
    ]) {
      expect(page, needle).toContain(needle);
    }
    // Text export downloads the already-loaded transcript (the engine still offers export_text for
    // other clients; the UI simply does not need an extra round-trip for text).
    expect(page).toContain("selected.text || ''");
  });

  it('searches recents client-side over the one library (no second store)', () => {
    expect(page).toContain("data-testid='transcript-search'");
    expect(page).toContain('Search transcripts');
    expect(page).toContain('visibleRecent');
    expect(page).toContain('No transcripts match that search.');
    // The search only filters the already-loaded library rows.
    expect(page).not.toMatch(/action:\s*'search'/);
  });

  it('exposes the human download/copy/share affordances', () => {
    for (const needle of [
      "data-testid='download-txt'",
      "data-testid='download-audio'",
      "data-testid='copy-transcript'",
      "data-testid='send-to-chat'",
      "data-testid='record-button'",
      "data-testid='upload-button'",
      "data-testid='stop-button'",
      "data-testid='cancel-button'",
    ]) {
      expect(page, needle).toContain(needle);
    }
  });
});
