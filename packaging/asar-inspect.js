function resolveAsar() {
  try { return require('path').dirname(require.resolve('@electron/asar/package.json')); } catch (e) {}
  if (process.env.ASAR_MODULE) return process.env.ASAR_MODULE;
  const local = require('path').join(__dirname, '..', 'desktop', 'node_modules', '@electron', 'asar');
  if (require('fs').existsSync(local)) return local;
  console.error('asar tools: @electron/asar not found. Run bun install in desktop/ or set ASAR_MODULE.');
  process.exit(2);
}
const asar = require(resolveAsar());
const fs = require('fs');

const target = process.argv[2];
const baseline = process.argv[3];
// Usage: node asar-inspect.js <candidate.asar> [baseline.asar]

function stats(p) {
  const raw = asar.getRawHeader(p);
  const files = [];
  const walk = (node, prefix) => {
    for (const [name, entry] of Object.entries(node.files || {})) {
      const full = prefix + '/' + name;
      if (entry.files) walk(entry, full);
      else files.push({ full, size: entry.size || 0, offset: entry.offset, unpacked: !!entry.unpacked });
    }
  };
  walk(raw.header, '');
  let sumSizes = 0, maxEnd = 0;
  const byOffset = new Map();
  for (const f of files) {
    sumSizes += f.size;
    const off = Number(f.offset) || 0;
    const end = off + f.size;
    if (end > maxEnd) maxEnd = end;
    if (!f.unpacked) {
      const key = f.offset + ':' + f.size;
      byOffset.set(key, (byOffset.get(key) || 0) + 1);
    }
  }
  let dedupGroups = 0, dedupBytesSaved = 0;
  for (const [k, n] of byOffset) {
    if (n > 1) { dedupGroups++; const size = Number(k.split(':')[1]); dedupBytesSaved += size * (n - 1); }
  }
  return { path: p, fileBytes: fs.statSync(p).size, files: files.length, sumSizes, maxEnd, unpacked: files.filter(f=>f.unpacked).length, dedupGroups, dedupBytesSaved };
}

console.log(JSON.stringify(stats(target), null, 2));
if (baseline) console.log(JSON.stringify(stats(baseline), null, 2));
