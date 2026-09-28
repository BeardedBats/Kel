/**
 * D-70 item 1 — where an answer on a needs-you card goes. Every answer goes to Kel, in that work's
 * own conversation, through a path that already exists (never to an agent, never a second answer
 * system): the approval's approve/deny route, the apply route with Nick as the actor, the resume
 * control, or a normal chat message (so the D-55 restart rule applies to a typed answer).
 *
 * LIVE-3: "Try again" (`continue`) on work that was interrupted, that no model here could run
 * (`no_model`) or that ran out of tries (`out_of_tries`) is the same "continue" message for that job.
 * An option with an `action` ("Change the model in Staff & models") is a place to go, not an answer:
 * nothing is sent to Kel for it.
 */
import {
  answerApply,
  answerApproval,
  answerMessage,
  answerResume,
  type OfficeQuestion,
  type OfficeQuestionOption,
} from './officeApi';

export type NeedsAnswer = { option: OfficeQuestionOption } | { text: string };

/** The wait kinds whose "Try again" is a "continue" message for the job. */
const CONTINUE_KINDS = new Set(['interrupted', 'no_model', 'out_of_tries']);

/** An option that opens a place in Kel instead of answering (nothing is sent for it). */
export const isPlaceOption = (option: Pick<OfficeQuestionOption, 'action'>): boolean => Boolean(option.action);

/**
 * Where a place option goes: Settings → Staff & models for `open_settings` / `staff` (with the work's
 * chat, so the page can say which model that chat uses), else the Settings page it names.
 */
export const placePath = (option: Pick<OfficeQuestionOption, 'action' | 'target'>, conversation?: string | null): string | null => {
  if (option.action !== 'open_settings') return null;
  const target = (option.target ?? '').trim();
  if (!target || target === 'staff') {
    return `/settings/staff${conversation ? `?conversation=${encodeURIComponent(conversation)}` : ''}`;
  }
  return `/settings/${encodeURIComponent(target)}`;
};

/** What the card says right after the answer is on its way (Figma 5b). */
export const answeredFollowUp = (question: Pick<OfficeQuestion, 'kind'>, answer: NeedsAnswer): string => {
  if ('option' in answer) {
    if (question.kind === 'approval' && answer.option.id === 'deny') return 'Kel won’t take that step';
    if (answer.option.id === 'leave') return 'Kel left it as it is';
    if (question.kind === 'apply' && answer.option.id === 'apply_anyway') return 'Kel applied the change';
    if (answer.option.id === 'continue' && (question.kind === 'no_model' || question.kind === 'out_of_tries'))
      return 'Kel is trying again';
  }
  return 'Kel is continuing';
};

export const answeredWords = (answer: NeedsAnswer): string => ('option' in answer ? answer.option.label : answer.text);

/** Send one answer through its existing route. Rejects with the engine's plain sentence. */
export const sendNeedsAnswer = async (question: OfficeQuestion, answer: NeedsAnswer): Promise<void> => {
  const conversation = question.conversation_id ?? null;
  const job = question.ref?.job ?? question.job_id ?? null;
  if ('text' in answer) {
    if (!conversation) throw new Error('Kel could not find this work’s chat.');
    await answerMessage(conversation, answer.text);
    return;
  }
  // A place to go is never an answer: nothing reaches Kel for it.
  if (isPlaceOption(answer.option)) return;
  const choice = answer.option.id;
  if (CONTINUE_KINDS.has(question.kind) && choice === 'continue') {
    if (!conversation || !job) throw new Error('Kel could not find this work’s chat.');
    await answerMessage(conversation, 'continue', job);
    return;
  }
  switch (question.kind) {
    case 'approval': {
      const kind = question.ref?.approval_kind;
      const id = question.ref?.approval_id;
      if (!kind || !id) throw new Error('Kel could not find that request any more.');
      await answerApproval(kind, id, choice === 'allow', conversation);
      return;
    }
    case 'apply':
    case 'second_opinion':
      if (!job) throw new Error('Kel could not find that work.');
      await answerApply(job, choice === 'apply_anyway' ? 'apply_anyway' : 'leave');
      return;
    case 'paused':
      if (!job) throw new Error('Kel could not find that work.');
      await answerResume(job);
      return;
    default:
      if (!conversation) throw new Error('Kel could not find this work’s chat.');
      await answerMessage(conversation, answer.option.label);
  }
};
