// Dedup-aware asar packer that reproduces the shipped archive's layout:
// content-addressed deduplication + per-file SHA256 integrity (4MB blocks),
// using @electron/asar's own Pickle and getFileIntegrity implementations.
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const { Readable } = require('stream');

function resolveAsar() {
  try { return require('path').dirname(require.resolve('@electron/asar/package.json')); } catch (e) {}
  if (process.env.ASAR_MODULE) return process.env.ASAR_MODULE;
  const local = require('path').join(__dirname, '..', 'desktop', 'node_modules', '@electron', 'asar');
  if (require('fs').existsSync(local)) return local;
  console.error('asar tools: @electron/asar not found. Run bun install in desktop/ or set ASAR_MODULE.');
  process.exit(2);
}
const ASAR = resolveAsar();
const { Pickle } = require(ASAR + '/lib/pickle');
const { getFileIntegrity } = require(ASAR + '/lib/integrity');

const src = path.resolve(process.argv[2]);
const dest = path.resolve(process.argv[3]);

function walk(dir, relPrefix) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const name = entry.name;
    const full = path.join(dir, name);
    const rel = relPrefix ? relPrefix + '/' + name : name;
    const st = fs.lstatSync(full);
    if (st.isDirectory()) {
      out.push({ kind: 'dir', rel });
      out.push(...walk(full, rel));
    } else if (st.isSymbolicLink()) {
      throw new Error('unexpected symlink: ' + full);
    } else {
      out.push({ kind: 'file', rel, full, size: st.size });
    }
  }
  return out;
}

function insert(node, rel, entry) {
  const parts = rel.split('/');
  let cur = node;
  for (let i = 0; i < parts.length - 1; i++) {
    const p = parts[i];
    if (!cur.files[p]) cur.files[p] = { files: {} };
    cur = cur.files[p];
  }
  const leaf = parts[parts.length - 1];
  if (entry.kind === 'file') {
    cur.files[leaf] = { size: entry.rec.size, offset: String(entry.rec.offset), integrity: entry.rec.integrity };
  } else {
    cur.files[leaf] = { files: {} };
  }
}

(async () => {
  const all = walk(src, '');
  const header = { files: {} };
  const dedup = new Map();
  const dataBufs = [];
  let dataLen = 0;

  const files = all.filter((e) => e.kind === 'file');
  for (const e of files) {
    const buf = fs.readFileSync(e.full);
    const key = crypto.createHash('sha256').update(buf).digest('hex');
    let rec = dedup.get(key);
    if (!rec) {
      const integrity = await getFileIntegrity(Readable.from([buf]));
      rec = { offset: dataLen, size: buf.length, integrity };
      dedup.set(key, rec);
      dataBufs.push(buf);
      dataLen += buf.length;
    }
    e.rec = rec;
  }

  for (const e of all) insert(header, e.rel, e);

  const headerJson = JSON.stringify(header);
  const hp = Pickle.createEmpty();
  hp.writeString(headerJson);
  const headerBuf = hp.toBuffer();
  const sp = Pickle.createEmpty();
  sp.writeUInt32(headerBuf.length);
  const sizeBuf = sp.toBuffer();

  const out = fs.createWriteStream(dest);
  out.write(sizeBuf);
  out.write(headerBuf);
  for (const b of dataBufs) out.write(b);
  out.end();
  await new Promise((res, rej) => { out.on('finish', res); out.on('error', rej); });

  const total = fs.statSync(dest).size;
  const saved = files.reduce((a, e) => a + e.rec.size, 0) - dataLen;
  console.log(JSON.stringify({ files: files.length, unique: dedup.size, dataLen, savedBytes: saved, totalBytes: total }));
})();
