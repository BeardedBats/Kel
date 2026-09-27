import { describe, expect, it } from 'vitest';
import { isKelWorkToolCall, kelWorkSubmissionId, KEL_WORK_TOOL_PREFIX } from '@/common/chat/kelWork';

describe('Kel hand-off tool calls', () => {
  it('recognises only the engine hand-off card id', () => {
    expect(KEL_WORK_TOOL_PREFIX).toBe('kel-work:');
    expect(isKelWorkToolCall('kel-work:acp-0123abcd')).toBe(true);
    expect(isKelWorkToolCall('kel-work:')).toBe(false);
    expect(isKelWorkToolCall('0f8e-job-id')).toBe(false);
    expect(isKelWorkToolCall('tool-kel-work:x')).toBe(false);
    expect(isKelWorkToolCall(undefined)).toBe(false);
    expect(isKelWorkToolCall(42)).toBe(false);
  });

  it('extracts the submission the card reads', () => {
    expect(kelWorkSubmissionId('kel-work:acp-0123abcd')).toBe('acp-0123abcd');
    expect(kelWorkSubmissionId('job-1')).toBeNull();
  });
});
