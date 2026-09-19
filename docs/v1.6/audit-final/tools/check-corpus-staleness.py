#!/usr/bin/env python3
"""Campaign C AUD-MINOR-005 gate: corpus staleness denylist at the RC head.

Reads the reconciliation-sensitive corpus files and fails when a known-stale marker is still
present or a required reconciliation marker is missing. With `--source <rev>` the file
contents are read from a git revision instead of the working tree, which makes the gate usable
as a pre/post discriminator.

Run from anywhere inside the repository:
    python docs/v1.6/audit-final/tools/check-corpus-staleness.py
    python docs/v1.6/audit-final/tools/check-corpus-staleness.py --source HEAD
"""
import argparse
import pathlib
import re
import subprocess

RULES = {
    "docs/v1.6/pre-audit/INVARIANT_LEDGER.md": {
        "deny": [
            r"Status: PLANNED \(",
            r"Status: OPEN_GAP",
            r"Status: PARTIAL \(open APR",
            r"PARTIAL \(F4 open\)",
            r"PARTIAL \(V1\.5 designed",
            r"PARTIAL \(isolation holds",
            r"DELIVERED \(F4 binding gap open\)",
            r"integration pending in Campaign A",
            r"REL-01 open",
        ],
        "require": [],
    },
    "docs/v1.6/pre-audit/MIGRATION_LEDGER.md": {
        "deny": [r"Next free version: \*\*20\*\*", r"\| planned \|", r"\*\*assertion pending\*\*", r"- \[ \] "],
        "require": [r"Next free version: \*\*22\*\*"],
    },
    "docs/v1.6/pre-audit/REQUIREMENTS_TRACEABILITY.md": {
        "deny": [
            r"REQ-R25-R9[^\n]*PENDING",
            r"REQ-R25-R11[^\n]*PENDING",
            r"REQ-R25-R12[^\n]*PENDING",
            r"REQ-WFWIRE[^\n]*PENDING",
            r"REQ-PKG-ASSERT[^\n]*PENDING",
            r"REQ-RC[^\n]*PENDING",
            r"re-verified open",
        ],
        "require": [],
    },
    "docs/v1.6/pre-audit/AUDIT_HANDOFF.md": {
        "deny": [r"\|\s*TBD"],
        "require": [r"FINALIZED at PRE-AUDIT RC"],
    },
    "docs/v1.6/pre-audit/P2_P3_DISPOSITION.md": {
        "deny": [],
        "require": [r"TL;DR \(Campaign C"],
    },
    "docs/v1.6-visual-ux/00_STATUS.md": {
        "deny": [],
        "require": [r"Reconciliation note \(Campaign C"],
    },
}


def load(root, relpath, rev):
    if rev:
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"{rev}:{relpath}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise SystemExit(f"cannot read {relpath} at {rev}: {result.stderr.strip()}")
        return result.stdout
    return (root / relpath).read_text(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None, help="git revision to read files from")
    args = parser.parse_args()

    root = pathlib.Path(
        subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    )
    failures = []
    for relpath, rules in RULES.items():
        text = load(root, relpath, args.source)
        for pattern in rules["deny"]:
            if re.search(pattern, text):
                failures.append(f"{relpath}: stale marker present: {pattern}")
        for pattern in rules["require"]:
            if not re.search(pattern, text):
                failures.append(f"{relpath}: required reconciliation marker missing: {pattern}")

    if failures:
        print("CORPUS LINT: FAIL%s" % (" (source: %s)" % args.source if args.source else ""))
        for failure in failures:
            print("  " + failure)
        return 1
    print("CORPUS LINT: PASS%s (%d files checked)" % (" (source: %s)" % args.source if args.source else "", len(RULES)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
