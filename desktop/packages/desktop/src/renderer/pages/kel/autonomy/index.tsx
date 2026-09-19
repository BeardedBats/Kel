/**
 * Kel V1.4 Autonomy — capability leases, boundary decisions, and the locked guardrail block.
 * Everything is read from `/api/autonomy`; only the user resolves a boundary request, and the
 * guardrail block is presented read-only by design.
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
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { kelAutonomy, type KelBoundaryRequest, type KelLease } from '@renderer/components/kel/kelApi';

const STATE_CLASS: Record<string, string> = {
  ACTIVE: 'kel-chip kel-chip--ok',
  REVOKED: 'kel-chip kel-chip--failed',
  PENDING: 'kel-chip kel-chip--wait',
  GRANTED: 'kel-chip kel-chip--ok',
  DENIED: 'kel-chip kel-chip--failed',
};

const CHECK_KINDS = ['write', 'repo', 'browser', 'tool', 'destructive'];

const STATE_TEXT: Record<string, string> = {
  ACTIVE: 'Active',
  REVOKED: 'Revoked',
  PENDING: 'Waiting',
};

export default function KelAutonomyPage() {
  const [leases, setLeases] = useState<KelLease[] | null>(null);
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

  const load = useCallback(async () => {
    try {
      const [leasePayload, requestPayload, guardrailPayload] = await Promise.all([
        kelAutonomy.leases(),
        kelAutonomy.requests(),
        kelAutonomy.guardrails(),
      ]);
      setLeases(leasePayload.leases ?? []);
      setRequests(requestPayload.requests ?? []);
      setRules(guardrailPayload.rules ?? []);
      setDigest(guardrailPayload.digest ?? '');
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
        setNote(`${label} recorded.`);
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
            <h1 className="kel-h1">Permissions</h1>
            <p className="kel-sub">
              {leases === null
                ? 'Loading…'
                : `${active.length === 1 ? '1 active permission' : `${active.length} active permissions`} · ${pending.length} waiting on you`}
            </p>
          </div>
          <span className="kel-grow" />
          <KelButton variant="secondary" onClick={() => void load()} disabled={busy}>
            Reload
          </KelButton>
          <KelButton
            variant="secondary"
            disabled={busy || active.length === 0}
            onClick={() => void act('Emergency stop', () => kelAutonomy.emergencyStop())}
          >
            Emergency stop
          </KelButton>
        </div>

        <p className="kel-meta">
          Emergency stop revokes every active permission and pauses all active or queued work; Kel stops
          at its next safe check. It does not undo work that already finished.
        </p>

        {error && <KelFailureCard error={error} onRetry={() => void load()} />}
        {!error && leases === null && <KelLoading rows={3} />}
        {note && <p className="kel-meta">{note}</p>}

        {!error && leases !== null && (
          <KelCard title="Active permissions">
            {leases.length === 0 ? (
              <KelEmpty
                title="No permissions yet in this project."
                why="Kel only gains permissions when you approve a reviewed plan — that approval records exactly what it may do. Kel enforces those limits while it works; anything outside them comes back to you as one access request."
              />
            ) : (
              <KelTable
                head={['Work', 'State', 'Expires', 'Scope', 'Actions']}
                rows={leases.map((lease) => [
                  <span className="kel-strong" key={`${lease.lease_id}-job`}>
                    {lease.job_id}
                  </span>,
                  <span className={STATE_CLASS[lease.state] ?? 'kel-chip'} key={`${lease.lease_id}-st`}>
                    {STATE_TEXT[lease.state] ?? lease.state.toLowerCase().replace(/_/g, ' ')}
                  </span>,
                  <span className="kel-meta" key={`${lease.lease_id}-exp`}>
                    {lease.expired ? 'Expired' : formatUntil(lease.expires_at)}
                  </span>,
                  <span className="kel-meta" key={`${lease.lease_id}-scope`}>
                    {lease.scope
                      .map((entry) => `${entry.kind}: ${entry.value}`)
                      .join(' · ')
                      .slice(0, 120)}
                  </span>,
                  <KelButton
                    key={`${lease.lease_id}-act`}
                    variant="quiet"
                    disabled={busy || lease.state !== 'ACTIVE'}
                    onClick={() => void act('Revoke', () => kelAutonomy.revoke(lease.lease_id, 'revoked from Autonomy'))}
                  >
                    Revoke
                  </KelButton>,
                ])}
              />
            )}
          </KelCard>
        )}

        {!error && leases !== null && (
          <KelCard title="Access requests">
            {pending.length === 0 ? (
              <KelEmpty
                title="Nothing is waiting for extra access."
                why="Kel asks here when work needs to go beyond what you already approved — once per scope, never per command."
              />
            ) : (
              pending.map((request) => (
                <div className="kel-card" key={request.request_id}>
                  <div className="kel-row">
                    <span className="kel-strong">{`${request.scope}: ${request.target}`}</span>
                    <span className={STATE_CLASS[request.status] ?? 'kel-chip'}>waiting on you</span>
                  </div>
                  {request.what && <p className="kel-sub">{request.what}</p>}
                  {request.why && <p className="kel-meta">{`Why: ${request.why}`}</p>}
                  {request.benefit && <p className="kel-meta">{`Benefit: ${request.benefit}`}</p>}
                  {request.fallback && <p className="kel-meta">{`If denied: ${request.fallback}`}</p>}
                  {request.risk && <p className="kel-meta">{`Risk: ${request.risk}`}</p>}
                  <div className="kel-row">
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

        <div className="kel-row">
          <KelButton variant="quiet" onClick={() => setAdvanced((value) => !value)}>
            {advanced ? 'Hide advanced details' : 'Advanced details'}
          </KelButton>
        </div>

        {advanced && (
          <>
            <KelCard title="Permission check">
          <p className="kel-sub">
            Test what Kel's permission checker would decide for a scope before any work runs. It refuses
            anything outside what you approved, work on locked or frozen targets, and anything it cannot
            verify.
          </p>
          <div className="kel-row">
            <KelTabs
              tabs={CHECK_KINDS.map((entry) => ({ id: entry, label: entry }))}
              active={kind}
              onSelect={setKind}
            />
          </div>
          <div className="kel-row">
            <input
              className="kel-input"
              value={target}
              placeholder={kind === 'tool' ? 'tool name, e.g. run_tests' : 'path, domain, or target'}
              aria-label="Scope target"
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
              Check scope
            </KelButton>
          </div>
          {decision && (
            <p className="kel-sub">
              {decision.allowed
                ? `Allowed — rule ${decision.rule}: ${decision.reason}`
                : `Refused — rule ${decision.rule}: ${decision.reason}`}
            </p>
          )}
          {!firstLeaseId && <p className="kel-meta">Grant a permission first; the check needs a scope to test against.</p>}
        </KelCard>

        {rules.length > 0 && (
          <KelSection title={`Locked guardrails · digest ${digest.slice(0, 12)}`}>
            <p className="kel-sub">
              These safety rules are locked and cannot be changed by projects, repositories, or web content;
              Kel refuses work that tries to change them. Every action is checked against them before it
              runs, and every decision is recorded.
            </p>
            <KelTable
              head={['Rule', 'What it means', 'Covered by test']}
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
          </KelSection>
            )}
          </>
        )}
      </main>
    </div>
  );
}
