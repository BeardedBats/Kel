/**
 * FN-12: write a new recipe, or rename and re-word one, on the Recipes page. A recipe is a name,
 * one line about it, and up to five steps in plain words; the engine keeps each change as a new
 * version of the recipe in this project (built-ins stay as shipped).
 */
import React, { useState } from 'react';
import { KelButton } from '@renderer/components/kel/KelPrimitives';
import type { KelRecipeStepDraft } from '@renderer/components/kel/kelApi';

export const MAX_RECIPE_STEPS = 5;

/**
 * What a step does, in words a person reads: its title unless that is only an internal id (older
 * recipes saved from work were titled "document" or "m1"), else the first sentence of what it does.
 */
export const stepLabel = (step: { id?: string; title?: string; objective?: string }): string => {
  const title = String(step.title ?? '').trim();
  const internal = !title || title === step.id || /^(m\d+|step-?\d+|document|research|coding|work)$/i.test(title);
  if (!internal) return title;
  const objective = String(step.objective ?? '').replace(/\s+/g, ' ').trim();
  const first = objective.split(/(?<=[.!?])\s/)[0].replace(/[.]$/, '');
  if (!first) return title || 'A step';
  if (first.length <= 90) return first;
  const cut = first.slice(0, 89);
  const space = cut.lastIndexOf(' ');
  return `${space > 30 ? cut.slice(0, space) : cut}…`;
};

export type RecipeEditorValue = { name: string; description: string; steps: KelRecipeStepDraft[] };

const RecipeEditor: React.FC<{
  heading: string;
  initial?: RecipeEditorValue;
  busy?: boolean;
  onSave: (value: RecipeEditorValue) => void;
  onCancel: () => void;
}> = ({ heading, initial, busy = false, onSave, onCancel }) => {
  const [name, setName] = useState(initial?.name ?? '');
  const [description, setDescription] = useState(initial?.description ?? '');
  const [steps, setSteps] = useState<KelRecipeStepDraft[]>(
    initial?.steps?.length ? initial.steps.map((step) => ({ ...step, objective: step.objective || step.title || '' })) : [{ objective: '' }]
  );
  const ready = name.trim().length > 0 && steps.every((step) => step.objective.trim().length > 0);
  const setStep = (index: number, objective: string) =>
    setSteps((current) => current.map((step, at) => (at === index ? { ...step, objective, title: undefined } : step)));
  return (
    <div className="kel-recipe-desktop-expanded kel-recipe-editor" role="group" aria-label={heading} data-testid="recipe-editor">
      <div className="kel-recipe-desktop-expanded-label">{heading}</div>
      <div className="kel-recipe-desktop-fields">
        <label>
          <span>Name</span>
          <input type="text" maxLength={80} value={name} onChange={(event) => setName(event.target.value)} aria-label="Recipe name" />
        </label>
        <label>
          <span>What it is for</span>
          <input type="text" maxLength={500} value={description} onChange={(event) => setDescription(event.target.value)}
            aria-label="What the recipe is for" />
        </label>
      </div>
      <ol className="kel-recipe-editor-steps">
        {steps.map((step, index) => (
          <li key={step.id ?? `new-${index}`}>
            <textarea rows={2} maxLength={600} value={step.objective} aria-label={`Step ${index + 1}`}
              placeholder="What Kel does in this step" onChange={(event) => setStep(index, event.target.value)} />
            {steps.length > 1 && !step.id && (
              <button type="button" className="kel-recipe-desktop-link" onClick={() => setSteps((current) => current.filter((_, at) => at !== index))}>
                Remove
              </button>
            )}
          </li>
        ))}
      </ol>
      <div className="kel-recipe-desktop-expanded-actions">
        {steps.length < MAX_RECIPE_STEPS && !initial?.steps?.some((step) => step.id) && (
          <button type="button" onClick={() => setSteps((current) => [...current, { objective: '' }])}>Add a step</button>
        )}
        <button type="button" disabled={busy} onClick={onCancel}>Cancel</button>
        <KelButton variant="primary" disabled={busy || !ready}
          onClick={() => onSave({ name: name.trim(), description: description.trim(), steps: steps.map((step) => ({ ...step, objective: step.objective.trim() })) })}>
          Save recipe
        </KelButton>
      </div>
    </div>
  );
};

export default RecipeEditor;
