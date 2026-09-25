import type { IMessageAcpToolCall, IMessagePlan } from '@/common/chat/chatLib';
import { normalizeAcpToolCall } from '@/common/chat/normalizeToolCall';
import { selectLatestPlan } from '@renderer/pages/conversation/PlanBar/useLatestPlan';
import { describe, expect, it } from 'vitest';

const tool = (id: string, kind: 'execute' | 'edit' | 'read', title: string,
  rawInput: Record<string, unknown>, rawOutput?: Record<string, unknown>): IMessageAcpToolCall => ({
  id, msg_id: id, conversation_id: 'fixture', type: 'acp_tool_call', position: 'left', created_at: 100,
  content: { update: { sessionUpdate: 'tool_call', tool_call_id: id, status: 'completed', kind, title, rawInput, rawOutput } },
} as IMessageAcpToolCall);

describe('current Figma tool and plan content', () => {
  it('shows the recorded command outcome, file count, and search query', () => {
    expect(normalizeAcpToolCall(tool('build', 'execute', 'Execute: npm run build',
      { command: 'npm run build' }, { approval: 'auto', duration_seconds: 14 }))?.description)
      .toBe('Auto-approved · 14 s');
    expect(normalizeAcpToolCall(tool('patch', 'edit', 'Patch Applied',
      { file_path: 'hero.tsx, nav.tsx, styles.css' }))?.description).toBe('3 file changes');
    expect(normalizeAcpToolCall(tool('search', 'read', 'Web Search',
      { query: 'lighthouse score hero image size' }))?.description)
      .toBe('lighthouse score hero image size');
  });

  it('uses the newest full plan snapshot when progress changes', () => {
    const plan = (id: string, at: number, completed: number): IMessagePlan => ({
      id, msg_id: id, conversation_id: 'fixture', type: 'plan', position: 'left', created_at: at,
      content: { session_id: 'fixture', entries: Array.from({ length: 5 }, (_, index) => ({
        content: `Step ${index + 1}`, status: index < completed ? 'completed' : 'pending',
      })) },
    });
    const latest = selectLatestPlan([plan('new', 200, 3), plan('old', 100, 2)]);
    expect(latest?.id).toBe('new');
    expect(latest?.content.entries.filter((entry) => entry.status === 'completed')).toHaveLength(3);
  });
});
