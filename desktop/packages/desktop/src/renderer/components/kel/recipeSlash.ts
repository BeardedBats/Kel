/**
 * CH-7 — Recipes in the composer's slash menu.
 *
 * Typing `/` lists the active project's Recipes next to the built-in commands, each with the
 * recipe's own plain description. Picking one inserts `/<recipe> ` so the person can say what it is
 * for; sending that line runs the recipe in the active project (General when "All projects" is
 * shown) through the engine's normal preview → run path — it never goes to the model as chat text.
 * The first required text input takes what was typed after the command.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { SlashCommandItem } from '@/common/chat/slash/types';
import {
  kelRecipeGet,
  kelRecipePreview,
  kelRecipeRun,
  kelRecipes,
  type KelRecipeEntry,
  type KelRecipeInput,
  type KelScope,
} from './kelApi';
import { ALL_PROJECTS, GENERAL_PROJECT_ID, GENERAL_PROJECT_NAME, projectLabel, useProjects } from './activeProject';

export type RecipeSlashEntry = { slug: string; recipeId: string; name: string; description: string };

/** `Fix a bug` → `fix-a-bug`. */
export const recipeSlug = (name: string): string =>
  name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

export const buildRecipeSlashEntries = (entries: KelRecipeEntry[], taken: ReadonlySet<string> = new Set()): RecipeSlashEntry[] => {
  const seen = new Set(taken);
  const out: RecipeSlashEntry[] = [];
  for (const entry of entries) {
    const recipeId = String(entry.recipe_id ?? entry.id ?? '');
    const name = String(entry.name ?? entry.title ?? recipeId);
    const slug = recipeSlug(name) || recipeSlug(recipeId);
    if (!recipeId || !slug || seen.has(slug)) continue;
    seen.add(slug);
    const description = String((entry as { description?: unknown }).description ?? '').trim();
    out.push({ slug, recipeId, name, description });
  }
  return out;
};

/** The slash line, when it names one of the recipes: `{ entry, rest }`. */
export const matchRecipeSlash = (
  input: string,
  entries: readonly RecipeSlashEntry[]
): { entry: RecipeSlashEntry; rest: string } | null => {
  const match = /^\/([a-z0-9-]+)(?:\s+([\s\S]*))?$/i.exec(input.trim());
  if (!match) return null;
  const entry = entries.find((item) => item.slug === match[1].toLowerCase());
  return entry ? { entry, rest: (match[2] ?? '').trim() } : null;
};

/** Values for a run: the typed text fills the first required text input; defaults fill the rest. */
export const recipeRunValues = (
  inputs: readonly KelRecipeInput[],
  rest: string
): { values: Record<string, string | boolean>; missing: KelRecipeInput[] } => {
  const values: Record<string, string | boolean> = {};
  for (const input of inputs) {
    if (input.default !== undefined && input.default !== '') values[input.name] = input.default;
  }
  const firstText = inputs.find((input) => (input.type === 'text' || input.type === 'path') && input.required);
  const target = firstText ?? inputs.find((input) => input.type === 'text' || input.type === 'path');
  if (rest && target) values[target.name] = rest;
  const missing = inputs.filter(
    (input) => input.required && input.type !== 'bool' && (values[input.name] === undefined || values[input.name] === '')
  );
  return { values, missing };
};

export type RecipeRunOutcome =
  | { kind: 'started'; text: string }
  | { kind: 'needs'; text: string };

export const useRecipeSlashCommands = (taken: ReadonlySet<string>) => {
  const { active, activeProject } = useProjects();
  const projectId = active === ALL_PROJECTS ? GENERAL_PROJECT_ID : active || GENERAL_PROJECT_ID;
  const projectName = active === ALL_PROJECTS || !activeProject ? GENERAL_PROJECT_NAME : projectLabel(activeProject);
  const [entries, setEntries] = useState<KelRecipeEntry[]>([]);

  useEffect(() => {
    let cancelled = false;
    kelRecipes({ project: projectId })
      .then((answer) => {
        if (!cancelled) setEntries(Array.isArray(answer?.entries) ? (answer.entries as KelRecipeEntry[]) : []);
      })
      .catch(() => {
        if (!cancelled) setEntries([]);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const recipes = useMemo(() => buildRecipeSlashEntries(entries, taken), [entries, taken]);

  const commands = useMemo<SlashCommandItem[]>(
    () =>
      recipes.map((recipe) => ({
        name: recipe.slug,
        description: recipe.description
          ? `${recipe.description} Runs in ${projectName}.`
          : `Run the “${recipe.name}” recipe in ${projectName}.`,
        kind: 'template',
        source: 'recipe',
        hint: 'Recipe',
        selectionBehavior: 'insert',
      })),
    [projectName, recipes]
  );

  const match = useCallback((input: string) => matchRecipeSlash(input, recipes), [recipes]);

  const run = useCallback(
    async (entry: RecipeSlashEntry, rest: string): Promise<RecipeRunOutcome> => {
      const scope: KelScope = { project: projectId };
      const { recipe } = await kelRecipeGet(entry.recipeId, scope);
      const { values, missing } = recipeRunValues((recipe?.inputs ?? []) as KelRecipeInput[], rest);
      if (missing.length > 0) {
        const what = missing.map((input) => input.description || input.name).join('; ');
        return { kind: 'needs', text: `“${entry.name}” needs more before it can start: ${what}. Type it after /${entry.slug}.` };
      }
      const preview = await kelRecipePreview(entry.recipeId, values, scope);
      if (preview.needs_project) {
        return {
          kind: 'needs',
          text: String(preview.message ?? `“${entry.name}” needs a folder for ${projectName}. Set one in Projects.`),
        };
      }
      await kelRecipeRun(entry.recipeId, values, scope);
      return { kind: 'started', text: `Started “${entry.name}” in ${projectName}. Follow it in Activity.` };
    },
    [projectId, projectName]
  );

  return { commands, match, run };
};
