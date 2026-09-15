// Builds side-by-side before/after comparison sheets from capture runs that share the harness view ids.
//
// Usage: node make-comparisons.cjs <outDir> <baselineDir> <baselineTag> <finalDir> <finalTag> [<finalDir> <finalTag> ...]
// Example: node make-comparisons.cjs docs/v1.4/screenshots/comparisons \
//            docs/v1.4/screenshots/baseline v13-fixture docs/v1.4/screenshots/g8 g8
//
// Output: <outDir>/<view-id>.png (baseline | final) + index.json listing pairs, sizes and gaps.
const fs = require('fs');
const path = require('path');
const os = require('os');

let playwright;
try {
  playwright = require('playwright');
} catch (error) {
  playwright = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
}
const { chromium } = playwright;

const outDir = path.resolve(process.argv[2] || 'comparisons');
const baselineDir = path.resolve(process.argv[3] || '');
const baselineTag = process.argv[4] || '';
const finals = [];
for (let i = 5; i + 1 < process.argv.length; i += 2) {
  finals.push({ dir: path.resolve(process.argv[i]), tag: process.argv[i + 1] });
}
fs.mkdirSync(outDir, { recursive: true });

function index(dir, tag) {
  const map = new Map();
  for (const file of fs.readdirSync(dir)) {
    if (!file.endsWith('.png')) continue;
    if (tag && !file.startsWith(`${tag}-`)) continue;
    const stripped = tag ? file.slice(tag.length + 1).replace(/\.png$/, '') : file.replace(/\.png$/, '');
    // Both capture generations prefix a run index ("02-01-boot-chat"), so the shared key is the view id
    // after that index. Route views ("12-diagnostics") carry no index and keep their own name.
    const segments = stripped.split('-');
    const view = segments.length > 2 ? segments.slice(1).join('-') : stripped;
    map.set(view, path.join(dir, file));
  }
  return map;
}

function escapeAttr(value) {
  return String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;');
}

(async () => {
  const baseline = index(baselineDir, baselineTag);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const pairs = [];
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-compare-'));

  for (const final of finals) {
    const candidates = index(final.dir, final.tag);
    for (const [view, finalPath] of candidates) {
      if (!baseline.has(view)) continue;
      const before = baseline.get(view);
      const html = `<!doctype html><html><head><meta charset="utf-8"><style>
        :root { color-scheme: light; }
        body { margin: 0; font: 14px/1.4 "Segoe UI", system-ui, sans-serif; background: #ffffff; }
        .sheet { display: flex; gap: 12px; padding: 12px; align-items: flex-start; }
        figure { margin: 0; flex: 0 0 auto; }
        figcaption { margin: 6px 0 0; font-size: 12px; color: #5c6470; }
        img { display: block; border: 1px solid #e5e7eb; border-radius: 8px; max-width: 780px; height: auto; }
        h1 { font-size: 16px; margin: 12px 12px 0; color: #14161a; }
      </style></head><body>
        <h1>${escapeAttr(view)}</h1>
        <div class="sheet">
          <figure><img src="file:///${escapeAttr(before.replace(/\\/g, '/'))}" alt="before"><figcaption>V1.3 baseline · ${escapeAttr(path.basename(before))}</figcaption></figure>
          <figure><img src="file:///${escapeAttr(finalPath.replace(/\\/g, '/'))}" alt="after"><figcaption>V1.4 · ${escapeAttr(path.basename(finalPath))}</figcaption></figure>
        </div>
      </body></html>`;
      const htmlPath = path.join(scratch, `${view}.html`);
      fs.writeFileSync(htmlPath, html, 'utf8');
      await page.goto(`file:///${htmlPath.replace(/\\/g, '/')}`);
      await page.waitForTimeout(250);
      const target = path.join(outDir, `${view}.png`);
      await page.screenshot({ path: target, fullPage: true });
      const beforeBytes = fs.statSync(before).size;
      const afterBytes = fs.statSync(finalPath).size;
      pairs.push({
        view,
        final: `${final.tag}`,
        baseline: path.relative(path.resolve(outDir, '..', '..'), before),
        final_file: path.relative(path.resolve(outDir, '..', '..'), finalPath),
        comparison: path.basename(target),
        baseline_bytes: beforeBytes,
        final_bytes: afterBytes,
        byte_delta: afterBytes - beforeBytes,
      });
    }
  }

  await browser.close();
  fs.rmSync(scratch, { recursive: true, force: true });
  fs.writeFileSync(path.join(outDir, 'index.json'), JSON.stringify({ schema: 1, pairs }, null, 2));
  console.log(JSON.stringify({ pairs: pairs.length, outDir, views: pairs.map((p) => p.view) }, null, 2));
})().catch((error) => {
  console.error('COMPARE-FAILED', String(error).slice(0, 500));
  process.exit(1);
});
