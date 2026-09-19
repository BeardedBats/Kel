/**
 * Batch 6 (visual findings 16/17): the supervision state machine for the Kel engine link.
 *
 * Pure logic — no timers, no IPC, no Electron. `KelService` drives it from a health poll and
 * performs the actions it returns. The machine exists so the reconnection behaviour is testable
 * and honest:
 *  - it never claims success it has not observed (only `alive()` after a restart retires an
 *    incident);
 *  - automatic restart attempts are budgeted per incident and that budget is NOT reset by a failed
 *    attempt, only by the engine actually answering again (or an explicit user action, which
 *    starts a new user-authorized incident).
 */

export type EngineHealthState = 'connected' | 'reconnecting' | 'recovered' | 'unrecoverable';

export interface EngineHealthConfig {
  /** Consecutive missed beats before the link is considered down. */
  failureThreshold: number;
  /** Automatic restart attempts allowed per incident before asking the person. */
  maxRestarts: number;
}

export interface EngineHealthSnapshot {
  state: EngineHealthState;
  failures: number;
  restarts: number;
  maxRestarts: number;
  at: number;
}

export type HealthDecisionAction = 'none' | 'restart' | 'manual';

export interface HealthDecision {
  state: EngineHealthState;
  action: HealthDecisionAction;
}

export const DEFAULT_ENGINE_HEALTH: EngineHealthConfig = { failureThreshold: 2, maxRestarts: 2 };

export class EngineHealthMachine {
  private state: EngineHealthState = 'connected';
  private failures = 0;
  private restarts = 0;
  private at = Date.now();
  private readonly config: EngineHealthConfig;

  constructor(config: Partial<EngineHealthConfig> = {}) {
    this.config = { ...DEFAULT_ENGINE_HEALTH, ...config };
  }

  /** A heartbeat was answered. */
  alive(now = Date.now()): HealthDecision {
    this.failures = 0;
    this.at = now;
    if (this.state !== 'connected') {
      this.state = 'connected';
      this.restarts = 0; // the incident is over: the engine answered again
    }
    return this.decision('none');
  }

  /** A heartbeat was missed. */
  missed(now = Date.now()): HealthDecision {
    this.failures += 1;
    this.at = now;
    if (this.failures < this.config.failureThreshold) return this.decision('none');
    if (this.state === 'unrecoverable') return this.decision('manual');
    if (this.restarts >= this.config.maxRestarts) {
      this.state = 'unrecoverable';
      return this.decision('manual');
    }
    this.state = 'reconnecting';
    this.restarts += 1;
    return this.decision('restart');
  }

  /** A restart attempt finished. `ok` means the engine is answering again. */
  restartFinished(ok: boolean, now = Date.now()): HealthDecision {
    this.at = now;
    if (ok) {
      this.state = 'recovered';
      this.failures = 0;
      return this.decision('none');
    }
    if (this.restarts >= this.config.maxRestarts) {
      this.state = 'unrecoverable';
      return this.decision('manual');
    }
    this.state = 'reconnecting';
    return this.decision('restart');
  }

  /** The person asked for another attempt after the automatic budget was spent. */
  manualRetry(now = Date.now()): HealthDecision {
    this.at = now;
    this.restarts = 0;
    this.failures = this.config.failureThreshold;
    this.state = 'reconnecting';
    this.restarts += 1;
    return this.decision('restart');
  }

  snapshot(): EngineHealthSnapshot {
    return { state: this.state, failures: this.failures, restarts: this.restarts, maxRestarts: this.config.maxRestarts, at: this.at };
  }

  private decision(action: HealthDecisionAction): HealthDecision {
    return { state: this.state, action };
  }
}
