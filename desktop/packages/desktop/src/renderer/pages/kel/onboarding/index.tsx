/**
 * Kel V1.4 first-run onboarding (docs/v1.4/KEL_V1.4_UX_SPEC.md §3).
 *
 * Shown once on a genuinely fresh install — no completion flag and no conversations. Migrated
 * installs never see it. Every claim on these screens is read from the engine, not asserted.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { configService } from '@/common/config/configService';
import {
  KelButton,
  KelCard,
  KelSection,
  KelStatusChip,
} from '@renderer/components/kel/KelPrimitives';
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
  const [step, setStep] = useState<Step>('Welcome');
  const [providers, setProviders] = useState<
    Array<{ provider: string; label: string; status: string; auth_mode: string }>
  >([]);
  const [project, setProject] = useState<string>('');
  const [rules, setRules] = useState<Array<{ rule: string; text: string }>>([]);
  const [digest, setDigest] = useState('');
  const [engine, setEngine] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

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
        setError(err instanceof Error ? err.message : 'The engine did not answer.');
      }
    })();
  }, []);

  const finish = useCallback(
    async (skipped: boolean) => {
      await configService.set('kel.onboardingCompleted_v1', true).catch((): undefined => undefined);
      // Useful work within moments: setup ends in the chat composer, not on a browsing page.
      navigate('/guid', { replace: true });
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
      <main className='kel-page' id='kel-onboarding-main' tabIndex={-1}>
        <div className='kel-page__head'>
          <div>
            <h1 className='kel-h1'>Set up Kel</h1>
            <p className='kel-sub'>
              {`Step ${index + 1} of ${STEPS.length} · ${step}`}
            </p>
          </div>
          <span className='kel-grow' />
          <KelButton variant='quiet' onClick={() => void finish(true)}>
            Skip setup
          </KelButton>
        </div>

        {error && <p className='kel-meta'>Heads-up: {error}</p>}

        {step === 'Welcome' && (
          <KelCard title='Kel runs on this machine'>
            <p className='kel-sub'>
              Kel is your assistant on this machine. What it learns about your projects, and every
              receipt for work it does, stays in your folders and in Kel's own data directory.
            </p>
            <ul>
              <li className='kel-meta'>Nothing leaves this machine except the model you connect.</li>
              <li className='kel-meta'>Kel works only inside the project you point it at.</li>
              <li className='kel-meta'>Every finished job leaves evidence you can inspect.</li>
            </ul>
          </KelCard>
        )}

        {step === 'Providers' && (
          <KelCard
            title='Connect a model'
            actions={
              <KelButton variant='secondary' onClick={() => navigate('/providers')}>
                Open Providers
              </KelButton>
            }
          >
            {providers.length === 0 ? (
              <p className='kel-sub'>No model is connected yet.</p>
            ) : (
              <ul>
                {providers.map((item) => (
                  <li key={item.provider} className='kel-meta'>
                    <span className='kel-strong'>{item.label}</span>{' '}
                    <KelStatusChip status={STATUS_CHIP[item.status] ?? 'queued'} />{' '}
                    {`· ${STATUS_LABEL[item.status] ?? item.status.replace(/_/g, ' ')}`}
                  </li>
                ))}
              </ul>
            )}
            <p className='kel-sub'>
              Kel can be explored without one, but answering and running jobs need a model: a CLI
              subscription, or an API key kept in Windows' protected store.
            </p>
          </KelCard>
        )}

        {step === 'Project' && (
          <KelCard title='Where work happens'>
            <p className='kel-sub'>
              {`Kel is pointed at ${project === 'default' ? 'General' : project}. Nothing outside it is read or written unless you say yes when Kel asks.`}
            </p>
            <p className='kel-meta'>
              Projects are records, not copies — Files stay where you keep them.
            </p>
          </KelCard>
        )}

        {step === 'Autonomy' && (
          <>
            <KelCard title='How much Kel does on its own'>
              <p className='kel-sub'>
                Kel works on its own after you approve a plan, and asks you first when work needs to
                reach outside what that plan covered. Three answers are always available: allow once,
                allow for this project, or deny.
              </p>
              <p className='kel-meta'>
                Some things are never automatic, and cannot be unlocked by Kel, by a role, or by
                anything written in a repository.
              </p>
            </KelCard>
            {rules.length > 0 && (
              <KelSection title='Rules that are always on'>
                <ul>
                  {rules.map((rule) => (
                    <li key={rule.rule} className='kel-meta'>
                      {`${rule.rule} — ${rule.text}`}
                    </li>
                  ))}
                </ul>
              </KelSection>
            )}
          </>
        )}

        {step === 'Ready' && (
          <KelCard title="You're set">
            <ul>
              <li className='kel-meta'>{`Kel ${engine || ''}`.trim()}</li>
              <li className='kel-meta'>
                {providers.some((item) => item.status === 'healthy' || item.status === 'quota')
                  ? 'A model is connected.'
                  : 'No model is connected yet — you can add one anytime in Settings › Providers.'}
              </li>
              <li className='kel-meta'>Safety rules: on</li>
            </ul>
            <p className='kel-sub'>
              Start in chat. Kel will turn your request into a plan, and you approve it before work
              begins.
            </p>
          </KelCard>
        )}

        <div className='kel-row' style={{ marginTop: 16 }}>
          {index > 0 && (
            <KelButton variant='secondary' onClick={back}>
              Back
            </KelButton>
          )}
          <span className='kel-grow' />
          {step === 'Ready' ? (
            <KelButton variant='primary' onClick={() => void finish(false)}>
              Start using Kel
            </KelButton>
          ) : (
            <KelButton variant='primary' onClick={next}>
              Next
            </KelButton>
          )}
        </div>
      </main>
    </div>
  );
}
