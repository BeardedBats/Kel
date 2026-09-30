// Proof required before the one permitted EBUSY packaging recovery.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { createRequire } = require('module');
const [rootArg, candidateArg, repair, installerArg] = process.argv.slice(2);
const root = path.resolve(rootArg), candidate = path.resolve(candidateArg);
const desktop = path.join(root, 'desktop'), packed = path.join(candidate, 'win-unpacked');
const resources = path.join(packed, 'resources'), archive = path.join(resources, 'app.asar');
const builder = createRequire(fs.realpathSync(path.join(desktop, 'node_modules/electron-builder/cli.js')));
const libPath = builder.resolve('app-builder-lib/package.json');
const lib = createRequire(libPath), asar = lib('@electron/asar'), resedit = lib('resedit');
const hash = b => crypto.createHash('sha256').update(Buffer.from(b)).digest('hex');
function bounded(file) {
  let current = path.resolve(file);
  if (current !== candidate && !current.startsWith(candidate + path.sep)) throw Error('Outside candidate path');
  while (current !== path.dirname(candidate)) {
    if (fs.lstatSync(current).isSymbolicLink() || fs.realpathSync(current) !== current) throw Error('Linked candidate path');
    current = path.dirname(current);
  }
}
function walk(dir) {
  const found = [];
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, item.name);
    if (item.isDirectory()) found.push(...walk(file));
    else if (item.isFile()) found.push(file);
    else throw Error('Linked candidate input');
  }
  return found;
}
function version(exe) {
  const resource = resedit.NtExecutableResource.from(exe);
  const values = resedit.Resource.VersionInfo.fromEntries(resource.entries);
  const strings = values.flatMap(v => v.getAvailableLanguages().map(lang => v.getStringValues(lang)));
  return { resource, strings };
}
(async () => {
  if (path.dirname(candidate) !== path.join(path.dirname(root), 'Temp') || fs.realpathSync(candidate) !== candidate)
    throw Error('Candidate must stay in canonical Temp');
  for (const file of [packed, resources, archive, path.join(packed, 'Kel.exe'), archive + '.unpacked']) bounded(file);
  let checked = 0;
  for (const file of walk(path.join(desktop, 'out'))) {
    const relative = path.relative(desktop, file);
    if (hash(fs.readFileSync(file)) !== hash(asar.extractFile(archive, relative))) throw Error('Candidate out differs: ' + relative);
    checked++;
  }
  if (!checked) throw Error('No built interface files to validate');
  let native = 0;
  function unpacked(node, prefix = '') {
    for (const [name, item] of Object.entries(node.files || {})) {
      const relative = path.join(prefix, name);
      if (item.files) unpacked(item, relative);
      else if (item.unpacked) {
        const file = path.join(archive + '.unpacked', relative);
        bounded(file);
        if (!fs.statSync(file).isFile() || fs.lstatSync(file).isSymbolicLink()) throw Error('Missing native unpacked file');
        if (item.integrity && hash(fs.readFileSync(file)) !== item.integrity.hash) throw Error('Native unpacked hash differs');
        if (relative.endsWith('.node')) native++;
      }
    }
  }
  unpacked(asar.getRawHeader(archive).header);
  if (!native) throw Error('Candidate has no unpacked native modules');
  const exePath = path.join(packed, 'Kel.exe');
  let exe = resedit.NtExecutable.from(fs.readFileSync(exePath));
  if (!version(exe).strings.some(s => s.ProductName === 'Kel' && s.FileDescription === 'Kel')) {
    if (repair !== '--repair-branding') throw Error('Candidate executable has no Kel branding');
    const donorPath = path.join(path.dirname(root), 'App/Kel.exe');
    if (fs.lstatSync(donorPath).isSymbolicLink()) throw Error('Linked executable donor');
    const donor = resedit.NtExecutable.from(fs.readFileSync(donorPath));
    const baseline = resedit.NtExecutable.from(fs.readFileSync(path.join(desktop, 'node_modules/electron/dist/electron.exe')));
    const code = e => e.getAllSections().find(s => s.info.name === '.text').data;
    // Exact Electron machine-code equality is stronger than an editable version string.
    if (hash(code(donor)) !== hash(code(baseline)) || hash(code(exe)) !== hash(code(baseline))) throw Error('Donor Electron runtime differs');
    if (!version(donor).strings.some(s => s.ProductName === 'Kel' && s.FileDescription === 'Kel')) throw Error('Donor has no Kel branding');
    exe = donor;
  }
  const integrity = await lib('./out/asar/integrity.js').computeData({ resourcesPath: resources,
    resourcesRelativePath: 'resources', resourcesDestinationPath: resources, extraResourceMatchers: [] });
  const resource = version(exe).resource;
  const old = resource.entries.find(e => e.type === 'INTEGRITY' && e.id === 'ELECTRONASAR');
  if (repair === '--repair-branding') {
    resource.entries = resource.entries.filter(e => !(e.type === 'INTEGRITY' && e.id === 'ELECTRONASAR'));
    resource.outputResource(exe); fs.writeFileSync(exePath, Buffer.from(exe.generate()));
    await lib('./out/electron/electronWin.js').addWinAsarIntegrity(exePath, integrity);
  } else {
    const expected = Object.entries(integrity).map(([file, value]) => ({ file: path.win32.normalize(file), alg: value.algorithm, value: value.hash }));
    if (!old || JSON.stringify(JSON.parse(Buffer.from(old.bin).toString('utf8').replace(/\0+$/, ''))) !== JSON.stringify(expected))
      throw Error('Executable ASAR integrity differs');
  }
  if (repair === '--installer') {
    const installer = path.resolve(installerArg); bounded(installer);
    if (path.dirname(installer) !== candidate || !/^Kel-Kibble-Update-.*\.exe$/.test(path.basename(installer))) throw Error('Invalid installer artifact');
    const tool = await lib('./out/toolsets/7zip.js').getPath7za();
    const proofDir = path.join(candidate, 'installer-proof-' + crypto.randomBytes(4).toString('hex'));
    fs.mkdirSync(proofDir); bounded(proofDir);
    const proof = {};
    for (const relative of ['resources/kel-engine/KelEngine.exe', 'resources/kibble-installed-update.json', 'resources/app.asar']) {
      const expected = path.join(packed, relative); bounded(expected);
      const size = fs.statSync(expected).size;
      const outputPath = path.join(proofDir, path.basename(relative));
      const fd = fs.openSync(outputPath, 'wx'); bounded(outputPath);
      const digest = crypto.createHash('sha256'); let received = 0;
      try {
        await new Promise((resolve, reject) => {
          const process = require('child_process').spawn(tool, ['x', '-so', installer, relative.replaceAll('/', path.sep)], { windowsHide: true });
          let note = '', failed = false;
          const timer = setTimeout(() => { failed = true; process.kill(); reject(Error('Installer proof timed out')); }, 5 * 60 * 1000);
          process.stdout.on('data', block => {
            if (failed) return;
            received += block.length;
            if (received > size) { failed = true; process.kill(); reject(Error('Installer payload exceeds checked size')); return; }
            try { digest.update(block); fs.writeSync(fd, block); }
            catch (error) { failed = true; process.kill(); reject(error); }
          });
          process.stderr.on('data', block => { note = (note + block.toString()).slice(-16000); });
          process.on('error', error => { clearTimeout(timer); failed = true; reject(error); });
          process.on('close', code => {
            clearTimeout(timer);
            // NSIS appends its uninstaller after the 7z data; 7za returns warning 1 for this tail.
            if (!failed && (code === 0 || code === 1)) resolve();
            else reject(Error('Installer payload extraction failed: ' + note));
          });
        });
      } finally { fs.closeSync(fd); }
      const actual = digest.digest('hex');
      if (received !== size || actual !== hash(fs.readFileSync(expected))) throw Error('Installer contains stale or missing payload: ' + relative);
      proof[relative] = { size, sha256: actual };
    }
    const proofPath = path.join(candidate, 'installer-payload-proof.json');
    if (fs.existsSync(proofPath)) bounded(proofPath);
    fs.writeFileSync(proofPath, JSON.stringify({ installerSha256: hash(fs.readFileSync(installer)), files: proof }, null, 2));
    console.log(JSON.stringify({ installerPayload: 'MATCH', files: proof }));
  }
  console.log(JSON.stringify({ outFilesChecked: checked, nativeModules: native, branding: 'Kel', integrity: true }));
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
