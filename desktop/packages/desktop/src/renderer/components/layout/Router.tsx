import React, { Suspense } from 'react';
import { HashRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import AppLoader from '@renderer/components/layout/AppLoader';
import DocumentTitle from '@renderer/components/layout/DocumentTitle';
import { useCrossSessionRateLimitNotice } from '@/renderer/hooks/system/useCrossSessionRateLimitNotice';
import { useAuth } from '@renderer/hooks/context/AuthContext';
import { TEAM_MODE_ENABLED } from '@/common/config/constants';
const Conversation = React.lazy(() => import('@renderer/pages/conversation'));
const Guid = React.lazy(() => import('@renderer/pages/guid'));
const AgentSettings = React.lazy(() => import('@renderer/pages/settings/AgentSettings'));
const AgentRepairPage = React.lazy(() => import('@renderer/pages/settings/AgentSettings/AgentRepairPage'));
const AssistantSettings = React.lazy(() => import('@renderer/pages/settings/AssistantSettings'));
const SkillsSettings = React.lazy(() => import('@renderer/pages/settings/SkillsSettings/SkillsHubSettings'));
const SkillDetailPage = React.lazy(() => import('@renderer/pages/settings/SkillsSettings/SkillDetailPage'));
const ToolsSettings = React.lazy(() => import('@renderer/pages/settings/ToolsSettings'));
const AppearanceSettings = React.lazy(() => import('@renderer/pages/settings/AppearanceSettings'));
const ModeSettings = React.lazy(() => import('@renderer/pages/settings/ModeSettings'));
const SystemSettings = React.lazy(() => import('@renderer/pages/settings/SystemSettings'));
const WebuiSettings = React.lazy(() => import('@renderer/pages/settings/WebuiSettings'));
const PetSettings = React.lazy(() => import('@renderer/pages/settings/PetSettings'));
const ArchivedSettings = React.lazy(() => import('@renderer/pages/settings/ArchivedSettings'));
const ExtensionSettingsPage = React.lazy(() => import('@renderer/pages/settings/ExtensionSettingsPage'));
const LoginPage = React.lazy(() => import('@renderer/pages/login'));
const ComponentsShowcase = React.lazy(() => import('@renderer/pages/TestShowcase'));
const ScheduledTasksPage = React.lazy(() => import('@renderer/pages/cron/ScheduledTasksPage'));
const TaskDetailPage = React.lazy(() => import('@renderer/pages/cron/ScheduledTasksPage/TaskDetailPage'));
const TeamIndex = React.lazy(() => import('@renderer/pages/team'));
const KelWorkCenter = React.lazy(() => import('@renderer/pages/kel/work'));
const KelTranscription = React.lazy(() => import('@renderer/pages/kel/transcription'));
const KelTeam = React.lazy(() => import('@renderer/pages/kel/team'));
const KelProjects = React.lazy(() => import('@renderer/pages/kel/projects'));
const KelProviders = React.lazy(() => import('@renderer/pages/kel/providers'));
const KelAutonomy = React.lazy(() => import('@renderer/pages/kel/autonomy'));
const KelOnboarding = React.lazy(() => import('@renderer/pages/kel/onboarding'));
const KelDiagnostics = React.lazy(() => import('@renderer/pages/kel/diagnostics'));

const withRouteFallback = (Component: React.LazyExoticComponent<React.ComponentType>) => (
  <Suspense fallback={<AppLoader />}>
    <Component />
  </Suspense>
);

/**
 * Legacy `/settings/capabilities?tab=tools` deep links now map to the standalone
 * Tools page; everything else (skills tab or no tab) lands on the Skills page.
 */
const CapabilitiesRedirect: React.FC = () => {
  const { search } = useLocation();
  const tab = new URLSearchParams(search).get('tab');
  return <Navigate to={tab === 'tools' ? '/settings/tools' : '/settings/skills'} replace />;
};

/**
 * Kel V1.2: the donor shell ships AionUI's multi-agent settings surfaces
 * (assistants, agent management, skills, tools, model, team). Kel is a
 * single-assistant product, so navigation to those surfaces is redirected to
 * the home screen. The page components stay in the bundle (their dynamic
 * imports are kept in the ternaries below) — capabilities are hidden, not
 * deleted. Flip this back to `false` to restore the donor surfaces.
 */
const HIDE_DONOR_AGENT_SURFACES = true;

/**
 * Human-visual repair (HV-12): the Office/Roster/Studio workforce surface exposes Kel's internal
 * staffing model to ordinary users and Advanced Worker View is deferred past V1.6. While true the
 * routes redirect to Home; the page and the Workforce runtime stay in the bundle. Flip to restore.
 */
const HIDE_WORKFORCE_SURFACES = true;

const ProtectedLayout: React.FC<{ layout: React.ReactElement }> = ({ layout }) => {
  const { status, user } = useAuth();
  // Mounted once for every authenticated route: the loop warning has to reach
  // the user even when they are looking at a THIRD conversation, which is the
  // whole reason it is a broadcast rather than an in-conversation banner.
  useCrossSessionRateLimitNotice(user?.id);

  if (status === 'checking') {
    return <AppLoader />;
  }

  if (status !== 'authenticated') {
    return <Navigate to='/login' replace />;
  }

  return React.cloneElement(layout);
};

const PanelRoute: React.FC<{ layout: React.ReactElement }> = ({ layout }) => {
  const { status } = useAuth();

  return (
    <HashRouter>
      <DocumentTitle />
      <Routes>
        <Route
          path='/login'
          element={status === 'authenticated' ? <Navigate to='/guid' replace /> : withRouteFallback(LoginPage)}
        />
        <Route element={<ProtectedLayout layout={layout} />}>
          <Route index element={<Navigate to='/guid' replace />} />
          <Route path='/guid' element={withRouteFallback(Guid)} />
          <Route path='/conversation/:id' element={withRouteFallback(Conversation)} />
          <Route
            path='/team/:id'
            element={
              HIDE_DONOR_AGENT_SURFACES || !TEAM_MODE_ENABLED ? (
                <Navigate to='/guid' replace />
              ) : (
                withRouteFallback(TeamIndex)
              )
            }
          />
          <Route
            path='/settings/model'
            element={<ModeSettings />}
          />
          <Route
            path='/assistants'
            element={HIDE_DONOR_AGENT_SURFACES ? <Navigate to='/guid' replace /> : withRouteFallback(AssistantSettings)}
          />
          <Route path='/settings/assistants' element={<Navigate to='/team/roster' replace />} />
          <Route
            path='/settings/agent'
            element={<Navigate to='/team/roster' replace />}
          />
          <Route
            path='/settings/agent/:id/repair'
            element={<Navigate to='/team/roster' replace />}
          />
          <Route
            path='/settings/skills'
            element={<Navigate to='/team/roster' replace />}
          />
          <Route
            path='/settings/skills/import-history'
            element={<Navigate to='/team/roster' replace />}
          />
          <Route
            path='/settings/skills/detail/:skillName'
            element={<Navigate to='/team/roster' replace />}
          />
          {/* Kel V1.6 visual fix (finding S1-1): a real Tools settings page exists and was already
              imported here, so redirecting away to /autonomy only ejected the user from the Settings
              shell. Render the page the label promises instead. */}
          <Route path='/settings/tools' element={withRouteFallback(ToolsSettings)} />
          <Route path='/settings/capabilities' element={<Navigate to='/team/roster' replace />} />
          <Route path='/settings/capabilities/skills/import-history' element={<Navigate to='/team/roster' replace />} />
          <Route path='/settings/skills-hub' element={<Navigate to='/team/roster' replace />} />
          <Route path='/settings/appearance' element={withRouteFallback(AppearanceSettings)} />
          <Route path='/settings/display' element={<Navigate to='/settings/appearance' replace />} />
          <Route path='/settings/webui' element={withRouteFallback(WebuiSettings)} />
          <Route path='/settings/pet' element={withRouteFallback(PetSettings)} />
          <Route path='/settings/archived' element={withRouteFallback(ArchivedSettings)} />
          <Route path='/settings/system' element={withRouteFallback(SystemSettings)} />
          <Route path='/settings/about' element={withRouteFallback(SystemSettings)} />
          <Route path='/settings/ext/:tabId' element={withRouteFallback(ExtensionSettingsPage)} />
          <Route path='/settings' element={<Navigate to='/settings/appearance' replace />} />
          <Route path='/test/components' element={withRouteFallback(ComponentsShowcase)} />
          <Route path='/scheduled' element={withRouteFallback(ScheduledTasksPage)} />
          <Route path='/scheduled/:job_id' element={withRouteFallback(TaskDetailPage)} />
          <Route path='/work' element={withRouteFallback(KelWorkCenter)} />
          <Route path='/transcription' element={withRouteFallback(KelTranscription)} />
          <Route
            path='/team'
            element={<Navigate to={HIDE_WORKFORCE_SURFACES ? '/guid' : '/team/office'} replace />}
          />
          <Route
            path='/team/office'
            element={HIDE_WORKFORCE_SURFACES ? <Navigate to='/guid' replace /> : withRouteFallback(KelTeam)}
          />
          <Route
            path='/team/roster'
            element={HIDE_WORKFORCE_SURFACES ? <Navigate to='/guid' replace /> : withRouteFallback(KelTeam)}
          />
          <Route
            path='/team/studio'
            element={HIDE_WORKFORCE_SURFACES ? <Navigate to='/guid' replace /> : withRouteFallback(KelTeam)}
          />
          <Route path='/projects' element={<Navigate to='/projects/knowledge' replace />} />
          <Route path='/projects/knowledge' element={withRouteFallback(KelProjects)} />
          <Route path='/projects/map' element={withRouteFallback(KelProjects)} />
          <Route path='/projects/recipes' element={withRouteFallback(KelProjects)} />
          <Route path='/providers' element={withRouteFallback(KelProviders)} />
          <Route path='/autonomy' element={withRouteFallback(KelAutonomy)} />
          <Route path='/onboarding' element={withRouteFallback(KelOnboarding)} />
          <Route path='/diagnostics' element={withRouteFallback(KelDiagnostics)} />
        </Route>
        <Route path='*' element={<Navigate to={status === 'authenticated' ? '/guid' : '/login'} replace />} />
      </Routes>
    </HashRouter>
  );
};

export default PanelRoute;
