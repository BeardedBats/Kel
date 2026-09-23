import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
/**
 * Kel V1.4 first-run onboarding (docs/v1.4/KEL_V1.4_UX_SPEC.md §3).
 *
 * Shown once on a genuinely fresh install — no completion flag and no conversations. Migrated
 * installs never see it. Every claim on these screens is read from the engine, not asserted.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { configService } from '@/common/config/configService';
import {
  KelButton,
  KelCard,
  KelStatusChip,
} from '@renderer/components/kel/KelPrimitives';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { kelAutonomy, kelProviders, kelState } from '@renderer/components/kel/kelApi';

const STEPS = ['Welcome', 'Providers', 'Project', 'Autonomy', 'Ready'] as const;
type Step = (typeof STEPS)[number];

const STATUS_CHIP: Record<string, 'verified' | 'waiting' | 'uncertain' | 'failed' | 'queued'> = {
  healthy: 'verified',
  quota: 'verified',
  quota_not_reported: 'queued',
  installed_not_authenticated: 'waiting',
  degraded: 'uncertain',
  unavailable: 'failed',
  not_installed: 'failed',
};

// Plain-language labels for provider states (the raw states stay on the Providers page).
const STATUS_LABEL: Record<string, string> = {
  healthy: 'ready',
  quota: 'ready',
  quota_not_reported: 'ready, usage not reported',
  installed_not_authenticated: 'needs you to sign in',
  degraded: 'limited right now',
  unavailable: 'not available',
  not_installed: 'not installed',
};

export default function KelOnboardingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState<Step>('Welcome');
  const [providers, setProviders] = useState<
    Array<{ provider: string; label: string; status: string; auth_mode: string }>
  >([]);
  const [project, setProject] = useState<string>('');
  const [rules, setRules] = useState<Array<{ rule: string; text: string }>>([]);
  const [digest, setDigest] = useState('');
  const [engine, setEngine] = useState<string>('');
  const [error, setError] = useState<unknown>(null);
  const [finishError, setFinishError] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const [providerPayload, statePayload, guardrailPayload] = await Promise.all([
          kelProviders.list(),
          kelState(),
          kelAutonomy.guardrails(),
        ]);
        setProviders(
          (providerPayload.providers ?? []).map((item) => ({
            provider: item.provider,
            label: item.label,
            status: item.status,
            auth_mode: item.auth_mode,
          }))
        );
        setProject(statePayload.projects?.[0]?.name ?? 'this project');
        setEngine(statePayload.engine_version ?? '');
        setRules((guardrailPayload.rules ?? []).slice(0, 6));
        setDigest(guardrailPayload.digest ?? '');
      } catch (err) {
        setError(err);
      }
    })();
  }, []);

  const finish = useCallback(
    async () => {
      try {
        setFinishError(false);
        await configService.set('kel.onboardingCompleted_v1', true);
        // Useful work within moments: setup ends in the chat composer.
        navigate('/guid', { replace: true });
      } catch (err) {
        console.error('Could not save Kel setup:', err);
        setFinishError(true);
      }
    },
    [navigate]
  );

  const index = STEPS.indexOf(step);
  const next = () => setStep(STEPS[Math.min(index + 1, STEPS.length - 1)]);
  const back = () => setStep(STEPS[Math.max(index - 1, 0)]);

  return (
    <div className='kel-scope'>
      <a className='kel-skip' href='#kel-onboarding-main'>
        Skip to main content
      </a>
      <main className='kel-page kel-shell-onboarding' id='kel-onboarding-main' tabIndex={-1}>
        <div className='kel-page__head'>
          <div>
            <ShellWorkspaceLink />
            <h1 className='kel-h1'>Set up Kel</h1>
          </div>
          <span className='kel-grow' />
          <KelButton onClick={() => navigate('/settings/model')}>Add Model</KelButton>
        </div>

        <p className='kel-meta kel-shell-setup-label'>{`Step ${index + 1} of ${STEPS.length} · ${step}`}</p>
        {(location.state as { setupGate?: boolean } | null)?.setupGate && (
          <p className='kel-meta' role='status'>Finish setup before opening the main Kel pages. Settings and setup controls remain available.</p>
        )}
        {finishError && <p className='kel-meta' role='alert'>Setup could not be saved. Try again.</p>}

        {error && (
          <p className='kel-meta'>
            Heads-up: {failureSentence(error, 'Setup could not read the engine just now — try again.')}
          </p>
        )}

        <KelCard title='Kel runs on this machine'>
          <div className='kel-row'>
            <span>Local runtime</span><span className='kel-meta'>{engine ? 'Detected · ready' : 'Checking runtime…'}</span>
            <span className='kel-grow' /><span className={`kel-chip ${engine ? 'kel-chip--ok' : 'kel-chip--wait'}`}>{engine ? 'Ready' : 'Checking'}</span>
          </div>
        </KelCard>

        <KelCard title='Connect a model' actions={<KelButton onClick={() => navigate('/providers')}>Open Providers</KelButton>}>
          {providers.length === 0 ? <p className='kel-meta'>No model is connected yet.</p> : providers.map(item => (
            <div className='kel-row' key={item.provider}>
              <span>{item.label}</span><span className='kel-meta'>{STATUS_LABEL[item.status] ?? item.status.replace(/_/g, ' ')}</span>
              <span className='kel-grow' /><KelStatusChip status={STATUS_CHIP[item.status] ?? 'queued'} />
            </div>
          ))}
        </KelCard>

        <KelCard title='Where work happens'>
          <div className='kel-row'>
            <div><div>Workspace folder</div><div className='kel-meta'>{project === 'default' ? 'General' : project || 'Loading…'}</div></div>
            <span className='kel-grow' /><KelButton onClick={() => navigate('/projects')}>Change</KelButton>
          </div>
        </KelCard>

        <KelCard title='How much Kel does on its own'>
          <div className='kel-row'><span>Autonomy</span><span className='kel-grow' />
            <KelButton onClick={() => navigate('/autonomy')}>Ask before edits</KelButton>
          </div>
        </KelCard>

        <KelCard title="You're set">
          <div className='kel-row'><KelButton onClick={() => void finish()}>Start using Kel</KelButton><span className='kel-meta'>You can change any of this later in Settings.</span></div>
        </KelCard>

      </main>
    </div>
  );
}
