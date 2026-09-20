/**
 * D6 — the landing "While you were away" card.
 *
 * Self-contained like the provider notice: it reads the same authoritative endpoints the shell
 * reads, derives only, and renders nothing when the brief is quiet. Every action opens the
 * existing surface that owns the follow-up; nothing here mutates work or resumes anything.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KelButton } from '@renderer/components/kel/KelPrimitives';
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
    <section className='kel-card' style={{ marginBottom: 12 }} data-testid='resumption-brief' aria-label='While you were away'>
      <div className='kel-row' style={{ alignItems: 'baseline', gap: 12 }}>
        <h2 className='kel-h2' style={{ margin: 0 }}>
          {brief.headline}
        </h2>
        <span className='kel-grow' />
        <span className='kel-meta'>{brief.summary}</span>
      </div>
      <div className='kel-divider' />
      {brief.lines.map((line) => (
        <div className='kel-attention__row' key={line.id}>
          <div className='kel-attention__text'>
            <strong>{line.title}</strong>
            <span className='kel-meta'>{line.detail}</span>
          </div>
          {line.action && (
            <KelButton variant='quiet' onClick={() => navigate(resolveConversationRoute(line.action!.to))}>
              {line.action.label}
            </KelButton>
          )}
        </div>
      ))}
    </section>
  );
};

export default KelResumptionBrief;
