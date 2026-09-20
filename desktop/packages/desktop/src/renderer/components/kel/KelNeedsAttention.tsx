/**
 * R9.D — "Needs your attention" (derived-only view).
 *
 * Reads the same authoritative endpoints the rest of the shell reads; renders a compact list of
 * things that genuinely need a person, each with the one action that opens the existing surface
 * which owns the decision. Owns no workflow truth: no mutations are invented here, and nothing
 * is rendered while the source cannot be read (the surrounding surface already reports failure).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { kelAutonomy, kelProviders, kelState } from './kelApi';
import { collectAttention, type AttentionItem } from './needsAttention';
import { KelButton } from './KelPrimitives';
import { resolveConversationRoute } from '@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync';

export const NeedsAttention: React.FC<{ projectId?: string }> = ({ projectId }) => {
  const navigate = useNavigate();
  const [items, setItems] = useState<AttentionItem[] | null>(null);

  const load = useCallback(async () => {
    try {
      const [state, boundary, providers] = await Promise.all([
        kelState(),
        kelAutonomy.requests(),
        // Setup needs are attention too; a failed read never invents items.
        kelProviders.list().catch((): null => null),
      ]);
      setItems(
        collectAttention(
          {
            jobs: state.jobs ?? [],
            continuation: state.continuation ?? [],
            boundaryRequests: boundary.requests ?? [],
            providers: (providers?.providers ?? []).map((entry) => ({
              id: entry.provider,
              label: entry.label,
              status: entry.status,
            })),
          },
          { projectId }
        )
      );
    } catch {
      // Honest silence: the host surface shows the failure; this derived view never invents.
      setItems(null);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (items === null) return null;

  return (
    <section className='kel-card' data-testid='needs-attention' aria-label='Needs your attention'>
      <div className='kel-row'>
        <h2 className='kel-h2'>Needs your attention</h2>
        <span className='kel-grow' />
        {items.length > 0 && <span className='kel-meta'>{items.length}</span>}
      </div>
      <div className='kel-divider' />
      {items.length === 0 ? (
        <p className='kel-meta' style={{ margin: 0 }}>
          Nothing needs you right now.
        </p>
      ) : (
        items.map((item) => (
          <div className='kel-attention__row' key={item.id}>
            <div className='kel-attention__text'>
              <strong>{item.title}</strong>
              <span className='kel-meta'>{item.detail}</span>
            </div>
            {item.action && (
              <KelButton variant='quiet' onClick={() => navigate(resolveConversationRoute(item.action!.to))}>
                {item.action.label}
              </KelButton>
            )}
          </div>
        ))
      )}
    </section>
  );
};
