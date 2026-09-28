/**
 * HVRA-MINOR-001: the Permissions surface presents work in human terms. Engine job ids are support
 * handles, not names — they belong in advanced/copy detail, never in the primary Work column.
 */

export interface JobLabelSource {
  id: string;
  contract?: { request?: string; handoff?: { title?: string | null } | null; recipe?: { name?: string | null } | null };
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
  const recipe = recipeRunTitle(job?.contract);
  if (recipe) return recipe;
  return shortRequest(job?.contract?.request) || fallback;
}

/**
 * FN-12: a recipe run is named after its recipe — "Ran Weekly rankings" — never its version or id
 * (office.py `recipe_title`); runs from before the name travelled with the work are read from their
 * request line ("Run recipe <name> v1.0.0 (<id>).").
 */
const OLD_RECIPE_LINE = /^Run recipe (.+?) v\d+\.\d+\.\d+ \([^)]*\)\.?/;
export function recipeRunTitle(contract: JobLabelSource['contract'] | null | undefined): string | null {
  let name = contract?.recipe?.name?.trim() ?? '';
  if (!name) name = OLD_RECIPE_LINE.exec(String(contract?.request ?? '').trim())?.[1]?.trim() ?? '';
  return name ? `Ran ${shortRequest(name, 56)}` : null;
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
