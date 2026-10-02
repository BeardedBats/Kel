/**
 * Settings → Kel → Staff & models (D-70 item 3).
 *
 * One row per staff role with its mode (Automatic / Preferred / Fixed), model and reasoning level,
 * read from and written to the engine's `/api/model` roles actions (D-66 design §2). The engine owns
 * the catalog, the D-67 starting defaults and what can run on this computer; this page shows exactly
 * that, in plain words, and never claims a model can run when the engine says it cannot. Kel's own
 * chat model stays on Settings → Model and in the composer (D-69: staff always use their role model).
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useArrival, useEntrance, useFlip } from '@renderer/motion';
import { useLocation } from 'react-router-dom';
import { KelButton, KelCard, KelLoading } from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import {
  MODE_HINTS,
  MODE_LABELS,
  PURPOSE_WORDS,
  STAFF_DESCRIPTIONS,
  TIER_WORDS,
  fellBackLine,
  inEffectLine,
  kelModelInEffect,
  kelStaffRanking,
  kelScopingThreshold,
  kelSetScopingThreshold,
  kelStaffResetRole,
  kelStaffRoles,
  kelStaffSetRole,
  orderRoles,
  reasoningLabel,
  type KelModelView,
  type RankingClass,
  type RankingView,
  type ScopingThresholdView,
  type StaffListing,
  type StaffMode,
  type StaffModelOption,
  type StaffRoleChoice,
  type StaffRoleModelOption,
  type StaffRoleRow,
} from '@renderer/components/kel/staffModels/staffModelsApi';
import SettingsPageWrapper from '../components/SettingsPageWrapper';
import SettingsAdvanced from '../components/SettingsAdvanced';
import './staffModels.css';

const MODES: StaffMode[] = ['AUTOMATIC', 'PREFERRED', 'FIXED'];
const REVIEW_ROLES = new Set(['verifier', 'oracle', 'sentinel']);

const modelLabel = (listing: StaffListing, id: string | null | undefined): string =>
  (id && (listing.models.find((model) => model.id === id)?.label ?? id)) || 'Kel chooses';

/** What happens when the chosen model cannot run here, from the engine's own rules (D-67, D-69). */
const consequence = (row: StaffRoleRow): string => {
  if (row.mode === 'FIXED') return 'Work for this role waits until it can run. Pick another model, or switch to Preferred.';
  if (REVIEW_ROLES.has(row.role)) return 'Kel hands the check to another available model and says so on the work card.';
  const fallbacks = row.fallbacks?.filter(Boolean) ?? [];
  if (fallbacks.length > 0) return `Kel falls back to ${fallbacks.join(', then ')} and says so on the work card.`;
  return 'Kel uses its usual choice instead and says so on the work card.';
};

const defaultSentence = (listing: StaffListing, row: StaffRoleRow): string | null => {
  const base = row.default;
  if (!base) return null;
  if (base.mode === 'AUTOMATIC') return 'Default: Automatic';
  return `Default: ${MODE_LABELS[base.mode] ?? base.mode} · ${modelLabel(listing, base.model)}`;
};

/**
 * LIVE-3: the models this role can pick — the engine's per-role options (each available or not for
 * this role, with why) when it sends them, else the shared catalog.
 */
const roleOptions = (listing: StaffListing, row: StaffRoleRow): StaffRoleModelOption[] =>
  row.model_options?.length ? row.model_options : listing.models;

/** A model for Preferred/Fixed when the row has none yet: the role's default, else one that can run. */
const pickModel = (listing: StaffListing, row: StaffRoleRow): string | null => {
  if (row.model) return row.model;
  const options = roleOptions(listing, row);
  const perRole = Boolean(row.model_options?.length);
  const fallback = row.default?.model ?? null;
  // Per role, a default this role can't use is passed over for one it can.
  if (fallback && (!perRole || options.find((model) => model.id === fallback)?.available !== false)) return fallback;
  return options.find((model) => model.available !== false)?.id ?? fallback ?? options[0]?.id ?? null;
};

const reasoningOptionsFor = (listing: StaffListing, row: StaffRoleRow): string[] => {
  if (row.mode === 'AUTOMATIC' || !row.model) return ['auto'];
  const fromRow = row.reasoning_options?.length ? row.reasoning_options : null;
  const fromModel = listing.models.find((model) => model.id === row.model)?.reasoning_options;
  return fromRow ?? (fromModel?.length ? fromModel : ['auto']);
};

/**
 * "DeepSeek Flash (can't change code, so it can't do the Builder's code work)" for a model this role
 * can't use (the engine's per-role reason); "(unavailable)" in the shared catalog of an older engine.
 */
const optionText = (model: StaffModelOption | StaffRoleModelOption, perRole: boolean): string => {
  if (model.available !== false) return model.label;
  if (!perRole) return `${model.label} (unavailable)`;
  const note = String(model.note ?? '').trim().replace(/[.\s]+$/, '');
  const why = note.toLowerCase().startsWith(model.label.toLowerCase()) ? note.slice(model.label.length).trim() : note;
  return `${model.label} (${why || 'unavailable'})`;
};

/** D-78 §10.15: the fallback note arrives while Nick watches; it is a resting state, so it settles in. */
const FallbackNote: React.FC<{ role: string; text: string }> = ({ role, text }) => {
  const ref = useRef<HTMLParagraphElement>(null);
  const arrived = useArrival();
  useEntrance(ref, arrived, { settle: true });
  return (
    <p ref={ref} className='kel-staff-row__last' data-testid={`staff-last-${role}`}>
      {text}
    </p>
  );
};

/** The rows below a note that arrives FLIP down to make room (snappy). */
const StaffRowsFlip: React.FC<{ flipKey: string; children: React.ReactNode }> = ({ flipKey, children }) => {
  const ref = useRef<HTMLDivElement>(null);
  useFlip(ref, flipKey, { selector: ':scope > .kel-staff-row' });
  return (
    <div ref={ref} className='kel-staff-models__rows'>
      {children}
    </div>
  );
};

function StaffRow({
  row,
  listing,
  busy,
  error,
  onChange,
  onReset,
}: {
  row: StaffRoleRow;
  listing: StaffListing;
  busy: boolean;
  error: string | null;
  onChange: (choice: StaffRoleChoice) => void;
  onReset: () => void;
}) {
  const automatic = row.mode === 'AUTOMATIC';
  const reasoningOptions = reasoningOptionsFor(listing, row);
  const unavailable = !automatic && row.model && row.available === false;
  const description = STAFF_DESCRIPTIONS[row.role];
  const options = roleOptions(listing, row);
  const perRole = Boolean(row.model_options?.length);
  const purpose = row.purpose ? PURPOSE_WORDS[row.purpose] ?? null : null;
  const fallbackDefault = defaultSentence(listing, row);
  const fellBack = fellBackLine(row.last_run);

  const changeMode = (mode: StaffMode) => {
    if (mode === row.mode) return;
    if (mode === 'AUTOMATIC') {
      onChange({ mode, reasoning: 'auto' });
      return;
    }
    const model = pickModel(listing, row);
    const options = listing.models.find((entry) => entry.id === model)?.reasoning_options ?? ['auto'];
    onChange({ mode, model, reasoning: options.includes(row.reasoning) ? row.reasoning : 'auto' });
  };

  const changeModel = (model: string) => {
    const options = listing.models.find((entry) => entry.id === model)?.reasoning_options ?? ['auto'];
    onChange({ mode: row.mode, model, reasoning: options.includes(row.reasoning) ? row.reasoning : 'auto' });
  };

  return (
    <div className='kel-staff-row' data-role={row.role} data-testid={`staff-row-${row.role}`} aria-busy={busy || undefined}>
      <div className='kel-staff-row__main'>
        <div className='kel-staff-row__name'>
          <strong>{row.label}</strong>
          {description && <span>{description}</span>}
          {purpose ? (
            <span className='kel-staff-row__purpose' data-testid={`staff-purpose-${row.role}`} data-purpose={row.purpose}>
              {purpose}
            </span>
          ) : null}
        </div>
        <div className='kel-staff-row__controls'>
          <label className='kel-staff-row__field'>
            <span>Mode</span>
            <select
              className='kel-select'
              aria-label={`${row.label}: mode`}
              title={MODE_HINTS[row.mode]}
              value={row.mode}
              disabled={busy}
              onChange={(event) => changeMode(event.target.value as StaffMode)}
            >
              {MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {MODE_LABELS[mode]}
                </option>
              ))}
            </select>
          </label>
          <label className='kel-staff-row__field kel-staff-row__field--model'>
            <span>Model</span>
            <select
              className='kel-select'
              aria-label={`${row.label}: model`}
              value={automatic ? '' : (row.model ?? '')}
              disabled={busy || automatic}
              onChange={(event) => changeModel(event.target.value)}
            >
              {automatic && <option value=''>Kel chooses</option>}
              {!automatic && row.model && !options.some((model) => model.id === row.model) && (
                <option value={row.model}>{row.model_label ?? row.model}</option>
              )}
              {/* LIVE-3: a model the engine says this role can't use can't be picked (the current one stays shown). */}
              {!automatic && options.map((model) => (
                <option
                  key={model.id}
                  value={model.id}
                  disabled={perRole && model.available === false && model.id !== row.model}
                  title={model.note ?? undefined}
                >
                  {optionText(model, perRole)}
                </option>
              ))}
            </select>
          </label>
          <label className='kel-staff-row__field'>
            <span>Reasoning</span>
            <select
              className='kel-select'
              aria-label={`${row.label}: reasoning`}
              value={reasoningOptions.includes(row.reasoning) ? row.reasoning : 'auto'}
              disabled={busy || reasoningOptions.length < 2}
              title={reasoningOptions.length < 2 ? "This model's own default level" : undefined}
              onChange={(event) => onChange({ mode: row.mode, model: row.model, reasoning: event.target.value })}
            >
              {reasoningOptions.map((level) => (
                <option key={level} value={level}>
                  {reasoningLabel(level)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <div className='kel-staff-row__foot'>
        {automatic ? (
          <span className='kel-staff-row__state' data-tone='ok'>Kel chooses</span>
        ) : unavailable ? (
          <span className='kel-staff-row__state' data-tone='wait'>Can't run here</span>
        ) : (
          <span className='kel-staff-row__state' data-tone='ok'>Available</span>
        )}
        {!automatic && unavailable ? (
          <span className='kel-staff-row__detail' data-testid={`staff-note-${row.role}`}>
            {`${(row.note ?? `${modelLabel(listing, row.model)} can't run on this computer`).replace(/[.\s]+$/, '')}. ${consequence(row)}`}
          </span>
        ) : null}
        <span className='kel-grow' />
        {row.is_default === false ? (
          <>
            {fallbackDefault && <span className='kel-staff-row__default'>{fallbackDefault}</span>}
            <KelButton variant='quiet' disabled={busy} ariaLabel={`Reset ${row.label} to default`} onClick={onReset}>
              Reset to default
            </KelButton>
          </>
        ) : (
          <span className='kel-staff-row__default'>Default</span>
        )}
      </div>
      {fellBack && <FallbackNote role={row.role} text={fellBack} />}
      {error && (
        <p className='kel-staff-row__error' role='alert'>
          {error}
        </p>
      )}
    </div>
  );
}

/** One kind of work in "How Kel picks models": who governs it, how much model it gets, the order. */
function RankingRow({ entry }: { entry: RankingClass }) {
  const runnable = entry.models.filter((model) => model.runnable).sort((a, b) => a.rank - b.rank);
  const blocked = entry.models.length - runnable.length;
  const first = runnable[0];
  const order = runnable.slice(0, 3).map((model) => model.label);
  return (
    <tr data-testid={`ranking-row-${entry.task_class}`}>
      <th scope='row'>{entry.label}</th>
      <td>{`${entry.role_label} · ${MODE_LABELS[entry.mode] ?? entry.mode_label ?? entry.mode}`}</td>
      <td>{TIER_WORDS[entry.tier] ?? entry.tier_label ?? entry.tier}</td>
      <td>
        {order.length ? (
          <>
            <span className='kel-staff-ranking__order'>{order.join(', then ')}</span>
            {first?.why ? <span className='kel-staff-ranking__why'>{`${first.label}: ${first.why}.`}</span> : null}
          </>
        ) : (
          <span className='kel-staff-ranking__why'>Nothing can run this here yet.</span>
        )}
        {blocked > 0 ? (
          <span className='kel-staff-ranking__why'>{`${blocked} other model${blocked === 1 ? '' : 's'} can't run here.`}</span>
        ) : null}
      </td>
    </tr>
  );
}

/**
 * Read-only "How Kel picks models" (Routing 2 §5.8): per kind of work, the Settings row that governs
 * it, how much model it gets, and the order Kel would try models in, with the reason for the first.
 */
export function RankingCard() {
  const [view, setView] = useState<RankingView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    kelStaffRanking()
      .then((next) => {
        if (alive) setView(next);
      })
      .catch((reason: unknown) => {
        if (alive) setError(`Kel couldn't read how it picks models. ${failureSentence(reason, 'Try again in a moment.')}`);
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <KelCard title='How Kel picks models'>
      {error ? (
        <p className='kel-staff-row__error' role='alert'>
          {error}
        </p>
      ) : !view ? (
        <KelLoading rows={3} />
      ) : (
        <div className='kel-staff-ranking__scroll'>
          <table className='kel-staff-ranking' data-testid='staff-ranking'>
            <thead>
              <tr>
                <th scope='col'>Work</th>
                <th scope='col'>Decided by</th>
                <th scope='col'>Effort</th>
                <th scope='col'>Kel tries</th>
              </tr>
            </thead>
            <tbody>
              {view.classes.map((entry) => (
                <RankingRow key={entry.task_class} entry={entry} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </KelCard>
  );
}

/**
 * When Kel asks its "before I start" questions (D-70 item 4): the engine's one scoping setting, in
 * plain words. The default is "Always for bigger work" (a Builder + Verifier pod or larger).
 */
export function ScopingThresholdCard() {
  const [view, setView] = useState<ScopingThresholdView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    kelScopingThreshold()
      .then((next) => {
        if (alive) setView(next);
      })
      .catch((reason: unknown) => {
        if (alive) setError(`Kel couldn't read this setting. ${failureSentence(reason, 'Try again in a moment.')}`);
      });
    return () => {
      alive = false;
    };
  }, []);

  const change = async (value: string) => {
    setBusy(true);
    setError(null);
    try {
      setView(await kelSetScopingThreshold(value));
    } catch (reason) {
      setError(`Kel couldn't save that, so nothing changed. ${failureSentence(reason, 'Try again in a moment.')}`);
    } finally {
      setBusy(false);
    }
  };

  const current = view?.options.find((option) => option.id === view.threshold) ?? null;
  return (
    <KelCard title='Questions before big work'>
      <div className='kel-staff-row kel-staff-row--setting' data-testid='scoping-threshold'>
        <div className='kel-staff-row__main'>
          <div className='kel-staff-row__name'>
            <strong>When Kel asks first</strong>
          </div>
          <div className='kel-staff-row__controls'>
            <label className='kel-staff-row__field kel-staff-row__field--model'>
              <span>Ask first</span>
              <select
                className='kel-select'
                aria-label='When Kel asks questions before it starts'
                value={view?.threshold ?? ''}
                disabled={!view || busy}
                onChange={(event) => void change(event.target.value)}
                data-testid='scoping-threshold-select'
              >
                {!view ? <option value=''>Reading…</option> : null}
                {(view?.options ?? []).map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <div className='kel-staff-row__foot'>
          <span className='kel-staff-row__detail' data-testid='scoping-threshold-hint'>
            {current?.hint ?? ''}
          </span>
        </div>
        {error && (
          <p className='kel-staff-row__error' role='alert'>
            {error}
          </p>
        )}
      </div>
    </KelCard>
  );
}

/**
 * FN-06: which model is in effect, said plainly. Opened from a chat (`?conversation=` — the engine's
 * id, e.g. from a needs-you card's "Change the model in Staff & models"), it names that chat's own
 * model when it has one; otherwise Kel's model, which every chat uses unless it picks its own.
 */
const useInEffect = (listing: StaffListing | null): { line: string | null; forChat: boolean } => {
  const { search } = useLocation();
  const conversation = new URLSearchParams(search).get('conversation');
  const [chatView, setChatView] = useState<KelModelView | null>(null);
  useEffect(() => {
    let alive = true;
    setChatView(null);
    if (!conversation) return;
    kelModelInEffect(conversation)
      .then((view) => {
        if (alive) setChatView(view);
      })
      .catch((): void => undefined);
    return () => {
      alive = false;
    };
    // Kel's model may have just changed on this page: read the chat's view again with the listing.
  }, [conversation, listing]);
  if (conversation && chatView) return { line: inEffectLine(chatView, true), forChat: true };
  return { line: inEffectLine(listing?.kel_model, false), forChat: false };
};

const StaffModelsSettings: React.FC = () => {
  const [listing, setListing] = useState<StaffListing | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      setListing(await kelStaffRoles());
      setLoadError(null);
    } catch (error) {
      setLoadError(error);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const write = useCallback(async (row: StaffRoleRow, run: () => Promise<StaffListing>, what: string) => {
    setBusy(row.role);
    setErrors((current) => {
      const next = { ...current };
      delete next[row.role];
      return next;
    });
    try {
      setListing(await run());
    } catch (error) {
      const sentence = failureSentence(error, 'Kel did not answer. Try again in a moment.');
      setErrors((current) => ({
        ...current,
        [row.role]: `Kel couldn't ${what} for ${row.label}, so nothing changed. ${sentence}`,
      }));
    } finally {
      setBusy(null);
    }
  }, []);

  const rows = listing ? orderRoles(listing.roles) : [];
  const inEffect = useInEffect(listing);

  return (
    <SettingsPageWrapper contentClassName='max-w-920px'>
      <div className='kel-staff-models flex flex-col gap-12px'>
        {loadError ? (
          <KelFailureCard error={loadError} onRetry={() => void load()} />
        ) : !listing ? (
          <KelCard title='Staff'>
            <KelLoading rows={4} />
          </KelCard>
        ) : (
          <KelCard title='Staff'>
            {inEffect.line && inEffect.forChat ? (
              <p className='kel-staff-models__in-effect' data-testid='staff-kel-in-effect' data-for-chat={inEffect.forChat || undefined}>
                {inEffect.line}
              </p>
            ) : null}
            {rows.length === 0 ? (
              <p className='kel-staff-models__note'>Kel did not list any staff roles. Try again in a moment.</p>
            ) : (
              <div className='kel-staff-models__rows'>
                {rows.map((row) => (
                  <div className='kel-staff-summary' key={row.role} data-testid={`staff-summary-${row.role}`}>
                    <strong>{row.label}</strong>
                    <span>{row.mode === 'AUTOMATIC' ? 'Kel chooses' : modelLabel(listing, row.model)}</span>
                    {row.mode !== 'AUTOMATIC' && row.available === false && <span className='kel-staff-summary__unavailable'>Not available</span>}
                  </div>
                ))}
              </div>
            )}
          </KelCard>
        )}
        {listing && !loadError ? (
          <SettingsAdvanced testId='staff-advanced'>
            <KelCard title='Staff choices'>
              <StaffRowsFlip flipKey={rows.map((row) => `${row.role}${fellBackLine(row.last_run) ? '!' : ''}`).join('|')}>
                {rows.map((row) => (
                  <StaffRow
                    key={row.role}
                    row={row}
                    listing={listing}
                    busy={busy === row.role}
                    error={errors[row.role] ?? null}
                    onChange={(choice) => void write(row, () => kelStaffSetRole(row.role, choice), 'save that change')}
                    onReset={() => void write(row, () => kelStaffResetRole(row.role), 'reset the model')}
                  />
                ))}
              </StaffRowsFlip>
            </KelCard>
            <ScopingThresholdCard />
            <RankingCard />
          </SettingsAdvanced>
        ) : null}
      </div>
    </SettingsPageWrapper>
  );
};

export default StaffModelsSettings;
