// Extract an app.asar into a directory (use to prepare the stage tree for repacking).
// Usage: node extract-asar.js <app.asar> <out-dir>
const path = require('path');
function resolveAsar() {
  try { return require('path').dirname(require.resolve('@electron/asar/package.json')); } catch (e) {}
  if (process.env.ASAR_MODULE) return process.env.ASAR_MODULE;
  const local = require('path').join(__dirname, '..', 'desktop', 'node_modules', '@electron', 'asar');
  if (require('fs').existsSync(local)) return local;
  console.error('asar tools: @electron/asar not found. Run bun install in desktop/ or set ASAR_MODULE.');
  process.exit(2);
}
const asar = require(resolveAsar());
const src = path.resolve(process.argv[2]);
const dest = path.resolve(process.argv[3]);
asar.extractAll(src, dest);
console.log('extracted', src, '->', dest);
