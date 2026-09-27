import { describe, expect, it } from 'vitest';
import { parseEngineFailure } from '@/renderer/pages/conversation/Messages/components/KelEngineFailureCard';

describe('parseEngineFailure', () => {
  it('extracts the reason from the legacy planning failure sentence', () => {
    expect(parseEngineFailure('Kel could not plan this request: Invalid structured result')).toBe(
      'Invalid structured result'
    );
  });

  it('extracts the reason from the hand-off start failure sentence', () => {
    expect(
      parseEngineFailure("I wasn't able to get that started — the model timed out. You can retry it from the card above.")
    ).toBe('the model timed out');
  });

  it('leaves ordinary replies alone', () => {
    expect(parseEngineFailure('The sky is usually blue.')).toBeNull();
    expect(parseEngineFailure('Here is why Kel could not plan this request: it was vague.')).toBeNull();
  });
});
