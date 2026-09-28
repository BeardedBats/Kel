/**
 * FN-11: the New chat composer offers the active project's Recipes in its slash menu (as an open
 * chat does) and a `/<recipe> …` line starts the recipe instead of a chat.
 */
import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import { startRecipeFromLine, useRecipeSlashCommands } from '@renderer/components/kel/recipeSlash';

const request = vi.fn(async (route: string, body?: Record<string, unknown>) => {
  if (route === '/api/project') return { projects: [{ id: 'default', name: 'General', root: null, kind: 'general' }], active: 'default' };
  if (route === '/api/recipes' && body?.action === 'list') {
    return { entries: [{ recipe_id: 'r.fix', name: 'Fix a bug', description: 'Reproduce and fix a bug.' }] };
  }
  return {};
});

beforeEach(() => {
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
  resetProjectsForTests();
});
afterEach(() => {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('New chat recipes', () => {
  it('lists recipes next to the built-in commands without shadowing them', async () => {
    const { result } = renderHook(() => useRecipeSlashCommands(new Set(['open'])));
    await waitFor(() => expect(result.current.commands.map((command) => command.name)).toEqual(['fix-a-bug']));
    expect(result.current.commands[0]).toMatchObject({ source: 'recipe', hint: 'Recipe', selectionBehavior: 'insert' });
  });

  it('a recipe line starts the recipe; any other line is sent as a message', async () => {
    const notify = { success: vi.fn(), warning: vi.fn(), error: vi.fn() };
    const setInput = vi.fn();
    const run = vi.fn(async () => ({ kind: 'started' as const, text: 'Started “Fix a bug” in General.' }));
    const entry = { slug: 'fix-a-bug', recipeId: 'r.fix', name: 'Fix a bug', description: '' };
    const slash = { match: (line: string) => (line.startsWith('/fix-a-bug') ? { entry, rest: line.slice(11).trim() } : null), run };
    expect(startRecipeFromLine('hello there', slash, setInput, notify)).toBe(false);
    expect(run).not.toHaveBeenCalled();
    expect(startRecipeFromLine('/fix-a-bug login fails', slash, setInput, notify)).toBe(true);
    expect(setInput).toHaveBeenCalledWith('');
    await waitFor(() => expect(notify.success).toHaveBeenCalledWith('Started “Fix a bug” in General.'));
    expect(run).toHaveBeenCalledWith(entry, 'login fails');
  });

  it('puts the line back when the recipe needs more', async () => {
    const notify = { success: vi.fn(), warning: vi.fn(), error: vi.fn() };
    const setInput = vi.fn();
    const entry = { slug: 'fix-a-bug', recipeId: 'r.fix', name: 'Fix a bug', description: '' };
    const slash = { match: () => ({ entry, rest: '' }), run: vi.fn(async () => ({ kind: 'needs' as const, text: 'needs more' })) };
    startRecipeFromLine('/fix-a-bug', slash, setInput, notify);
    await waitFor(() => expect(notify.warning).toHaveBeenCalledWith('needs more'));
    expect(setInput).toHaveBeenLastCalledWith('/fix-a-bug');
  });
});
