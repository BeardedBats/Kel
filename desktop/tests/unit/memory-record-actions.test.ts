/**
 * Knowledge-record action gating: the Work panel must offer only what the engine accepts.
 *
 * The engine refuses `correct`/`retract` on records that are not active (retract also accepts
 * stale) and confirms only active records; a forgotten tombstone has no content to purge. These
 * tests pin the panel's action matrix to those guards.
 */
import { describe, expect, it } from 'vitest';
import { memoryRecordActions, type MemoryRecordLike } from '@/renderer/components/kel/memoryRecordActions';

const record = (over: Partial<MemoryRecordLike> = {}): MemoryRecordLike => ({
  status: 'active',
  user_confirmed: 0,
  trust: 3,
  summary: 'A saved fact',
  ...over,
});

describe('memoryRecordActions', () => {
  it('offers confirm/edit/retract/forget on an active unconfirmed record', () => {
    expect(memoryRecordActions(record())).toEqual({
      confirm: true,
      edit: true,
      retract: true,
      forget: true,
    });
  });

  it('hides confirm once the user has confirmed the record', () => {
    expect(memoryRecordActions(record({ user_confirmed: 1, trust: 2 })).confirm).toBe(false);
  });

  it('hides confirm for trust levels that are already authoritative or untrusted', () => {
    expect(memoryRecordActions(record({ trust: 2 })).confirm).toBe(false);
    expect(memoryRecordActions(record({ trust: 7 })).confirm).toBe(false);
  });

  it('never offers edit/confirm/retract on a superseded record, but still allows purge', () => {
    expect(memoryRecordActions(record({ status: 'superseded' }))).toEqual({
      confirm: false,
      edit: false,
      retract: false,
      forget: true,
    });
  });

  it('allows retracting a stale record but not editing or confirming it', () => {
    expect(memoryRecordActions(record({ status: 'stale' }))).toEqual({
      confirm: false,
      edit: false,
      retract: true,
      forget: true,
    });
  });

  it('offers nothing on a forgotten tombstone', () => {
    expect(memoryRecordActions(record({ status: 'retracted', summary: '' }))).toEqual({
      confirm: false,
      edit: false,
      retract: false,
      forget: false,
    });
  });

  it('still allows purging a retracted record whose content was kept', () => {
    expect(memoryRecordActions(record({ status: 'retracted' }))).toEqual({
      confirm: false,
      edit: false,
      retract: false,
      forget: true,
    });
  });
});
