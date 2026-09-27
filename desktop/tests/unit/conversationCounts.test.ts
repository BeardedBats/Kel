/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

import { describe, expect, it } from 'vitest';
import { conversationCounts, knownEmpty } from '../../packages/desktop/src/process/services/kel/conversationCounts';

describe('start-up conversation counts (ST-23)', () => {
  const listed = {
    conversations: [
      { id: 'empty', message_count: 0, job_count: 0 },
      { id: 'talked', message_count: 3, job_count: 0 },
      { id: 'worked', message_count: 0, job_count: 1 },
    ],
  };

  it('skips only conversations the engine said are empty', () => {
    const counts = conversationCounts(listed);
    expect(knownEmpty(counts, 'empty')).toBe(true);
    expect(knownEmpty(counts, 'talked')).toBe(false);
    expect(knownEmpty(counts, 'worked')).toBe(false);
  });

  it('never skips a conversation it has no count for', () => {
    expect(knownEmpty(conversationCounts(listed), 'unknown')).toBe(false);
    // An older engine without the route: everything is read as before.
    expect(conversationCounts({ error: 'Not found' })).toBeNull();
    expect(knownEmpty(null, 'empty')).toBe(false);
    expect(knownEmpty(conversationCounts({ conversations: [{ id: 'bad', message_count: '0' }] }), 'bad')).toBe(false);
  });
});
