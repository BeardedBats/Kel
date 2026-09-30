import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { WorkImport, ProcedureStatus, ResultFeedback, OutputVersions, ProjectWorkSearch, TaskOutcomeFacts, ContextStatusFacts } from '@renderer/components/kel/WorkHubControls';
import { KelTabs } from '@renderer/components/kel/KelPrimitives';

const api = vi.hoisted(() => ({ preview: vi.fn(), confirm: vi.fn(), get: vi.fn(), review: vi.fn(), retire: vi.fn(), restore: vi.fn(), feedback: vi.fn(), versions: vi.fn(), read: vi.fn(), office: vi.fn(), state: vi.fn(), search: vi.fn(), outcome: vi.fn() }));
vi.mock('@renderer/components/kel/kelApi', () => ({ KEL_ALL_CONVERSATIONS: '*', kelState: api.state, kelHubSearch: api.search, kelWorkImports: { preview: api.preview, confirm: api.confirm }, kelProcedures: { get: api.get, review: api.review, retire: api.retire, restore: api.restore }, kelTaskOutcomes: { feedback: api.feedback, get: api.outcome }, kelArtifacts: { versions: api.versions, read: api.read }, kelOffice: api.office }));
vi.mock('@renderer/components/kel/activeProject', () => ({ ALL_PROJECTS: '*', useProjects: () => ({ active: 'p', loaded: true }) }));
vi.mock('@renderer/components/kel/ShellSourceCardHeader', () => ({ default: () => null, sourceCard: () => null }));
vi.mock('@renderer/motion', () => ({ EdgePill: () => null }));
const Location = () => <output data-testid="route">{useLocation().pathname}</output>;
beforeEach(() => {
  vi.resetAllMocks();
  api.office.mockResolvedValue({ items: [{ job_id: 'verified-work', title: 'Write the release note', state: 'done' }] });
  api.state.mockResolvedValue({ jobs: [{ id: 'verified-work', state: 'CLOSED', verdict: 'VERIFIED' }] });
  api.get.mockResolvedValue({ recipe_id: 'recipe', version: '1.0.0', state: 'draft' });
  api.preview.mockResolvedValue({ preview_id: 'preview', digest: 'digest', title: 'Imported note', message_count: 1, snippet: 'Source text', omissions: ['Attachments'], continuation_supported: false });
  api.confirm.mockResolvedValue({ conversation_id: 'engine-chat', mode: 'import' });
});
afterEach(() => { cleanup(); delete (window as unknown as { kelAPI?: unknown }).kelAPI; });

it('requires review and exact confirmation before adopting an imported conversation', async () => {
  const open = vi.fn().mockResolvedValue('desktop-chat');
  (window as unknown as { kelAPI: unknown }).kelAPI = { openEngineConversation: open };
  render(<MemoryRouter><WorkImport projectId="p" /><Location /></MemoryRouter>);
  fireEvent.click(screen.getByText('Import a transcript'));
  fireEvent.change(screen.getByLabelText('Transcript'), { target: { value: 'Source text' } });
  fireEvent.click(screen.getByRole('button', { name: 'Review import' }));
  expect(await screen.findByRole('region', { name: 'Import review' })).toBeTruthy();
  expect(api.confirm).not.toHaveBeenCalled();
  expect(screen.getByText('Attachments')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm import and open chat' }));
  await waitFor(() => expect(screen.getByTestId('route').textContent).toBe('/conversation/desktop-chat'));
  expect(api.confirm).toHaveBeenCalledWith('p', expect.objectContaining({ preview_id: 'preview', digest: 'digest' }));
  expect(open).toHaveBeenCalledWith('engine-chat');
});

it('invalidates review when the user changes source text and retains it on failure', async () => {
  render(<MemoryRouter><WorkImport projectId="p" /></MemoryRouter>);
  fireEvent.click(screen.getByText('Import a transcript'));
  fireEvent.change(screen.getByLabelText('Transcript'), { target: { value: 'First' } });
  fireEvent.click(screen.getByRole('button', { name: 'Review import' }));
  await screen.findByRole('button', { name: 'Confirm import and open chat' });
  fireEvent.change(screen.getByLabelText('Transcript'), { target: { value: 'Changed' } });
  expect(screen.queryByRole('button', { name: 'Confirm import and open chat' })).toBeNull();
  api.preview.mockRejectedValue(new Error('offline'));
  fireEvent.click(screen.getByRole('button', { name: 'Review import' }));
  await screen.findByRole('alert');
  expect((screen.getByLabelText('Transcript') as HTMLTextAreaElement).value).toBe('Changed');
});

it('chooses named evidence and suppresses an old procedure mutation after project changes', async () => {
  let resolve!: (value: unknown) => void;
  api.review.mockImplementation(() => new Promise(done => { resolve = done; }));
  const view = render(<ProcedureStatus projectId="p" recipeId="recipe" />);
  await screen.findByText('Draft procedure · Version 1.0.0');
  fireEvent.change(screen.getByLabelText('Checked work'), { target: { value: 'verified-work' } });
  fireEvent.click(screen.getByRole('button', { name: 'Mark reviewed' }));
  expect(api.review).toHaveBeenCalledWith('p', 'recipe', '1.0.0', 'verified-work');
  view.rerender(<ProcedureStatus projectId="other" recipeId="other-recipe" />);
  await screen.findByText('Draft procedure · Version 1.0.0');
  resolve({ recipe_id: 'recipe', version: '1.0.0', state: 'reviewed' });
  await waitFor(() => expect(screen.queryByText('Reviewed procedure · Version 1.0.0')).toBeNull());
});

it('does not open a revision for feedback belonging to a previous job', async () => {
  let resolve!: (value: unknown) => void;
  api.feedback.mockImplementation(() => new Promise(done => { resolve = done; }));
  const revise = vi.fn();
  const view = render(<ResultFeedback projectId="p" jobId="first" onRevise={revise} />);
  fireEvent.click(screen.getByRole('button', { name: 'Needs changes' }));
  view.rerender(<ResultFeedback projectId="p" jobId="second" onRevise={revise} />);
  resolve({});
  await waitFor(() => expect(api.feedback).toHaveBeenCalledWith('p', 'first', 'revision_requested'));
  expect(revise).not.toHaveBeenCalled();
});

it('reads the exact chosen artifact version and displays source text without executing it', async () => {
  api.versions.mockResolvedValue({ versions: [{ id: 'old', filename: 'report.md', created: 1, superseded_by: 'new' }, { id: 'new', filename: 'report.md', created: 2 }] });
  api.read.mockResolvedValue('<script>danger()</script>');
  render(<OutputVersions jobId="job" />);
  fireEvent.click(screen.getByText('Outputs'));
  const buttons = await screen.findAllByRole('button', { name: 'report.md' });
  fireEvent.click(buttons[0]);
  expect(await screen.findByText('<script>danger()</script>')).toBeTruthy();
  expect(api.read).toHaveBeenCalledWith('old');
  expect(document.querySelector('script')).toBeNull();
});

it('moves shared tab focus with arrows and Home/End', () => {
  const Tabs = () => { const [active, setActive] = React.useState('one'); return <KelTabs tabs={[{ id: 'one', label: 'One' }, { id: 'two', label: 'Two' }]} active={active} onSelect={setActive} />; };
  render(<Tabs />);
  const one = screen.getByRole('tab', { name: 'One' }); const two = screen.getByRole('tab', { name: 'Two' });
  one.focus(); fireEvent.keyDown(one, { key: 'ArrowRight' });
  expect(document.activeElement).toBe(two); expect(two.getAttribute('tabindex')).toBe('0');
  fireEvent.keyDown(two, { key: 'Home' }); expect(document.activeElement).toBe(one);
  fireEvent.keyDown(one, { key: 'End' }); expect(document.activeElement).toBe(two);
});

it('searches this Project and opens the exact artifact result', async () => {
  api.search.mockResolvedValue({ query: "Nick's notes", artifacts: [{ id: 'version-old', title: 'Notes.md', superseded_by: 'version-new', link: { kind: 'artifact', id: 'version-old' } }] });
  api.read.mockResolvedValue('Earlier notes');
  render(<MemoryRouter><ProjectWorkSearch projectId="project" /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('Search'), { target: { value: "Nick's notes" } });
  fireEvent.click(screen.getByRole('button', { name: 'Search' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Notes.md' }));
  expect(await screen.findByText('Earlier notes')).toBeTruthy();
  expect(api.search).toHaveBeenCalledWith('project', "Nick's notes");
  expect(api.read).toHaveBeenCalledWith('version-old');
});

it('keeps unknown cost explicit and exposes freshness counts without source bytes', async () => {
  api.outcome.mockResolvedValue({ job_id: 'job', elapsed_ms: null, worker_retries: 2, call_count: 3, costs: { reported: null, estimated: 0.012, unknown_calls: 1 }, feedback: null });
  render(<><TaskOutcomeFacts projectId="p" jobId="job" /><ContextStatusFacts status={{ state: 'degraded', omissions: [{ reason: 'Source changed', text: 'SECRET SOURCE BYTES' }], freshness: { checked: 2, stale: ['id'], unknown: [{ ref: 'id' }] } }} /></>);
  expect(await screen.findByText('$0.0120')).toBeTruthy();
  expect(screen.getAllByText('Unknown').length).toBeGreaterThan(0);
  expect(screen.getByText('Sources that may need an update: 1')).toBeTruthy();
  expect(screen.queryByText('SECRET SOURCE BYTES')).toBeNull();
});
