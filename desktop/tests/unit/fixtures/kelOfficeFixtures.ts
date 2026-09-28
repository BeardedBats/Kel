/**
 * D-68 fixtures: Office payloads shaped like docs/v2/design/D-66_WORKFORCE_LIVE.md §4, with the
 * sample work from the Figma frames (page "Office — D-66 explorations", 4a–4d). Test data only.
 */
import type { OfficeItem, OfficeItemDetail } from '@renderer/components/kel/workCards/officeApi';

/** 2026-09-27 09:12 local time, as epoch seconds. */
export const AT = (hour: number, minute: number) => Math.floor(new Date(2026, 8, 27, hour, minute).getTime() / 1000);

export const MIC: OfficeItem = {
  job_id: 'job-mic',
  title: 'Mic mute toggle app',
  project_id: 'personal',
  conversation_id: 'engine-morning',
  submission_id: 'sub-mic',
  kind: 'code',
  state: 'working',
  status_line: 'Building the hotkey and tray icon',
  needs_you: false,
  progress: { done: 2, total: 5, label: '2 of 5 steps done' },
  team_size: 4,
  team: [
    { role: 'kel', role_label: 'Kel', state: 'working' },
    { role: 'builder', role_label: 'Builder', state: 'working' },
    { role: 'builder', role_label: 'Builder', state: 'working' },
    { role: 'verifier', role_label: 'Verifier', state: 'working' },
  ],
  started_at: AT(9, 12),
  updated_at: AT(9, 30),
};

export const LAPTOP: OfficeItem = {
  job_id: 'job-laptop',
  title: 'Laptop research',
  project_id: 'personal',
  conversation_id: 'engine-laptop',
  kind: 'research',
  state: 'needs_you',
  status_line: 'Needs your budget',
  needs_you: true,
  progress: { done: 2, total: 4 },
  team: [
    { role: 'discovery', role_label: 'Discovery', state: 'waiting' },
    { role: 'discovery', role_label: 'Discovery', state: 'waiting' },
  ],
  started_at: AT(9, 5),
  updated_at: AT(9, 25),
};

export const PITCHER: OfficeItem = {
  job_id: 'job-pitcher',
  title: 'Pitcher List weekly post',
  project_id: 'personal',
  conversation_id: 'engine-pitcher',
  kind: 'writing',
  state: 'in_review',
  progress: { done: 4, total: 5 },
  team: [
    { role: 'builder', role_label: 'Builder', state: 'done' },
    { role: 'verifier', role_label: 'Verifier', state: 'working' },
    { role: 'oracle', role_label: 'Oracle', state: 'working' },
  ],
  started_at: AT(8, 40),
  updated_at: AT(9, 28),
};

export const KITCHEN: OfficeItem = {
  job_id: 'job-kitchen',
  title: 'Kitchen reno quotes',
  project_id: 'personal',
  conversation_id: 'engine-kitchen',
  kind: 'research',
  state: 'working',
  progress: { done: 1, total: 3 },
  team: [
    { role: 'discovery', role_label: 'Discovery', state: 'working' },
    { role: 'utility', role_label: 'Utility', state: 'working' },
  ],
  started_at: AT(9, 20),
  updated_at: AT(9, 29),
};

export const RECEIPTS: OfficeItem = {
  job_id: 'job-receipts',
  title: 'Receipts tidy-up',
  project_id: 'personal',
  conversation_id: 'engine-receipts',
  submission_id: 'sub-receipts',
  kind: 'code',
  state: 'done',
  status_line: 'Done and checked',
  progress: { done: 5, total: 5 },
  team: [],
  started_at: AT(9, 18),
  updated_at: AT(9, 40),
};

export const BACKUP: OfficeItem = {
  job_id: 'job-backup',
  title: 'Backup check',
  project_id: 'personal',
  conversation_id: 'engine-backup',
  kind: 'writing',
  state: 'failed',
  progress: { done: 3, total: 4 },
  started_at: AT(8, 0),
  updated_at: AT(8, 15),
};

/** The Figma order: the four visible cards, then the two behind "+2 more". */
export const FIGMA_ORDER: OfficeItem[] = [MIC, LAPTOP, PITCHER, RECEIPTS, KITCHEN, BACKUP].map((item, order) => ({ ...item, order }));

export const MIC_DETAIL: OfficeItemDetail = {
  ...MIC,
  team: undefined,
  why: null,
  next: null,
  staff: [
    {
      id: 'kel',
      role: 'kel',
      role_label: 'Kel',
      doing: 'Split the build in two and lined up the checks',
      state: 'working',
      model_label: 'ChatGPT Luna',
      model_confirmed: true,
      reasoning: 'auto',
      asked: { model_label: 'ChatGPT Luna', reasoning: 'auto' },
    },
    {
      id: 'b1',
      role: 'builder',
      role_label: 'Builder',
      doing: 'Writing the global hotkey listener',
      state: 'working',
      model_label: 'Claude Opus 5.5',
      model_confirmed: true,
      reasoning: 'high',
      asked: { model_label: 'Claude Opus 5.5', reasoning: 'high' },
    },
    {
      id: 'b2',
      role: 'builder',
      role_label: 'Builder',
      doing: 'Building the tray icon and its menu',
      state: 'working',
      model_label: 'Claude Opus 4.8',
      model_confirmed: true,
      reasoning: 'high',
      asked: { model_label: 'Claude Opus 5.5', reasoning: 'high' },
    },
    {
      id: 'v1',
      role: 'verifier',
      role_label: 'Verifier',
      doing: 'Reviewing the first build',
      state: 'working',
      model_label: 'GPT-6 Astra',
      model_confirmed: false,
      reasoning: 'medium',
      asked: { model_label: 'GPT-6 Astra', reasoning: 'medium' },
    },
  ],
  steps: [
    { id: 'm1', label: 'Plan the app', state: 'done', at: AT(9, 13) },
    { id: 'm2', label: 'Set up the project', state: 'done', at: AT(9, 16) },
    { id: 'm3', label: 'Build the hotkey and tray icon', state: 'running', at: null },
    { id: 'm4', label: 'Check it on your PC', state: 'pending', at: null },
    { id: 'm5', label: 'Hand it over to you', state: 'pending', at: null },
  ],
  review: {
    verdict: null,
    checked_by: 'GPT-6 Astra',
    independence: 'full',
    findings: [
      {
        severity: 'blocker',
        area: 'functional-testing',
        summary:
          'Mute works in Teams and Zoom. The tray icon doesn’t change when you mute from Windows settings, so it went back to a Builder.',
        where: 'src/tray.ts',
        status: 'open',
      },
    ],
  },
  oracle: { state: 'waiting', why: null, independence: 'full', model_label: 'GPT-6 Astra', reasoning: 'high', findings: [] },
  files_changed: ['src/hotkey.ts', 'src/tray.ts', 'assets/mic-muted.ico', 'package.json'],
  verification: { result: 'in_progress', summary: ['2 of 4 passed'] },
  links: { conversation_id: 'engine-morning', submission_id: 'sub-mic', message_seq: 4 },
};

export const RECEIPTS_DETAIL: OfficeItemDetail = {
  ...RECEIPTS,
  team: undefined,
  result:
    'Sorted 64 receipts into one folder per month, renamed each as date – shop – amount, and made a summary spreadsheet. The totals match your receipts to the cent.',
  staff: [
    { id: 'kel', role: 'kel', role_label: 'Kel', doing: 'Planned the tidy-up and applied it', state: 'done', model_label: 'ChatGPT Luna', model_confirmed: true, reasoning: 'auto' },
    { id: 'u1', role: 'utility', role_label: 'Utility', doing: 'Read and renamed 64 receipts', state: 'done', model_label: 'Claude Sonnet', model_confirmed: true, reasoning: 'low', asked: { model_label: 'DeepSeek Flash', reasoning: 'low' } },
    { id: 'b1', role: 'builder', role_label: 'Builder', doing: 'Made the summary spreadsheet', state: 'done', model_label: 'Claude Opus 5.5', model_confirmed: true, reasoning: 'medium' },
    { id: 'v1', role: 'verifier', role_label: 'Verifier', doing: 'Checked every total against the receipts', state: 'done', model_label: 'GPT-6 Astra', model_confirmed: true, reasoning: 'medium' },
  ],
  steps: [
    { id: 'm1', label: 'Find the receipts', state: 'done', at: AT(9, 18) },
    { id: 'm2', label: 'Read dates, shops, amounts', state: 'done', at: AT(9, 26) },
    { id: 'm3', label: 'Rename and sort by month', state: 'done', at: AT(9, 31) },
    { id: 'm4', label: 'Make the summary sheet', state: 'done', at: AT(9, 35) },
    { id: 'm5', label: 'Check and apply', state: 'done', at: AT(9, 40) },
  ],
  review: { verdict: 'VERIFIED', checked_by: 'GPT-6 Astra', independence: 'full', findings: [] },
  oracle: { state: 'not_needed', why: null, independence: 'full', findings: [] },
  files_changed: ['64 receipts, renamed', 'receipts-2026.xlsx'],
  verification: { result: 'passed', summary: ['6 of 6 checks'] },
  application: { state: 'APPLIED', auto: true, root: 'C:\\Users\\Nick\\Documents\\Receipts\\2026', files: 65, waiting_reason: null },
  links: { conversation_id: 'engine-receipts', submission_id: 'sub-receipts', message_seq: 9 },
};
