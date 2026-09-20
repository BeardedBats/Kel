#!/usr/bin/env node
/**
 * Donor-token context scanner for the V1.6 human-visual re-audit (read-only).
 * Usage: node donor-contexts.cjs <rootDir> <maxPerToken> <token...>
 */
'use strict';
const fs = require('fs');
const path = require('path');

const [root, maxStr, ...tokens] = process.argv.slice(2);
const max = parseInt(maxStr || '12', 10);
const results = new Map(tokens.map((t) => [t, []]));
const totals = new Map(tokens.map((t) => [t, 0]));

function scan(f) {
  let s;
  try {
    s = fs.readFileSync(f, 'utf8');
  } catch (e) {
    return;
  }
  for (const t of tokens) {
    let idx = s.indexOf(t);
    while (idx !== -1) {
      totals.set(t, totals.get(t) + 1);
      if (results.get(t).length < max) {
        const a = Math.max(0, idx - 70);
        const b = Math.min(s.length, idx + t.length + 70);
        results.get(t).push(path.relative(root, f) + ' :: ' + s.slice(a, b).replace(/\s+/g, ' '));
      }
      idx = s.indexOf(t, idx + 1);
    }
  }
}

function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else if (/\.(js|cjs|mjs|ts|tsx|jsx|json|nsh|nsi|ps1|html|css|txt|md)$/i.test(e.name)) scan(p);
  }
}

walk(path.resolve(root));
for (const t of tokens) {
  console.log(`== ${t} : total=${totals.get(t)} (showing up to ${max}) ==`);
  for (const r of results.get(t)) console.log('  ' + r);
  console.log();
}
