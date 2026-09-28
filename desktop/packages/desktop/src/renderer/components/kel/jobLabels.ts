/**
 * HVRA-MINOR-001: the Permissions surface presents work in human terms. Engine job ids are support
 * handles, not names — they belong in advanced/copy detail, never in the primary Work column.
 */

export interface JobLabelSource {
  id: string;
  contract?: { request?: string; handoff?: { title?: string | null } | null };
}

/** The engine's shortening of a request for a title (office.py `_short`): whole words, one line. */
const shortRequest = (text: string | undefined | null, limit = 60): string => {
  const words = String(text ?? '').split(/\s+/).filter(Boolean).join(' ');
  if (words.length <= limit) return words;
  const cut = words.slice(0, limit - 1);
  const space = cut.lastIndexOf(' ');
  return `${space > 0 ? cut.slice(0, space) : cut}…`;
};

/**
 * VIS-13 / JR-17: one name for a piece of work everywhere — the title its work card shows. That is
 * the engine's handoff title when the work was handed off, else the request shortened the same way
 * the engine shortens it (office.py `_title`), so Activity, Home, notifications and the card agree.
 */
export function workTitle(
  job: { contract?: JobLabelSource['contract'] } | null | undefined,
  fallback = 'Untitled work'
): string {
  const handoff = job?.contract?.handoff?.title?.trim();
  if (handoff) return handoff;
  return shortRequest(job?.contract?.request) || fallback;
}

const FALLBACK_WORK_LABEL = 'Work item';

/**
 * The human label for a lease's work: the job's own request text when the job is known — never the
 * raw engine job id. Falls back to a neutral label instead of leaking an internal identifier.
 */
export function workLabelFor(jobId: string, jobs: ReadonlyArray<JobLabelSource> | null | undefined): string {
  const job = jobs?.find((candidate) => candidate.id === jobId);
  return job ? workTitle(job, FALLBACK_WORK_LABEL) : FALLBACK_WORK_LABEL;
}

/** D-73.5: work that finished and passed its checks — the only work that can be saved as a recipe. */
export const passedItsChecks = (job: { state?: string; verdict?: string | null }): boolean =>
  job.state === 'CLOSED' && String(job.verdict ?? '').toUpperCase() === 'VERIFIED';
