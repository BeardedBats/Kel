/**
 * Kel V1.4 Providers — one card per provider with the engine's real state, the readiness preflight,
 * and credential METADATA only (values never reach the engine).
 * Design: docs/v1.4/KEL_V1.4_PROVIDER_SPEC.md.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelLoading,
  KelSection,
  KelTable,
  formatWhen,
} from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import {
  kelCapabilities,
  kelProviders,
  type KelCapabilityRow,
  type KelCredentialMetadata,
  type KelProviderStatus,
} from '@renderer/components/kel/kelApi';
import { presentProvider, toneChipClass, usableNow } from '@renderer/components/kel/providerStatus';

const Providers: React.FC = () => {
  const navigate = useNavigate();
  const [providers, setProviders] = useState<KelProviderStatus[] | null>(null);
  const [capabilities, setCapabilities] = useState<KelCapabilityRow[] | null>(null);
  const [credentialRows, setCredentialRows] = useState<KelCredentialMetadata[]>([]);
  const [capability, setCapability] = useState('text');
  const [prefer, setPrefer] = useState('');
  const [readiness, setReadiness] = useState<{
    chosen: { provider: string; model: string; label: string } | null;
    chain: string[];
    reasons: string[];
    reason: string;
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [secure, setSecure] = useState<{ available: boolean; providers: Record<string, string[]> } | null>(
    null
  );
  const [storeDraft, setStoreDraft] = useState({ provider: 'deepseek', field: 'api_key', value: '' });
  const [keyDraft, setKeyDraft] = useState<{ provider: string; value: string } | null>(null);

  useEffect(() => {
    void (async () => {
      const status = await window.kelAPI?.credentials?.status().catch((): null => null);
      if (status) setSecure(status);
    })();
  }, []);

  const load = useCallback(async () => {
    try {
      const [list, credentials, capabilityRows] = await Promise.all([
        kelProviders.list(),
        kelProviders.credentials(),
        kelCapabilities().catch((): KelCapabilityRow[] => []),
      ]);
      setProviders(list.providers ?? []);
      setCredentialRows(credentials.credentials ?? []);
      setCapabilities(capabilityRows);
      setError(null);
    } catch (err) {
      setProviders([]);
      setError(err);
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
      setNote(`Readiness didn't go through. ${failureSentence(err, 'The engine did not answer — try again.')}`);
    } finally {
      setBusy(false);
    }
  }, [capability, prefer]);

  const saveKey = useCallback(
    async (provider: string) => {
      const draft = keyDraft;
      if (!draft || draft.provider !== provider || !draft.value) return;
      const field = 'api_key';
      setBusy(true);
      setNote(null);
      try {
        await window.kelAPI?.credentials?.set(provider, field, draft.value);
        await kelProviders.setCredential(provider, [field], `kel:provider:${provider}:${field}`);
        const status = await window.kelAPI?.credentials?.status();
        if (status) setSecure(status);
        const listedBack = Boolean(status?.providers?.[provider]?.includes(field));
        setKeyDraft(null);
        await load();
        setNote(
          listedBack
            ? `Saved and verified ${provider}: the key is in the OS store and recorded for the engine. Kel starts using it the next time its engine starts.`
            : `Saved ${provider}, but the OS store did not list the key back — check it again before relying on it.`
        );
      } catch (err) {
        setNote(`Couldn't save the key for ${provider}. ${failureSentence(err, 'The engine did not answer — try again.')}`);
      } finally {
        setBusy(false);
      }
    },
    [keyDraft, load]
  );

  const removeKey = useCallback(
    async (provider: string) => {
      setBusy(true);
      setNote(null);
      try {
        await window.kelAPI?.credentials?.remove(provider);
        await kelProviders.deleteCredential(provider);
        const status = await window.kelAPI?.credentials?.status();
        if (status) setSecure(status);
        await load();
        setNote(`Removed the stored key and its engine metadata for ${provider}.`);
      } catch (err) {
        setNote(`Couldn't remove the key for ${provider}. ${failureSentence(err, 'The engine did not answer — try again.')}`);
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
                : `${providers.length} providers · ${providers.filter(usableNow).length} usable right now`}
            </p>
          </div>
          <span className="kel-grow" />
          <KelButton variant="secondary" onClick={() => void load()} disabled={busy}>
            Reload
          </KelButton>
        </div>

        {error && <KelFailureCard error={error} onRetry={() => void load()} />}
        {!error && providers === null && <KelLoading rows={4} />}
        {note && <p className="kel-meta">{note}</p>}

        {!error &&
          (providers ?? []).map((provider) => {
            const view = presentProvider(provider);
            const needsSetup = view.label === 'Needs setup';
            const hasStored = credentialRows.some((row) => row.provider === provider.provider);
            return (
            <KelCard
              key={provider.provider}
              title={provider.label}
              chip={<span className={toneChipClass(view.tone)}>{view.label}</span>}
              actions={
                <span className="kel-row">
                  {provider.class === 'api' ? (
                    <>
                      <KelButton
                        variant={needsSetup ? 'primary' : 'secondary'}
                        disabled={busy}
                        onClick={() =>
                          setKeyDraft((draft) =>
                            draft?.provider === provider.provider ? null : { provider: provider.provider, value: '' }
                          )
                        }
                      >
                        {needsSetup ? 'Set up' : 'Update key'}
                      </KelButton>
                      {hasStored && (
                        <KelButton
                          variant="quiet"
                          disabled={busy}
                          onClick={() => void removeKey(provider.provider)}
                        >
                          Remove key
                        </KelButton>
                      )}
                    </>
                  ) : needsSetup ? (
                    <KelButton variant="secondary" disabled={busy} onClick={() => void load()}>
                      Check again
                    </KelButton>
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
                {view.reason}
                {view.until ? ` · Kel tries again ${formatWhen(view.until)}` : ''}
                {provider.planType ? ` · plan ${provider.planType}` : ''}
              </p>
              {keyDraft?.provider === provider.provider && (
                <div className="kel-row">
                  <input
                    className="kel-input"
                    type="password"
                    aria-label={`${provider.label} API key`}
                    placeholder="paste the key — it goes to the OS store, never the engine"
                    value={keyDraft.value}
                    onChange={(event) => setKeyDraft({ provider: provider.provider, value: event.target.value })}
                  />
                  <KelButton
                    variant="primary"
                    disabled={busy || !keyDraft.value || !secure?.available}
                    onClick={() => void saveKey(provider.provider)}
                  >
                    Save + Verify
                  </KelButton>
                  <KelButton variant="quiet" disabled={busy} onClick={() => setKeyDraft(null)}>
                    Cancel
                  </KelButton>
                </div>
              )}
              {provider.class === 'api' && !secure?.available && (
                <p className="kel-meta">
                  OS-backed storage is unavailable on this system, so Kel cannot store a key here.
                </p>
              )}
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
            );
          })}

        <KelCard
          title="Integrations"
          chip={
            <span className="kel-meta">
              {capabilities === null
                ? 'checking'
                : capabilities.every((row) => row.availability === 'available')
                  ? 'all available'
                  : 'some need setup'}
            </span>
          }
        >
          <p className="kel-sub">
            The tools Kel can use in this app, straight from the engine — connected, needing setup, or
            unavailable, with the reason. Per-chat control lives beside the message box (the tools pill).
          </p>
          {(capabilities ?? []).map((row) => (
            <div className="kel-row" key={row.id}>
              <div className="kel-attention__text">
                <strong>{row.label}</strong>
                <span className="kel-meta">
                  {row.availability === 'available'
                    ? 'Connected'
                    : row.availability === 'needs_setup'
                      ? `Needs setup — ${row.availability_reason || 'a key or setting is missing'}`
                      : `Unavailable — ${row.availability_reason || 'not on this machine'}`}
                  {row.effective === 'on' ? ' · In use' : ' · Off'}
                </span>
              </div>
              <span className="kel-grow" />
              {row.availability === 'needs_setup' && (
                <KelButton variant="quiet" onClick={() => navigate('/settings/tools')}>
                  Set up
                </KelButton>
              )}
            </div>
          ))}
        </KelCard>

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
            <span className="kel-code"> safeStorage </span>) and never reaches the engine's database,
            which keeps only the field names and a reference. No IPC returns the value to this window.
            Stored values are injected into provider runs from OS-backed storage at engine start —
            never into logs, exports, or the engine database. New values apply the next time Kel
            starts its engine.
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
                      `Couldn't store the credential. ${failureSentence(err, 'The engine did not answer — try again.')}`
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
