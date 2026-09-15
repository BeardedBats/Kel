// Renders design-direction mockups (HTML) to PNG and audits them in-page.
// Usage: node render-directions.cjs <outDir> <file1.html> [file2.html ...]
// Requires Playwright: PLAYWRIGHT_MODULE env, or `playwright` resolvable;
// browsers live under PLAYWRIGHT_BROWSERS_PATH.
//
// Output per file: <name>-1440.png (full page), <name>-1280.png (viewport),
// plus directions-audit.json with per-file contrast/typography/keyboard data.
const path = require('path');
const fs = require('fs');

let playwright;
try {
  playwright = require('playwright');
} catch (error) {
  playwright = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
}
const { chromium } = playwright;

const outDir = path.resolve(process.argv[2] || '.');
const files = process.argv.slice(3).map((f) => path.resolve(f));
fs.mkdirSync(outDir, { recursive: true });

// Shared in-page audit: WCAG contrast of visible text, font sizes, palette, emoji, focusables.
const AUDIT = () => {
  const parse = (c) => {
    const m = String(c).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map((s) => parseFloat(s));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const lum = ({ r, g, b }) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const ratio = (a, b) => {
    const L1 = lum(a); const L2 = lum(b);
    return Math.round(((Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05)) * 100) / 100;
  };
  const bgOf = (el) => {
    let n = el;
    while (n && n !== document.documentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.6) return c;
      n = n.parentElement;
    }
    return { r: 255, g: 255, b: 255, a: 1 };
  };
  const samples = []; const sizes = {}; const palette = { text: {}, bg: {} }; const seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    if (samples.length >= 260) break;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.5) continue;
    const hasDirectText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (!hasDirectText) continue;
    const text = el.textContent.replace(/\s+/g, ' ').trim().slice(0, 60);
    if (!text || seen.has(text)) continue;
    seen.add(text);
    const fg = parse(cs.color); const bg = bgOf(el);
    if (!fg) continue;
    const size = Math.round(parseFloat(cs.fontSize) * 10) / 10;
    sizes[size] = (sizes[size] || 0) + 1;
    const rgb = (c) => `rgb(${Math.round(c.r)},${Math.round(c.g)},${Math.round(c.b)})`;
    palette.text[rgb(fg)] = (palette.text[rgb(fg)] || 0) + 1;
    palette.bg[rgb(bg)] = (palette.bg[rgb(bg)] || 0) + 1;
    const large = size >= 24 || (size >= 18.66 && parseInt(cs.fontWeight, 10) >= 700);
    samples.push({ text, size, fg: rgb(fg), bg: rgb(bg), ratio: ratio(fg, bg), need: large ? 3 : 4.5 });
  }
  const focusables = [...document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')]
    .filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  const top = (obj, n) => Object.entries(obj).sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => ({ value: k, count: v }));
  const failures = samples.filter((s) => s.ratio < s.need);
  return {
    textSamples: samples.length,
    contrastFailureCount: failures.length,
    contrastFailures: failures.slice(0, 20),
    fontSizeHistogram: Object.fromEntries(Object.entries(sizes).sort((a, b) => Number(a[0]) - Number(b[0]))),
    smallestText: Math.min(...Object.keys(sizes).map(Number)),
    largestText: Math.max(...Object.keys(sizes).map(Number)),
    paletteText: top(palette.text, 8),
    paletteBg: top(palette.bg, 8),
    emojiCharacters: (document.body.innerText.match(/\p{Extended_Pictographic}/gu) || []).length,
    focusableCount: focusables.length,
    focusableSample: focusables.slice(0, 10).map((e) => `${e.tagName}${e.getAttribute('aria-label') ? '[' + e.getAttribute('aria-label') + ']' : ''}: ${(e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 40)}`),
  };
};

(async () => {
  const browser = await chromium.launch();
  const results = [];
  for (const file of files) {
    const name = path.basename(file).replace(/\.html$/, '');
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    await page.goto('file:///' + file.replace(/\\/g, '/'));
    await page.waitForTimeout(400);
    const audit = await page.evaluate(AUDIT);
    // Focus-ring assertion (independent-review requirement): the first tab stop must be the skip
    // link, and every subsequent stop must show a computed focus ring (outline or box-shadow).
    const stops = [];
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(80);
      stops.push(await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return { tag: 'BODY' };
        const cs = getComputedStyle(el);
        const ring = (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0)
          || (cs.boxShadow && cs.boxShadow !== 'none');
        return {
          tag: el.tagName,
          text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 40),
          outline: `${cs.outlineStyle} ${cs.outlineWidth}`,
          ring: Boolean(ring),
        };
      }));
    }
    const focusRingFailures = stops.filter((s) => s.tag !== 'BODY' && !s.ring).length;
    const firstStopIsSkipLink = /skip to main content/i.test(String((stops[0] || {}).text || ''));
    await page.screenshot({ path: path.join(outDir, `${name}-1440.png`), fullPage: true });
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, `${name}-1280.png`) });
    results.push({ name, file: path.basename(file), audit, focus: { stops, focusRingFailures, firstStopIsSkipLink } });
    await page.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(outDir, 'directions-audit.json'), JSON.stringify({ schema: 1, renderedAt: new Date().toISOString(), results }, null, 2));
  console.log(JSON.stringify(results.map((r) => ({
    name: r.name,
    contrastFailures: r.audit.contrastFailureCount,
    smallestText: r.audit.smallestText,
    focusable: r.audit.focusableCount,
    focusRingFailures: r.focus.focusRingFailures,
    firstStopIsSkipLink: r.focus.firstStopIsSkipLink,
    emoji: r.audit.emojiCharacters,
  })), null, 2));
  const focusOk = results.every((r) => r.focus.focusRingFailures === 0 && r.focus.firstStopIsSkipLink);
  if (!focusOk) {
    console.error('FOCUS-ASSERTION-FAILED: a focusable element lacks a visible ring, or the first tab stop is not the skip link.');
    process.exitCode = 1;
  }
})().catch((err) => {
  console.error('RENDER-FAILED', String(err).slice(0, 500));
  process.exit(1);
});
