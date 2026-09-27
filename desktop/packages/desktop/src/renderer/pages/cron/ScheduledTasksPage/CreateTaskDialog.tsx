/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 *
 * D-57: create or edit a scheduled task in the engine. Kel is the only assistant; the model list
 * is Kel's own (`/api/model`), with options Kel cannot use shown but not pickable. The engine
 * describes the timing and checks the whole task; its refusal is shown in its own words.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Form, Input, Select, Message, TimePicker, Radio, Button, Switch } from '@arco-design/web-react';
import taskChevron from '@renderer/assets/figma/task/chevron-down.svg';
import AionModal from '@renderer/components/base/AionModal';
import { Down } from '@icon-park/react';
import dayjs from 'dayjs';
import {
  kelRecipeGet,
  kelRecipes,
  kelSchedules,
  type KelModelChoice,
  type KelRecipeInput,
  type KelSchedule,
  type KelScheduleCadence,
  type KelScheduleDraft,
  type KelScheduleStartMode,
} from '@renderer/components/kel/kelApi';
import { unavailableNote, useKelModelState } from '@renderer/components/kel/KelModelControl';
import { ALL_PROJECTS, GENERAL_PROJECT_ID, liveProjects, projectLabel, useProjects } from '@renderer/components/kel/activeProject';
import {
  FREQUENCY_LABELS,
  HOUR_INTERVALS,
  MINUTE_INTERVALS,
  WEEKDAYS,
  cadenceFromFrequency,
  createDefaultCustomSchedule,
  describeCadence,
  formatNextRun,
  frequencyFromCadence,
  type CustomFrequencyMode,
  type CustomIntervalUnit,
  type CustomScheduleState,
  type FrequencyType,
} from '@renderer/pages/cron/cronUtils';
import { scheduleActions } from '@renderer/pages/cron/useSchedules';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';

const FormItem = Form.Item;
const TextArea = Input.TextArea;
const Option = Select.Option;

interface CreateTaskDialogProps {
  visible: boolean;
  onClose: () => void;
  /** When provided, the dialog edits this schedule. */
  editSchedule?: KelSchedule;
  /** The app chat a new task may keep running in ("Ongoing conversation"). */
  conversation_id?: string;
}

const MONTH_DAYS = Array.from({ length: 31 }, (_, index) => index + 1);
const AUTOMATIC = '';
const modelValue = (choice: KelModelChoice | null | undefined) =>
  choice?.provider ? `${choice.provider}::${choice.model ?? ''}` : AUTOMATIC;
const modelChoice = (value: string): KelModelChoice | null => {
  if (!value) return null;
  const [provider, model] = value.split('::');
  return { provider, model: model || null };
};

type RecipeEntry = { recipe_id: string; name: string };

const CreateTaskDialog: React.FC<CreateTaskDialogProps> = ({ visible, onClose, editSchedule, conversation_id }) => {
  const isMobile = Boolean(useLayoutContext()?.isMobile);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const { projects, active } = useProjects();
  const { state: modelState } = useKelModelState();
  const [frequency, setFrequency] = useState<FrequencyType>('manual');
  const [time, setTime] = useState('09:00');
  const [weekday, setWeekday] = useState('MON');
  const [customSchedule, setCustomSchedule] = useState<CustomScheduleState>(createDefaultCustomSchedule);
  const [startMode, setStartMode] = useState<KelScheduleStartMode>('new_conversation');
  const [skipIfRunning, setSkipIfRunning] = useState(true);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [model, setModel] = useState<string>(AUTOMATIC);
  const [projectId, setProjectId] = useState<string>(GENERAL_PROJECT_ID);
  const [useRecipe, setUseRecipe] = useState(false);
  const [recipeId, setRecipeId] = useState<string | undefined>(undefined);
  const [recipeInputs, setRecipeInputs] = useState<Record<string, unknown>>({});
  const [recipes, setRecipes] = useState<RecipeEntry[] | null>(null);
  const [recipeFields, setRecipeFields] = useState<KelRecipeInput[]>([]);
  const [existingConversation, setExistingConversation] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ text: string; tone: 'ok' | 'error' } | null>(null);
  const isEditMode = Boolean(editSchedule);
  // A new task follows this computer's zone (null); an edited one keeps the zone it has.
  const timezone = editSchedule ? (editSchedule.timezone ?? null) : null;

  // Reset whenever the dialog opens.
  useEffect(() => {
    if (!visible) return;
    if (editSchedule) {
      const picked = frequencyFromCadence(editSchedule.cadence);
      setFrequency(picked.frequency);
      setTime(picked.time);
      setWeekday(picked.weekday);
      setCustomSchedule(picked.custom);
      setStartMode(editSchedule.start_mode);
      setSkipIfRunning(editSchedule.skip_if_running);
      setModel(modelValue(editSchedule.model));
      setProjectId(editSchedule.project_id || GENERAL_PROJECT_ID);
      const recipe = editSchedule.target?.kind === 'recipe' ? editSchedule.target : null;
      setUseRecipe(Boolean(recipe));
      setRecipeId(recipe?.recipe_id);
      setRecipeInputs(recipe?.inputs ?? {});
      setAdvancedOpen(Boolean(recipe) || editSchedule.project_id !== GENERAL_PROJECT_ID);
      setExistingConversation(editSchedule.conversation_id ?? null);
      form.setFieldsValue({
        name: editSchedule.name,
        prompt: editSchedule.target?.kind === 'instruction' ? editSchedule.target.text : '',
      });
    } else {
      form.resetFields();
      setFrequency('manual');
      setTime('09:00');
      setWeekday('MON');
      setCustomSchedule(createDefaultCustomSchedule());
      setStartMode('new_conversation');
      setSkipIfRunning(true);
      setModel(AUTOMATIC);
      setProjectId(active && active !== ALL_PROJECTS ? active : GENERAL_PROJECT_ID);
      setUseRecipe(false);
      setRecipeId(undefined);
      setRecipeInputs({});
      setAdvancedOpen(false);
      setExistingConversation(null);
    }
    setPreview(null);
    // `active` is read once per opening on purpose: switching projects must not reset a draft.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, editSchedule, form]);

  // A task made from a chat may keep running in that chat's engine conversation.
  useEffect(() => {
    if (!visible || editSchedule || !conversation_id) return;
    let alive = true;
    window.kelAPI
      ?.conversation(conversation_id)
      .then((cid) => {
        if (alive && typeof cid === 'string') setExistingConversation(cid);
      })
      .catch((): undefined => undefined);
    return () => {
      alive = false;
    };
  }, [visible, editSchedule, conversation_id]);

  // Recipes of the chosen project (only read once the person asks for one).
  useEffect(() => {
    if (!visible || !useRecipe) return;
    let alive = true;
    setRecipes(null);
    kelRecipes({ project: projectId })
      .then((answer) => {
        if (!alive) return;
        const entries = Array.isArray((answer as { entries?: unknown }).entries) ? ((answer as { entries: unknown[] }).entries) : [];
        setRecipes(
          entries
            .map((entry) => entry as { recipe_id?: unknown; name?: unknown })
            .filter((entry) => typeof entry.recipe_id === 'string')
            .map((entry) => ({ recipe_id: entry.recipe_id as string, name: typeof entry.name === 'string' ? entry.name : (entry.recipe_id as string) }))
        );
      })
      .catch(() => alive && setRecipes([]));
    return () => {
      alive = false;
    };
  }, [visible, useRecipe, projectId]);

  useEffect(() => {
    setRecipeFields([]);
    if (!visible || !useRecipe || !recipeId) return;
    let alive = true;
    kelRecipeGet(recipeId, { project: projectId })
      .then((answer) => {
        if (alive) setRecipeFields(Array.isArray(answer?.recipe?.inputs) ? answer.recipe.inputs : []);
      })
      .catch((): undefined => undefined);
    return () => {
      alive = false;
    };
  }, [visible, useRecipe, recipeId, projectId]);

  const cadence: KelScheduleCadence = useMemo(
    () => cadenceFromFrequency(frequency, time, weekday, customSchedule),
    [frequency, time, weekday, customSchedule]
  );

  // Live preview: the engine's own sentence and the next run, or why it would refuse the timing.
  useEffect(() => {
    if (!visible) return;
    if (cadence.kind === 'manual') {
      setPreview({ text: 'Runs only when you choose Run now.', tone: 'ok' });
      return;
    }
    if (cadence.kind === 'cron' && !cadence.expr) {
      setPreview(null);
      return;
    }
    let alive = true;
    const timer = setTimeout(() => {
      kelSchedules
        .preview(cadence, timezone)
        .then((answer) => {
          if (!alive) return;
          if (answer?.valid === false) {
            setPreview({ text: answer.message?.trim() || 'Kel cannot use this timing.', tone: 'error' });
            return;
          }
          const next = Array.isArray(answer?.next) ? answer.next[0] : undefined;
          const sentence = (answer?.description?.trim() || describeCadence(cadence)).replace(/\.$/, '');
          setPreview({ text: next ? `${sentence}. Next: ${formatNextRun(next)}` : sentence, tone: 'ok' });
        })
        .catch((error: unknown) => {
          if (alive) setPreview({ text: String((error as Error)?.message || 'Kel cannot use this timing.'), tone: 'error' });
        });
    }, 250);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [visible, cadence, timezone]);

  const modelOptions = useMemo(
    () =>
      (modelState?.providers ?? []).flatMap((provider) =>
        provider.options.map((option) => ({
          value: `${provider.id}::${option.id}`,
          label: option.label,
          note: unavailableNote(option, provider),
        }))
      ),
    [modelState]
  );
  // A saved model Kel no longer offers stays visible (as unavailable) rather than vanishing.
  const unknownSavedModel = model && !modelOptions.some((option) => option.value === model) ? model : null;

  const projectOptions = useMemo(() => {
    const live = liveProjects(projects);
    return live.some((project) => project.id === projectId) || !projectId
      ? live
      : [...live, { id: projectId, name: editSchedule?.project_name || 'Project unavailable' }];
  }, [projects, projectId, editSchedule?.project_name]);

  const handleFrequencyChange = (value: FrequencyType) => {
    setFrequency(value);
    if (value !== 'custom') setCustomSchedule(createDefaultCustomSchedule());
  };

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validate();
      if (useRecipe && !recipeId) {
        Message.error('Choose a recipe to run, or switch back to instructions.');
        return;
      }
      if (startMode === 'existing' && !existingConversation) {
        Message.error('There is no conversation to keep adding to. Choose “New conversation”.');
        return;
      }
      setSubmitting(true);
      const draft: KelScheduleDraft = {
        name: String(values.name ?? '').trim(),
        project_id: projectId,
        target: useRecipe
          ? { kind: 'recipe', recipe_id: recipeId!, inputs: recipeInputs }
          : { kind: 'instruction', text: String(values.prompt ?? '').trim() },
        cadence,
        timezone,
        start_mode: startMode,
        conversation_id: startMode === 'existing' ? existingConversation : null,
        model: modelChoice(model),
        skip_if_running: skipIfRunning,
      };
      if (editSchedule) {
        await scheduleActions.update(editSchedule.id, draft);
        Message.success('Saved.');
      } else {
        await scheduleActions.create(draft);
        Message.success('Scheduled task created.');
      }
      onClose();
    } catch (error) {
      // Form validation errors are shown on the fields; an engine refusal is shown as it said it.
      const text = String((error as Error)?.message || '').trim();
      if (text && !(error && typeof error === 'object' && 'errors' in (error as object))) Message.error(text);
    } finally {
      setSubmitting(false);
    }
  }, [form, useRecipe, recipeId, recipeInputs, startMode, existingConversation, projectId, cadence, timezone, model, skipIfRunning, editSchedule, onClose]);

  const showTimePicker = frequency === 'daily' || frequency === 'weekdays' || frequency === 'weekly';
  const hasExistingConversation = Boolean(existingConversation);
  const setCustomTime = (_value: string, picked?: dayjs.Dayjs) => {
    if (picked) setCustomSchedule((current) => ({ ...current, time: picked.format('HH:mm') }));
  };

  const modelSelect = (
    <Select
      data-testid='scheduled-task-model-select'
      value={model}
      onChange={(value: string) => setModel(value)}
      arrowIcon={!isMobile ? <img src={taskChevron} alt='' /> : undefined}
      aria-label='Model'
    >
      <Option value={AUTOMATIC}>Automatic</Option>
      {modelOptions.map((option) => (
        <Option key={option.value} value={option.value} disabled={Boolean(option.note)}>
          <span title={option.note ?? undefined}>{option.label}{option.note ? ` — ${option.note}` : ''}</span>
        </Option>
      ))}
      {unknownSavedModel && <Option value={unknownSavedModel} disabled>{`${unknownSavedModel.split('::')[1] || unknownSavedModel} — not available`}</Option>}
    </Select>
  );

  return (
    <AionModal
      variant='standard'
      header={{ title: isEditMode ? 'Edit scheduled task' : 'New scheduled task', showClose: true }}
      visible={visible}
      onCancel={onClose}
      onOk={() => void handleSubmit()}
      confirmLoading={submitting}
      okText={isEditMode ? 'Save' : 'Create task'}
      cancelText='Cancel'
      className='kel-shell-task-modal w-[min(600px,calc(100vw-32px))] max-w-600px'
      unmountOnExit
    >
      <div>
        <Form form={form} layout='vertical' className='kel-shell-task-form'>
          <FormItem className='kel-shell-task-name' label='Name' field='name' rules={[{ required: true, message: 'Give the task a name' }]}>
            <Input placeholder='Morning brief' />
          </FormItem>

          <FormItem className='kel-shell-task-assistant' label='Assistant'>
            <Select data-testid='cron-assistant-select' value='kel' disabled arrowIcon={!isMobile ? <img src={taskChevron} alt='' /> : undefined}>
              <Option value='kel'>Kel</Option>
            </Select>
          </FormItem>

          <FormItem label='Each run starts' className='kel-shell-task-execution'>
            <Radio.Group value={startMode} onChange={(value) => setStartMode(value as KelScheduleStartMode)} className='flex flex-wrap items-center gap-20px'>
              <Radio value='new_conversation' className='kel-shell-task-execution-option m-0 min-w-0 text-14px text-t-secondary cursor-pointer'>
                <span className='kel-shell-task-execution-label'>New conversation</span>
                <span className='kel-shell-task-execution-description'>A clean chat every time</span>
              </Radio>
              <Radio value='existing' disabled={!hasExistingConversation} className='kel-shell-task-execution-option m-0 min-w-0 text-14px text-t-secondary cursor-pointer'>
                <span className='kel-shell-task-execution-label'>Ongoing conversation</span>
                <span className='kel-shell-task-execution-description'>{hasExistingConversation ? 'Adds to the same chat' : 'Start the task from a chat to use this'}</span>
              </Radio>
            </Radio.Group>
          </FormItem>

          {useRecipe ? (
            <div className='kel-shell-task-prompt kel-shell-task-recipe-summary'>
              <p className='kel-meta'>Each run follows the recipe chosen under Advanced settings.</p>
            </div>
          ) : (
            <FormItem className='kel-shell-task-prompt' label='Instructions' field='prompt' rules={[{ required: true, message: 'Instructions are required' }]}>
              <TextArea placeholder='Summarize yesterday’s activity and anything waiting on me.' autoSize={{ minRows: 3, maxRows: 8 }} />
            </FormItem>
          )}

          <FormItem label='Frequency' className='kel-shell-task-frequency'>
            <Select className='kel-shell-task-frequency-select' data-testid='cron-frequency-select' value={frequency} onChange={handleFrequencyChange}>
              {(Object.keys(FREQUENCY_LABELS) as FrequencyType[]).map((value) => <Option key={value} value={value}>{FREQUENCY_LABELS[value]}</Option>)}
            </Select>
            <Radio.Group className='kel-shell-task-frequency-options kel-desktop-only' value={frequency} onChange={(value) => handleFrequencyChange(value as FrequencyType)}>
              {(Object.keys(FREQUENCY_LABELS) as FrequencyType[]).map((value) => <Radio key={value} value={value}>{FREQUENCY_LABELS[value]}</Radio>)}
            </Radio.Group>
          </FormItem>

          {frequency === 'custom' && (
            <div className='kel-shell-task-custom mb-16px rounded-12px border border-solid border-[var(--color-border-2)] p-14px'>
              <FormItem label='Repeat'>
                <Select data-testid='custom-frequency-mode' value={customSchedule.mode}
                  onChange={(mode: CustomFrequencyMode) => setCustomSchedule((current) => ({ ...current, mode }))}>
                  <Option value='interval'>Every few minutes or hours</Option>
                  <Option value='daily'>Daily</Option>
                  <Option value='weekly'>On chosen days</Option>
                  <Option value='monthly'>Monthly</Option>
                  <Option value='advanced'>Advanced (cron)</Option>
                </Select>
              </FormItem>
              {customSchedule.mode === 'interval' && (
                <div className='flex items-end gap-12px'>
                  <FormItem label='Every' className='mb-0 flex-1'>
                    <Select data-testid='custom-interval-value' value={customSchedule.interval}
                      onChange={(interval: number) => setCustomSchedule((current) => ({ ...current, interval }))}>
                      {(customSchedule.intervalUnit === 'minutes' ? MINUTE_INTERVALS : HOUR_INTERVALS).map((value) => <Option key={value} value={value}>{value}</Option>)}
                    </Select>
                  </FormItem>
                  <FormItem label='Unit' className='mb-0 flex-1'>
                    <Select data-testid='custom-interval-unit' value={customSchedule.intervalUnit}
                      onChange={(intervalUnit: CustomIntervalUnit) => setCustomSchedule((current) => ({ ...current, intervalUnit, interval: intervalUnit === 'minutes' ? 30 : 1 }))}>
                      <Option value='minutes'>Minutes</Option>
                      <Option value='hours'>Hours</Option>
                    </Select>
                  </FormItem>
                </div>
              )}
              {customSchedule.mode === 'weekly' && (
                <FormItem label='Days'>
                  <Select mode='multiple' value={customSchedule.weekdays}
                    onChange={(weekdays: string[]) => weekdays.length > 0 && setCustomSchedule((current) => ({ ...current, weekdays }))}>
                    {WEEKDAYS.map((day) => <Option key={day.value} value={day.value}>{day.label}</Option>)}
                  </Select>
                </FormItem>
              )}
              {customSchedule.mode === 'monthly' && (
                <FormItem label='Day of the month'>
                  <Select value={customSchedule.monthDay} onChange={(monthDay: number) => setCustomSchedule((current) => ({ ...current, monthDay }))}>
                    {MONTH_DAYS.map((value) => <Option key={value} value={value}>{value}</Option>)}
                  </Select>
                </FormItem>
              )}
              {(customSchedule.mode === 'daily' || customSchedule.mode === 'weekly' || customSchedule.mode === 'monthly') && (
                <FormItem label='Time' className='mb-0'>
                  <TimePicker format='HH:mm' value={dayjs(`2000-01-01 ${customSchedule.time}`)} onChange={setCustomTime} allowClear={false} className='w-full' />
                </FormItem>
              )}
              {customSchedule.mode === 'advanced' && (
                <FormItem label='Cron expression' className='mb-0'>
                  <Input data-testid='custom-cron-expression' placeholder='0 9 * * MON-FRI' value={customSchedule.advancedExpression}
                    onChange={(advancedExpression) => setCustomSchedule((current) => ({ ...current, advancedExpression }))} />
                </FormItem>
              )}
            </div>
          )}

          {showTimePicker && (
            <div className='kel-shell-task-time flex items-center gap-12px mb-16px'>
              <TimePicker value={dayjs(`2000-01-01 ${time}`)} onChange={(_value, picked) => picked && setTime(picked.format('HH:mm'))}
                allowClear={false} className='w-120px' format={!isMobile ? 'h:mm A' : 'HH:mm'}
                icons={!isMobile ? { inputSuffix: <img src={taskChevron} alt='' /> } : undefined} />
            </div>
          )}

          <div className='kel-shell-task-model' data-testid='scheduled-task-model-field'>
            <label className='block'>Model</label>
            {modelSelect}
          </div>

          {frequency === 'weekly' && (
            <div className='kel-shell-task-weekday mb-16px'>
              <Select value={weekday} onChange={setWeekday} aria-label='Day'>
                {WEEKDAYS.map((d) => <Option key={d.value} value={d.value}>{d.label}</Option>)}
              </Select>
            </div>
          )}

          {preview && (
            <p className='kel-shell-task-preview' data-testid='scheduled-task-preview' data-tone={preview.tone} role='status'>{preview.text}</p>
          )}

          <div className='kel-shell-task-queue mb-20px flex items-start justify-between gap-16px rounded-12px border border-solid border-[var(--color-border-2)] px-14px py-12px'>
            <div className='min-w-0'>
              <p className='m-0 text-14px font-medium text-t-primary'>Skip if still running</p>
              <p className='mb-0 mt-4px text-12px leading-18px text-t-secondary'>Skip a run if the last one is still going.</p>
            </div>
            <Switch checked={skipIfRunning} onChange={setSkipIfRunning} aria-label='Skip if still running' />
          </div>

          <div className='kel-shell-task-advanced mt-16px'>
            <Button type='text' onClick={() => setAdvancedOpen((open) => !open)} className='!h-auto !p-0 hover:!bg-transparent' aria-expanded={advancedOpen}>
              <span className='flex items-center gap-6px text-14px font-medium text-t-primary'>
                <Down size='14' fill='currentColor' className={`shrink-0 transition-transform ${advancedOpen ? 'rotate-180' : ''}`} />
                <span>Advanced settings</span>
              </span>
            </Button>
            {advancedOpen && (
              <div className='mt-12px grid gap-x-16px gap-y-16px md:grid-cols-2' data-testid='scheduled-task-advanced'>
                <div className='min-w-0'>
                  <label className='mb-8px block text-14px font-medium text-t-primary'>Project</label>
                  <Select value={projectId} aria-label='Project' onChange={(value: string) => { setProjectId(value); setRecipeId(undefined); setRecipeInputs({}); }}>
                    {projectOptions.map((project) => (
                      <Option key={project.id} value={project.id}>{'archived' in project ? projectLabel(project) : project.name}</Option>
                    ))}
                  </Select>
                </div>
                <div className='min-w-0 flex items-center justify-between gap-12px'>
                  <span className='text-14px font-medium text-t-primary'>Run a recipe instead</span>
                  <Switch checked={useRecipe} onChange={setUseRecipe} aria-label='Run a recipe instead' />
                </div>
                {useRecipe && (
                  <div className='min-w-0 md:col-span-2'>
                    <label className='mb-8px block text-14px font-medium text-t-primary'>Recipe</label>
                    <Select value={recipeId} placeholder={recipes === null ? 'Loading recipes…' : recipes.length === 0 ? 'This project has no recipes yet' : 'Choose a recipe'}
                      disabled={!recipes || recipes.length === 0} aria-label='Recipe'
                      onChange={(value: string) => { setRecipeId(value); setRecipeInputs({}); }}>
                      {(recipes ?? []).map((recipe) => <Option key={recipe.recipe_id} value={recipe.recipe_id}>{recipe.name}</Option>)}
                    </Select>
                  </div>
                )}
                {useRecipe && recipeFields.map((field) => (
                  <div className='min-w-0' key={field.name}>
                    <label className='mb-8px block text-14px font-medium text-t-primary'>{field.description || field.name}{field.required ? '' : ' (optional)'}</label>
                    {field.type === 'bool' ? (
                      <Switch checked={Boolean(recipeInputs[field.name] ?? field.default)} aria-label={field.name}
                        onChange={(checked) => setRecipeInputs((current) => ({ ...current, [field.name]: checked }))} />
                    ) : field.type === 'choice' ? (
                      <Select value={(recipeInputs[field.name] as string | undefined) ?? (field.default as string | undefined)} aria-label={field.name}
                        onChange={(value: string) => setRecipeInputs((current) => ({ ...current, [field.name]: value }))}>
                        {(field.choices ?? []).map((choice) => <Option key={choice} value={choice}>{choice}</Option>)}
                      </Select>
                    ) : (
                      <Input value={String(recipeInputs[field.name] ?? field.default ?? '')} aria-label={field.name} maxLength={field.max_chars}
                        onChange={(value) => setRecipeInputs((current) => ({ ...current, [field.name]: value }))} />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Form>
      </div>
    </AionModal>
  );
};

export default CreateTaskDialog;
