/**
 * Unified native module rebuild utility
 * Handles rebuilding native modules for different platforms and architectures
 *
 * Supports vx toolchain management:
 * - Uses 'vx --with msvc' on Windows to ensure MSVC compiler is available
 * - Falls back to standard bunx if vx is not available
 */

const { execSync, execFileSync, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * Check if vx is available in the system
 */
function isVxAvailable() {
  try {
    const result = spawnSync('vx', ['--version'], { stdio: 'ignore' });
    return result.status === 0;
  } catch {
    return false;
  }
}

/**
 * Get bunx command for the current platform
 * Windows requires bunx.cmd, others use bunx
 * Note: does NOT add 'vx' prefix here — the caller's cmdPrefix (e.g. 'vx --with msvc')
 * already provides the vx entry point, so we must not nest another 'vx' call.
 */
function getBunxCommand() {
  return process.platform === 'win32' ? 'bun x' : 'bun x';
}

/**
 * Get command prefix for native compilation with proper toolchain.
 * On Windows, returns 'vx --with msvc' so MSVC env vars are injected into
 * the subprocess environment before bunx/node-gyp runs.
 * On other platforms returns 'vx' to ensure the correct bun version is used.
 * Returns '' when vx is not available.
 */
function getCommandPrefix(platform, useVx = true) {
  if (!useVx || !isVxAvailable()) {
    return '';
  }
  if (platform === 'win32' || platform === 'windows') {
    // 'vx --with msvc <cmd>' injects VCINSTALLDIR and related env vars so
    // node-gyp can locate the MSVC compiler without a separate choco install.
    return 'vx --with msvc';
  }
  return 'vx';
}

/**
 * Normalize architecture names
 */
function normalizeArch(arch) {
  const archMap = {
    x64: 'x64',
    arm64: 'arm64',
    ia32: 'ia32',
    armv7l: 'arm',
  };
  return archMap[arch] || arch;
}

/**
 * Get modules to rebuild based on platform
 */
function getModulesToRebuild(platform) {
  // Windows: Skip node-pty (cross-compilation fails with missing conpty API types)
  // Linux: Skip node-pty (no ARM64 prebuilds available, cross-compilation requires ARM64 toolchain)
  // macOS: Skip node-pty (cross-compilation from ARM64→x64 fails, use @lydell/node-pty-* prebuilts)
  if (platform === 'win32' || platform === 'windows') {
    return ['better-sqlite3'];
  } else if (platform === 'linux') {
    return ['better-sqlite3'];
  }
  // macOS: only rebuild better-sqlite3, skip node-pty
  return ['better-sqlite3'];
}

/**
 * Build environment variables for native module compilation
 */
function buildEnvironment(platform, targetArch, electronVersion) {
  const env = {
    ...process.env,
    npm_config_arch: targetArch,
    npm_config_target_arch: targetArch,
    npm_config_build_from_source: 'true',
    npm_config_runtime: 'electron',
    npm_config_disturl: 'https://electronjs.org/headers',
    npm_config_target: electronVersion,
  };

  // Windows-specific environment
  if (platform === 'win32' || platform === 'windows') {
    env.MSVS_VERSION = '2022';
    env.GYP_MSVS_VERSION = '2022';
    env.WindowsTargetPlatformVersion = '10.0.19041.0';
    env._WIN32_WINNT = '0x0A00';
  }

  return env;
}

/**
 * Read the NODE_MODULE_VERSION of the pinned Electron binary (ELECTRON_RUN_AS_NODE makes it
 * behave as Node for a single evaluation). Used to resolve prebuilds without node-abi's tables.
 */
function electronAbi(projectRoot) {
  const exe = path.join(
    projectRoot,
    'node_modules',
    'electron',
    'dist',
    process.platform === 'win32' ? 'electron.exe' : 'electron'
  );
  if (!fs.existsSync(exe)) return null;
  try {
    const out = execFileSync(exe, ['-p', 'process.versions.modules'], {
      env: { ...process.env, ELECTRON_RUN_AS_NODE: '1' },
      encoding: 'utf8',
      timeout: 30000,
    });
    const abi = parseInt(String(out).trim(), 10);
    return Number.isFinite(abi) ? abi : null;
  } catch {
    return null;
  }
}

/**
 * Locate the prebuild-install library inside the project's dependency tree. Works for npm
 * layouts (hoisted or nested) and for bun's `.bun/` layout used by this repository.
 */
function resolvePrebuildInstall(projectRoot) {
  const candidates = [];
  try {
    candidates.push(
      path.dirname(require.resolve('prebuild-install/package.json', { paths: [projectRoot, __dirname] }))
    );
  } catch {
    /* not resolvable from here */
  }
  try {
    for (const root of [
      path.join(projectRoot, 'node_modules'),
      path.join(__dirname, '..', 'node_modules'),
    ]) {
      const bunRoot = path.join(root, '.bun');
      if (!fs.existsSync(bunRoot)) continue;
      for (const entry of fs.readdirSync(bunRoot)) {
        if (entry.startsWith('prebuild-install@')) {
          candidates.push(path.join(bunRoot, entry, 'node_modules', 'prebuild-install'));
        }
      }
    }
  } catch {
    /* ignore */
  }
  return candidates.find((dir) => fs.existsSync(path.join(dir, 'util.js'))) || null;
}

/**
 * V1.5: fetch the official prebuilt binary for the *pinned* Electron ABI through the
 * prebuild-install library API. The CLI cannot be used here: it resolves the ABI via
 * node-abi, whose tables do not know Electron 44.3.0, so any electron-runtime invocation
 * exits before parsing flags. Passing the ABI explicitly (read from the pinned binary)
 * keeps the download path working without touching the dependency tree.
 *
 * Returns nothing when the download was started (the async callback exits the process);
 * returns an exit code number on early failure. Run as a child process via `--fetch-prebuild`.
 */
function fetchPrebuildForPinnedAbi(payload) {
  const { moduleRoot, moduleName, platform, arch, electronVersion, abi, projectRoot } = payload;
  if (!moduleRoot || !moduleName || !fs.existsSync(moduleRoot)) {
    console.error('fetch-prebuild: module root not found:', moduleRoot);
    return 2;
  }
  const installDir = resolvePrebuildInstall(projectRoot);
  if (!installDir) {
    console.error('fetch-prebuild: prebuild-install is not resolvable from', projectRoot);
    return 2;
  }
  const util = require(path.join(installDir, 'util'));
  const download = require(path.join(installDir, 'download'));
  const pkg = JSON.parse(fs.readFileSync(path.join(moduleRoot, 'package.json'), 'utf8'));
  const log = {
    info: (...a) => console.log('    ', ...a),
    warn: (...a) => console.warn('    ', ...a),
    error: (...a) => console.error('    ', ...a),
    http: () => {},
    verbose: () => {},
  };
  const opts = {
    pkg,
    log,
    force: true,
    path: moduleRoot,
    runtime: 'electron',
    target: electronVersion,
    platform,
    arch,
    abi: String(abi),
    tagPrefix: 'v',
    'tag-prefix': 'v',
  };
  const url = util.getDownloadUrl(opts);
  console.log('     URL:', url);
  download(url, opts, (err) => {
    if (err) {
      console.error('     download failed:', err.message);
      process.exit(1);
    }
    if (findNodeFiles(moduleRoot).length > 0) {
      console.log('     ✓ prebuilt binary installed');
      process.exit(0);
    }
    console.error('     download completed but no .node file was installed');
    process.exit(1);
  });
}

/**
 * Rebuild native modules using electron-rebuild
 *
 * @param {Object} options
 * @param {string} options.platform - Platform name (win32, darwin, linux)
 * @param {string} options.arch - Target architecture (x64, arm64, etc.)
 * @param {string} options.electronVersion - Electron version
 * @param {string} options.cwd - Working directory (default: project root)
 * @param {string[]} [options.modules] - Modules to rebuild (default: auto-detect by platform)
 */
function rebuildWithElectronRebuild(options) {
  const {
    platform,
    arch,
    electronVersion,
    cwd = path.resolve(__dirname, '..'),
    modules = getModulesToRebuild(platform),
  } = options;

  const targetArch = normalizeArch(arch);
  const env = buildEnvironment(platform, targetArch, electronVersion);

  const bunxCmd = getBunxCommand();
  const rebuildCmd = `${bunxCmd} electron-rebuild --only ${modules.join(',')} --force --arch ${targetArch} --electron-version ${electronVersion}`;

  execSync(rebuildCmd, {
    stdio: 'inherit',
    cwd,
    env,
  });
}

/**
 * Check if cross-compilation from source is supported
 */
function canCrossCompileFromSource(buildArch, targetArch, platform) {
  // macOS can cross-compile between x64 and arm64
  if (platform === 'darwin') {
    return true;
  }

  // Windows x64 can cross-compile to arm64 with proper toolchain
  if (platform === 'win32' && buildArch === 'x64' && targetArch === 'arm64') {
    return true;
  }

  // Linux cannot reliably cross-compile without ARM64 toolchain
  // Must use prebuild-install for cross-arch builds
  return buildArch === targetArch;
}

/**
 * Rebuild a single module using prebuild-install (faster for prebuilt binaries)
 * Falls back to electron-rebuild if prebuild-install fails
 *
 * @param {Object} options
 * @param {string} options.moduleName - Module name (e.g., 'better-sqlite3')
 * @param {string} options.moduleRoot - Path to module directory
 * @param {string} options.platform - Platform name
 * @param {string} options.arch - Target architecture
 * @param {string} options.electronVersion - Electron version
 * @param {string} [options.projectRoot] - Project root for fallback rebuild
 * @param {boolean} [options.forceRebuild] - Force rebuild from source (skip prebuild-install)
 * @param {string} [options.buildArch] - Build machine architecture (for cross-compilation detection)
 */
function rebuildSingleModule(options) {
  const {
    moduleName,
    moduleRoot,
    platform,
    arch,
    electronVersion,
    projectRoot = path.resolve(__dirname, '..'),
    forceRebuild = false,
    buildArch = process.arch,
  } = options;

  const targetArch = normalizeArch(arch);
  const normalizedBuildArch = normalizeArch(buildArch);
  const isCrossCompile = normalizedBuildArch !== targetArch;

  const env = buildEnvironment(platform, targetArch, electronVersion);
  env.npm_config_platform = platform;
  env.npm_config_target_platform = platform;

  const bunxCmd = getBunxCommand();
  const cmdPrefix = getCommandPrefix(platform);
  const useShell = cmdPrefix.length > 0; // Need shell for vx prefix

  // For Linux cross-compilation, ALWAYS use prebuild-install
  // because electron-rebuild cannot cross-compile without ARM64 toolchain
  const mustUsePrebuild = platform === 'linux' && isCrossCompile;

  // V1.5: same-architecture rebuilds first try the official prebuilt for the pinned Electron
  // ABI (resolved from the pinned binary itself — see fetchPrebuildForPinnedAbi for why the
  // CLI path cannot work against Electron 44).
  if (!forceRebuild && normalizedBuildArch === targetArch) {
    const abi = electronAbi(projectRoot);
    if (abi) {
      console.log(`     Using pinned Electron ABI ${abi} for prebuilt resolution`);
      try {
        execFileSync(
          process.execPath,
          [
            __filename,
            '--fetch-prebuild',
            JSON.stringify({ moduleRoot, moduleName, platform, arch: targetArch, electronVersion, abi, projectRoot }),
          ],
          { stdio: 'inherit', timeout: 300000 }
        );
        return true;
      } catch (error) {
        console.log(`     Direct prebuild fetch failed (${error.message}); falling back...`);
      }
    }
  }

  if (mustUsePrebuild) {
    console.log(`     Linux cross-compilation detected (${normalizedBuildArch} → ${targetArch})`);

    // Check if module already has prebuilds
    const prebuildsDir = path.join(moduleRoot, 'prebuilds', `${platform}-${targetArch}`);
    if (fs.existsSync(prebuildsDir)) {
      const files = fs.readdirSync(prebuildsDir);
      const hasNodeFile = files.some((f) => f.endsWith('.node'));
      if (hasNodeFile) {
        console.log(`     ✓ Found existing prebuilds in ${prebuildsDir}, skipping rebuild`);

        // Delete build/ and bin/ to prevent node-gyp-build from loading wrong architecture
        // node-gyp-build search order: bin/ -> build/Release/ -> prebuilds/
        const buildDir = path.join(moduleRoot, 'build');
        if (fs.existsSync(buildDir)) {
          console.log(`     Removing build/ directory to force use of prebuilds/`);
          fs.rmSync(buildDir, { recursive: true, force: true });
        }

        const binDir = path.join(moduleRoot, 'bin');
        if (fs.existsSync(binDir)) {
          console.log(`     Removing bin/ directory to force use of prebuilds/`);
          fs.rmSync(binDir, { recursive: true, force: true });
        }

        return true;
      }
    }

    console.log(`     No existing prebuilds found, trying prebuild-install...`);
  }

  // Try prebuild-install first (required for Linux cross-compile)
  if (!forceRebuild || mustUsePrebuild) {
    try {
      env.npm_config_build_from_source = 'false';
      const prebuildArgs = [
        '--yes',
        'prebuild-install',
        '--runtime=electron',
        `--target=${electronVersion}`,
        `--platform=${platform}`,
        `--arch=${targetArch}`,
        '--force',
      ];

      const fullCmd = cmdPrefix
        ? `${cmdPrefix} ${bunxCmd} ${prebuildArgs.join(' ')}`
        : `${bunxCmd} ${prebuildArgs.join(' ')}`;
      console.log(`     Running: ${fullCmd}`);

      if (useShell) {
        execSync(fullCmd, {
          cwd: moduleRoot,
          env,
          stdio: 'inherit',
          shell: true,
        });
      } else {
        execFileSync(bunxCmd, prebuildArgs, {
          cwd: moduleRoot,
          env,
          stdio: 'inherit',
          shell: true,
        });
      }

      console.log(`     ✓ prebuild-install succeeded`);
      return true;
    } catch (error) {
      if (mustUsePrebuild) {
        // For Linux cross-compile, prebuild-install MUST succeed
        console.error(`     ✗ prebuild-install failed and cross-compilation from source not supported`);
        console.error(`     Error: ${error.message}`);
        return false;
      }
      // For other cases, fall back to rebuild
      console.log(`     prebuild-install failed, falling back to electron-rebuild...`);
    }
  }

  // Use electron-rebuild to build from source
  if (!canCrossCompileFromSource(normalizedBuildArch, targetArch, platform)) {
    console.error(`     ✗ Cross-compilation from ${normalizedBuildArch} to ${targetArch} not supported on ${platform}`);
    return false;
  }

  try {
    env.npm_config_build_from_source = 'true';
    const rebuildArgs = [
      '--yes',
      'electron-rebuild',
      '--only',
      moduleName,
      '--force',
      `--platform=${platform}`,
      `--arch=${targetArch}`,
    ];

    const fullCmd = cmdPrefix
      ? `${cmdPrefix} ${bunxCmd} ${rebuildArgs.join(' ')}`
      : `${bunxCmd} ${rebuildArgs.join(' ')}`;
    console.log(`     Running: ${fullCmd}`);

    if (useShell) {
      execSync(fullCmd, {
        cwd: projectRoot,
        env,
        stdio: 'inherit',
        shell: true,
      });
    } else {
      execFileSync(bunxCmd, rebuildArgs, {
        cwd: projectRoot,
        env,
        stdio: 'inherit',
        shell: true,
      });
    }
    return true;
  } catch (error) {
    console.error(`❌ Failed to rebuild ${moduleName}:`, error.message);
    return false;
  }
}

/**
 * Recursively search for .node files in a directory
 */
function findNodeFiles(dir, maxDepth = 3, currentDepth = 0) {
  if (currentDepth >= maxDepth || !fs.existsSync(dir)) {
    return [];
  }

  const results = [];
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        results.push(...findNodeFiles(fullPath, maxDepth, currentDepth + 1));
      } else if (entry.isFile() && entry.name.endsWith('.node')) {
        results.push(fullPath);
      }
    }
  } catch (error) {
    // Ignore permission errors
  }

  return results;
}

/**
 * Verify native module binary exists
 */
function verifyModuleBinary(moduleRoot, moduleName) {
  const binaryPathsToCheck = {
    'better-sqlite3': [path.join(moduleRoot, 'build', 'Release', 'better_sqlite3.node')],
    'node-pty': [
      path.join(moduleRoot, 'build', 'Release', 'pty.node'),
      path.join(moduleRoot, 'build', 'Release', 'conpty.node'),
      path.join(moduleRoot, 'build', 'Release', 'conpty_console_list.node'),
    ],
  };

  const pathsToCheck = binaryPathsToCheck[moduleName] || [];

  // First check known paths
  for (const binaryPath of pathsToCheck) {
    if (fs.existsSync(binaryPath)) {
      console.log(`     Debug: Found binary at ${binaryPath}`);
      return true;
    }
  }

  // If not found, search recursively
  console.log(`     Debug: Binary not found in expected locations, searching recursively...`);
  const foundFiles = findNodeFiles(moduleRoot);
  if (foundFiles.length > 0) {
    console.log(`     Debug: Found .node files:`);
    foundFiles.forEach((f) => console.log(`       - ${f}`));
    return true;
  }

  console.log(`     Debug: No .node files found in ${moduleRoot}`);
  return false;
}

// Child mode: `node rebuildNativeModules.js --fetch-prebuild <json>` performs ONE prebuilt
// download with an explicit ABI and exits (see fetchPrebuildForPinnedAbi).
if (process.argv[2] === '--fetch-prebuild') {
  let code;
  try {
    code = fetchPrebuildForPinnedAbi(JSON.parse(process.argv[3] || '{}'));
  } catch (error) {
    console.error('fetch-prebuild failed:', error.message);
    code = 1;
  }
  if (typeof code === 'number') process.exit(code);
}

module.exports = {
  normalizeArch,
  getModulesToRebuild,
  buildEnvironment,
  rebuildWithElectronRebuild,
  rebuildSingleModule,
  verifyModuleBinary,
  canCrossCompileFromSource,
  isVxAvailable,
  getBunxCommand,
  getCommandPrefix,
};
