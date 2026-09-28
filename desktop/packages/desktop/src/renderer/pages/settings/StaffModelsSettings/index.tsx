/**
 * Settings → Kel → Staff & models (D-70 item 3).
 *
 * One row per staff role with its mode (Automatic / Preferred / Fixed), model and reasoning level,
 * read from and written to the engine's `/api/model` roles actions (D-66 design §2). The engine owns
 * the catalog, the D-67 starting defaults and what can run on this computer; this page shows exactly
 * that, in plain words, and never claims a model can run when the engine says it cannot. Kel's own
 * chat model stays on Settings → Model and in the composer (D-69: staff always use their role model).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { KelButton, KelCard, KelLoading } from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import {
  MODE_HINTS,
  MODE_LABELS,
  STAFF_DESCRIPTIONS,
  kelStaffResetRole,
  kelStaffRoles,
  kelStaffSetRole,
  orderRoles,
  reasoningLabel,
  type StaffListing,
  type StaffMode,
  type StaffModelOption,
  type StaffRoleChoice,
  type StaffRoleRow,
} from '@renderer/components/kel/staffModels/staffModelsApi';
import SettingsPageWrapper from '../components/SettingsPageWrapper';
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

/** A model for Preferred/Fixed when the row has none yet: the role's default, else one that can run. */
const pickModel = (listing: StaffListing, row: StaffRoleRow): string | null =>
  row.model ??
  row.default?.model ??
  listing.models.find((model) => model.available !== false)?.id ??
  listing.models[0]?.id ??
  null;

const reasoningOptionsFor = (listing: StaffListing, row: StaffRoleRow): string[] => {
  if (row.mode === 'AUTOMATIC' || !row.model) return ['auto'];
  const fromRow = row.reasoning_options?.length ? row.reasoning_options : null;
  const fromModel = listing.models.find((model) => model.id === row.model)?.reasoning_options;
  return fromRow ?? (fromModel?.length ? fromModel : ['auto']);
};

const optionText = (model: StaffModelOption): string =>
  model.available === false ? `${model.label} (unavailable)` : model.label;

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
  const fallbackDefault = defaultSentence(listing, row);

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
              {!automatic && row.model && !listing.models.some((model) => model.id === row.model) && (
                <option value={row.model}>{row.model_label ?? row.model}</option>
              )}
              {!automatic && listing.models.map((model) => (
                <option key={model.id} value={model.id}>
                  {optionText(model)}
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
        <span className='kel-staff-row__detail' data-testid={`staff-note-${row.role}`}>
          {automatic
            ? MODE_HINTS.AUTOMATIC
            : unavailable
              ? `${(row.note ?? `${modelLabel(listing, row.model)} can't run on this computer`).replace(/[.\s]+$/, '')}. ${consequence(row)}`
              : MODE_HINTS[row.mode]}
        </span>
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
      {error && (
        <p className='kel-staff-row__error' role='alert'>
          {error}
        </p>
      )}
    </div>
  );
}

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
            <p className='kel-staff-models__note' data-testid='staff-defaults-note'>
              Kel hands real work to its staff, and each role runs on its own model. Every role starts on
              Kel's recommended default; change one here or reset it any time. The model you pick in a chat
              is only for Kel's own replies.
            </p>
            {rows.length === 0 ? (
              <p className='kel-staff-models__note'>Kel did not list any staff roles. Try again in a moment.</p>
            ) : (
              <div className='kel-staff-models__rows'>
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
              </div>
            )}
          </KelCard>
        )}
      </div>
    </SettingsPageWrapper>
  );
};

export default StaffModelsSettings;
