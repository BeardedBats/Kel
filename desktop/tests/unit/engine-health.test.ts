/**
 * Batch 6 (visual findings 16/17) — pins for the supervision state machine.
 *
 * The invariants under test (they back the R10 requirements): a restart only happens after
 * consecutive missed beats; the automatic budget is spent, never silently reset by a failed
 * attempt; success is only ever claimed after the engine answered again; and a person's explicit
 * retry starts a fresh user-authorised incident.
 */
import { describe, expect, it } from 'vitest';
import { EngineHealthMachine } from '@process/services/kel/engineHealth';

describe('EngineHealthMachine', () => {
  it('stays connected below the failure threshold', () => {
    const machine = new EngineHealthMachine({ failureThreshold: 2, maxRestarts: 2 });
    expect(machine.missed()).toEqual({ state: 'connected', action: 'none' });
    expect(machine.alive()).toEqual({ state: 'connected', action: 'none' });
  });

  it('asks for one restart once the link is down, and claims recovery only after success', () => {
    const machine = new EngineHealthMachine({ failureThreshold: 2, maxRestarts: 2 });
    machine.missed();
    expect(machine.missed()).toEqual({ state: 'reconnecting', action: 'restart' });
    expect(machine.restartFinished(true)).toEqual({ state: 'recovered', action: 'none' });
    // The incident retires only when the engine actually answers again.
    expect(machine.snapshot().state).toBe('recovered');
    expect(machine.alive()).toEqual({ state: 'connected', action: 'none' });
    expect(machine.snapshot().restarts).toBe(0);
  });

  it('does not reset the automatic budget on a failed restart', () => {
    const machine = new EngineHealthMachine({ failureThreshold: 1, maxRestarts: 2 });
    expect(machine.missed()).toEqual({ state: 'reconnecting', action: 'restart' }); // attempt 1
    expect(machine.restartFinished(false)).toEqual({ state: 'reconnecting', action: 'restart' }); // next attempt is still allowed
    expect(machine.missed()).toEqual({ state: 'reconnecting', action: 'restart' }); // attempt 2
    expect(machine.restartFinished(false)).toEqual({ state: 'unrecoverable', action: 'manual' }); // budget spent, never reset
    expect(machine.snapshot().restarts).toBe(2);
  });

  it('goes unrecoverable after the budget is spent and asks the person', () => {
    const machine = new EngineHealthMachine({ failureThreshold: 1, maxRestarts: 1 });
    machine.missed();
    expect(machine.restartFinished(false)).toEqual({ state: 'unrecoverable', action: 'manual' });
    // Further missed beats keep asking for the person; no silent extra attempts.
    expect(machine.missed()).toEqual({ state: 'unrecoverable', action: 'manual' });
  });

  it('a person-started retry is a new incident and can recover', () => {
    const machine = new EngineHealthMachine({ failureThreshold: 1, maxRestarts: 1 });
    machine.missed();
    machine.restartFinished(false);
    expect(machine.snapshot().state).toBe('unrecoverable');
    expect(machine.manualRetry()).toEqual({ state: 'reconnecting', action: 'restart' });
    expect(machine.restartFinished(true)).toEqual({ state: 'recovered', action: 'none' });
    expect(machine.alive()).toEqual({ state: 'connected', action: 'none' });
  });

  it('an answered heartbeat during reconnecting retires the incident without a restart', () => {
    const machine = new EngineHealthMachine({ failureThreshold: 2, maxRestarts: 2 });
    machine.missed();
    machine.missed(); // reconnecting, one restart authorised
    expect(machine.alive()).toEqual({ state: 'connected', action: 'none' });
    expect(machine.snapshot().restarts).toBe(0);
  });
});
