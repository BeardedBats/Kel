/**
 * ST-02 — "Report issue" saves a Kibble fix with the diagnostics as its note and says
 * "Saved to Kibble." only after the save succeeds. The stopped-engine screen has no report
 * button (the engine that would store the fix is the thing that stopped).
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const save = vi.fn();
const success = vi.fn();
const error = vi.fn();

vi.mock('@/renderer/components/kel/kelApi', () => ({ kelDogfood: { save: (body: unknown) => save(body) } }));
vi.mock('@renderer/components/kel/kelApi', () => ({
  kelDogfood: { save: (body: unknown) => save(body) },
  engineDiagnostics: async () => ({}),
}));
vi.mock('@arco-design/web-react', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  Message: { success: (text: string) => success(text), error: (text: string) => error(text) },
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock('@renderer/components/base/AionModal', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

import FeedbackButton from '@renderer/components/base/FeedbackButton';
import KelStoppedEngineView from '@renderer/components/kel/KelStoppedEngineView';

beforeEach(() => {
  save.mockReset();
  success.mockReset();
  error.mockReset();
  window.location.hash = '#/settings/tools';
});
afterEach(() => {
  cleanup();
  window.location.hash = '';
});

describe('Report issue saves to Kibble', () => {
  it('creates an OPEN fix whose note carries the diagnostics, then says so', async () => {
    save.mockResolvedValue({ id: 'FIX-0007', status: 'OPEN' });
    render(
      <FeedbackButton
        module='mcp-tools'
        label='Report issue'
        reportTitle='MCP server "github" failed its check'
        feedbackExtra={{ mcpServerName: 'github', mcpServerStatus: 'Failed', transport: 'stdio' }}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Report issue' }));
    await waitFor(() => expect(success).toHaveBeenCalledWith('Saved to Kibble.'));
    expect(save).toHaveBeenCalledTimes(1);
    const body = save.mock.calls[0][0] as { transcript: string; route: string };
    expect(body.transcript.split('\n')).toEqual([
      'MCP server "github" failed its check',
      'Area: mcp-tools',
      'mcpServerName: github',
      'mcpServerStatus: Failed',
      'transport: stdio',
    ]);
    expect(body.route).toBe('/settings/tools');
    expect(error).not.toHaveBeenCalled();
  });

  it('does not claim success when the save fails', async () => {
    save.mockRejectedValue(new Error("This device can't reach Kel right now."));
    render(<FeedbackButton module='mcp-tools' label='Report issue' />);
    fireEvent.click(screen.getByRole('button', { name: 'Report issue' }));
    await waitFor(() => expect(error).toHaveBeenCalledTimes(1));
    expect(String(error.mock.calls[0][0])).toContain('could not save this to Kibble');
    expect(success).not.toHaveBeenCalled();
  });
});

describe('stopped engine screen', () => {
  it('offers restart and technical details but no report button', () => {
    render(
      <KelStoppedEngineView
        frame={{ state: 'unrecoverable', attempts: 2, detail: 'exit 1', at: 0 } as never}
        retrying={false}
        onRestart={() => undefined}
      />
    );
    expect(screen.getByRole('button', { name: 'Restart engine' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: /report/i })).toBeNull();
  });
});
