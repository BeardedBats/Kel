/**
 * HVRA-MINOR-001: the Permissions surface presents work in human terms. Engine job ids are support
 * handles, not names — they belong in advanced/copy detail, never in the primary Work column.
 */

export interface JobLabelSource {
  id: string;
  contract?: { request?: string };
}

const FALLBACK_WORK_LABEL = 'Work item';
const MAX_LABEL_LENGTH = 120;

/** First line of a request, trimmed and bounded for table display. */
function firstLine(text: string | undefined | null, max = MAX_LABEL_LENGTH): string {
  if (!text) return '';
  const line = text.trim().split(/\r?\n/, 1)[0].trim();
  if (!line) return '';
  return line.length > max ? `${line.slice(0, max - 1).trimEnd()}…` : line;
}

/**
 * The human label for a lease's work: the job's own request text when the job is known — never the
 * raw engine job id. Falls back to a neutral label instead of leaking an internal identifier.
 */
export function workLabelFor(jobId: string, jobs: ReadonlyArray<JobLabelSource> | null | undefined): string {
  const job = jobs?.find((candidate) => candidate.id === jobId);
  return firstLine(job?.contract?.request) || FALLBACK_WORK_LABEL;
}
