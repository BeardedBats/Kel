import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

// D-54: a project is the one context boundary, so no Kel surface calls anything a "Workspace". The
// chat's file panel is "Files"; the switcher, pickers and pages say "Project(s)". This guards the
// visible words only — code names such as `workspacePath` or CSS classes are not labels.
const RENDERER = join(__dirname, '../../packages/desktop/src/renderer');
const ROOTS = ['components/kel', 'pages/kel', 'pages/guid', 'pages/conversation/components/ChatLayout'];

const sources = (dir: string): string[] =>
  readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.(ts|tsx)$/.test(name) ? [path] : [];
  });

/** Drop comments so doc comments may still explain what a variable holds. */
const withoutComments = (source: string) =>
  source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"`])\/\/.*$/gm, '$1');

/** A capitalised "Workspace(s)" inside a string literal or JSX text is a label someone reads. */
const LABEL = /(['"`])[^'"`\n]*\bWorkspaces?\b[^'"`\n]*\1|>[^<>{}\n]*\bWorkspaces?\b[^<>{}\n]*</g;

describe('no user-facing "Workspace" label (D-54)', () => {
  const files = ROOTS.flatMap((root) => sources(join(RENDERER, root)));

  it('scans the Kel surfaces', () => {
    expect(files.length).toBeGreaterThan(20);
  });

  it.each(files.map((file) => [relative(RENDERER, file), file]))('%s', (_name, file) => {
    const found = withoutComments(readFileSync(file, 'utf8')).match(LABEL) ?? [];
    expect(found).toEqual([]);
  });

  it('the Home composer strings (en-US guid.json) say project, not workspace', () => {
    const values: string[] = [];
    const walk = (value: unknown) => {
      if (typeof value === 'string') values.push(value);
      else if (value && typeof value === 'object') Object.values(value).forEach(walk);
    };
    walk(JSON.parse(readFileSync(join(RENDERER, 'services/i18n/locales/en-US/guid.json'), 'utf8')));
    expect(values.filter((value) => /workspace/i.test(value))).toEqual([]);
    expect(values).toContain('General');
  });
});
