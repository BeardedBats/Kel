/**
 * D-72 — plain words for what Kel's messages and work used (the engine's measured usage).
 *
 * A subscription call (Codex, Claude Code) is "Included in your plan", never "$0.00"; a metered call
 * shows its cost, "~" when it is estimated from the list price; an unknown number is left out rather
 * than shown as zero.
 */
import type { KelUsage } from '@/common/chat/kelMessageMeta';

const num = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

/** "$0.02", "<$0.01", "~$0.40" (estimated) — null when the cost is unknown. */
export const costAmount = (cost: number | null | undefined, basis?: string | null): string | null => {
  if (!num(cost)) return null;
  const approx = basis === 'estimated' ? '~' : '';
  if (cost > 0 && cost < 0.01) return `<${approx}$0.01`;
  return `${approx}$${cost.toFixed(2)}`;
};

/** The cost chip's words: the plan, the metered cost, or both; null when nothing is known. */
export const costWords = (usage: KelUsage | null | undefined): string | null => {
  if (!usage) return null;
  if (usage.billing === 'plan') return 'Included in your plan';
  const amount = costAmount(usage.cost, usage.cost_basis);
  if (usage.billing === 'mixed') return amount ? `${amount} + your plan` : 'Partly included in your plan';
  return amount;
};

/** What the cost chip's tooltip says (the basis in words). */
export const costHint = (usage: KelUsage | null | undefined): string => {
  if (!usage) return '';
  if (usage.billing === 'plan') {
    const equivalent = costAmount(usage.plan_cost_equivalent);
    return `Ran on your subscription, so it costs nothing extra${equivalent ? ` (about ${equivalent} at API prices)` : ''}.`;
  }
  if (usage.cost_basis === 'estimated') return 'Approximate cost, estimated from the model’s list price.';
  if (usage.cost_basis === 'reported') return 'Cost as the model’s service reported it.';
  return 'Approximate cost.';
};

/** "1.4K tokens" — null when no count was reported. */
export const tokenWords = (tokens: number | null | undefined): string | null =>
  num(tokens)
    ? `${new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(tokens)} tokens`
    : null;

/** "0.8 s", "14 s", "3 min", "1 h 5 min" — null when not measured. */
export const timeWords = (ms: number | null | undefined): string | null => {
  if (!num(ms) || ms < 0) return null;
  const seconds = ms / 1000;
  if (seconds < 10) return `${Math.max(0.1, Math.round(seconds * 10) / 10)} s`;
  if (seconds < 90) return `${Math.round(seconds)} s`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
};

/** The chips under a reply, in order: cost, tokens, time, model. Empty when nothing is known. */
export const usageChips = (usage: KelUsage | null | undefined): Array<{ key: string; text: string; hint?: string }> => {
  if (!usage) return [];
  const chips: Array<{ key: string; text: string; hint?: string }> = [];
  const cost = costWords(usage);
  if (cost) chips.push({ key: 'cost', text: cost, hint: costHint(usage) });
  const tokens = tokenWords(usage.tokens);
  if (tokens) chips.push({ key: 'tokens', text: tokens, hint: 'Tokens the model processed for this.' });
  const time = timeWords(usage.ms);
  if (time) chips.push({ key: 'time', text: time, hint: 'How long the model took.' });
  const models = (usage.models ?? []).filter(Boolean);
  const model = usage.model_label || models[models.length - 1];
  if (model) chips.push({ key: 'model', text: model, hint: models.length > 1 ? `Models used: ${models.join(', ')}` : 'The model that answered.' });
  return chips;
};

/** One line for a work card's detail header: "Included in your plan · 86K tokens · 3 min of model time". */
export const usageHeaderLine = (usage: KelUsage | null | undefined): string | null => {
  if (!usage) return null;
  const parts = [costWords(usage), tokenWords(usage.tokens), timeWords(usage.ms) ? `${timeWords(usage.ms)} of model time` : null];
  const kept = parts.filter((part): part is string => Boolean(part));
  return kept.length ? kept.join('  ·  ') : null;
};
