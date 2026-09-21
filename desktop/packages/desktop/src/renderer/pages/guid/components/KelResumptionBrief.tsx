/**
 * D6 — the landing "While you were away" card.
 *
 * Self-contained like the provider notice: it reads the same authoritative endpoints the shell
 * reads, derives only, and renders nothing when the brief is quiet. Every action opens the
 * existing surface that owns the follow-up; nothing here mutates work or resumes anything.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import statusCheck from '@renderer/assets/figma/status-check.svg';
import { kelAutonomy, kelProviders, kelState } from '@renderer/components/kel/kelApi';
import { buildResumptionBrief, type ResumptionBrief } from '@renderer/components/kel/resumptionBrief';
import { resolveConversationRoute } from '@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync';

const KelResumptionBrief: React.FC = () => {
  const navigate = useNavigate();
  const [brief, setBrief] = useState<ResumptionBrief | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [state, boundary, providers] = await Promise.all([
          kelState(),
          kelAutonomy.requests(),
          // A failed read never invents lines; setup needs simply stay out of this brief.
          kelProviders.list().catch((): null => null),
        ]);
        if (cancelled) return;
        setBrief(
          buildResumptionBrief({
            jobs: state.jobs ?? [],
            continuation: state.continuation ?? [],
            boundaryRequests: boundary.requests ?? [],
            providers: (providers?.providers ?? []).map((entry) => ({
              id: entry.provider,
              label: entry.label,
              status: entry.status,
            })),
            restore: state.restore ?? null,
          })
        );
      } catch {
        // The shell reports engine failures on their own surfaces; this card stays silent.
        if (!cancelled) setBrief(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!brief || brief.quiet) return null;

  return (
    <section className='kel-card kel-shell-needs-you' data-testid='resumption-brief' aria-label='Needs you'>
      <h2 className='kel-shell-needs-you-title'>Needs you</h2>
      {brief.lines.map((line) => {
        const success = line.kind === 'finished' || (line.kind === 'restore' && line.id === 'restore-ok');
        const tone = success ? 'success' : line.kind === 'active' ? 'unread' : 'attention';
        const text = line.id.startsWith('brief-connection-')
          ? line.detail.replace(/ — finish setting it up/, ' needs setup')
          : line.kind === 'finished'
            ? `${line.title.replace(/^Finished: /, '')} — ${line.detail}`
            : `${line.title}${line.detail ? ` — ${line.detail}` : ''}`;
        const content = <>
          {success ? <img className='kel-shell-status-check' src={statusCheck} width={16} height={16} alt='' /> : <span className='kel-shell-status-dot' aria-hidden='true' />}
          <span>{text}</span>
        </>;
        return line.action ? (
          <button type='button' className='kel-shell-attention-line' data-tone={tone} key={line.id}
            title={line.action.label} onClick={() => navigate(resolveConversationRoute(line.action!.to))}>{content}</button>
        ) : <div className='kel-shell-attention-line' data-tone={tone} key={line.id}>{content}</div>;
      })}
    </section>
  );
};

export default KelResumptionBrief;
