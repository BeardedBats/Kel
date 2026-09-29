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
 * D-87: the page is "Connect to X". One button per known service; choosing one fills in everything the
 * catalogue (`connection_services.py`) knows and asks only for the values Nick has to supply, under the
 * service's own name for each. The generic form for any other API sits behind a quiet "Other service".
 * Connected services are simple rows: name, state, Test, Disconnect.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Baseball, Figma, Github, Google } from '@icon-park/react';
import { KelButton, KelCard, KelLoading, formatWhen } from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import {
  CONNECTION_CHECK_LABELS,
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
  type KelKnownServiceField,
} from '@renderer/components/kel/kelApi';

interface Draft {
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

const draftFor = (connection: KelConnection): Draft & { id: string } => ({
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

/**
 * D-87: the values Nick supplies for a known service, in the catalogue's words. A catalogue without
 * field rows (an older engine) still gets a labelled field from the framework's template.
 */
export const connectFields = (
  service: KelKnownService,
  list: Pick<KelConnectionList, 'templates'> | null
): KelKnownServiceField[] => {
  if (service.fields?.length) return service.fields;
  if (service.auth_method === 'basic') {
    return [
      { name: 'username', label: 'Username', secret: false },
      { name: 'password', label: 'Password', secret: true },
    ];
  }
  return [
    {
      name: connectionCredentialField(list, service.kind),
      label: connectionTemplate(list, service.kind)?.credential_label || 'Credential',
      secret: true,
    },
  ];
};

/** ST-07: the row states the recorded check, not just that a credential exists. */
export const connectionRowStatus = (
  connection: Pick<KelConnection, 'has_credentials' | 'last_test_state' | 'last_test_at'> &
    Partial<Pick<KelConnection, 'kind' | 'auth_state'>>
): { label: string; state: string } => {
  if (!connection.has_credentials) return { label: 'Needs a credential', state: 'needs-credential' };
  if (connection.kind === 'oauth' && connection.auth_state && connection.auth_state !== 'connected') {
    return {
      label: connection.auth_state === 'needs_reconnect' ? 'Sign-in expired' : 'Not signed in',
      state: 'needs-credential',
    };
  }
  if (connection.last_test_at && connection.last_test_state) {
    return {
      label: CONNECTION_CHECK_LABELS[connection.last_test_state] ?? 'Checked',
      state: connection.last_test_state === 'ok' ? 'ready' : 'check-failed',
    };
  }
  return { label: 'Ready — not tested', state: 'ready' };
};

/** Service icons the app already ships (IconPark, monochrome); anything else gets the neutral glyph. */
const SERVICE_ICONS: Record<string, React.ComponentType<Record<string, unknown>>> = {
  github: Github,
  figma: Figma,
  'google-drive': Google,
  'pitcher-list': Baseball,
};

const ServiceGlyph: React.FC<{ id: string }> = ({ id }) => {
  const Icon = SERVICE_ICONS[id];
  return Icon ? (
    <span className="kel-connect-glyph" aria-hidden="true">
      <Icon theme="outline" size={16} fill="currentColor" strokeWidth={3} />
    </span>
  ) : (
    <img className="kel-connect-glyph" src={connectionIcon} alt="" />
  );
};

/** The three things a person can mean by "how the credential is presented". */
const prefixMode = (prefix: string | null): 'auto' | 'raw' | 'custom' =>
  prefix === null || prefix === undefined ? 'auto' : prefix === '' ? 'raw' : 'custom';

const AUTH_METHODS: Array<{ id: KelConnection['auth_method']; label: string }> = [
  { id: 'header', label: 'Header' },
  { id: 'bearer', label: 'Bearer token' },
  { id: 'query', label: 'Query parameter' },
  { id: 'basic', label: 'Username and password' },
];

interface Connecting {
  service: KelKnownService;
  values: Record<string, string>;
  address: string;
}

const Connections: React.FC = () => {
  const [list, setList] = useState<KelConnectionList | null>(null);
  const [heldByShell, setHeldByShell] = useState<Record<string, string[]> | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [connecting, setConnecting] = useState<Connecting | null>(null);
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
  const [confirmDisconnect, setConfirmDisconnect] = useState<string | null>(null);
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
    // The services Kel already knows. Best effort: without them "Other service" still works.
    const services = await kelConnections.knownServices().catch((): null => null);
    setKnown(services?.services ?? []);
    // V2-04: what Kel can do with the services that are actually usable. Best effort again.
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

  const connectingId = connecting?.service.id;
  useEffect(() => {
    if (connectingId) document.querySelector<HTMLInputElement>('.kel-connect-form input')?.focus();
  }, [connectingId]);

  const connections = useMemo(() => list?.connections ?? [], [list]);

  /** The ones with something Kel can actually do, so the card never lists an empty service. */
  const doable = useMemo(
    () =>
      connections.filter(
        (connection) => connection.has_credentials && (actionsByConnection[connection.id] ?? []).length > 0
      ),
    [connections, actionsByConnection]
  );

  /** The known services still to connect — the ones with no connection row yet. */
  const addable = useMemo(
    () => known.filter((service) => !connections.some((connection) => connection.id === service.id)),
    [known, connections]
  );

  const knownById = useMemo(() => new Map(known.map((service) => [service.id, service])), [known]);

  const startConnect = useCallback((service: KelKnownService) => {
    setDraft(null);
    setNote(null);
    setConnecting({ service, values: {}, address: '' });
  }, []);

  /**
   * D-87: connect a known service. Save the catalogue's row, hand each value to the shell's custody (the
   * value never goes to the engine), then — for an account sign-in — start the browser sign-in.
   */
  const connectService = useCallback(async () => {
    const pending = connecting;
    if (!pending) return;
    const { service, values, address } = pending;
    setBusy(true);
    setNote(null);
    try {
      const custody = window.kelAPI?.credentials;
      if (!custody) throw new Error('Storing credentials is only available in the Kel app.');
      const existing = connections.find((item) => item.id === service.id);
      const base = knownServiceDraft(service);
      const saved = await kelConnections.save({
        ...base,
        ...(existing ? { id: existing.id } : {}),
        base_url: service.base_url || address.trim(),
      });
      for (const field of connectFields(service, list)) {
        await custody.set(connectionCustodyKey(saved.id), field.name, values[field.name] ?? '');
      }
      setConnecting(null);
      if (service.kind === 'oauth' && custody.oauthConnect) {
        const outcome = await custody.oauthConnect(saved.id);
        await load();
        setNote(
          outcome?.state === 'connected'
            ? `${service.name} is connected.`
            : String(outcome?.note ?? 'The sign-in did not finish.')
        );
        return;
      }
      await load();
      const listed = await kelConnections.list().catch((): null => null);
      const recorded = Boolean(listed?.connections?.find((item) => item.id === saved.id)?.has_credentials);
      setNote(
        recorded
          ? `${service.name} is connected.`
          : 'The credential is stored, but Kel did not record it back — connect again before relying on it.'
      );
    } catch (err) {
      setNote(failureSentence(err, 'That did not go through — check the details and try again.'));
    } finally {
      setBusy(false);
    }
  }, [connecting, connections, list, load]);

  const saveConnection = useCallback(async () => {
    if (!draft) return;
    setBusy(true);
    setNote(null);
    try {
      const saved = await kelConnections.save({ ...draft });
      setDraft(null);
      await load();
      setNote(`${saved.name} is saved.`);
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
          ? `${pending.name} is connected.`
          : 'The credential is stored, but Kel did not record it back — save it again before relying on it.'
      );
    } catch (err) {
      setNote(failureSentence(err, 'Kel could not store that credential — try again.'));
    } finally {
      setBusy(false);
    }
  }, [credentialDraft, list, load]);

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
        if (!custody?.testConnection) throw new Error('Checking a connection is only available in the Kel app.');
        const checked = await custody.testConnection(connection.id);
        await load();
        setNote(`Checked ${checked.name}.`);
      } catch (err) {
        setNote(failureSentence(err, 'Kel could not check that connection — try again.'));
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  /** V2-04b: the account sign-in runs in the main process; this page only asks and shows the outcome. */
  const signInConnection = useCallback(
    async (connection: KelConnection) => {
      setBusy(true);
      setNote(null);
      try {
        const custody = window.kelAPI?.credentials;
        if (!custody?.oauthConnect) throw new Error('Signing in is only available in the Kel app.');
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

  /** V2-04: do one thing with a service; the answer is shown here and nowhere else. */
  const doAction = useCallback(
    async (connection: KelConnection, action: KelConnectionAction, confirmed = false) => {
      setBusy(true);
      setNote(null);
      try {
        const custody = window.kelAPI?.credentials;
        if (!custody?.runConnection)
          throw new Error('Doing something with a connection is only available in the Kel app.');
        const done = (await custody.runConnection(connection.id, action.id, {}, confirmed)) as KelConnectionRun;
        setAnswers((current) => ({ ...current, [action.id]: done }));
        setConfirmAction(null);
        setNote(done.state === 'ok' ? `${action.name} — done.` : `${action.name} — ${done.note}`);
      } catch (err) {
        setNote(failureSentence(err, 'Kel could not do that — try again.'));
      } finally {
        setBusy(false);
      }
    },
    []
  );

  /** Disconnect: sign out if signed in, then the value (only the main process can reach it), then the record. */
  const disconnect = useCallback(
    async (connection: KelConnection) => {
      setBusy(true);
      setNote(null);
      try {
        const custody = window.kelAPI?.credentials;
        if (connection.kind === 'oauth' && connection.auth_state === 'connected') {
          await custody?.oauthRevoke?.(connection.id).catch((): undefined => undefined);
        }
        await custody?.remove(connectionCustodyKey(connection.id));
        await kelConnections.remove(connection.id);
        setCredentialDraft(null);
        setConfirmDisconnect(null);
        await load();
        setNote(`${connection.name} is disconnected.`);
      } catch (err) {
        setNote(failureSentence(err, 'Kel could not disconnect that service — try again.'));
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

  const pendingAction = doable
    .flatMap((connection) => (actionsByConnection[connection.id] ?? []).map((action) => ({ connection, action })))
    .find(({ action }) => action.id === confirmAction);

  const connectingFields = connecting ? connectFields(connecting.service, list) : [];
  const connectReady =
    connecting !== null &&
    (Boolean(connecting.service.base_url) || Boolean(connecting.address.trim())) &&
    connectingFields.every((field) => Boolean(connecting.values[field.name]));

  return (
    <div className="kel-page kel-connections-page">
      <div className="kel-page__head">
        <div><ShellWorkspaceLink /><h1 className="kel-h1">Connections</h1></div>
      </div>

      {note && <p className="kel-meta">{note}</p>}

      {connections.length > 0 && (
        <KelCard className="kel-connections-services" title="Connected">
          {connections.map((connection) => {
            const shellFields = heldByShell?.[connection.id] ?? [];
            const disagree = shellFields.length > 0 && !connection.has_credentials;
            const status = connectionRowStatus(connection);
            const service = knownById.get(connection.id);
            const failedCheck =
              connection.last_test_at && connection.last_test_state && connection.last_test_state !== 'ok'
                ? connectionCheckSentence(connection, formatWhen(connection.last_test_at))
                : null;
            const needsSignIn =
              connection.kind === 'oauth' && connection.has_credentials && connection.auth_state !== 'connected';
            return (
              <div className="kel-row kel-connection-row kel-connection-configured-row" key={connection.id}>
                <ServiceGlyph id={connection.id} />
                <div className="kel-attention__text">
                  <strong>{connection.name}</strong>
                  {disagree && (
                    <span className="kel-meta kel-connection-warning">
                      This computer still holds a credential for it that Kel has no record of — save it
                      again to restore the link.
                    </span>
                  )}
                  {failedCheck && <span className="kel-meta kel-connection-warning">{failedCheck}</span>}
                </div>
                <span
                  className="kel-connection-status"
                  title={
                    connection.last_test_at ? connectionCheckSentence(connection, formatWhen(connection.last_test_at)) ?? undefined : undefined
                  }
                  data-state={status.state}
                  data-testid="connection-row-status"
                >
                  {status.label}
                </span>
                {needsSignIn && (
                  <KelButton variant="primary" disabled={busy} onClick={() => void signInConnection(connection)}>
                    {service?.connect_label ?? 'Connect'}
                  </KelButton>
                )}
                {!connection.has_credentials && (
                  <KelButton
                    variant="primary"
                    disabled={busy}
                    onClick={() =>
                      service ? startConnect(service) : setCredentialDraft(credentialDraftFor(connection, list))
                    }
                  >
                    Add credential
                  </KelButton>
                )}
                {connection.can_test && (
                  <KelButton
                    variant="quiet"
                    disabled={busy || !connection.has_credentials}
                    onClick={() => void checkConnection(connection)}
                  >
                    Test
                  </KelButton>
                )}
                {confirmDisconnect === connection.id ? (
                  <>
                    <KelButton variant="danger" disabled={busy} onClick={() => void disconnect(connection)}>
                      Confirm disconnect
                    </KelButton>
                    <KelButton variant="quiet" disabled={busy} onClick={() => setConfirmDisconnect(null)}>
                      Keep
                    </KelButton>
                  </>
                ) : (
                  <KelButton variant="quiet" disabled={busy} onClick={() => setConfirmDisconnect(connection.id)}>
                    Disconnect
                  </KelButton>
                )}
                {credentialDraft?.id === connection.id && (
                  <div className="kel-connection-inline-credential">
                    <div className="kel-connection-credential-fields">
                      <label className="kel-meta" htmlFor="kel-connection-field">
                        {credentialDraft.usesHeader ? 'Header name' : 'Credential field'}
                        <input
                          id="kel-connection-field"
                          className="kel-input"
                          value={credentialDraft.usesHeader ? credentialDraft.header : credentialDraft.field}
                          readOnly={credentialDraft.usesHeader && !credentialDraft.headerEditable}
                          onChange={(event) =>
                            setCredentialDraft({
                              ...credentialDraft,
                              [credentialDraft.usesHeader ? 'header' : 'field']: event.target.value,
                            })
                          }
                        />
                      </label>
                      <label className="kel-meta" htmlFor="kel-connection-value">
                        Credential
                        <input
                          id="kel-connection-value"
                          className="kel-input"
                          type="password"
                          autoComplete="off"
                          value={credentialDraft.value}
                          onChange={(event) => setCredentialDraft({ ...credentialDraft, value: event.target.value })}
                        />
                      </label>
                    </div>
                    <div className="kel-connection-credential-actions">
                      <span className="kel-grow" />
                      <KelButton variant="quiet" disabled={busy} onClick={() => setCredentialDraft(null)}>
                        Cancel
                      </KelButton>
                      <KelButton
                        variant="primary"
                        disabled={
                          busy ||
                          !credentialDraft.value ||
                          !credentialDraft.field ||
                          (credentialDraft.usesHeader && !credentialDraft.header)
                        }
                        onClick={() => void saveCredential()}
                      >
                        Save credential
                      </KelButton>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </KelCard>
      )}

      {connecting ? (
        <KelCard
          title={`Connect to ${connecting.service.name}`}
          className="kel-connection-form kel-connect-form"
        >
          {!connecting.service.base_url && (
            <div className="kel-row">
              <label className="kel-meta" htmlFor="kel-connect-address">
                API address
              </label>
              <input
                id="kel-connect-address"
                className="kel-input"
                autoComplete="off"
                value={connecting.address}
                onChange={(event) => setConnecting({ ...connecting, address: event.target.value })}
              />
            </div>
          )}
          {connectingFields.map((field) => (
            <div className="kel-row" key={field.name}>
              <label className="kel-meta" htmlFor={`kel-connect-${field.name}`}>
                {field.label}
              </label>
              <input
                id={`kel-connect-${field.name}`}
                className="kel-input"
                type={field.secret ? 'password' : 'text'}
                autoComplete="off"
                spellCheck={false}
                value={connecting.values[field.name] ?? ''}
                onChange={(event) =>
                  setConnecting({
                    ...connecting,
                    values: { ...connecting.values, [field.name]: event.target.value },
                  })
                }
              />
            </div>
          ))}
          {connecting.service.where && (
            <p className="kel-meta kel-connect-where" data-testid="connect-where">
              {connecting.service.where}
            </p>
          )}
          <div className="kel-row kel-connection-form__actions">
            <KelButton variant="quiet" disabled={busy} onClick={() => setConnecting(null)}>
              Cancel
            </KelButton>
            <KelButton variant="confirm" disabled={busy || !connectReady} onClick={() => void connectService()}>
              {connecting.service.connect_label ?? 'Connect'}
            </KelButton>
          </div>
        </KelCard>
      ) : draft ? (
        <KelCard
          title="Other service"
          className={`kel-connection-form${showAdvancedConnectionFields ? ' kel-connection-form--advanced' : ''}`}
        >
          <button
            type="button"
            className="kel-connection-advanced-toggle"
            aria-expanded={showAdvancedConnectionFields}
            onClick={() => setShowAdvancedConnectionFields((open) => !open)}
          >
            Advanced options
          </button>
          <div className="kel-row">
            <label className="kel-meta" htmlFor="kel-connection-name">
              Service name
            </label>
            <input
              id="kel-connection-name"
              className="kel-input"
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          </div>
          <div className="kel-row kel-connection-advanced-field">
            <label className="kel-meta" htmlFor="kel-connection-kind">
              Credential type
            </label>
            <select
              id="kel-connection-kind"
              className="kel-input"
              value={draft.kind}
              onChange={(event) => setDraft({ ...draft, kind: event.target.value as KelConnection['kind'] })}
            >
              {(list?.templates ?? []).map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
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
                      auth_prefix: mode === 'auto' ? null : mode === 'raw' ? '' : draft.auth_prefix || 'Bearer ',
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
          <div className="kel-row kel-connection-advanced-field">
            <label className="kel-meta" htmlFor="kel-connection-notes">
              What Kel should use it for
            </label>
            <input
              id="kel-connection-notes"
              className="kel-input"
              value={draft.notes}
              onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
            />
          </div>
          <div className="kel-row kel-connection-form__actions">
            <KelButton variant="quiet" disabled={busy} onClick={() => setDraft(null)}>
              Cancel
            </KelButton>
            <KelButton variant="confirm" disabled={busy || !draft.name.trim()} onClick={() => void saveConnection()}>
              Add connection
            </KelButton>
          </div>
        </KelCard>
      ) : (
        <KelCard className="kel-connections-connect" title={connections.length ? 'Connect another service' : 'Connect a service'}>
          {addable.length > 0 && (
            <div className="kel-connect-grid">
              {addable.map((service) => (
                <button
                  type="button"
                  key={service.id}
                  className="kel-connect-service"
                  disabled={busy}
                  onClick={() => startConnect(service)}
                >
                  <ServiceGlyph id={service.id} />
                  <span>{service.name}</span>
                </button>
              ))}
            </div>
          )}
          <button
            type="button"
            className="kel-connect-other"
            disabled={busy}
            onClick={() => {
              setNote(null);
              setDraft({ ...EMPTY_DRAFT });
            }}
          >
            Other service
          </button>
        </KelCard>
      )}

      {doable.length > 0 && (
        <KelCard title="What Kel can do" className="kel-connections-actions">
          {doable.map((connection) =>
            (actionsByConnection[connection.id] ?? []).map((action) => {
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
                  <KelButton
                    variant="primary"
                    disabled={busy}
                    onClick={() => (action.mutating ? setConfirmAction(action.id) : void doAction(connection, action))}
                  >
                    Run
                  </KelButton>
                </div>
              );
            })
          )}
          {pendingAction && (
            <div className="kel-connection-action-confirmation">
              <p>⚠ This changes something in {pendingAction.connection.name}.</p>
              <div className="kel-row">
                <span className="kel-grow" />
                <KelButton variant="quiet" disabled={busy} onClick={() => setConfirmAction(null)}>
                  Cancel
                </KelButton>
                <KelButton
                  variant="primary"
                  disabled={busy}
                  onClick={() => void doAction(pendingAction.connection, pendingAction.action, true)}
                >
                  Yes, run it
                </KelButton>
              </div>
            </div>
          )}
        </KelCard>
      )}
    </div>
  );
};

export default Connections;
