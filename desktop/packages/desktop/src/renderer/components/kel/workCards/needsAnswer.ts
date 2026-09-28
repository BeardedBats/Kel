/**
 * D-70 item 1 — where an answer on a needs-you card goes. Every answer goes to Kel, in that work's
 * own conversation, through a path that already exists (never to an agent, never a second answer
 * system): the approval's approve/deny route, the apply route with Nick as the actor, the resume
 * control, or a normal chat message (so the D-55 restart rule applies to a typed answer).
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

/** What the card says right after the answer is on its way (Figma 5b). */
export const answeredFollowUp = (question: Pick<OfficeQuestion, 'kind'>, answer: NeedsAnswer): string => {
  if ('option' in answer) {
    if (question.kind === 'approval' && answer.option.id === 'deny') return 'Kel won’t take that step';
    if (answer.option.id === 'leave') return 'Kel left it as it is';
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
  const choice = answer.option.id;
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
    case 'interrupted':
      if (!conversation || !job) throw new Error('Kel could not find this work’s chat.');
      await answerMessage(conversation, 'continue', job);
      return;
    default:
      if (!conversation) throw new Error('Kel could not find this work’s chat.');
      await answerMessage(conversation, answer.option.label);
  }
};
