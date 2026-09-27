import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
/**
 * Kel Permissions — what Kel may do right now, the access requests waiting on you, and (behind
 * "Details") the checker, the emergency stop, and the locked safety rules.
 * Everything is read from `/api/autonomy`; only the user resolves an access request. The default
 * view speaks in plain access words (JR-18) — ids, digests and rule tables stay behind Details.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelLoading,
  KelSection,
  KelTable,
  KelTabs,
  formatWhen,
  formatUntil,
} from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { KelAuthorityCard } from '@renderer/components/kel/KelAuthorityCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { KEL_ALL_CONVERSATIONS, kelAutonomy, kelState, type KelBoundaryRequest, type KelLease, type KelWorkJob } from '@renderer/components/kel/kelApi';
import { workLabelFor } from '@renderer/components/kel/jobLabels';
import { accessLabel } from '@renderer/components/kel/workLanguage';

const STATE_CLASS: Record<string, string> = {
  ACTIVE: 'kel-chip kel-chip--ok',
  REVOKED: 'kel-chip kel-chip--failed',
  PENDING: 'kel-chip kel-chip--wait',
  GRANTED: 'kel-chip kel-chip--ok',
  DENIED: 'kel-chip kel-chip--failed',
};

const CHECK_KINDS = ['write', 'repo', 'browser', 'tool', 'destructive'];

const CHECK_KIND_LABEL: Record<string, string> = {
  write: 'Change files',
  repo: 'Repository',
  browser: 'Website',
  tool: 'Tool',
  destructive: 'Delete files',
};

const STATE_TEXT: Record<string, string> = {
  ACTIVE: 'Active',
  REVOKED: 'Turned off',
  PENDING: 'Waiting',
};

/** A permission's access, in plain words, one line per kind of access. */
const leaseAccess = (lease: KelLease): string =>
  Array.from(new Set(lease.scope.map((entry) => accessLabel(entry.kind, entry.value)))).join(' · ') || 'No access yet';

export default function KelAutonomyPage() {
  const [leases, setLeases] = useState<KelLease[] | null>(null);
  const [jobs, setJobs] = useState<KelWorkJob[]>([]);
  const [requests, setRequests] = useState<KelBoundaryRequest[]>([]);
  const [rules, setRules] = useState<Array<{ rule: string; text: string; test: string }>>([]);
  const [digest, setDigest] = useState('');
  const [kind, setKind] = useState('write');
  const [target, setTarget] = useState('');
  const [decision, setDecision] = useState<{ allowed: boolean; rule: string; reason: string } | null>(
    null
  );
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [advanced, setAdvanced] = useState(false);
  // D15 — emergency stop is deliberate: the first click arms it, the second click stops everything.
  const [stopArmed, setStopArmed] = useState(false);

  const load = useCallback(async () => {
    try {
      const [leasePayload, requestPayload, guardrailPayload, statePayload] = await Promise.all([
        kelAutonomy.leases(),
        kelAutonomy.requests(),
        kelAutonomy.guardrails(),
        // Work labels come from the same engine; when the state read is unavailable the table
        // falls back to a neutral label instead of failing the whole page (HVRA-MINOR-001).
        kelState(KEL_ALL_CONVERSATIONS).catch((): null => null),
      ]);
      setLeases(leasePayload.leases ?? []);
      setRequests(requestPayload.requests ?? []);
      setRules(guardrailPayload.rules ?? []);
      setDigest(guardrailPayload.digest ?? '');
      setJobs(statePayload?.jobs ?? []);
      setError(null);
    } catch (err) {
      setLeases([]);
      setError(err);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const act = useCallback(
    async (label: string, fn: () => Promise<unknown>) => {
      setBusy(true);
      setNote(null);
      try {
        await fn();
        setNote(`${label} — done.`);
        await load();
      } catch (err) {
        setNote(`${label} failed. ${failureSentence(err, 'The engine did not answer — try again.')}`);
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  const active = (leases ?? []).filter((lease) => lease.state === 'ACTIVE');
  const pending = requests.filter((request) => request.status === 'PENDING');
  const firstLeaseId = leases && leases.length ? leases[0].lease_id : '';

  return (
    <div className="kel-scope">
      <a className="kel-skip" href="#kel-autonomy-main">
        Skip to main content
      </a>
      <main className="kel-page" id="kel-autonomy-main" tabIndex={-1}>
        <div className="kel-page__head">
          <div>
            <ShellWorkspaceLink /><h1 className="kel-h1">Permissions</h1>
          </div>
          <span className="kel-grow" />
          <KelButton variant="quiet" ariaLabel={advanced ? 'Hide permission details' : 'Show permission details'} onClick={() => setAdvanced(value => !value)}>
            {advanced ? 'Hide details' : 'Details'}
          </KelButton>
        </div>

        {stopArmed && (
          <p className="kel-meta kel-strong">
            This will revoke every active permission and pause all active or queued work now. Finished
            work is not undone — choose Yes to confirm, or Keep going to leave everything as it is.
          </p>
        )}

        {/* D-64: the mode first — Full access by default, one switch back to Ask first. */}
        <KelAuthorityCard />

        {error && <KelFailureCard error={error} onRetry={() => void load()} />}
        {!error && leases === null && <KelLoading rows={3} />}
        {note && <p className="kel-meta">{note}</p>}

        {!error && leases !== null && (
          <KelCard title="Active permissions">
            {leases.length === 0 ? (
              <KelEmpty
                title="No permissions yet in this project."
                why=""
              />
            ) : (
              <div className="kel-permission-table-scroll" tabIndex={0} role="region" aria-label="Active permissions table">
              <KelTable
                head={['Work', 'State', 'Expires', 'Access', '']}
                rows={leases.map((lease) => [
                  <span className="kel-strong" key={`${lease.lease_id}-job`}>
                    {workLabelFor(lease.job_id, jobs)}
                  </span>,
                  <span className={STATE_CLASS[lease.state] ?? 'kel-chip'} key={`${lease.lease_id}-st`}>
                    {STATE_TEXT[lease.state] ?? lease.state.toLowerCase().replace(/_/g, ' ')}
                  </span>,
                  <span className="kel-meta" key={`${lease.lease_id}-exp`}>
                    {lease.expired ? 'Expired' : formatUntil(lease.expires_at)}
                  </span>,
                  <span className="kel-meta" key={`${lease.lease_id}-scope`}>
                    {leaseAccess(lease)}
                  </span>,
                  <KelButton
                    key={`${lease.lease_id}-act`}
                    variant="quiet"
                    disabled={busy || lease.state !== 'ACTIVE'}
                    onClick={() => void act('Turned off', () => kelAutonomy.revoke(lease.lease_id, 'revoked from Permissions'))}
                  >
                    Turn off
                  </KelButton>,
                ])}
              />
              </div>
            )}
          </KelCard>
        )}

        {!error && leases !== null && (
          <KelCard title="Access requests">
            {pending.length === 0 ? (
              <KelEmpty
                title="Nothing is waiting for extra access."
                why=""
              />
            ) : (
              pending.map((request) => (
                <div className="kel-card" key={request.request_id}>
                  <div className="kel-row kel-permission-request-heading">
                    <span className="kel-strong">{accessLabel(request.scope, request.target)}</span>
                    <span className={STATE_CLASS[request.status] ?? 'kel-chip'}>Waiting on you</span>
                  </div>
                  {request.what && <p className="kel-sub">{request.what}</p>}
                  {request.why && <p className="kel-meta">{`Why: ${request.why}`}</p>}
                  {request.benefit && <p className="kel-meta">{`Benefit: ${request.benefit}`}</p>}
                  {request.fallback && <p className="kel-meta">{`If denied: ${request.fallback}`}</p>}
                  {request.risk && <p className="kel-meta">{`Risk: ${request.risk}`}</p>}
                  <div className="kel-row kel-permission-actions">
                    <KelButton
                      variant="primary"
                      disabled={busy}
                      onClick={() =>
                        void act('Allow once', () =>
                          kelAutonomy.resolveRequest(request.request_id, true, 'once')
                        )
                      }
                    >
                      Allow once
                    </KelButton>
                    <KelButton
                      variant="secondary"
                      disabled={busy}
                      onClick={() =>
                        void act('Allow for this project', () =>
                          kelAutonomy.resolveRequest(request.request_id, true, 'project')
                        )
                      }
                    >
                      Allow for this project
                    </KelButton>
                    <KelButton
                      variant="quiet"
                      disabled={busy}
                      onClick={() =>
                        void act('Deny', () => kelAutonomy.resolveRequest(request.request_id, false))
                      }
                    >
                      Deny
                    </KelButton>
                  </div>
                </div>
              ))
            )}
          </KelCard>
        )}

        <KelCard title="Safety rules">
          <p className="kel-sub kel-permission-check-desktop">
            Kel checks every action against safety rules that projects, repositories and web content can't change.
          </p>
          <button type="button" className="kel-permission-check-mobile" aria-expanded={advanced} onClick={() => setAdvanced(value => !value)}>
            <span>Safety rules</span>
            <span>{advanced ? 'Hide details' : 'Details'}</span>
          </button>
        </KelCard>

        {advanced && (
          <>
          <div className="kel-row">          <KelButton variant="secondary" onClick={() => void load()} disabled={busy}>
            Reload
          </KelButton>
          {!stopArmed ? (
            <KelButton
              variant="secondary"
              disabled={busy || active.length === 0}
              onClick={() => setStopArmed(true)}
            >
              Emergency stop
            </KelButton>
          ) : (
            <>
              <KelButton
                variant="primary"
                disabled={busy}
                onClick={() =>
                  void act('Emergency stop', async () => {
                    await kelAutonomy.emergencyStop();
                    setStopArmed(false);
                  })
                }
              >
                Yes — stop everything
              </KelButton>
              <KelButton variant="quiet" disabled={busy} onClick={() => setStopArmed(false)}>
                Keep going
              </KelButton>
            </>
          )}</div>
        <p className="kel-meta">
          Emergency stop revokes every active permission and pauses all active or queued work; Kel stops
          at its next safe check. It does not undo work that already finished.
        </p>
            <p className="kel-meta">
              Changes apply immediately — turning off a permission stops the next step, even while work is
              running, and nothing widens on its own: extra access only follows an access request you approve.
            </p>
            <KelCard title="Check what Kel may do">
          <p className="kel-sub">
            Ask whether Kel would be allowed to do something before any work runs. Kel refuses anything
            outside what you approved, anything locked, and anything it cannot verify.
          </p>
          <div className="kel-row">
            <KelTabs
              tabs={CHECK_KINDS.map((entry) => ({ id: entry, label: CHECK_KIND_LABEL[entry] ?? entry }))}
              active={kind}
              onSelect={setKind}
            />
          </div>
          <div className="kel-row">
            <input
              className="kel-input"
              value={target}
              placeholder={kind === 'tool' ? 'Tool name, e.g. run_tests' : kind === 'browser' ? 'Website, e.g. example.com' : 'Folder or file'}
              aria-label="What to check"
              onChange={(event) => setTarget(event.target.value)}
            />
            <KelButton
              variant="secondary"
              disabled={busy || !firstLeaseId}
              onClick={() =>
                void act('Check', async () => {
                  const result =
                    kind === 'tool'
                      ? await kelAutonomy.check(firstLeaseId, kind, '', target)
                      : await kelAutonomy.check(firstLeaseId, kind, target);
                  setDecision(result);
                })
              }
            >
              Check
            </KelButton>
          </div>
          {decision && (
            <p className="kel-sub">
              {decision.allowed ? `Allowed — ${decision.reason}` : `Not allowed — ${decision.reason}`}
            </p>
          )}
          {!firstLeaseId && <p className="kel-meta">Nothing to check against yet — this works once Kel has a permission for some work.</p>}
        </KelCard>

        {leases !== null && leases.length > 0 && (
          <KelCard title="Work references">
            <p className="kel-meta">
              Support detail — the references behind the Work column, for troubleshooting only.
            </p>
            <KelTable
              head={['Work', 'Job id', 'Lease id']}
              rows={leases.map((lease) => [
                <span key={`${lease.lease_id}-wl`}>{workLabelFor(lease.job_id, jobs)}</span>,
                <span className="kel-code" key={`${lease.lease_id}-wj`}>
                  {lease.job_id}
                </span>,
                <span className="kel-code" key={`${lease.lease_id}-wls`}>
                  {lease.lease_id}
                </span>,
              ])}
            />
          </KelCard>
        )}

        {rules.length > 0 && (
          <KelSection title="Safety rules (locked)">
            <p className="kel-sub">
              These safety rules are locked and cannot be changed by projects, repositories, or web content;
              Kel refuses work that tries to change them. Every action is checked against them before it
              runs, and every decision is recorded.
            </p>
            <KelTable
              head={['Rule', 'What it means', 'Checked by']}
              rows={rules.map((rule) => [
                <span className="kel-strong" key={`${rule.rule}-id`}>
                  {rule.rule}
                </span>,
                <span key={`${rule.rule}-text`}>{rule.text}</span>,
                <span className="kel-code" key={`${rule.rule}-test`}>
                  {rule.test}
                </span>,
              ])}
            />
            {digest && <p className="kel-meta">{`Rule set fingerprint ${digest.slice(0, 12)}`}</p>}
          </KelSection>
            )}
          </>
        )}
      </main>
    </div>
  );
}
