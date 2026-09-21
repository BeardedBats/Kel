/**
 * Kel V2.0 — Connections: the one place to see and manage the services Kel can use.
 *
 * A Connection means exactly one thing: Kel has credentials for this service and can use its API.
 * There is no per-service screen anywhere else, no per-service store, and no place on this page where
 * a credential value is shown after it is saved — the value goes to the OS-backed store in the main
 * process, and the engine only ever records that one exists.
 *
 * V2-02 adds Test connection: the shell decrypts the value, the engine makes one request, and this
 * page shows what came back — working, refused, nothing there, not reachable, no answer.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelLoading,
  formatWhen,
} from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import {
  CONNECTION_KIND_LABELS,
  connectionCheckSentence,
  connectionCredentialField,
  connectionCustodyKey,
  kelConnections,
  type KelConnection,
  type KelConnectionList,
} from '@renderer/components/kel/kelApi';

interface Draft {
  id?: string;
  name: string;
  kind: KelConnection['kind'];
  base_url: string;
  auth_method: KelConnection['auth_method'];
  auth_header: string;
  docs_url: string;
  test_endpoint: string;
  notes: string;
}

const EMPTY_DRAFT: Draft = {
  name: '',
  kind: 'api_key',
  base_url: '',
  auth_method: 'header',
  auth_header: '',
  docs_url: '',
  test_endpoint: '',
  notes: '',
};

const draftFor = (connection: KelConnection): Draft => ({
  id: connection.id,
  name: connection.name,
  kind: connection.kind,
  base_url: connection.base_url,
  auth_method: connection.auth_method,
  auth_header: connection.auth_header,
  docs_url: connection.docs_url,
  test_endpoint: connection.test_endpoint,
  notes: connection.notes,
});

const AUTH_METHODS: Array<{ id: KelConnection['auth_method']; label: string }> = [
  { id: 'header', label: 'Header' },
  { id: 'bearer', label: 'Bearer token' },
  { id: 'query', label: 'Query parameter' },
  { id: 'basic', label: 'Username and password' },
];

/** How a person reads this connection's state — derived, never stored. */
const stateSentence = (connection: KelConnection): string => {
  if (!connection.has_credentials) return 'Needs a credential';
  if (connection.last_test_state === 'ok') return 'Ready — checked and working';
  if (connection.last_test_state === 'refused') return 'Ready, but the check was refused';
  return 'Ready — Kel has a credential';
};

const Connections: React.FC = () => {
  const [list, setList] = useState<KelConnectionList | null>(null);
  const [heldByShell, setHeldByShell] = useState<Record<string, string[]> | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [credentialDraft, setCredentialDraft] = useState<{
    id: string;
    name: string;
    field: string;
    value: string;
  } | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const listed = await kelConnections.list();
      setList(listed);
      setError(null);
    } catch (err) {
      setList({ connections: [], counts: { ready: 0, needs_credentials: 0 }, states: [], kinds: [] });
      setError(err);
    }
    // The shell's own view of what it holds. Best effort: without it the page still shows the
    // engine's truth, it just cannot reconcile a disagreement.
    const shell = await window.kelAPI?.credentials?.connectionStatus?.().catch((): undefined => undefined);
    setHeldByShell(shell ?? null);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const connections = useMemo(() => list?.connections ?? [], [list]);

  const saveConnection = useCallback(async () => {
    if (!draft) return;
    setBusy(true);
    setNote(null);
    try {
      const saved = await kelConnections.save({
        id: draft.id,
        name: draft.name,
        kind: draft.kind,
        base_url: draft.base_url,
        auth_method: draft.auth_method,
        auth_header: draft.auth_header,
        docs_url: draft.docs_url,
        test_endpoint: draft.test_endpoint,
        notes: draft.notes,
      });
      setDraft(null);
      await load();
      setNote(`${saved.name} is saved. Add its credential and Kel can start using it.`);
    } catch (err) {
      setNote(failureSentence(err, 'That did not go through — check the details and try again.'));
    } finally {
      setBusy(false);
    }
  }, [draft, load]);

  const saveCredential = useCallback(async () => {
    const pending = credentialDraft;
    if (!pending || !pending.value) return;
    setBusy(true);
    setNote(null);
    try {
      const custody = window.kelAPI?.credentials;
      if (!custody) throw new Error('Storing credentials is only available in the Kel app.');
      // The shell encrypts the value into the OS store and syncs the metadata (field names + a
      // pointer) into the engine; the value itself never leaves the main process.
      await custody.set(connectionCustodyKey(pending.id), pending.field, pending.value);
      setCredentialDraft(null);
      await load();
      const listed = await kelConnections.list().catch((): null => null);
      const recorded = Boolean(listed?.connections?.find((item) => item.id === pending.id)?.has_credentials);
      setNote(
        recorded
          ? `${pending.name} is ready — the credential is in this computer's secure store and Kel has recorded it.`
          : `The credential is stored, but Kel did not record it back — save it again before relying on it.`
      );
    } catch (err) {
      setNote(failureSentence(err, 'Kel could not store that credential — try again.'));
    } finally {
      setBusy(false);
    }
  }, [credentialDraft, load]);

  const forgetCredential = useCallback(
    async (connection: KelConnection) => {
      setBusy(true);
      setNote(null);
      try {
        const custody = window.kelAPI?.credentials;
        if (!custody) throw new Error('Storing credentials is only available in the Kel app.');
        await custody.remove(connectionCustodyKey(connection.id));
        await load();
        // Honest verification: the custody delete also clears the engine's record of the credential.
        // If that did not land, say so instead of claiming the connection is clean.
        const listed = await kelConnections.list().catch((): null => null);
        const stillRecorded = Boolean(
          listed?.connections?.find((item) => item.id === connection.id)?.has_credentials
        );
        setNote(
          stillRecorded
            ? `The value is gone from this computer, but Kel still has a record of it — save the credential again or tell Kel to check.`
            : `The stored credential for ${connection.name} is gone. Kel will ask again before using it.`
        );
      } catch (err) {
        setNote(failureSentence(err, 'Kel could not remove that credential — try again.'));
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  /**
   * V2-02 Test Connection. The shell decrypts the credential, the engine makes one request, and what
   * comes back is the record — the value never reaches this page.
   */
  const checkConnection = useCallback(
    async (connection: KelConnection) => {
      setBusy(true);
      setNote(null);
      try {
        const custody = window.kelAPI?.credentials;
        if (!custody?.testConnection)
          throw new Error('Checking a connection is only available in the Kel app.');
        const checked = await custody.testConnection(connection.id);
        await load();
        // The row carries the detail sentence the engine recorded; the note is just the confirmation.
        setNote(`Checked ${checked.name}.`);
      } catch (err) {
        setNote(failureSentence(err, 'Kel could not check that connection — try again.'));
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  const removeConnection = useCallback(
    async (connection: KelConnection) => {
      setBusy(true);
      setNote(null);
      try {
        // The value first (only the main process can reach it), then the record.
        await window.kelAPI?.credentials?.remove(connectionCustodyKey(connection.id));
        await kelConnections.remove(connection.id);
        setConfirmRemove(null);
        await load();
        setNote(`${connection.name} is removed. Kel will not use it any more.`);
      } catch (err) {
        setNote(failureSentence(err, 'Kel could not remove that connection — try again.'));
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  if (error) {
    return (
      <div className="kel-page">
        <KelFailureCard error={error} onRetry={() => void load()} />
      </div>
    );
  }

  if (list === null) return <KelLoading />;

  const ready = list.counts.ready;
  const needing = list.counts.needs_credentials;

  return (
    <div className="kel-page">
      <div className="kel-page__head">
        <h1 className="kel-h1">Connections</h1>
        <p className="kel-sub">
          The services Kel can use. You keep the credential — it is stored encrypted on this computer,
          and Kel only ever records that it exists.
        </p>
      </div>

      {note && <p className="kel-meta">{note}</p>}

      <KelCard
        title="Services"
        chip={
          <span className="kel-meta">
            {connections.length === 0
              ? 'none yet'
              : `${ready} ready · ${needing} needing a credential`}
          </span>
        }
        actions={
          <KelButton variant="primary" onClick={() => setDraft({ ...EMPTY_DRAFT })} disabled={busy}>
            Add a service
          </KelButton>
        }
      >
        {connections.length === 0 ? (
          <KelEmpty
            title="No connections yet."
            why="Add a service and its credential, and Kel can work with it directly instead of you copying things across."
            actionLabel="Add a service"
            onAction={() => setDraft({ ...EMPTY_DRAFT })}
          />
        ) : (
          connections.map((connection) => {
            const shellFields = heldByShell?.[connection.id] ?? [];
            const disagree = shellFields.length > 0 && !connection.has_credentials;
            return (
              <div className="kel-row" key={connection.id}>
                <div className="kel-attention__text">
                  <strong>{connection.name}</strong>
                  <span className="kel-meta">
                    {[stateSentence(connection), connection.kind_label, connection.base_url]
                      .filter(Boolean)
                      .join(' · ')}
                  </span>
                  {disagree && (
                    <span className="kel-meta">
                      This computer still holds a credential for it that Kel has no record of — save it
                      again to restore the link.
                    </span>
                  )}
                  {connection.last_test_at ? (
                    <span className="kel-meta">
                      {connectionCheckSentence(connection, formatWhen(connection.last_test_at))}
                    </span>
                  ) : null}
                  {connection.docs_url && (
                    <span className="kel-meta">
                      Docs: {connection.docs_url}
                    </span>
                  )}
                  {connection.notes && <span className="kel-meta">{connection.notes}</span>}
                  <span className="kel-meta">
                    {connection.has_credentials
                      ? `Credential fields: ${connection.credential_fields.join(', ')} · updated ${formatWhen(connection.updated)}`
                      : `Added ${formatWhen(connection.created)}`}
                  </span>
                </div>
                <span className="kel-grow" />
                {connection.can_test && (
                  <KelButton
                    variant="quiet"
                    disabled={busy}
                    onClick={() => void checkConnection(connection)}
                  >
                    Test connection
                  </KelButton>
                )}
                <KelButton
                  variant={connection.has_credentials ? 'quiet' : 'primary'}
                  disabled={busy}
                  onClick={() =>
                    setCredentialDraft({
                      id: connection.id,
                      name: connection.name,
                      field:
                        connection.credential_fields[0] ??
                        connectionCredentialField(connection.kind),
                      value: '',
                    })
                  }
                >
                  {connection.has_credentials ? 'Replace credential' : 'Add credential'}
                </KelButton>
                {connection.has_credentials && (
                  <KelButton variant="quiet" disabled={busy} onClick={() => void forgetCredential(connection)}>
                    Remove credential
                  </KelButton>
                )}
                <KelButton variant="quiet" disabled={busy} onClick={() => setDraft(draftFor(connection))}>
                  Edit
                </KelButton>
                {confirmRemove === connection.id ? (
                  <>
                    <KelButton variant="quiet" disabled={busy} onClick={() => void removeConnection(connection)}>
                      Confirm remove
                    </KelButton>
                    <KelButton variant="quiet" disabled={busy} onClick={() => setConfirmRemove(null)}>
                      Cancel
                    </KelButton>
                  </>
                ) : (
                  <KelButton variant="quiet" disabled={busy} onClick={() => setConfirmRemove(connection.id)}>
                    Remove
                  </KelButton>
                )}
              </div>
            );
          })
        )}
      </KelCard>

      {credentialDraft && (
        <KelCard
          title={`Credential for ${credentialDraft.name}`}
          chip={<span className="kel-meta">stored encrypted on this computer</span>}
        >
          <p className="kel-sub">
            The value is encrypted into this computer's own secure store. Kel records the field name and
            a pointer — never the value, so it never reaches the engine's database, logs or exports.
          </p>
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-field">
              Field name
            </label>
            <input
              id="kel-connection-field"
              className="kel-input"
              value={credentialDraft.field}
              onChange={(event) =>
                setCredentialDraft({ ...credentialDraft, field: event.target.value })
              }
            />
          </div>
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-value">
              Credential
            </label>
            <input
              id="kel-connection-value"
              className="kel-input"
              type="password"
              autoComplete="off"
              value={credentialDraft.value}
              onChange={(event) =>
                setCredentialDraft({ ...credentialDraft, value: event.target.value })
              }
            />
          </div>
          <div className="kel-row">
            <KelButton
              variant="primary"
              disabled={busy || !credentialDraft.value || !credentialDraft.field}
              onClick={() => void saveCredential()}
            >
              Save credential
            </KelButton>
            <KelButton variant="quiet" disabled={busy} onClick={() => setCredentialDraft(null)}>
              Cancel
            </KelButton>
          </div>
        </KelCard>
      )}

      {draft && (
        <KelCard
          title={draft.id ? `Edit ${draft.name || 'connection'}` : 'Add a service'}
          chip={<span className="kel-meta">what Kel needs to reach the service</span>}
        >
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-name">
              Service name
            </label>
            <input
              id="kel-connection-name"
              className="kel-input"
              placeholder="Stripe"
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          </div>
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-kind">
              How Kel signs in
            </label>
            <select
              id="kel-connection-kind"
              className="kel-input"
              value={draft.kind}
              onChange={(event) =>
                setDraft({ ...draft, kind: event.target.value as KelConnection['kind'] })
              }
            >
              {CONNECTION_KIND_LABELS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label} — {option.hint}
                </option>
              ))}
            </select>
          </div>
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-method">
              How the credential is sent
            </label>
            <select
              id="kel-connection-method"
              className="kel-input"
              value={draft.auth_method}
              onChange={(event) =>
                setDraft({ ...draft, auth_method: event.target.value as KelConnection['auth_method'] })
              }
            >
              {AUTH_METHODS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          {draft.auth_method === 'header' || draft.auth_method === 'query' ? (
            <div className="kel-row">
              <label className="kel-meta" htmlFor="kel-connection-header">
                {draft.auth_method === 'header' ? 'Header name' : 'Parameter name'}
              </label>
              <input
                id="kel-connection-header"
                className="kel-input"
                placeholder="Authorization"
                value={draft.auth_header}
                onChange={(event) => setDraft({ ...draft, auth_header: event.target.value })}
              />
            </div>
          ) : null}
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-base">
              API address
            </label>
            <input
              id="kel-connection-base"
              className="kel-input"
              placeholder="https://api.example.com/v1"
              value={draft.base_url}
              onChange={(event) => setDraft({ ...draft, base_url: event.target.value })}
            />
          </div>
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-docs">
              Documentation address
            </label>
            <input
              id="kel-connection-docs"
              className="kel-input"
              placeholder="https://example.com/docs"
              value={draft.docs_url}
              onChange={(event) => setDraft({ ...draft, docs_url: event.target.value })}
            />
          </div>
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-test">
              Test address
            </label>
            <input
              id="kel-connection-test"
              className="kel-input"
              placeholder="https://api.example.com/v1/account"
              value={draft.test_endpoint}
              onChange={(event) => setDraft({ ...draft, test_endpoint: event.target.value })}
            />
          </div>
          <p className="kel-meta">
            The test address is what Kel will check when it verifies this connection — nothing is called
            until you ask for that.
          </p>
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-notes">
              What Kel should use it for
            </label>
            <input
              id="kel-connection-notes"
              className="kel-input"
              placeholder="payouts only"
              value={draft.notes}
              onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
            />
          </div>
          <div className="kel-row">
            <KelButton variant="primary" disabled={busy || !draft.name.trim()} onClick={() => void saveConnection()}>
              {draft.id ? 'Save changes' : 'Add connection'}
            </KelButton>
            <KelButton variant="quiet" disabled={busy} onClick={() => setDraft(null)}>
              Cancel
            </KelButton>
          </div>
        </KelCard>
      )}
    </div>
  );
};

export default Connections;
