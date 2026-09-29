// FN-01 / D-81: Claude Code PreToolUse hook that keeps a Kel worker inside Kel's Memory folder.
//
// Claude Code runs this before every tool call, in every permission mode — bypassPermissions
// auto-approves tool calls "except explicit deny rules", and a PreToolUse hook is the documented
// way to gate every call (Claude Code 2.1.283). The policy is a JSON file Kel writes per run
// (KEL_GUARD_POLICY). It is an ALLOW-LIST (D-81):
//   * read + write: the run's working copy, the Memory folder (every project in it), the run's temp;
//   * read only:    Memory\Kel (Kel's mirror of its settings, chats and notes), a few named files,
//                   and the system and tool folders the CLIs need (Windows, Program Files, PATH);
//   * everything else is refused: "That's outside Kel's Memory folder, so I can't touch it."
// Fails closed: if the check itself breaks, the tool call is denied.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const FILE_TOOLS = new Set(['Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'NotebookRead', 'Glob', 'Grep', 'LS']);
const WRITE_TOOLS = new Set(['Write', 'Edit', 'MultiEdit', 'NotebookEdit']);
const SHELL_TOOLS = new Set(['Bash', 'PowerShell']);
const win = process.platform === 'win32';
// Git for Windows mounts these inside its own install folder: system paths, read-only for work.
const POSIX_SYSTEM = ['/usr', '/bin', '/etc', '/mingw64', '/mingw32', '/dev', '/proc', '/tmp', '/opt', '/lib'];
const REFUSAL = "That's outside Kel's Memory folder, so I can't touch it.";

function norm(p) {
  let text = path.resolve(p);
  // Resolve links on the longest existing prefix, so a junction cannot smuggle a path past the check.
  let head = text, tail = [];
  for (;;) {
    try { head = fs.realpathSync.native(head); break; } catch {
      const parent = path.dirname(head);
      if (parent === head) break;
      tail.unshift(path.basename(head)); head = parent;
    }
  }
  text = path.join(head, ...tail).replace(/[\\/]+$/, '');
  if (/^[A-Za-z]:$/.test(text)) text += path.sep;
  return win ? text.toLowerCase() : text;
}

function inside(target, root) {
  if (!root) return false;
  const sep = path.sep;
  return target === root || target.startsWith(root.endsWith(sep) ? root : root + sep);
}

function vars() {
  const home = process.env.USERPROFILE || os.homedir();
  return { HOME: home, USERPROFILE: home, APPDATA: process.env.APPDATA, LOCALAPPDATA: process.env.LOCALAPPDATA,
    TEMP: process.env.TEMP, TMP: process.env.TMP, KEL_DATA_DIR: process.env.KEL_DATA_DIR };
}

function expandText(text) {
  const v = vars();
  let t = String(text || '');
  t = t.replace(/\$env:([A-Za-z_][A-Za-z0-9_]*)/gi, (m, n) => v[n.toUpperCase()] ?? process.env[n] ?? m);
  t = t.replace(/%([A-Za-z_][A-Za-z0-9_()]*)%/g, (m, n) => v[n.toUpperCase()] ?? process.env[n] ?? m);
  t = t.replace(/\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?/g, (m, n) => v[n.toUpperCase()] ?? process.env[n] ?? m);
  return t;
}

// A POSIX-rooted Git Bash system path (/usr/bin/env, /dev/null, /tmp/x), or a Windows switch (/c, /s).
function systemToken(t) {
  if (!win || !t.startsWith('/') || t.startsWith('//')) return false;
  if (POSIX_SYSTEM.some(p => t === p || t.startsWith(p + '/'))) return true;
  return /^\/[A-Za-z?]{1,3}$/.test(t);  // a switch: cmd /c, dir /s /b, findstr /i
}

function expand(token, cwd) {
  let t = String(token || '').trim().replace(/^['"`]+|['"`;,)]+$/g, '');
  t = t.replace(/^(\d?>>?|<|&>)/, '');
  if (!t) return null;
  t = expandText(t);
  if (systemToken(t)) return null;
  const home = vars().HOME;
  if (t === '~' || t.startsWith('~/') || t.startsWith('~\\')) t = home + t.slice(1);
  if (win) {
    const bash = /^\/([a-zA-Z])(\/|$)(.*)$/.exec(t);  // Git Bash /c/Users/...
    if (bash) t = bash[1] + ':/' + bash[3];
  }
  const star = t.search(/[*?[]/);
  if (star >= 0) t = t.slice(0, star);
  if (!t) return null;
  return path.isAbsolute(t) ? t : path.resolve(cwd, t);
}

function pathish(token) {
  return /[\\/~%$]/.test(token) || token.startsWith('.');
}

function load(policyFile) {
  const policy = JSON.parse(fs.readFileSync(policyFile, 'utf8'));
  return {
    raw: policy,
    workspace: norm(policy.workspace),
    memory: policy.memory ? norm(policy.memory) : null,
    mirror: policy.mirror ? norm(policy.mirror) : null,
    writable: (policy.writable || []).map(norm),
    readable: (policy.readable || []).map(norm),
    system: (policy.system || []).map(norm),
    protected: (policy.protected || []).map(p => ({ path: norm(p.path), label: p.label, shown: p.path })),
    log: policy.log || null,
  };
}

function outside(target, label) {
  return `Kel blocked this: ${target} is outside Kel's Memory folder${label ? ` (it is ${label})` : ''}. ` +
    'Every AI tool Kel runs works only inside the Memory folder and the working copy. Do not try another way. ' +
    `Finish the rest of the request; that part was not done, so say plainly in your answer: "${REFUSAL}"`;
}

// null when the access is fine; a plain sentence when it is not.
function check(policy, target, write, fileTool) {
  const t = norm(target);
  if (inside(t, policy.workspace)) return null;
  if (policy.mirror && inside(t, policy.mirror)) {
    if (write && fileTool) {
      return `Kel blocked this: ${target} is in Memory\\Kel, Kel's own read-only copy of its settings, chats and ` +
        'notes. Read it freely, but never change it; agents never change Kel\'s settings. Say so plainly if the request asked for it.';
    }
    return null;
  }
  if (policy.memory && inside(t, policy.memory)) return null;
  if (policy.writable.some(r => inside(t, r))) return null;
  if (!write && policy.readable.some(r => t === r)) return null;
  for (const root of policy.protected) {
    if (inside(t, root.path)) return outside(target, root.label);
  }
  if (policy.system.some(r => inside(t, r))) {
    if (write && fileTool) return outside(target, 'a system or program folder');
    return null;
  }
  return outside(target, null);
}

// Shell words, quote-aware: a quoted string is one word (so "C:\Program Files\Git\bin\bash.exe" stays whole).
function words(command) {
  const out = [];
  const re = /"([^"]*)"|'([^']*)'|`([^`]*)`|([^\s|&;<>()"'`]+)/g;
  let m;
  while ((m = re.exec(String(command || '')))) {
    if (m[4] !== undefined) for (const piece of m[4].split(/=(?=.)/)) out.push(piece);
    else out.push(m[1] ?? m[2] ?? m[3]);
  }
  return out;
}

function shellTargets(command, cwd) {
  const out = [];
  for (const word of words(command)) {
    const clean = word.trim();
    if (!clean || !pathish(clean)) continue;
    const target = expand(clean, cwd);
    if (target) out.push(target);
  }
  return out;
}

// Drive-letter paths anywhere in the command (also inside code: node -e "fs.readFileSync('C:/...')").
// Each comes as [the path up to the first space, the path up to the next quote or separator].
function embeddedPaths(command) {
  const text = expandText(command);
  const out = [];
  const re = /(?<![A-Za-z0-9])([A-Za-z]:[\\/][^\s'"`;|&<>()*?]*)(?=([^'"`;|&<>()*?\r\n]*))/g;
  let m;
  while ((m = re.exec(text))) out.push([m[1], (m[1] + m[2]).trimEnd()]);
  return out;
}

function decide(policy, input) {
  const tool = input.tool_name || '';
  const args = input.tool_input || {};
  const cwd = input.cwd || policy.raw.workspace;
  if (tool.startsWith('mcp__')) {
    // A tool server is its own process: no file rule reaches inside it.
    return 'Kel blocked this: a Kel worker does not use outside tool servers. Use the file and shell tools in the working copy.';
  }
  if (FILE_TOOLS.has(tool)) {
    const write = WRITE_TOOLS.has(tool);
    const targets = [args.file_path, args.notebook_path, args.path].filter(v => typeof v === 'string' && v);
    if (tool === 'Glob' && typeof args.pattern === 'string' && pathish(args.pattern)) {
      const base = expand(args.pattern, args.path || cwd);
      if (base) targets.push(base);
    }
    if (!targets.length && (tool === 'Glob' || tool === 'Grep' || tool === 'LS')) targets.push(cwd);
    for (const target of targets) {
      const reason = check(policy, path.isAbsolute(target) ? target : path.resolve(cwd, target), write, true);
      if (reason) return reason;
    }
    return null;
  }
  if (SHELL_TOOLS.has(tool)) {
    const command = String(args.command || '');
    const here = check(policy, cwd, false, false);
    if (here) return here;
    for (const target of shellTargets(command, cwd)) {
      const reason = check(policy, target, true, false);
      if (reason) return reason;
    }
    for (const [short, long] of embeddedPaths(command)) {
      const reason = check(policy, short, true, false);
      if (!reason) continue;
      // "C:\Program Files\..." splits at its space: the longer form counts only when it has no "..".
      if (long !== short && !/(^|[\\/])\.\.([\\/]|$)/.test(long) && !check(policy, long, true, false)) continue;
      return reason;
    }
    return null;
  }
  return null;
}

function record(policy, input, reason) {
  if (!policy?.log) return;
  try {
    fs.appendFileSync(policy.log, JSON.stringify({ at: Date.now() / 1000, tool: input?.tool_name,
      input: input?.tool_input, reason }) + '\n');
  } catch {}
}

function deny(reason) {
  process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse',
    permissionDecision: 'deny', permissionDecisionReason: reason } }));
  process.exit(0);
}

export { decide, load, check, shellTargets, embeddedPaths, words, REFUSAL };

const main = Boolean(process.argv[1]) && path.resolve(process.argv[1]).toLowerCase() === fileURLToPath(import.meta.url).toLowerCase();
if (main) {
  let data = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { data += chunk; });
  process.stdin.on('end', () => {
    let policy = null, input = null;
    try {
      input = JSON.parse(data || '{}');
      policy = load(process.env.KEL_GUARD_POLICY);
      const reason = decide(policy, input);
      if (reason) { record(policy, input, reason); deny(reason); }
      process.exit(0);
    } catch (error) {
      const reason = 'Kel could not check this step safely, so it was not run (' + String(error).slice(0, 120) + ').';
      record(policy, input, reason);
      deny(reason);
    }
  });
}
