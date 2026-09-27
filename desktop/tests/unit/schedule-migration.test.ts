/**
 * D-57: the donor scheduler's tasks move into the engine once — imported first, switched off in
 * the old scheduler only after the engine confirms, never replayed, never doubled.
 */
import { describe, expect, it } from 'vitest';
import {
  cronMinimumGapMinutes,
  migrateDonorSchedules,
  type DonorCronJob,
  type ScheduleImport,
  type ScheduleMigrationDeps,
} from '@/process/services/kel/scheduleMigration';

const NOW = Date.UTC(2026, 8, 27, 12, 0, 0);

const job = (id: string, over: Partial<DonorCronJob> = {}): DonorCronJob => ({
  id,
  name: `Task ${id}`,
  enabled: true,
  schedule: { kind: 'cron', expr: '0 9 * * MON-FRI', tz: 'America/New_York' },
  target: { payload: { text: `Do ${id}` }, execution_mode: 'new_conversation' },
  metadata: { conversation_id: `donor-${id}` },
  state: { queue_enabled: true },
  ...over,
});

type Call = { to: 'engine' | 'donor'; route: string; body?: unknown; method?: string };

function world(jobs: DonorCronJob[], options: { refuse?: (item: ScheduleImport) => string | null; failDisable?: Set<string> } = {}) {
  const calls: Call[] = [];
  const schedules = new Map<string, ScheduleImport & { id: string }>();
  const disabled = new Set<string>();
  let marker: unknown = null;
  let engineDone = false;
  const engine: ScheduleMigrationDeps['engine'] = async (route, body) => {
    calls.push({ to: 'engine', route, body });
    const request = (body ?? {}) as { action?: string; items?: ScheduleImport[]; root?: string; record?: unknown };
    if (route === '/api/schedules' && request.action === 'migration_status') {
      if (request.record) engineDone = true;
      return { done: engineDone, at: null, summary: null };
    }
    if (route === '/api/schedules' && request.action === 'import') {
      return {
        results: (request.items ?? []).map((item) => {
          const existing = schedules.get(item.origin);
          if (existing) return { origin: item.origin, id: existing.id, status: 'exists', problem: existing.problem, message: null };
          const refusal = options.refuse?.(item) ?? null;
          if (refusal) return { origin: item.origin, id: null, status: 'refused', problem: null, message: refusal };
          const id = `sched-${item.origin}`;
          schedules.set(item.origin, { ...item, id });
          return { origin: item.origin, id, status: item.enabled ? 'imported' : 'imported_paused', problem: item.problem, message: null };
        }),
      };
    }
    if (route === '/api/model') {
      return { providers: [{ id: 'anthropic', label: 'Claude', options: [{ id: 'claude-sonnet', label: 'Claude Sonnet', available: true }] }] };
    }
    if (route === '/api/conversations') return { conversations: [{ id: 'cid-a', project_id: 'proj-chat' }] };
    if (route === '/api/project' && request.root === 'C:/work/site') return { id: 'proj-site' };
    if (route === '/api/project') throw new Error('That folder is gone.');
    throw new Error(`unexpected engine call ${route}`);
  };
  const donor: ScheduleMigrationDeps['donor'] = async (route, body, method) => {
    calls.push({ to: 'donor', route, body, method });
    if (route === '/api/cron/jobs') return jobs;
    const runs = /^\/api\/cron\/jobs\/([^/]+)\/conversations$/.exec(route);
    if (runs) {
      return Array.from({ length: 25 }, (_, index) => ({ id: `run-${runs[1]}-${index}`, created_at: NOW - index * 60_000 }));
    }
    const put = /^\/api\/cron\/jobs\/([^/]+)$/.exec(route);
    if (put && method === 'PUT') {
      if (options.failDisable?.has(put[1])) throw new Error('Kel integration: 500 crashed');
      disabled.add(put[1]);
      return {};
    }
    throw new Error(`unexpected donor call ${route}`);
  };
  const deps: ScheduleMigrationDeps = {
    engine,
    donor,
    engineConversationFor: (donorId) =>
      donorId === 'donor-a' ? 'cid-a' : donorId.startsWith('run-') ? `cid-${donorId}` : undefined,
    isDone: () => marker !== null,
    markDone: (summary) => {
      marker = summary;
    },
    now: () => NOW,
  };
  return { deps, calls, schedules, disabled, get marker() { return marker; }, set failDisable(ids: Set<string>) { options.failDisable = ids; } };
}

describe('scheduleMigration (D-57)', () => {
  it('imports every task before switching any old task off, and maps each field', async () => {
    const w = world([
      job('a', { target: { payload: { text: 'Keep going' }, execution_mode: 'existing' }, metadata: { conversation_id: 'donor-a', agent_config: { model_id: 'claude-sonnet' } }, state: { queue_enabled: false } }),
      job('b', { schedule: { kind: 'every', everyMs: 120_000 }, metadata: { conversation_id: 'donor-b', agent_config: { workspace: 'C:/work/site', model_id: 'gpt-9' } } }),
      job('c', { schedule: { kind: 'at', atMs: NOW - 3_600_000 } }),
      job('d', { schedule: { kind: 'cron', expr: '' }, enabled: false, target: { payload: { text: 'Manual' }, execution_mode: 'existing' } }),
    ]);
    const report = await migrateDonorSchedules(w.deps);

    expect(report.state).toBe('done');
    const firstDisable = w.calls.findIndex((call) => call.method === 'PUT');
    const lastImport = w.calls.map((call) => (call.body as { action?: string } | undefined)?.action).lastIndexOf('import');
    expect(lastImport).toBeGreaterThan(-1);
    expect(firstDisable).toBeGreaterThan(lastImport);
    expect([...w.disabled].sort()).toEqual(['a', 'b', 'c', 'd']);
    for (const call of w.calls.filter((entry) => entry.method === 'PUT')) expect(call.body).toEqual({ enabled: false });

    const a = w.schedules.get('a')!;
    expect(a).toMatchObject({ start_mode: 'existing', conversation_id: 'cid-a', project_id: 'proj-chat', skip_if_running: false, enabled: true, model: { provider: 'anthropic', model: 'claude-sonnet' }, cadence: { kind: 'cron', expr: '0 9 * * MON-FRI' }, timezone: 'America/New_York' });
    expect(a.runs).toHaveLength(20);
    expect(a.runs[0]).toEqual({ conversation_id: 'cid-run-a-0', at: NOW / 1000 });

    const b = w.schedules.get('b')!;
    expect(b).toMatchObject({ project_id: 'proj-site', enabled: false, model: null, cadence: { kind: 'interval', minutes: 5 }, timezone: null });
    expect(b.problem).toMatch(/every 2 minutes/);
    expect(b.notes.join(' ')).toMatch(/Automatic/);

    expect(w.schedules.get('c')).toMatchObject({ enabled: false, cadence: { kind: 'once', at: (NOW - 3_600_000) / 1000 } });
    const d = w.schedules.get('d')!;
    expect(d).toMatchObject({ enabled: false, cadence: { kind: 'manual' }, start_mode: 'new_conversation', project_id: 'default' });
    expect(d.notes.join(' ')).toMatch(/new conversation/);
    expect(w.marker).not.toBeNull();
  });

  it('leaves the old task running when the engine does not confirm the import', async () => {
    const w = world([job('a')]);
    const engine = w.deps.engine;
    w.deps.engine = async (route, body) => {
      if ((body as { action?: string } | undefined)?.action === 'import') throw new Error('Kel is busy.');
      return engine(route, body);
    };
    const report = await migrateDonorSchedules(w.deps);
    expect(report.state).toBe('incomplete');
    expect(w.calls.some((call) => call.method === 'PUT')).toBe(false);
    expect(w.marker).toBeNull();
  });

  it('finishes after a crash between import and switch-off without doubling or replaying', async () => {
    const w = world([job('a'), job('b')], { failDisable: new Set(['b']) });
    const first = await migrateDonorSchedules(w.deps);
    expect(first.state).toBe('incomplete');
    expect(w.marker).toBeNull();
    expect(w.disabled.has('a')).toBe(true);
    expect(w.disabled.has('b')).toBe(false);
    expect(w.schedules.size).toBe(2);

    w.failDisable = new Set();
    const second = await migrateDonorSchedules(w.deps);
    expect(second.state).toBe('done');
    expect(w.schedules.size).toBe(2); // `exists`, not a second copy
    expect([...w.disabled].sort()).toEqual(['a', 'b']);
    expect(w.marker).not.toBeNull();
  });

  it('does nothing on a later launch once done', async () => {
    const w = world([job('a')]);
    await migrateDonorSchedules(w.deps);
    const before = w.calls.length;
    const again = await migrateDonorSchedules(w.deps);
    expect(again.state).toBe('skipped');
    expect(w.calls.length).toBe(before);
  });

  it('still moves and switches off a task the engine refuses, paused as a manual task in General', async () => {
    const w = world([job('bad', { schedule: { kind: 'cron', expr: '61 * * * *' } }), job('good')], {
      refuse: (item) => (item.cadence.kind === 'cron' && item.cadence.expr.startsWith('61') ? 'That timing is not valid.' : null),
    });
    const report = await migrateDonorSchedules(w.deps);
    expect(report.state).toBe('done');
    const bad = w.schedules.get('bad')!;
    expect(bad).toMatchObject({ enabled: false, cadence: { kind: 'manual' }, project_id: 'default' });
    expect(bad.problem).toMatch(/That timing is not valid/);
    expect(report.paused).toContain('bad');
    expect([...w.disabled].sort()).toEqual(['bad', 'good']);
  });

  it('waits for an engine that has no schedules yet', async () => {
    const w = world([job('a')]);
    w.deps.engine = async () => {
      throw new Error('Unknown action');
    };
    const report = await migrateDonorSchedules(w.deps);
    expect(report.state).toBe('skipped');
    expect(w.calls.some((call) => call.to === 'donor')).toBe(false);
  });

  it('measures the tightest cron gap', () => {
    expect(cronMinimumGapMinutes('*/2 * * * *')).toBe(2);
    expect(cronMinimumGapMinutes('* * * * *')).toBe(1);
    expect(cronMinimumGapMinutes('0,30 * * * *')).toBe(30);
    expect(cronMinimumGapMinutes('0 9 * * *')).toBe(60);
    expect(cronMinimumGapMinutes('0,58 9 * * *')).toBe(58);
    expect(cronMinimumGapMinutes('*/15 * * * *')).toBe(15);
  });
});
