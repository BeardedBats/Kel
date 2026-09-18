/**
 * Which knowledge-record actions apply, given the record's own state.
 *
 * Mirrors the engine's guards so the Work panel never offers an action the engine will refuse:
 * `Memory.confirm` and `Memory.correct` require an active record, `Memory.retract` also accepts
 * stale ones, and `Memory.forget` purges content on any record — except an already-purged
 * tombstone, which has nothing left to remove.
 */
export type MemoryRecordLike = {
  status: string;
  user_confirmed: number;
  trust: number;
  summary: string;
};

export type MemoryRecordActions = {
  confirm: boolean;
  edit: boolean;
  retract: boolean;
  forget: boolean;
};

export function memoryRecordActions(r: MemoryRecordLike): MemoryRecordActions {
  const active = r.status === 'active';
  return {
    confirm: active && !r.user_confirmed && r.trust > 2 && r.trust < 7,
    edit: active,
    retract: active || r.status === 'stale',
    forget: !(r.status === 'retracted' && !r.summary),
  };
}
