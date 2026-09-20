/**
 * D8 — staffing in the user's language.
 *
 * The engine's staffing ladder (D0–D4), hard rules, tier ceilings and budget classes stay internal.
 * Normal Kel surfaces say what is HAPPENING ("Kel is using an independent review."), never
 * workforce internals — no tier names, role versions, snapshot digests, budgets or assignment ids.
 * Engine role names are already human ("Independent Reviewer", "Security Reviewer"); this module
 * turns an assignment's derived state into one plain sentence plus a supporting line.
 */

export type StaffingAssignment = {
  assignment_id: string;
  role: string;
  derived_state?: string;
  updated?: number;
  provider?: string | null;
  model?: string | null;
  role_version?: number;
  snapshot_digest?: string;
  budget?: number;
  spent?: number;
};

const REVIEW_ROLES = /review|verif|audit|assurance|red team|sentinel/i;
const SECURITY_ROLES = /security/i;
const FINISHED_STATES = new Set(['DONE', 'COMPLETE', 'COMPLETED', 'CLOSED', 'ACCEPTED', 'VERIFIED']);
const FAILED_STATES = new Set(['FAILED', 'BLOCKED', 'REJECTED']);
const WAITING_STATES = new Set(['WAITING', 'WAITING_RESOURCE', 'AWAITING_USER', 'AWAITING', 'PAUSED', 'READY']);

const subjectFor = (role: string): string => {
  const isReview = REVIEW_ROLES.test(role);
  const isSecurity = SECURITY_ROLES.test(role);
  if (isSecurity && !isReview) return 'A security check';
  if (isReview) return 'An independent review';
  return 'Extra help';
};

/** One plain sentence for a specialist currently involved in the work. */
export function assignmentLine(assignment: StaffingAssignment): string {
  const role = assignment.role || '';
  const state = (assignment.derived_state || '').toUpperCase();
  const subject = subjectFor(role);
  if (FAILED_STATES.has(state)) return `${subject}: stopped and needs a look`;
  if (WAITING_STATES.has(state)) return `${subject}: waiting`;
  if (FINISHED_STATES.has(state)) return `${subject}: finished`;
  return `${subject}: in progress`;
}

/** The one line a person needs before the detail: is Kel alone, or is someone checking the work? */
export function staffingSummary(assignments: StaffingAssignment[]): string {
  if (!assignments.length) return 'Kel is working alone on this step.';
  const reviews = assignments.filter((entry) => REVIEW_ROLES.test(entry.role || '')).length;
  const parts: string[] = [];
  if (reviews > 0) {
    parts.push(reviews === 1 ? 'Kel is using an independent review.' : `Kel is using ${reviews} independent reviews.`);
  }
  const others = assignments.length - reviews;
  if (others > 0) parts.push(others === 1 ? 'One more specialist is helping.' : `${others} specialists are helping.`);
  return parts.join(' ');
}
