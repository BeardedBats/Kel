#!/usr/bin/env node
/**
 * Audit tool — app.asar comparison for the V1.6 human-visual delta re-audit.
 * Extracts two app.asar archives and reports a precise recursive difference summary:
 * file-count, files only in one side, and byte-differing common files (with sizes).
 *
 * Usage:
 *   ASAR_MODULE=<path-to-@electron/asar> node asar-compare.cjs <asarA> <destA> <asarB> <destB> <reportFile>
 */
'use strict';
const fs = require('fs');
const path = require('path');
const asar = require(process.env.ASAR_MODULE || '@electron/asar');

const [a, destA, b, destB, report] = process.argv.slice(2);
if (!a || !destA || !b || !destB || !report) {
  console.error('usage: asar-compare.cjs <asarA> <destA> <asarB> <destB> <reportFile>');
  process.exit(2);
}

fs.rmSync(destA, { recursive: true, force: true });
fs.rmSync(destB, { recursive: true, force: true });
const extract = (archive, dest) => {
  if (typeof asar.extractAll === 'function') return asar.extractAll(archive, dest);
  if (typeof asar.extract === 'function') return asar.extract(archive, dest);
  if (asar.default && typeof asar.default.extractAll === 'function') return asar.default.extractAll(archive, dest);
  throw new Error('no extract API on @electron/asar; keys=' + Object.keys(asar).slice(0, 24).join(','));
};
extract(a, destA);
extract(b, destB);

function walk(root) {
  const out = [];
  (function rec(d) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) rec(p);
      else out.push(path.relative(root, p));
    }
  })(root);
  return out.sort();
}

const la = walk(destA);
const lb = walk(destB);
const setA = new Set(la);
const setB = new Set(lb);
const onlyA = la.filter((x) => !setB.has(x));
const onlyB = lb.filter((x) => !setA.has(x));
const common = la.filter((x) => setB.has(x));
const differing = [];
for (const rel of common) {
  const pa = fs.readFileSync(path.join(destA, rel));
  const pb = fs.readFileSync(path.join(destB, rel));
  if (pa.length !== pb.length || !pa.equals(pb)) {
    differing.push({ rel: rel.split(path.sep).join('/'), sizeA: pa.length, sizeB: pb.length });
  }
}

const lines = [];
lines.push(`fileCountA=${la.length}`);
lines.push(`fileCountB=${lb.length}`);
lines.push(`onlyA=${JSON.stringify(onlyA.map((x) => x.split(path.sep).join('/')).slice(0, 80))}`);
lines.push(`onlyB=${JSON.stringify(onlyB.map((x) => x.split(path.sep).join('/')).slice(0, 80))}`);
lines.push(`differingCommonFiles=${differing.length}`);
for (const d of differing.slice(0, 200)) lines.push(`  DIFF ${d.rel} (A=${d.sizeA} B=${d.sizeB})`);
fs.writeFileSync(report, lines.join('\n') + '\n');
console.log(lines.slice(0, 5).join('\n'));
console.log('differing:', differing.length);
