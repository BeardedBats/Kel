import { ipcBridge } from '@/common';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';
import { KelDefaultModelCard } from '@renderer/components/kel/KelModelControl';
import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import { KelAuthorityCard } from '@renderer/components/kel/KelAuthorityCard';
import { announceProjectsChanged, setActiveProject, useProjects } from '@renderer/components/kel/activeProject';
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
import { kelAutonomy, kelProjects, kelProviders, kelState } from '@renderer/components/kel/kelApi';

const STEPS = ['Welcome', 'Connect a model', 'Project', 'Autonomy', 'Ready'] as const;
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
  const isMobile = Boolean(useLayoutContext()?.isMobile);
  const setupState = location.state as { setupGate?: boolean; setupStep?: Step } | null;
  const [step, setStep] = useState<Step>(setupState?.setupStep ?? 'Welcome');
  // D-54: the folder is the active project's own (the engine keeps it; nothing is stored here).
  const { newChatProject, loaded: projectsLoaded } = useProjects();
  const projectFolder = newChatProject?.root ?? '';
  const [folderBusy, setFolderBusy] = useState(false);
  const [folderError, setFolderError] = useState('');
  const [providers, setProviders] = useState<
    Array<{ provider: string; label: string; status: string; auth_mode: string }>
  >([]);
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
        // Useful work within moments: setup ends in the chat composer, in the active project.
        navigate('/guid', { replace: true });
      } catch (err) {
        console.error('Could not save Kel setup:', err);
        setFinishError(true);
      }
    },
    [navigate]
  );

  const index = STEPS.indexOf(step);
  const selectStep = (selected: Step) => {
    setStep(selected);
    navigate('/onboarding', { replace: true, state: { ...setupState, setupStep: selected } });
  };
  /** A chosen folder becomes a project (the one already using it, or a new one named after it). */
  const chooseProjectFolder = async () => {
    setFolderBusy(true);
    setFolderError('');
    let folder: string | undefined;
    try {
      folder = (await ipcBridge.dialog.showOpen.invoke({ properties: ['openDirectory', 'createDirectory'] }))?.[0];
    } catch {
      setFolderError('The folder picker could not open. Try again.');
      setFolderBusy(false);
      return;
    }
    try {
      if (folder) {
        const project = await kelProjects.forFolder(folder);
        announceProjectsChanged();
        await setActiveProject(project.id);
      }
    } catch (err) {
      setFolderError(failureSentence(err, 'Kel could not use that folder. Try another one.'));
    } finally {
      setFolderBusy(false);
    }
  };

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
          <KelButton variant='primary' onClick={() => navigate('/settings/model')}>Add Model</KelButton>
        </div>

        {!isMobile && <nav className='kel-shell-setup-progress' aria-label='Setup steps'>{STEPS.map((label, i) => <button key={label} type='button' aria-label={`Step ${i + 1}: ${label}`} aria-current={i === index ? 'step' : undefined} data-visited={i < index} onClick={() => selectStep(label)} />)}</nav>}
        {isMobile ? <p className='kel-meta kel-shell-setup-label'>{`Step ${index + 1} of ${STEPS.length} · ${['Welcome', 'Providers', 'Project', 'Autonomy', 'Ready'][index]}`}</p> : <div className='kel-meta kel-shell-setup-label'><span>{`Step ${index + 1} of ${STEPS.length}`}</span><span>{step}</span></div>}
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

        {!isMobile ? <KelDefaultModelCard compact title='Connect a model' /> : (
        <KelCard title='Connect a model' actions={<KelButton onClick={() => navigate('/settings/providers')}>Open Providers</KelButton>}>
          {providers.length === 0 ? <p className='kel-meta'>No model is connected yet.</p> : providers.map(item => (
            <div className='kel-row' key={item.provider}>
              <span>{item.label}</span><span className='kel-meta'>{STATUS_LABEL[item.status] ?? item.status.replace(/_/g, ' ')}</span>
              <span className='kel-grow' /><KelStatusChip status={STATUS_CHIP[item.status] ?? 'queued'} />
            </div>
          ))}
        </KelCard>
        )}

        <KelCard title='Where work happens'>
          <div className='kel-row'>
            <div><div>Project folder</div><div className='kel-meta' title={projectFolder || undefined}>{isMobile ? (newChatProject?.name ?? (projectsLoaded ? 'General' : 'Loading…')) : projectFolder || 'No folder selected'}</div></div>
            <span className='kel-grow' /><KelButton variant="primary" disabled={folderBusy} onClick={() => isMobile ? navigate('/projects/list') : void chooseProjectFolder()}>Change</KelButton>
          </div>
        </KelCard>

        {folderError && <p className='kel-meta' role='alert'>{folderError}</p>}

        {/* D-64 settles the Autonomy step: Full access by default, with the same switch as Settings. */}
        <KelAuthorityCard />

        <KelCard title="You're set">
          <div className='kel-row'><KelButton variant={isMobile ? 'secondary' : 'primary'} onClick={() => void finish()}>Start using Kel</KelButton><span className='kel-meta'>You can change any of this later in Settings.</span></div>
        </KelCard>

      </main>
    </div>
  );
}
