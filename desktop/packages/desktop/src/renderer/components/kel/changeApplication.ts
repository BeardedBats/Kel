/**
 * D-65 — plain words for where a verified coding change stands in the project folder, shared by the
 * in-chat work card and the Work panel so both say the same thing.
 *
 * Full access applies a verified change on its own (it can be undone); a change that failed or
 * skipped its checks, one touching a protected place, or any change under Ask first keeps the
 * "Apply checked changes" button.
 */
import type { KelChangeApplication } from './kelApi';

type JobLike = { verdict?: string | null; contract?: { kind?: string } | null; application?: KelChangeApplication | null };

const filesText = (files: number | null | undefined): string =>
  typeof files === 'number' && files > 0 ? ` (${files} file${files === 1 ? '' : 's'})` : '';

/** Applied (or mid-undo): the card offers Undo instead of Apply. */
export const isApplied = (application: KelChangeApplication | null | undefined): boolean =>
  application?.state === 'APPLIED' || application?.state === 'UNDOING';

/** The Apply button shows only for a verified coding change that is not in the project right now. */
export const canApplyChange = (job: JobLike): boolean =>
  job.verdict === 'VERIFIED' && job.contract?.kind === 'coding' && !isApplied(job.application);

export const canUndoChange = (job: JobLike): boolean =>
  job.contract?.kind === 'coding' && isApplied(job.application);

/** The last folder in a path ("C:\Users\Nick\R6Proj" → "R6Proj"). */
export const folderName = (path: string | null | undefined): string | null => {
  const parts = String(path ?? '')
    .split(/[\\/]+/)
    .filter(Boolean);
  return parts.length ? parts[parts.length - 1] : null;
};

/**
 * Where a change went, once: "Calc demo (folder R6Proj)", or just the folder when the project is
 * named after it. Never the full path — that stays behind "Open folder".
 */
export const placeWords = (application: KelChangeApplication | null | undefined): string => {
  const folder = application?.folder || folderName(application?.root);
  const name = application?.project_name?.trim() || null;
  if (name && folder && name.toLowerCase() !== folder.toLowerCase()) return `${name} (folder ${folder})`;
  return name || folder || 'your project';
};

/** One line for the card: what happened to the change, or null when there is nothing to say. */
export const applicationLine = (application: KelChangeApplication | null | undefined): string | null => {
  if (!application) return null;
  const where = ` to ${placeWords(application)}`;
  if (application.state === 'APPLIED')
    return `${application.auto ? 'Applied automatically' : 'Applied'}${where}${filesText(application.files)}. The earlier files are saved.`;
  if (application.state === 'UNDOING') return 'Putting the earlier files back…';
  if (application.state === 'UNDONE') return 'Undone — the earlier files are back.';
  if (application.waiting_reason) return `Waiting for you: Kel did not apply it on its own — ${application.waiting_reason}.`;
  return null;
};
