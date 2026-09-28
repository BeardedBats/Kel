/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 *
 * D-57: scheduled tasks live in the engine. These helpers build the cadence the dialog sends and
 * word a schedule for the page. The engine's own `description` ("Every weekday at 9:00") wins;
 * the local wording is only for a schedule the engine has not described.
 */

import type { TChatConversation } from '@/common/config/storage';
import type { KelSchedule, KelScheduleCadence } from '@renderer/components/kel/kelApi';
import { formatDateTime } from '@/renderer/services/i18n/format';

export type FrequencyType = 'manual' | 'hourly' | 'daily' | 'weekdays' | 'weekly' | 'custom';
export type CustomFrequencyMode = 'interval' | 'daily' | 'weekly' | 'monthly' | 'advanced';
export type CustomIntervalUnit = 'minutes' | 'hours';

export type CustomScheduleState = {
  mode: CustomFrequencyMode;
  interval: number;
  intervalUnit: CustomIntervalUnit;
  time: string;
  weekdays: string[];
  monthDay: number;
  advancedExpression: string;
};

export const WEEKDAYS = [
  { value: 'MON', label: 'Monday' },
  { value: 'TUE', label: 'Tuesday' },
  { value: 'WED', label: 'Wednesday' },
  { value: 'THU', label: 'Thursday' },
  { value: 'FRI', label: 'Friday' },
  { value: 'SAT', label: 'Saturday' },
  { value: 'SUN', label: 'Sunday' },
];

/** Settled policy 3: the engine runs a task at most every 5 minutes. */
export const MINUTE_INTERVALS = [5, 10, 15, 20, 30];
export const HOUR_INTERVALS = [1, 2, 3, 4, 6, 8, 12];

export const FREQUENCY_LABELS: Record<FrequencyType, string> = {
  manual: 'Manual',
  hourly: 'Hourly',
  daily: 'Daily',
  weekdays: 'Weekdays',
  weekly: 'Weekly',
  custom: 'Custom',
};

export function createDefaultCustomSchedule(): CustomScheduleState {
  return {
    mode: 'interval',
    interval: 30,
    intervalUnit: 'minutes',
    time: '09:00',
    weekdays: ['MON', 'TUE', 'WED', 'THU', 'FRI'],
    monthDay: 1,
    advancedExpression: '',
  };
}

const hhmm = (hour: string | number, minute: string | number) =>
  `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;

/** The frequency tab, time and weekday a cadence is edited with. */
export function frequencyFromCadence(cadence: KelScheduleCadence | null): {
  frequency: FrequencyType;
  time: string;
  weekday: string;
  custom: CustomScheduleState;
} {
  const base = { time: '09:00', weekday: 'MON', custom: createDefaultCustomSchedule() };
  if (!cadence || cadence.kind === 'manual') return { ...base, frequency: 'manual' };
  if (cadence.kind === 'interval') {
    const hours = cadence.minutes % 60 === 0 ? cadence.minutes / 60 : 0;
    if (hours === 1) return { ...base, frequency: 'hourly' };
    return {
      ...base,
      frequency: 'custom',
      custom: hours
        ? { ...base.custom, interval: hours, intervalUnit: 'hours' }
        : { ...base.custom, interval: cadence.minutes, intervalUnit: 'minutes' },
    };
  }
  if (cadence.kind === 'once') {
    return { ...base, frequency: 'custom', custom: { ...base.custom, mode: 'advanced', advancedExpression: '' } };
  }
  const expr = cadence.expr.trim();
  const parts = expr.split(/\s+/);
  if (parts.length !== 5) return { ...base, frequency: 'custom', custom: { ...base.custom, mode: 'advanced', advancedExpression: expr } };
  const [minute, hour, day, month, dow] = parts;
  const simple = /^\d{1,2}$/.test(minute) && /^\d{1,2}$/.test(hour);
  if (minute === '0' && hour === '*' && day === '*' && month === '*' && dow === '*') return { ...base, frequency: 'hourly' };
  if (simple && day === '*' && month === '*') {
    const time = hhmm(hour, minute);
    const upper = dow.toUpperCase();
    if (upper === '*') return { ...base, frequency: 'daily', time };
    if (upper === 'MON-FRI' || upper === '1-5') return { ...base, frequency: 'weekdays', time };
    if (WEEKDAYS.some((d) => d.value === upper)) return { ...base, frequency: 'weekly', time, weekday: upper };
    const days = upper.split(',');
    if (days.length > 1 && days.every((d) => WEEKDAYS.some((w) => w.value === d)))
      return { ...base, frequency: 'custom', custom: { ...base.custom, mode: 'weekly', time, weekdays: days } };
  }
  if (simple && /^\d{1,2}$/.test(day) && month === '*' && dow === '*')
    return { ...base, frequency: 'custom', custom: { ...base.custom, mode: 'monthly', time: hhmm(hour, minute), monthDay: Number(day) } };
  return { ...base, frequency: 'custom', custom: { ...base.custom, mode: 'advanced', advancedExpression: expr } };
}

/** The cadence the dialog's choices describe. */
export function cadenceFromFrequency(
  frequency: FrequencyType,
  time: string,
  weekday: string,
  custom: CustomScheduleState
): KelScheduleCadence {
  const [hour, minute] = time.split(':').map(Number);
  switch (frequency) {
    case 'manual':
      return { kind: 'manual' };
    case 'hourly':
      return { kind: 'interval', minutes: 60 };
    case 'daily':
      return { kind: 'cron', expr: `${minute} ${hour} * * *` };
    case 'weekdays':
      return { kind: 'cron', expr: `${minute} ${hour} * * MON-FRI` };
    case 'weekly':
      return { kind: 'cron', expr: `${minute} ${hour} * * ${weekday}` };
    case 'custom': {
      const [customHour, customMinute] = custom.time.split(':').map(Number);
      switch (custom.mode) {
        case 'interval':
          return { kind: 'interval', minutes: custom.intervalUnit === 'hours' ? custom.interval * 60 : custom.interval };
        case 'daily':
          return { kind: 'cron', expr: `${customMinute} ${customHour} * * *` };
        case 'weekly':
          return { kind: 'cron', expr: `${customMinute} ${customHour} * * ${custom.weekdays.join(',')}` };
        case 'monthly':
          return { kind: 'cron', expr: `${customMinute} ${customHour} ${custom.monthDay} * *` };
        case 'advanced':
          return { kind: 'cron', expr: custom.advancedExpression.trim() };
      }
    }
  }
  return { kind: 'manual' };
}

const clock = (hour: number, minute: number) => {
  const suffix = hour < 12 ? 'AM' : 'PM';
  const h = hour % 12 === 0 ? 12 : hour % 12;
  return `${h}:${String(minute).padStart(2, '0')} ${suffix}`;
};

/** A plain sentence for a cadence the engine has not described (never a raw expression alone). */
export function describeCadence(cadence: KelScheduleCadence | null, locale?: string): string {
  if (!cadence) return 'Schedule unavailable';
  switch (cadence.kind) {
    case 'manual':
      return 'Only when you run it';
    case 'interval': {
      if (cadence.minutes === 60) return 'Every hour';
      if (cadence.minutes % 60 === 0) return `Every ${cadence.minutes / 60} hours`;
      return `Every ${cadence.minutes} minutes`;
    }
    case 'once':
      return `Once, ${formatDateTime(cadence.at * 1000, locale)}`;
    case 'cron': {
      const picked = frequencyFromCadence(cadence);
      const [hour, minute] = picked.time.split(':').map(Number);
      const at = clock(hour, minute);
      if (picked.frequency === 'hourly') return 'Every hour';
      if (picked.frequency === 'daily') return `Every day at ${at}`;
      if (picked.frequency === 'weekdays') return `Every weekday at ${at}`;
      if (picked.frequency === 'weekly') {
        const day = WEEKDAYS.find((d) => d.value === picked.weekday)?.label ?? picked.weekday;
        return `Every ${day} at ${at}`;
      }
      if (picked.custom.mode === 'monthly') {
        const [h, m] = picked.custom.time.split(':').map(Number);
        return `Monthly on day ${picked.custom.monthDay} at ${clock(h, m)}`;
      }
      if (picked.custom.mode === 'weekly') {
        const [h, m] = picked.custom.time.split(':').map(Number);
        const days = picked.custom.weekdays.map((d) => WEEKDAYS.find((w) => w.value === d)?.label.slice(0, 3) ?? d);
        return `${days.join(', ')} at ${clock(h, m)}`;
      }
      return `Custom schedule (${cadence.expr})`;
    }
  }
}

/** The engine's sentence for this schedule, or the local wording. */
export function scheduleSentence(schedule: Pick<KelSchedule, 'description' | 'cadence'>, locale?: string): string {
  return schedule.description?.trim() || describeCadence(schedule.cadence, locale);
}

/** When it runs next, in the app language (engine times are epoch seconds). */
export function formatNextRun(seconds: number | null | undefined, locale?: string): string {
  if (!seconds) return '—';
  return formatDateTime(seconds * 1000, locale);
}


/** A chat made by the old scheduler names its task here; links to it go through `?origin=`. */
export function resolveCronJobId(extra: TChatConversation['extra'] | undefined): string | undefined {
  const maybeExtra = extra as { cron_job_id?: unknown; cronJobId?: unknown } | undefined;
  const snakeCase = maybeExtra?.cron_job_id;
  if (typeof snakeCase === 'string' && snakeCase.trim()) return snakeCase;
  const camelCase = maybeExtra?.cronJobId;
  if (typeof camelCase === 'string' && camelCase.trim()) return camelCase;
  return undefined;
}

/** A schedule's status for the small indicators: a problem first, then paused, else active. */
export type ScheduleStatus = 'active' | 'paused' | 'error';
export function scheduleStatus(schedule: Pick<KelSchedule, 'enabled' | 'problem' | 'status'>): ScheduleStatus {
  if (schedule.problem || schedule.status === 'needs_attention') return 'error';
  if (schedule.status === 'done') return 'paused';
  return schedule.enabled ? 'active' : 'paused';
}

/** The list chip: the engine's own reading of the schedule, in words. */
export function scheduleChip(schedule: Pick<KelSchedule, 'enabled' | 'problem' | 'status'>): { label: string; tone: string } {
  if (schedule.problem || schedule.status === 'needs_attention') return { label: 'Needs attention', tone: 'kel-chip--failed' };
  if (schedule.status === 'done') return { label: 'Done', tone: 'kel-chip--wait' };
  if (!schedule.enabled || schedule.status === 'paused') return { label: 'Paused', tone: 'kel-chip--wait' };
  if (schedule.status === 'manual') return { label: 'Manual', tone: 'kel-chip--ok' };
  return { label: 'Active', tone: 'kel-chip--ok' };
}
