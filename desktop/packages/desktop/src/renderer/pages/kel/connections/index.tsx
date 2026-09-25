import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import connectionIcon from '@renderer/assets/figma/nav-connections.svg';
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
 *
 * V2-03 adds the known services: the eight services Nick uses come with their address, the header the
 * credential goes in, where the documentation is, and what he has to go and fetch. Picking one fills
 * the form in; adding it by hand works exactly the same way.
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
  CONNECTION_CHECK_LABELS,
  KNOWN_SERVICE_SOURCE_LABELS,
  connectionAnswerText,
  connectionCheckSentence,
  connectionCredentialField,
  connectionCustodyKey,
  connectionTemplate,
  kelConnections,
  knownServiceDraft,
  type KelConnection,
  type KelConnectionAction,
  type KelConnectionList,
  type KelConnectionRun,
  type KelKnownService,
} from '@renderer/components/kel/kelApi';

interface Draft {
  id?: string;
  name: string;
  kind: KelConnection['kind'];
  base_url: string;
  auth_method: KelConnection['auth_method'];
  auth_header: string;
  /** null: Kel decides; '': send the value as it is; a word: add that word in front. */
  auth_prefix: string | null;
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
  auth_prefix: null,
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
  auth_prefix: connection.auth_prefix,
  docs_url: connection.docs_url,
  test_endpoint: connection.test_endpoint,
  notes: connection.notes,
});

const credentialDraftFor = (connection: KelConnection, list: KelConnectionList) => ({
  id: connection.id,
  name: connection.name,
  field: connection.credential_fields[0] ?? connectionCredentialField(list, connection.kind),
  header: connection.auth_header || 'Authorization',
  usesHeader: connection.auth_method === 'header' || connection.auth_method === 'bearer',
  headerEditable: connection.auth_method === 'header',
  value: '',
});

/** The three things a person can mean by "how the credential is presented". */
const prefixMode = (prefix: string | null): 'auto' | 'raw' | 'custom' =>
  prefix === null || prefix === undefined ? 'auto' : prefix === '' ? 'raw' : 'custom';

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
    header: string;
    usesHeader: boolean;
    headerEditable: boolean;
    value: string;
  } | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null);
  const [known, setKnown] = useState<KelKnownService[]>([]);
  const [actionsByConnection, setActionsByConnection] = useState<Record<string, KelConnectionAction[]>>(
    {}
  );
  const [answers, setAnswers] = useState<Record<string, KelConnectionRun>>({});
  const [confirmAction, setConfirmAction] = useState<string | null>(null);
  const [showAdvancedConnectionFields, setShowAdvancedConnectionFields] = useState(false);

  const load = useCallback(async () => {
    let current: KelConnection[] = [];
    try {
      const listed = await kelConnections.list();
      setList(listed);
      current = listed.connections;
      setError(null);
    } catch (err) {
      setList({ connections: [], counts: { ready: 0, needs_credentials: 0 }, states: [], kinds: [], templates: [] });
      setError(err);
    }
    // The shell's own view of what it holds. Best effort: without it the page still shows the
    // engine's truth, it just cannot reconcile a disagreement.
    const shell = await window.kelAPI?.credentials?.connectionStatus?.().catch((): undefined => undefined);
    setHeldByShell(shell ?? null);
    // The services Kel already knows how to talk to. Best effort too: without them Nick types the
    // addresses himself, which is exactly what an unknown service needs anyway.
    const services = await kelConnections.knownServices().catch((): null => null);
    setKnown(services?.services ?? []);
    // V2-04: what Kel can do with the services that are actually usable. Best effort again — a connection
    // without a credential has nothing Kel can do yet, and the page still works without this.
    const usable = current.filter((item) => item.has_credentials);
    const found = await Promise.all(
      usable.map(async (item) => {
        const row = await kelConnections.actions(item.id).catch((): null => null);
        return [item.id, row?.actions ?? []] as const;
      })
    );
    setActionsByConnection(Object.fromEntries(found));
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const draftOpen = draft !== null;
  useEffect(() => {
    if (draftOpen) document.getElementById('kel-connection-name')?.focus();
  }, [draftOpen]);

  const connections = useMemo(() => list?.connections ?? [], [list]);

  /** The connections Kel could actually use: the ones with a credential the shell holds. */
  const usable = useMemo(
    () => connections.filter((connection) => connection.has_credentials),
    [connections]
  );

  /** The ones with something Kel can actually do, so the card never lists an empty service. */
  const doable = useMemo(
    () => usable.filter((connection) => (actionsByConnection[connection.id] ?? []).length > 0),
    [usable, actionsByConnection]
  );

  /** The known services Kel can add with one click — the ones not already connected. */
  const addable = useMemo(
    () => known.filter((service) => !connections.some((connection) => connection.id === service.id)),
    [known, connections]
  );

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
        auth_prefix: draft.auth_prefix,
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
      const connection = list?.connections.find((item) => item.id === pending.id);
      if (connection && pending.headerEditable && pending.header !== connection.auth_header) {
        await kelConnections.save({ ...draftFor(connection), auth_header: pending.header });
      }
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
  }, [credentialDraft, list, load]);

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

  /**
   * V2-04b: the account sign-in. Only the Kel app can finish it — the main process opens the system
   * browser, claims the finished sign-in into the OS-backed custody, and hands this page the
   * outcome. A signed-in connection signs out here too.
   */
  const signInConnection = useCallback(
    async (connection: KelConnection) => {
      setBusy(true);
      setNote(null);
      try {
        const custody = window.kelAPI?.credentials;
        if (connection.auth_state === 'connected') {
          if (!custody?.oauthRevoke)
            throw new Error('Signing out of a service is only available in the Kel app.');
          const done = await custody.oauthRevoke(connection.id);
          await load();
          setNote(String(done?.note ?? `${connection.name} is signed out.`));
          return;
        }
        if (!custody?.oauthConnect)
          throw new Error('Signing in is only available in the Kel app, where the credential lives.');
        const outcome = await custody.oauthConnect(connection.id);
        await load();
        setNote(
          outcome?.state === 'connected'
            ? `${connection.name} is connected.`
            : String(outcome?.note ?? 'The sign-in did not finish.')
        );
      } catch (err) {
        setNote(failureSentence(err, 'Kel could not finish that sign-in — try again.'));
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  /**
   * V2-04: do one thing with a service. The shell decrypts the credential, the engine makes the request
   * and records that it happened, and the service's answer comes back here — where it is shown and
   * nowhere else.
   */
  const doAction = useCallback(
    async (connection: KelConnection, action: KelConnectionAction, confirmed = false) => {
      setBusy(true);
      setNote(null);
      try {
        const custody = window.kelAPI?.credentials;
        if (!custody?.runConnection)
          throw new Error('Doing something with a connection is only available in the Kel app.');
        const done = (await custody.runConnection(
          connection.id,
          action.id,
          {},
          confirmed
        )) as KelConnectionRun;
        setAnswers((current) => ({ ...current, [action.id]: done }));
        setConfirmAction(null);
        setNote(
          done.state === 'ok' ? `${action.name} — done.` : `${action.name} — ${done.note}`
        );
      } catch (err) {
        setNote(failureSentence(err, 'Kel could not do that — try again.'));
      } finally {
        setBusy(false);
      }
    },
    []
  );

  const removeConnection = useCallback(
    async (connection: KelConnection) => {
      setBusy(true);
      setNote(null);
      try {
        // The value first (only the main process can reach it), then the record.
        await window.kelAPI?.credentials?.remove(connectionCustodyKey(connection.id));
        await kelConnections.remove(connection.id);
        setCredentialDraft(null);
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
  const pendingAction = doable.flatMap((connection) =>
    (actionsByConnection[connection.id] ?? []).map((action) => ({ connection, action }))
  ).find(({ action }) => action.id === confirmAction);

  return (
    <div className="kel-page kel-connections-page">
      <div className="kel-page__head">
        <div><ShellWorkspaceLink /><h1 className="kel-h1">Connections</h1></div>
        {connections.length > 0 && <KelButton variant="primary" onClick={() => setDraft({ ...EMPTY_DRAFT })} disabled={busy}>
          Add a service
        </KelButton>}
      </div>

      {note && <p className="kel-meta">{note}</p>}

      <KelCard
        className={`kel-connections-services${connections.length === 0 ? ' kel-connections-empty' : ''}`}
        title="Services"
        chip={
          <span className="kel-meta">
            {connections.length === 0
              ? 'none yet'
              : `${ready} ready · ${needing} needing a credential`}
          </span>
        }
      >
        {connections.length === 0 && <p className="kel-connections-caption">The services Kel can use. You keep the credential.</p>}
        {connections.length === 0 ? (
          <div className="kel-connections-empty-body"><img src={connectionIcon} alt="" width={20} height={20} /><KelEmpty
            title="No connections yet."
            why="Add a service and its credential. Then Kel can work with it directly."
            actionLabel="Add a service"
            onAction={() => setDraft({ ...EMPTY_DRAFT })}
          /></div>
        ) : (
          connections.map((connection) => {
            const shellFields = heldByShell?.[connection.id] ?? [];
            const disagree = shellFields.length > 0 && !connection.has_credentials;
            return (
              <div className="kel-row kel-connection-row kel-connection-configured-row" key={connection.id}>
                <img className="kel-connection-row-icon" src={connectionIcon} alt="" />
                <div className="kel-attention__text">
                  <strong>{connection.name}</strong>
                  <span className="kel-meta">
                    {[connection.kind_label, connection.base_url]
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
                  {connection.kind === 'oauth' && (
                    <span className="kel-meta">
                      {connection.auth_state === 'connected'
                        ? `Signed in${connection.auth_scopes.length ? ` · ${connection.auth_scopes.length} permission${connection.auth_scopes.length === 1 ? '' : 's'}` : ''}`
                        : connection.auth_state === 'needs_reconnect'
                          ? 'The sign-in no longer works — connect again'
                          : connection.auth_state === 'pending'
                            ? 'Sign-in started in your browser'
                            : 'Not signed in'}
                    </span>
                  )}
                </div>
                <span className="kel-connection-status" title={stateSentence(connection)} data-state={connection.has_credentials ? 'ready' : 'needs-credential'}>
                  {connection.has_credentials ? 'Ready' : 'Needs a credential'}
                </span>
                <span className="kel-grow" />
                {connection.can_test && (
                  <KelButton
                    variant="quiet"
                    disabled={busy}
                    onClick={() => void checkConnection(connection)}
                  >
                    Test
                  </KelButton>
                )}
                <KelButton variant="primary" disabled={busy} onClick={() => setCredentialDraft(credentialDraftFor(connection, list))}>
                  Edit
                </KelButton>
                <details className="kel-connection-more"><summary>More actions</summary>
                <KelButton variant="quiet" disabled={busy} onClick={() => setDraft(draftFor(connection))}>
                  Edit service details
                </KelButton>
                {connection.kind === 'oauth' && (
                  <KelButton
                    variant={connection.auth_state === 'connected' ? 'quiet' : 'primary'}
                    disabled={busy}
                    onClick={() => void signInConnection(connection)}
                  >
                    {connection.auth_state === 'connected'
                      ? 'Sign out'
                      : connection.auth_state === 'needs_reconnect'
                        ? 'Reconnect'
                        : 'Connect'}
                  </KelButton>
                )}
                <KelButton
                  variant={connection.has_credentials ? 'quiet' : 'primary'}
                  disabled={busy}
                  onClick={() => setCredentialDraft(credentialDraftFor(connection, list))}
                >
                  {connection.has_credentials ? 'Replace credential' : 'Add credential'}
                </KelButton>
                {connection.has_credentials && (
                  <KelButton variant="quiet" disabled={busy} onClick={() => void forgetCredential(connection)}>
                    Remove credential
                  </KelButton>
                )}
                </details>
                {credentialDraft?.id === connection.id && (
                  <div className="kel-connection-inline-credential">
                    <div className="kel-connection-credential-fields">
                      <label className="kel-meta" htmlFor="kel-connection-field">{credentialDraft.usesHeader ? 'Header name' : 'Credential field'}
                        <input id="kel-connection-field" className="kel-input"
                          value={credentialDraft.usesHeader ? credentialDraft.header : credentialDraft.field}
                          readOnly={credentialDraft.usesHeader && !credentialDraft.headerEditable}
                          onChange={(event) => setCredentialDraft({ ...credentialDraft,
                            [credentialDraft.usesHeader ? 'header' : 'field']: event.target.value })} />
                      </label>
                      <label className="kel-meta" htmlFor="kel-connection-value">Credential
                        <input id="kel-connection-value" className="kel-input" type="password" autoComplete="off"
                          placeholder="••••••••••••••••••••" value={credentialDraft.value}
                          onChange={(event) => setCredentialDraft({ ...credentialDraft, value: event.target.value })} />
                      </label>
                    </div>
                    <div className="kel-connection-credential-actions">
                      {confirmRemove === connection.id ? <>
                        <KelButton variant="quiet" disabled={busy} onClick={() => void removeConnection(connection)}>Confirm remove</KelButton>
                        <KelButton variant="quiet" disabled={busy} onClick={() => setConfirmRemove(null)}>Keep service</KelButton>
                      </> : <KelButton variant="quiet" disabled={busy} onClick={() => setConfirmRemove(connection.id)}>Remove service</KelButton>}
                      <span className="kel-grow" />
                      <KelButton variant="quiet" disabled={busy} onClick={() => setCredentialDraft(null)}>Cancel</KelButton>
                      <KelButton variant="primary" disabled={busy || !credentialDraft.value || !credentialDraft.field || (credentialDraft.usesHeader && !credentialDraft.header)}
                        onClick={() => void saveCredential()}>Save credential</KelButton>
                    </div>
                    <p className="kel-meta kel-connection-custody-note">Kel stores the value in this computer's secure store.</p>
                  </div>
                )}
              </div>
            );
          })
        )}
      </KelCard>

      {connections.length > 0 && addable.length > 0 && <KelCard title="Available services" className="kel-connections-available">
        <p className="kel-connections-caption">Known services you can set up when you need them.</p>
        <div className="kel-connections-available-list">{addable.map((service) => <div className="kel-row kel-connection-row kel-connection-available-row" key={service.id}>
          <div className="kel-attention__text">
            <strong>{service.name}</strong>
            <span className="kel-meta">
              {[connectionTemplate(list, service.kind)?.label,
                service.base_url || 'address comes with your credential'].filter(Boolean).join(' · ')}
            </span>
            <span className="kel-connection-extra">Kel needs {service.credential}.</span>
            <span className="kel-connection-extra">{KNOWN_SERVICE_SOURCE_LABELS[service.source]}</span>
          </div>
          <span className="kel-grow" />
          <KelButton variant="primary" disabled={busy}
            onClick={() => setDraft({ ...knownServiceDraft(service) })}>Set up {service.name}</KelButton>
        </div>)}</div>
      </KelCard>}

      {doable.length > 0 && (
        <KelCard
          title="What Kel can do"
          className="kel-connections-actions"
        >
          <p className="kel-connections-caption">Kel runs these only when you ask.</p>
          {doable.map((connection) => {
            const actions = actionsByConnection[connection.id] ?? [];
            return actions.map((action) => {
              const answer = answers[action.id];
              return (
                <div className="kel-row kel-connection-action-row" key={action.id}>
                  <div className="kel-attention__text" title={action.description}>
                    <strong>{action.name}</strong>
                    <span className="kel-meta">{connection.name}</span>
                    {answer && (
                      <span className="kel-meta">
                        {CONNECTION_CHECK_LABELS[answer.state] ?? 'Done'} — {answer.note}
                      </span>
                    )}
                    {answer && connectionAnswerText(answer.result) && (
                      <pre className="kel-meta">{connectionAnswerText(answer.result)}</pre>
                    )}
                  </div>
                  <span className="kel-grow" />
                  <span className="kel-connection-action-status" data-mutating={action.mutating}>
                    {action.mutating ? 'Asks first' : 'Reads only'}
                  </span>
                  <KelButton variant="primary" disabled={busy}
                    onClick={() => action.mutating ? setConfirmAction(action.id) : void doAction(connection, action)}>
                    Run
                  </KelButton>
                </div>
              );
            });
          })}
          {pendingAction && <div className="kel-connection-action-confirmation">
            <p>⚠ This changes something in {pendingAction.connection.name}. Kel asks before it changes anything.</p>
            <div className="kel-row">
              <span className="kel-grow" />
              <KelButton variant="quiet" disabled={busy} onClick={() => setConfirmAction(null)}>Cancel</KelButton>
              <KelButton variant="primary" disabled={busy}
                onClick={() => void doAction(pendingAction.connection, pendingAction.action, true)}>Yes, run it</KelButton>
            </div>
          </div>}
        </KelCard>
      )}

      {draft && (
        <KelCard
          title={draft.id ? `Edit ${draft.name || 'connection'}` : 'Add a service'}
          className={`kel-connection-form${showAdvancedConnectionFields ? ' kel-connection-form--advanced' : ''}`}
          chip={<span className="kel-meta">what Kel needs to reach the service</span>}
        >
          {!draft.id && addable.length > 0 && <details className="kel-connection-templates">
            <summary>Start with a known service</summary>
            <div>{addable.map((service) => <div key={service.id}>
              <button type="button" onClick={() => setDraft({ ...knownServiceDraft(service) })}>Set up {service.name}</button>
              <span>Kel needs {service.credential}.</span>
              <span>{KNOWN_SERVICE_SOURCE_LABELS[service.source]}</span>
            </div>)}</div>
          </details>}
          <button type="button" className="kel-connection-advanced-toggle"
            aria-expanded={showAdvancedConnectionFields}
            onClick={() => setShowAdvancedConnectionFields((open) => !open)}>Advanced options</button>
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
          <div className="kel-row kel-connection-advanced-field">
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
              {(list?.templates ?? []).map((option) => (
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
            <>
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
              <div className="kel-row kel-connection-advanced-field">
                <label className="kel-meta" htmlFor="kel-connection-prefix">
                  How the credential is presented
                </label>
                <select
                  id="kel-connection-prefix"
                  className="kel-input"
                  value={prefixMode(draft.auth_prefix)}
                  onChange={(event) => {
                    const mode = event.target.value;
                    setDraft({
                      ...draft,
                      auth_prefix:
                        mode === 'auto' ? null : mode === 'raw' ? '' : (draft.auth_prefix || 'Bearer '),
                    });
                  }}
                >
                  <option value="auto">Kel works it out</option>
                  <option value="raw">Send the value exactly as it is</option>
                  <option value="custom">Kel adds a word in front</option>
                </select>
              </div>
              {prefixMode(draft.auth_prefix) === 'custom' ? (
                <div className="kel-row kel-connection-advanced-field">
                  <label className="kel-meta" htmlFor="kel-connection-prefix-word">
                    The word before the credential
                  </label>
                  <input
                    id="kel-connection-prefix-word"
                    className="kel-input"
                    placeholder="Bearer "
                    value={draft.auth_prefix ?? ''}
                    onChange={(event) => setDraft({ ...draft, auth_prefix: event.target.value })}
                  />
                </div>
              ) : null}
              <span className="kel-meta kel-connection-advanced-field">
                Services expect this differently: GitHub and Stripe want “Bearer ”, Discord wants “Bot ”,
                Figma and ClickUp want the value exactly as it is.
              </span>
            </>
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
          <p className="kel-meta">Kel calls this to check the credential.</p>
          <div className="kel-row kel-connection-advanced-field">
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
