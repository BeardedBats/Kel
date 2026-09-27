/**
 * Machinery words stay out of the primary view (JR-16/JR-18; audit CP-5, CP-6, WK-12):
 *   Permissions  — access in plain words; digest, rule tables and ids only behind Details;
 *   Providers    — the preflight row reports the preflight's own result (never a fixed "Not tested");
 *   Diagnostics  — disabled controls explain themselves in visible text; one save action; no full
 *                  paths; no "leaves this computer" claim.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Permissions from '@renderer/pages/kel/autonomy';
import Providers from '@renderer/pages/kel/providers';
import Diagnostics from '@renderer/pages/kel/diagnostics';
import { accessLabel } from '@renderer/components/kel/workLanguage';

// The modal's theme plumbing is not under test; render its header subtitle and body directly.
vi.mock('@renderer/components/base/AionModal', () => ({
  default: ({ visible, header, children }: { visible: boolean; header?: { subtitle?: string }; children?: React.ReactNode }) =>
    visible ? <div role='dialog'>{header?.subtitle}{children}</div> : null,
}));

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const install = (handler: (route: string, body?: Record<string, unknown>) => unknown) => {
  const request = vi.fn(async (route: string, body?: Record<string, unknown>) => handler(route, body));
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
  return request;
};

describe('Permissions in plain words', () => {
  it('says what access Kel has, and keeps the digest, rules and ids behind Details', async () => {
    install((route, body) => {
      if (route === '/api/autonomy' && body?.action === 'leases') {
        return {
          leases: [{
            lease_id: 'lease-abc123', job_id: 'job-xyz789', project_id: 'p', profile: 'p', review_ref: 'r',
            issued_at: 1, expires_at: Date.now() / 1000 + 3600, state: 'ACTIVE', expired: false,
            scope: [{ kind: 'root', value: 'C:\\Users\\Nick\\Projects\\garden', uses_remaining: 3 }, { kind: 'domain', value: 'example.com', uses_remaining: 1 }],
          }],
        };
      }
      if (route === '/api/autonomy' && body?.action === 'requests') {
        return { requests: [{ request_id: 'br-1', lease_id: 'lease-abc123', scope: 'write', target: 'C:\\Users\\Nick\\Projects\\garden\\plan.md', status: 'PENDING', created: 1 }] };
      }
      if (route === '/api/autonomy' && body?.action === 'guardrails') {
        return { rules: [{ rule: 'G1', text: 'Never widen access on its own', test: 'test_g1' }], digest: 'deadbeefcafe1234' };
      }
      if (route.startsWith('/api/state')) {
        return { jobs: [{ id: 'job-xyz789', state: 'RUNNING', contract: { request: 'Plan the garden beds' } }], providers: [], projects: [] };
      }
      return {};
    });
    render(<MemoryRouter><Permissions /></MemoryRouter>);
    expect(await screen.findByText('Plan the garden beds')).toBeTruthy();
    expect(screen.getByText('Read files in garden · Visit example.com')).toBeTruthy();
    expect(screen.getByText('Change files in plan.md')).toBeTruthy();
    const text = () => document.body.textContent ?? '';
    for (const banned of ['digest', 'deadbeef', 'Locked guardrails', 'Scope', 'job-xyz789', 'lease-abc123', 'C:\\Users', 'Run check']) {
      expect(text()).not.toContain(banned);
    }
    fireEvent.click(screen.getByRole('button', { name: 'Show permission details' }));
    expect(text()).toContain('Safety rules (locked)');
    expect(text()).toContain('job-xyz789');
  });

  it('labels every access kind plainly', () => {
    expect(accessLabel('write', '/home/me/notes/')).toBe('Change files in notes');
    expect(accessLabel('repo', 'C:\\code\\kel')).toBe('Work in the kel repository');
    expect(accessLabel('browser', 'docs.python.org')).toBe('Visit docs.python.org');
    expect(accessLabel('tool', 'run_tests')).toBe('Use the run tests tool');
    expect(accessLabel('destructive', '/tmp/x')).toBe('Delete or overwrite files in x');
  });
});

describe('Providers preflight', () => {
  it('reports the preflight result instead of a fixed "Not tested"', async () => {
    install((route, body) => {
      if (route === '/api/providers' && body?.action === 'list') return { providers: [] };
      if (route === '/api/providers' && body?.action === 'credentials') return { credentials: [{ provider: 'deepseek', fields: ['api_key'], credential_ref: 'kel:provider:deepseek:api_key' }] };
      if (route === '/api/providers' && body?.action === 'readiness') {
        return { chosen: { provider: 'codex', model: 'gpt-5', label: 'Codex' }, chain: ['codex'], reasons: [], reason: 'Codex can take text work.' };
      }
      if (route === '/api/capabilities') return [];
      return {};
    });
    render(<MemoryRouter><Providers /></MemoryRouter>);
    const row = await screen.findByTestId('preflight-model-row');
    expect(row.textContent).toContain('Not checked');
    expect(document.body.textContent).not.toContain('Not tested');
    // The credential reference is support detail, closed by default.
    expect((screen.getByTestId('credential-details') as HTMLDetailsElement).open).toBe(false);
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Run preflight' }));
    });
    await waitFor(() => expect(screen.getByTestId('preflight-model-row').textContent).toContain('Pass'));
    expect(screen.getByTestId('preflight-model-row').textContent).toContain('Codex');
  });
});

describe('Diagnostics', () => {
  it('explains disabled controls in visible text and saves one report without showing a full path', async () => {
    const request = install((route, body) => {
      if (route !== '/api/diagnostics') return {};
      switch (body?.action) {
        case 'snapshot':
          return { engine_version: '2.0', counts: { jobs: 1, runs: 1 }, database: { integrity: 'ok' }, jobs: {}, runs: { by_state: {}, expired_unfenced: 0 }, providers: {}, processes: [] };
        case 'performance':
          return { startup_spans: [], measurements: [], basis: '' };
        case 'retention':
          return { retention_days: {} };
        case 'export':
          return { receipt: { included: ['counts'], excluded: ['credentials'] } };
        case 'report':
          return { path: 'C:\\Users\\Nick\\Desktop\\Kel\\Data\\diagnostics\\issue-report-20260927-101500.md', bytes: 2048, redacted: false, excluded: [] };
        default:
          return {};
      }
    });
    render(<MemoryRouter><Diagnostics /></MemoryRouter>);
    const clear = await screen.findByRole('button', { name: 'Clear' });
    expect((clear as HTMLButtonElement).disabled).toBe(true);
    expect(document.getElementById(clear.getAttribute('aria-describedby') ?? '')?.textContent).toBe('Not available in this version yet.');
    fireEvent.click(screen.getByRole('button', { name: 'Export and issue report' }));
    await screen.findByText('Included');
    expect(document.body.textContent).not.toContain('before anything leaves this computer');
    expect(screen.queryByRole('button', { name: 'Write local draft' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Export sanitized diagnostics' })).toBeNull();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Save report' }));
    });
    expect(request.mock.calls.filter(([, body]) => body?.action === 'report')).toHaveLength(1);
    const saved = await screen.findByText(/Saved issue-report-20260927-101500\.md/);
    expect(saved.textContent).not.toContain('C:\\');
  });
});
