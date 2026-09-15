/**
 * Kel V1.4 Providers — one card per provider with the engine's real state, the readiness preflight,
 * and credential METADATA only (values never reach the engine).
 * Design: docs/v1.4/KEL_V1.4_PROVIDER_SPEC.md.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelErrorState,
  KelLoading,
  KelSection,
  KelTable,
  formatWhen,
} from '@renderer/components/kel/KelPrimitives';
import {
  kelProviders,
  type KelCredentialMetadata,
  type KelProviderStatus,
} from '@renderer/components/kel/kelApi';

const chipClass = (status: string): string => {
  if (status === 'healthy' || status === 'quota') return 'kel-chip kel-chip--ok';
  if (status === 'degraded' || status === 'quota_not_reported') return 'kel-chip kel-chip--uncertain';
  if (status === 'installed_not_authenticated') return 'kel-chip kel-chip--wait';
  if (status === 'not_installed' || status === 'unavailable') return 'kel-chip kel-chip--failed';
  return 'kel-chip';
};

const statusText = (provider: KelProviderStatus): string => {
  if (provider.status === 'quota') {
    return `${provider.quota}% left${provider.quota_reset ? ` · resets ${formatWhen(provider.quota_reset)}` : ''}`;
  }
  if (provider.status === 'quota_not_reported') return 'quota not reported';
  return provider.status.replace(/_/g, ' ');
};

const Providers: React.FC = () => {
  const [providers, setProviders] = useState<KelProviderStatus[] | null>(null);
  const [credentialRows, setCredentialRows] = useState<KelCredentialMetadata[]>([]);
  const [capability, setCapability] = useState('text');
  const [prefer, setPrefer] = useState('');
  const [readiness, setReadiness] = useState<{
    chosen: { provider: string; model: string; label: string } | null;
    chain: string[];
    reasons: string[];
    reason: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [secure, setSecure] = useState<{ available: boolean; providers: Record<string, string[]> } | null>(
    null
  );
  const [storeDraft, setStoreDraft] = useState({ provider: 'deepseek', field: 'api_key', value: '' });

  useEffect(() => {
    void (async () => {
      const status = await window.kelAPI?.credentials?.status().catch(() => null);
      if (status) setSecure(status);
    })();
  }, []);

  const load = useCallback(async () => {
    try {
      const [list, credentials] = await Promise.all([
        kelProviders.list(),
        kelProviders.credentials(),
      ]);
      setProviders(list.providers ?? []);
      setCredentialRows(credentials.credentials ?? []);
      setError(null);
    } catch (err) {
      setProviders([]);
      setError(err instanceof Error ? err.message : 'The engine did not answer.');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runReadiness = useCallback(async () => {
    setBusy(true);
    setNote(null);
    try {
      const result = await kelProviders.readiness(capability, prefer);
      setReadiness(result);
    } catch (err) {
      setNote(`Readiness failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  }, [capability, prefer]);

  const setMetadata = useCallback(
    async (provider: string) => {
      setBusy(true);
      setNote(null);
      try {
        await kelProviders.setCredential(provider, ['api_key'], `kel:provider:${provider}:api_key`);
        await load();
        setNote(
          `Recorded credential metadata for ${provider}. The value itself lives in the OS store, never in the engine.`
        );
      } catch (err) {
        setNote(`Could not record metadata: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  const deleteMetadata = useCallback(
    async (provider: string) => {
      setBusy(true);
      setNote(null);
      try {
        await kelProviders.deleteCredential(provider);
        await load();
        setNote(`Removed credential metadata for ${provider}.`);
      } catch (err) {
        setNote(`Could not remove metadata: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  return (
    <div className="kel-scope">
      <a className="kel-skip" href="#kel-providers-main">
        Skip to main content
      </a>
      <main className="kel-page" id="kel-providers-main" tabIndex={-1}>
        <div className="kel-page__head">
          <div>
            <h1 className="kel-h1">Providers</h1>
            <p className="kel-sub">
              {providers === null
                ? 'Reading provider state…'
                : `${providers.length} providers · ${providers.filter((p) => p.status === 'healthy' || p.status === 'quota').length} usable right now`}
            </p>
          </div>
          <span className="kel-grow" />
          <KelButton variant="secondary" onClick={() => void load()} disabled={busy}>
            Reload
          </KelButton>
        </div>

        {error && (
          <KelErrorState
            title="Provider state could not be read"
            cause={error}
            fix="Check that the Kel engine is running, then press Reload."
          />
        )}
        {!error && providers === null && <KelLoading rows={4} />}
        {note && <p className="kel-meta">{note}</p>}

        {!error &&
          (providers ?? []).map((provider) => (
            <KelCard
              key={provider.provider}
              title={provider.label}
              chip={<span className={chipClass(provider.status)}>{statusText(provider)}</span>}
              actions={
                <span className="kel-row">
                  {provider.class === 'api' ? (
                    <>
                      <KelButton
                        variant="secondary"
                        disabled={busy}
                        onClick={() => void setMetadata(provider.provider)}
                      >
                        Set credential metadata
                      </KelButton>
                      <KelButton
                        variant="quiet"
                        disabled={busy}
                        onClick={() => void deleteMetadata(provider.provider)}
                      >
                        Remove
                      </KelButton>
                    </>
                  ) : null}
                </span>
              }
            >
              <p className="kel-sub">
                {provider.class === 'native-cli' ? 'Native CLI' : 'API'} ·{' '}
                {provider.auth_mode === 'subscription' ? 'subscription session' : 'API key (billed per use)'}
                {provider.base_url ? ` · ${provider.base_url}` : ''}
              </p>
              <p className="kel-meta">
                {provider.note}
                {provider.failures ? ` · ${provider.failures} recent failures` : ''}
                {provider.circuit_until ? ` · circuit open until ${formatWhen(provider.circuit_until)}` : ''}
                {provider.planType ? ` · plan ${provider.planType}` : ''}
              </p>
              <KelTable
                head={['Model', 'Capabilities']}
                rows={(provider.models ?? []).map((model) => [
                  <span className="kel-strong" key={`${provider.provider}-${model.id}`}>
                    {model.id}
                  </span>,
                  <span className="kel-meta" key={`${provider.provider}-${model.id}-caps`}>
                    {(model.capabilities ?? []).join(' · ') || 'text'}
                  </span>,
                ])}
              />
            </KelCard>
          ))}

        <KelCard title="Readiness preflight">
          <p className="kel-sub">
            What Kel would use for a capability right now, and why — the engine records the fallback
            reason instead of guessing.
          </p>
          <div className="kel-row">
            {['text', 'vision', 'tools', 'edit', 'shell'].map((name) => (
              <KelButton
                key={name}
                variant={name === capability ? 'primary' : 'quiet'}
                onClick={() => setCapability(name)}
              >
                {name}
              </KelButton>
            ))}
            <span className="kel-meta">prefer</span>
            {['', 'claude-code', 'codex', 'internal', 'deepseek'].map((name) => (
              <KelButton
                key={name || 'auto'}
                variant={name === prefer ? 'primary' : 'quiet'}
                onClick={() => setPrefer(name)}
              >
                {name || 'auto'}
              </KelButton>
            ))}
            <KelButton variant="primary" disabled={busy} onClick={() => void runReadiness()}>
              Check readiness
            </KelButton>
          </div>
          {readiness && (
            <>
              <p className="kel-strong">
                {readiness.chosen
                  ? `Chosen: ${readiness.chosen.label} · ${readiness.chosen.model}`
                  : 'No provider can take this capability right now'}
              </p>
              <p className="kel-meta">{readiness.reason}</p>
              {readiness.reasons.length > 0 && (
                <ul>
                  {readiness.reasons.map((reason) => (
                    <li className="kel-meta" key={reason}>
                      {reason}
                    </li>
                  ))}
                </ul>
              )}
              <p className="kel-meta">Chain: {readiness.chain.join(' → ') || 'none'}</p>
            </>
          )}
        </KelCard>

        <KelSection title="Store a provider credential (OS-backed)">
          <p className="kel-sub">
            The value is encrypted by the desktop main process with Windows DPAPI (Electron
            <span className="kel-code"> safeStorage </span>) and never reaches the engine, which keeps
            only the field names and a reference. No IPC returns the value to this window.
          </p>
          <div className="kel-row">
            <select
              className="kel-input"
              aria-label="Provider"
              value={storeDraft.provider}
              onChange={(event) => setStoreDraft({ ...storeDraft, provider: event.target.value })}
            >
              {(providers ?? []).map((item) => (
                <option key={item.provider} value={item.provider}>
                  {item.label}
                </option>
              ))}
            </select>
            <input
              className="kel-input"
              aria-label="Field name"
              value={storeDraft.field}
              onChange={(event) => setStoreDraft({ ...storeDraft, field: event.target.value })}
            />
            <input
              className="kel-input"
              type="password"
              aria-label="Credential value"
              placeholder="paste the key — the engine never stores it"
              value={storeDraft.value}
              onChange={(event) => setStoreDraft({ ...storeDraft, value: event.target.value })}
            />
            <KelButton
              variant="primary"
              disabled={busy || !storeDraft.value || !secure?.available}
              onClick={() => {
                void (async () => {
                  setBusy(true);
                  setNote(null);
                  try {
                    await window.kelAPI?.credentials?.set(
                      storeDraft.provider,
                      storeDraft.field || 'api_key',
                      storeDraft.value
                    );
                    setStoreDraft((draft) => ({ ...draft, value: '' }));
                    const status = await window.kelAPI?.credentials?.status();
                    if (status) setSecure(status);
                    setNote(`Stored ${storeDraft.field || 'api_key'} for ${storeDraft.provider}.`);
                    await load();
                  } catch (err) {
                    setNote(
                      `Could not store the credential: ${
                        err instanceof Error ? err.message : String(err)
                      }`
                    );
                  } finally {
                    setBusy(false);
                  }
                })();
              }}
            >
              Store credential
            </KelButton>
          </div>
          <p className="kel-meta">
            {secure?.available
              ? `OS-backed storage available · stored: ${
                  Object.entries(secure.providers)
                    .map(([provider, fields]) => `${provider} (${fields.join(', ')})`)
                    .join(' · ') || 'nothing yet'
                }`
              : 'OS-backed storage is unavailable on this system — Kel keeps metadata only.'}
          </p>
        </KelSection>

        <KelSection title="Credential metadata (values are never stored here)">
          {credentialRows.length === 0 ? (
            <KelEmpty
              title="No Kel-owned credential metadata yet."
              why="The engine stores the provider, the field names, and a reference — the value itself lives in the OS-backed store."
            />
          ) : (
            <KelTable
              head={['Provider', 'Fields', 'Reference', 'Updated']}
              rows={credentialRows.map((row) => [
                <span className="kel-strong" key={`${row.provider}-p`}>
                  {row.provider}
                </span>,
                <span className="kel-meta" key={`${row.provider}-f`}>
                  {(row.fields ?? []).join(', ')}
                </span>,
                <span className="kel-code" key={`${row.provider}-r`}>
                  {row.credential_ref}
                </span>,
                <span className="kel-meta" key={`${row.provider}-u`}>
                  {formatWhen(row.updated ?? null)}
                </span>,
              ])}
            />
          )}
        </KelSection>
      </main>
    </div>
  );
};

export default Providers;
