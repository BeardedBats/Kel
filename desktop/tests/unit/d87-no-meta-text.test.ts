/**
 * D-87.2 — no meta descriptions. Nick removed every line that explains how Kel uses something or restates
 * the obvious (section subtitles, helper lines under fields, "Kel does X for you" copy). This pins that
 * the removed sentences stay gone from every renderer source and the English locale, so one cannot
 * quietly come back through a copy-paste. The Connections page's own removals are also proven in the DOM
 * by connections-page.dom.test.tsx.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const renderer = path.resolve(here, '..', '..', 'packages', 'desktop', 'src', 'renderer');

const sources = (dir: string): string[] =>
  readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return sources(full);
    return /\.(tsx?|json)$/.test(name) && !name.endsWith('.d.ts') ? [full] : [];
  });

const REMOVED = [
  // Connections
  'what Kel needs to reach the service',
  'Kel calls this to check the credential',
  'The services Kel can use. You keep the credential.',
  'Kel knows this address from the service',
  'Kel assumes the usual address',
  'Kel does not know this address; the service tells you',
  'Known services you can set up when you need them.',
  'Kel runs these only when you ask.',
  "Kel stores the value in this computer's secure store.",
  'Kel asks before it changes anything.',
  'Add a service and its credential. Then Kel can work with it directly.',
  'Services expect this differently',
  // Model
  "Kel uses this model for normal conversations",
  'Kel talks with you, plans and hands work to the staff on this model',
  'Automatic<span>Kel picks what is available</span>',
  'Add an API-backed model of your own.',
  // Staff & models
  'Kel hands real work to its staff, and each role runs on its own model',
  'For each kind of work: the staff setting that decides it',
  'Before bigger work Kel can ask two or three quick questions',
  // Permissions
  "Kel checks every action against safety rules that projects, repositories and web content can't change.",
  'Changes apply immediately — turning off a permission',
  'Ask whether Kel would be allowed to do something before any work runs',
  'Support detail — the references behind the Work column',
  'These safety rules are locked and cannot be changed by projects',
  // Providers
  'Values are never stored here.',
  'This checks routing only. It does not send a prompt',
  'The engine stores the provider, the field names, and a reference',
  'it goes to the OS store, never the engine',
  // Tools
  'Configure MCP servers and built-in tools',
  'Used to verify whether the MCP configuration is available',
  // Skills
  'Skills are ready-made instructions Kel can follow',
  // Set up Kel
  'Nothing leaves your computer unless you connect a provider.',
  'Choose the folder for the project new chats start in.',
  'You can change any of this later in Settings.',
  'Detected · ready',
  // Appearance
  'Select or customize a theme',
  // System
  'Open Kel automatically when you sign in to this computer.',
  'Closing the window keeps Kel running in the tray so background work continues.',
  'Tell you on the desktop when work finishes or Kel needs you',
  'Use the graphics card to draw Kel.',
  'How long Kel waits for a model to answer before giving up',
  'Stop helper processes that have been idle this long',
  'Text files larger than this open with a notice',
  'Launch Kel automatically when you sign in to macOS or Windows.',
  'Kill idle agent processes after this duration',
  'Stops this computer from sleeping while Kel is open',
  'Save a copy of your chats, projects and settings to a folder.',
  // Diagnostics
  'The report is built from an allowlist, not by filtering a dump',
  // Remote / WebUI
  'Turn on WebUI to reach Kel from your phone or a browser.',
  'Scan the QR code with your phone to log in automatically',
  // Archived
  'Conversations and teams you archived.</p>',
  'Archived chats will appear here.',
  // Projects, Knowledge, Recipes
  'Your active project is the same on every device.',
  'A project keeps its chats, knowledge and folder together.',
  'What Kel knows about how this project is built.',
  'Kel only changes what it knows when you agree',
  'clearing these first keeps it simple',
  'Kel records what it learns while working',
  'Kel builds a map of the project from its own verified work.',
  'Recipes capture a workflow Kel finished and verified',
  'Steps Kel saved from finished work. Run one again any time.',
  'Check the inputs. Then start the recipe.',
  'Review the inputs before Kel starts this recipe.',
  // Activity, Scheduled
  'When you ask Kel for something real, its progress shows up here.',
  'A scheduled task asks Kel to do the same thing on a schedule',
  'Skip a run if the last one is still going.',
  'If the last run has not finished, Kel skips this one.',
];

describe('D-87.2: the removed meta descriptions stay removed', () => {
  const files = sources(renderer).map((file) => ({ file, text: readFileSync(file, 'utf8') }));

  it('scans the renderer and its English locale', () => {
    expect(files.length).toBeGreaterThan(100);
    expect(files.some(({ file }) => file.endsWith(path.join('en-US', 'settings.json')))).toBe(true);
  });

  it.each(REMOVED)('"%s" is gone', (text) => {
    const found = files.filter((entry) => entry.text.includes(text)).map((entry) => path.relative(renderer, entry.file));
    expect(found).toEqual([]);
  });
});
