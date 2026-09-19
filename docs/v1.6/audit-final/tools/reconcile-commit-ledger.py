#!/usr/bin/env python3
"""Campaign C AUD-MINOR-001 gate: the COMMIT_LEDGER must reconcile 1:1 with git.

Read-only. Parses every commit-table row of `docs/v1.6/pre-audit/COMMIT_LEDGER.md` and
fails (exit 1) when:
  - a commit in `git rev-list 8a2b25d..08f5667` has no ledger row;
  - a row's SHA cell is a placeholder or prose instead of a hex SHA (`HEAD`, `R6 tests+record`);
  - a row's declared parent does not match the commit's real parent(s).

Run from anywhere inside the repository:
    python docs/v1.6/audit-final/tools/reconcile-commit-ledger.py
"""
import pathlib
import re
import subprocess

RANGE = "8a2b25d..08f56673ea93ed84568018937bb190e0a5acd71b"
LEDGER = "docs/v1.6/pre-audit/COMMIT_LEDGER.md"
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def main():
    root = pathlib.Path(git("rev-parse", "--show-toplevel").strip())
    ledger = (root / LEDGER).read_text(encoding="utf-8", errors="replace")
    listed, malformed, parents = set(), [], {}
    for line in ledger.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        row = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(row) < 2:
            continue
        first, second = row[0], row[1]
        f, s = first.strip("`"), second.strip("`")
        if SHA_RE.match(f):
            listed.add(f)
        elif second.startswith("`") and SHA_RE.match(s):
            malformed.append("placeholder SHA cell: %r" % first)
        elif first and not first.startswith("`") and SHA_RE.match(s):
            malformed.append("non-SHA first cell: %r" % first)
        if SHA_RE.match(f) and second.startswith("`") and SHA_RE.match(s):
            parents[f] = s

    real = git("rev-list", RANGE).split()
    unlisted = [
        sha[:7]
        for sha in real
        if not any(l.startswith(sha[:7]) or sha.startswith(l) for l in listed)
    ]
    mismatches = []
    for sha7, declared in parents.items():
        real_parents = git("show", "-s", "--format=%P", sha7).split()
        if not any(p.startswith(declared) or declared.startswith(p[:7]) for p in real_parents):
            mismatches.append((sha7, declared, " ".join(p[:7] for p in real_parents) or "(root)"))

    if unlisted or malformed or mismatches:
        print("LEDGER RECONCILIATION: FAIL")
        for sha7 in unlisted:
            print("  unlisted commit: %s" % sha7)
        for message in malformed:
            print("  malformed row: %s" % message)
        for sha7, declared, actual in mismatches:
            print("  parent mismatch: %s declares %s, real parents %s" % (sha7, declared, actual))
        return 1
    print(
        "LEDGER RECONCILIATION: PASS - %d commits in %s; every row well-formed, 1:1"
        % (len(real), RANGE)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
