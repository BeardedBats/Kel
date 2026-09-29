// FN-01: Claude Code PreToolUse hook that keeps a Kel worker out of protected places.
//
// Claude Code runs this before every tool call, in every permission mode — bypassPermissions
// auto-approves tool calls "except explicit deny rules", and a PreToolUse hook is the documented
// way to gate every call (Claude Code 2.1.283). The policy is a JSON file Kel writes per run
// (KEL_GUARD_POLICY): the run's working copy (the only place file tools may write), a few files
// the worker may read, and the protected roots (Kel's own data, the installed app, credential
// folders, KEL_PROTECTED_PATHS) that no tool may read or write. Fails closed: if the check itself
// breaks, the tool call is denied.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const FILE_TOOLS = new Set(['Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'NotebookRead', 'Glob', 'Grep', 'LS']);
const WRITE_TOOLS = new Set(['Write', 'Edit', 'MultiEdit', 'NotebookEdit']);
const SHELL_TOOLS = new Set(['Bash', 'PowerShell']);
const win = process.platform === 'win32';

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
  return win ? text.toLowerCase() : text;
}

function inside(target, root) {
  if (!root) return false;
  const sep = path.sep;
  return target === root || target.startsWith(root.endsWith(sep) ? root : root + sep);
}

function expand(token, cwd) {
  let t = String(token || '').trim().replace(/^['"`]+|['"`;,)]+$/g, '');
  t = t.replace(/^(\d?>>?|<|&>)/, '');
  if (!t) return null;
  const home = process.env.USERPROFILE || os.homedir();
  const vars = { HOME: home, USERPROFILE: home, APPDATA: process.env.APPDATA, LOCALAPPDATA: process.env.LOCALAPPDATA,
    TEMP: process.env.TEMP, TMP: process.env.TMP, KEL_DATA_DIR: process.env.KEL_DATA_DIR };
  t = t.replace(/\$env:([A-Za-z_][A-Za-z0-9_]*)/gi, (m, v) => vars[v.toUpperCase()] ?? process.env[v] ?? m);
  t = t.replace(/%([A-Za-z_][A-Za-z0-9_]*)%/g, (m, v) => vars[v.toUpperCase()] ?? process.env[v] ?? m);
  t = t.replace(/\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?/g, (m, v) => vars[v.toUpperCase()] ?? process.env[v] ?? m);
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
    writable: (policy.writable || []).map(norm),
    readable: (policy.readable || []).map(norm),
    protected: (policy.protected || []).map(p => ({ path: norm(p.path), label: p.label, shown: p.path })),
    log: policy.log || null,
  };
}

// null when the access is fine; a plain sentence when it is not.
function check(policy, target, write, fileTool) {
  const t = norm(target);
  if (inside(t, policy.workspace)) return null;
  if (!write && policy.readable.some(r => t === r)) return null;
  for (const root of policy.protected) {
    if (inside(t, root.path)) {
      return `Kel blocked this: ${target} is in ${root.label}, which Kel never ${fileTool ? (write ? 'changes' : 'opens') : 'touches'} for work. ` +
        'Do not try another way. Finish the rest of the request, and say plainly in your answer that this part was not done ' +
        'because that folder is off-limits (offer to save it in the project instead).';
    }
  }
  if (write && fileTool && !policy.writable.some(r => inside(t, r))) {
    return `Kel blocked this: ${target} is outside the working copy. Make every file change inside the working copy ` +
      `(${policy.raw.workspace}); Kel applies the checked change to the project itself.`;
  }
  return null;
}

function shellTargets(command, cwd) {
  const out = [];
  const tokens = String(command || '').split(/[\s|&;()<>]+/);
  for (const raw of tokens) {
    for (const piece of raw.split(/=(?=.)/)) {
      const clean = piece.replace(/^['"`]+|['"`]+$/g, '');
      if (!clean || !pathish(clean)) continue;
      const target = expand(clean, cwd);
      if (target) out.push(target);
    }
  }
  return out;
}

function textHit(policy, command) {
  const text = String(command || '').replace(/["'`]/g, '').toLowerCase();
  const variants = [text, text.replace(/\\\\/g, '\\'), text.replace(/\//g, '\\'), text.replace(/\\/g, '/')];
  for (const root of policy.protected) {
    const r = root.path.toLowerCase();
    const forms = [r, r.replace(/\\/g, '/'), win ? '/' + r[0] + r.slice(2).replace(/\\/g, '/') : r];
    if (forms.some(f => variants.some(v => {
      let i = v.indexOf(f);
      while (i >= 0) {
        // A mention of the working copy (which may sit inside Kel's data) is the work itself.
        const rest = v.slice(i);
        const ws = policy.workspace.toLowerCase();
        const wsForms = [ws, ws.replace(/\\/g, '/'), win ? '/' + ws[0] + ws.slice(2).replace(/\\/g, '/') : ws];
        if (!wsForms.some(w => rest.startsWith(w))) return true;
        i = v.indexOf(f, i + 1);
      }
      return false;
    }))) return root;
  }
  return null;
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
    for (const target of shellTargets(command, cwd)) {
      const reason = check(policy, target, true, false);
      if (reason) return reason;
    }
    const root = textHit(policy, command);
    if (root) return check(policy, root.shown, true, false) ||
      `Kel blocked this: the command names ${root.label}, which Kel never touches for work.`;
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

export { decide, load, check, shellTargets };

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
