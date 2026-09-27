/**
 * Kel conversational hand-off (D-53): the engine ends the chat turn after acknowledging real work
 * and emits one ACP tool call whose id is `kel-work:<submission id>`. That row is not a tool step —
 * it is the live card for the background work, so it renders standalone and never joins a tool
 * summary group.
 */
export const KEL_WORK_TOOL_PREFIX = 'kel-work:';

export const isKelWorkToolCall = (id: unknown): id is string =>
  typeof id === 'string' && id.startsWith(KEL_WORK_TOOL_PREFIX) && id.length > KEL_WORK_TOOL_PREFIX.length;

/** The submission id a work card reads, or null for any other tool call. */
export const kelWorkSubmissionId = (id: unknown): string | null =>
  isKelWorkToolCall(id) ? id.slice(KEL_WORK_TOOL_PREFIX.length) : null;

type PollJob = { state?: string };
type PollSubmission = { state?: string };
export type PollState = { jobs?: PollJob[] | null; submissions?: PollSubmission[] | null } | null | undefined;

export const KEL_POLL_ACTIVE_MS = 2500;
export const KEL_POLL_IDLE_MS = 10000;

/**
 * How long the conversation's durable-work poll waits before its next read. It never stops: work
 * can be handed off at any moment and its result must still arrive, so an idle conversation only
 * slows down (10 s) and speeds up again (2.5 s) while any job is open or any request is still being
 * started.
 */
export const nextPollDelay = (state: PollState): number => {
  const jobs = state?.jobs ?? [];
  const submissions = state?.submissions ?? [];
  const openJob = jobs.some((job) => !['CLOSED', 'CANCELLED'].includes(String(job?.state ?? '')));
  const planning = submissions.some((submission) => submission?.state === 'PLANNING');
  return openJob || planning ? KEL_POLL_ACTIVE_MS : KEL_POLL_IDLE_MS;
};
