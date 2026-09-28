/**
 * D-70 — what a Kel message carries under its text, chosen from the details the engine recorded
 * with it: Kel's "before I start" questions (a scoping card), the compact done card on a result
 * whose work has a top card, or — for everything else, and for work from before the cards — the
 * existing on-demand Details.
 */
import type { KelMessageMeta } from '@/common/chat/kelMessageMeta';
import React from 'react';
import { KelMessageDetails } from '@renderer/pages/conversation/Messages/components/KelMessageDetails';
import { KelDoneCard } from './KelDoneCard';
import { KelScopingCard } from './KelScopingCard';

export const KelMessageCard: React.FC<{ meta: KelMessageMeta; conversationId?: string }> = ({ meta, conversationId }) => {
  if (meta.kind === 'scoping' && meta.scoping) return <KelScopingCard scopingId={meta.scoping} conversationId={conversationId} />;
  if (meta.kind === 'result' && meta.job) {
    return <KelDoneCard job={meta.job} meta={meta} fallback={<KelMessageDetails meta={meta} />} />;
  }
  return <KelMessageDetails meta={meta} />;
};

export default KelMessageCard;
