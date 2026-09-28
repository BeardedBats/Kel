/**
 * The end-to-end and packaged check scripts (desktop/tests/e2e, packaging/*.cjs) drive the app by
 * route. When a page is retired (the Work page, D-70; the Desktop Pet, D-56; the donor cron UI,
 * D-57) a script still pointing at it keeps "passing" against a redirect. This pins every route a
 * script names to a route the renderer's router really has, and keeps retired routes out except
 * where a script checks the retirement itself.
 */
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const DESKTOP = path.resolve(__dirname, '../..');
const REPO = path.resolve(DESKTOP, '..');
const ROUTER = path.join(DESKTOP, 'packages/desktop/src/renderer/components/layout/Router.tsx');

/** Routes that only redirect away from a retired page. */
const RETIRED = new Set(['/work', '/settings/pet']);
/** Scripts that name a retired route on purpose, to prove it redirects. */
const RETIREMENT_CHECKS: Record<string, string[]> = {
  'kel-shell.e2e.ts': ['/work'],
  'verify-installed-battery.cjs': ['/settings/pet'],
};
/** The first segments the app routes; anything else (API paths, file paths) is not a page route. */
const PAGE_ROOTS = /^\/(guid|work|settings|projects|scheduled|activity|team|transcription|providers|autonomy|diagnostics|onboarding|dogfood|connections|assistants|login|cron|tasks)(\/|$)/;

const routerPatterns = (): RegExp[] => {
  const source = fs.readFileSync(ROUTER, 'utf8');
  return [...source.matchAll(/path='([^']+)'/g)]
    .map((match) => match[1])
    .filter((route) => route !== '*')
    .map((route) => new RegExp('^' + route.replace(/:[^/]+/g, '[^/]+').replace(/\/\*$/, '(/.*)?') + '$'));
};

const scripts = (): string[] => [
  ...fs.readdirSync(path.join(DESKTOP, 'tests/e2e')).filter((name) => name.endsWith('.e2e.ts')).map((name) => path.join(DESKTOP, 'tests/e2e', name)),
  ...fs.readdirSync(path.join(REPO, 'packaging')).filter((name) => /\.(cjs|js)$/.test(name)).map((name) => path.join(REPO, 'packaging', name)),
];

/** Whole string literals that are a page route ('/activity', '#/settings/about', `/scheduled`). */
const routesIn = (source: string): string[] =>
  [...source.matchAll(/(['"`])#?(\/[a-z][a-z0-9/_:-]*)\1/gi)]
    .map((match) => match[2].replace(/\/$/, ''))
    .filter((route) => PAGE_ROOTS.test(route));

describe('packaged and e2e scripts target routes the app has', () => {
  const patterns = routerPatterns();
  const files = scripts();

  it('finds the router and the scripts', () => {
    expect(patterns.length).toBeGreaterThan(20);
    expect(files.some((file) => file.endsWith('verify-installed-battery.cjs'))).toBe(true);
    expect(files.some((file) => file.endsWith('kel-shell.e2e.ts'))).toBe(true);
  });

  it('names only routes the router serves, and retired ones only to check the retirement', () => {
    const problems: string[] = [];
    let checked = 0;
    for (const file of files) {
      const name = path.basename(file);
      for (const route of new Set(routesIn(fs.readFileSync(file, 'utf8')))) {
        checked += 1;
        if (!patterns.some((pattern) => pattern.test(route))) problems.push(`${name}: ${route} is not a route`);
        else if (RETIRED.has(route) && !(RETIREMENT_CHECKS[name] ?? []).includes(route)) problems.push(`${name}: ${route} is retired`);
      }
    }
    expect(problems).toEqual([]);
    expect(checked).toBeGreaterThan(40);
  });

  it('no script drives the retired donor cron API', () => {
    const offenders = files.filter((file) => /\/api\/cron\b/.test(fs.readFileSync(file, 'utf8'))).map((file) => path.basename(file));
    expect(offenders).toEqual([]);
  });
});
