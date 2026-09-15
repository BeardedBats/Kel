/**
 * Kel V1.4 Team — Office / Roster / Studio (docs/v1.4/KEL_V1.4_TEAM_MODEL.md).
 *
 * Office shows real assignments only (engine-derived state, run-linked).
 * Roster shows role templates and their current version.
 * Studio shows the structured role editor with the locked guardrail block rendered read-only,
 * append-only version history, and copy-forward rollback.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelErrorState,
  KelLoading,
  KelMeter,
  KelStatusChip,
  KelTable,
  KelTabs,
  formatWhen,
  statusFromDerived,
} from '@renderer/components/kel/KelPrimitives';
import {
  KelAssignment,
  KelRole,
  KelRoleDetail,
  KelTeamEvent,
  kelTeam,
} from '@renderer/components/kel/kelApi';

type View = 'office' | 'roster' | 'studio';

const FIELD_LABELS: Array<[string, string]> = [
  ['goal', 'Goal'],
  ['inputs', 'Inputs'],
  ['outputs', 'Outputs'],
  ['quality_bar', 'Quality bar'],
  ['boundaries', 'Boundaries'],
  ['escalation', 'Escalation'],
  ['evidence_expectations', 'Evidence expectations'],
];

function text(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

const viewFromPath = (path: string): View => {
  if (path.startsWith('/team/roster')) return 'roster';
  if (path.startsWith('/team/studio')) return 'studio';
  return 'office';
};

export default function KelTeamPage() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [view, setView] = useState<View>(viewFromPath(pathname));
  useEffect(() => {
    setView(viewFromPath(pathname));
  }, [pathname]);
  const [assignments, setAssignments] = useState<KelAssignment[] | null>(null);
  const [roles, setRoles] = useState<KelRole[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [events, setEvents] = useState<KelTeamEvent[]>([]);
  const [detail, setDetail] = useState<KelRoleDetail | null>(null);
  const [history, setHistory] = useState<Array<{ version: number; created: number }>>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [office, roster] = await Promise.all([kelTeam.office(), kelTeam.roster()]);
      setAssignments(office.assignments);
      setRoles(roster.roles);
      setDepartments(roster.departments);
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openAssignment = useCallback(async (assignmentId: string) => {
    setSelected(assignmentId);
    try {
      const timeline = await kelTeam.timeline(assignmentId);
      setEvents(timeline.events);
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
      setEvents([]);
    }
  }, []);

  const openRole = useCallback(async (templateId: string) => {
    setBusy(true);
    try {
      const [role, versions] = await Promise.all([kelTeam.role(templateId), kelTeam.history(templateId)]);
      setDetail(role);
      setHistory(versions.versions);
      setView('studio');
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
    } finally {
      setBusy(false);
    }
  }, []);

  const rollback = useCallback(
    async (templateId: string, to: number) => {
      setBusy(true);
      try {
        await kelTeam.rollback(templateId, to);
        await openRole(templateId);
      } catch (err) {
        setError(String(err instanceof Error ? err.message : err));
      } finally {
        setBusy(false);
      }
    },
    [openRole]
  );

  const waiting = useMemo(
    () => (assignments ?? []).filter((row) => row.derived_state === 'WAITING').length,
    [assignments]
  );

  const summary = assignments
    ? `${assignments.length} assignment${assignments.length === 1 ? '' : 's'} · ${
        waiting === 1 ? '1 waiting on you' : `${waiting} waiting on you`
      }`
    : 'Loading assignments…';

  return (
    <div className="kel-scope">
      <a className="kel-skip" href="#kel-main">
        Skip to main content
      </a>
      <main className="kel-page" id="kel-main">
        <div className="kel-page__head">
          <div>
            <h1 className="kel-h1">Team</h1>
            <p className="kel-sub">{summary}</p>
          </div>
          <span className="kel-grow" />
          <KelTabs
            tabs={[
              { id: 'office', label: 'Office' },
              { id: 'roster', label: 'Roster' },
              { id: 'studio', label: 'Studio' },
            ]}
            active={view}
            onSelect={(id) => {
              setView(id as View);
              navigate('/team/' + id);
            }}
          />
        </div>

        {error && (
          <KelErrorState
            title="Kel could not read the team state"
            cause={error}
            fix="Check that the engine is running, then retry."
          />
        )}

        {!error && assignments === null && <KelLoading rows={4} />}

        {!error && assignments !== null && view === 'office' && (
          <KelCard title="Office" chip={<span className="kel-meta">real assignments only</span>}>
            {assignments.length === 0 ? (
              <KelEmpty
                title="No specialists are working right now."
                why="Assignments appear here as soon as Kel staffs a step of a real job."
                actionLabel="Seed the default roster"
                onAction={() => void load()}
              />
            ) : (
              <KelTable
                head={['Specialist', 'State', 'Step', 'Provider', 'Budget', 'Updated']}
                rows={assignments.map((row) => [
                  <button
                    type="button"
                    className="kel-btn kel-btn--quiet"
                    onClick={() => void openAssignment(row.assignment_id)}
                  >
                    {row.role} <span className="kel-meta">v{row.role_version}</span>
                  </button>,
                  <KelStatusChip status={statusFromDerived(row.derived_state)} />,
                  <span className="kel-meta">{row.milestone_id}</span>,
                  <span className="kel-meta">
                    {row.provider ?? '—'}
                    {row.model ? ` · ${row.model}` : ''}
                  </span>,
                  <KelMeter used={row.spent ?? 0} total={row.budget ?? 0} />,
                  <span className="kel-meta">{formatWhen(row.updated)}</span>,
                ])}
              />
            )}
          </KelCard>
        )}

        {!error && view === 'office' && selected && (
          <KelCard
            title="Assignment activity"
            chip={<span className="kel-meta">{selected}</span>}
            actions={
              <KelButton variant="quiet" onClick={() => setSelected(null)} ariaLabel="Close activity">
                Close
              </KelButton>
            }
          >
            {events.length === 0 ? (
              <KelEmpty title="No activity recorded yet." why="Events appear as the assignment runs." />
            ) : (
              <KelTable
                head={['When', 'Event', 'Actor', 'Detail']}
                rows={events.map((event) => [
                  <span className="kel-meta">{formatWhen(event.at)}</span>,
                  <span className="kel-strong">{event.kind}</span>,
                  <span className="kel-meta">{event.actor}</span>,
                  <span className="kel-meta">{text(event.detail)}</span>,
                ])}
              />
            )}
          </KelCard>
        )}

        {!error && view === 'roster' && (
          <KelCard title="Roster" chip={<span className="kel-meta">{roles.length} roles</span>}>
            {roles.length === 0 ? (
              <KelEmpty
                title="No roles yet."
                why="Kel needs a roster before it can staff any step."
                actionLabel="Seed the default roster"
                onAction={() => {
                  void kelTeam.seed().then(load);
                }}
              />
            ) : (
              departments.map((department) => (
                <div key={department}>
                  <h2 className="kel-h2">{department}</h2>
                  {roles
                    .filter((role) => role.department === department)
                    .map((role) => (
                      <div className="kel-row" key={role.template_id}>
                        <span className="kel-strong">{role.name}</span>
                        <span className="kel-meta">
                          v{role.version ?? '—'} · {role.assignments} assignment
                          {role.assignments === 1 ? '' : 's'}
                        </span>
                        <span className="kel-grow" />
                        <KelButton onClick={() => void openRole(role.template_id)}>Open in Studio</KelButton>
                      </div>
                    ))}
                  <div className="kel-divider" />
                </div>
              ))
            )}
          </KelCard>
        )}

        {!error && view === 'studio' && !detail && (
          <KelEmpty
            title="Choose a role to configure."
            why="Studio shows the structured instructions, tool policy, budget, and version history."
            actionLabel="Go to the roster"
            onAction={() => setView('roster')}
          />
        )}

        {!error && view === 'studio' && detail && (
          <>
            <KelCard
              title={`Studio — ${detail.template_id}`}
              chip={<span className="kel-meta">version {detail.role_version}</span>}
              actions={
                <KelButton variant="quiet" onClick={() => setView('roster')}>
                  Back to roster
                </KelButton>
              }
            >
              {FIELD_LABELS.map(([key, label]) => (
                <div key={key} style={{ marginBottom: 12 }}>
                  <div className="kel-meta">{label}</div>
                  <div>{text(detail.fields[key])}</div>
                </div>
              ))}
              <div className="kel-row">
                <span className="kel-meta">Tool policy</span>
                <span className="kel-code">{text(detail.fields.tool_policy)}</span>
              </div>
              <div className="kel-row">
                <span className="kel-meta">Budget</span>
                <span>{text(detail.fields.budget)} attempt units</span>
              </div>
              <div className="kel-row">
                <span className="kel-meta">Resolved from</span>
                <span className="kel-meta">{detail.sources.join(' · ')}</span>
              </div>
            </KelCard>

            <KelCard
              title="Locked guardrails"
              chip={<span className="kel-meta">read-only — not editable by any role</span>}
            >
              {detail.locked_block.map((rule) => (
                <div key={rule.rule} className="kel-row" style={{ alignItems: 'flex-start' }}>
                  <span className="kel-code">{rule.rule}</span>
                  <span className="kel-meta">{rule.text}</span>
                </div>
              ))}
            </KelCard>

            <KelCard title="Version history" chip={<span className="kel-meta">append-only</span>}>
              <KelTable
                head={['Version', 'Created', 'Action']}
                rows={history
                  .slice()
                  .reverse()
                  .map((entry) => [
                    `v${entry.version}`,
                    <span className="kel-meta">{formatWhen(entry.created)}</span>,
                    entry.version === detail.role_version ? (
                      <span className="kel-meta">current</span>
                    ) : (
                      <KelButton
                        variant="quiet"
                        disabled={busy}
                        onClick={() => void rollback(detail.template_id, entry.version)}
                      >
                        Roll back to this version
                      </KelButton>
                    ),
                  ])}
              />
            </KelCard>
          </>
        )}
      </main>
    </div>
  );
}
