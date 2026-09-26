/** Compact Kibble build copy comes from job state and reported milestones. */
export function kibbleBuildSummary(job: { state?: string; milestones?: Record<string, { state?: string }> } | null) {
  const labels: Record<string, string> = { RUNNING: 'Running', READY: 'Ready', QUEUED: 'Waiting to start', CLOSED: 'Finished', CANCELLED: 'Cancelled', CANCELLING: 'Stopping', PAUSED: 'Paused', AWAITING_USER: 'Waiting on you', WAITING_RESOURCE: 'Waiting for a model', BLOCKED: 'Blocked' };
  const state = job?.state ?? 'QUEUED';
  const steps = Object.values(job?.milestones ?? {});
  const running = steps.findIndex(step => step.state === 'RUNNING');
  const progress = state === 'RUNNING' && running >= 0 ? ` · step ${running + 1} of ${steps.length}` : '';
  return { text: `${labels[state] ?? state.toLowerCase().replace(/_/g, ' ')}${progress}`, running: state === 'RUNNING', stage: state === 'RUNNING' ? 'Building' : null };
}
