#!/usr/bin/env python3
"""Campaign B audit tool: classify every commit in the declared unaudited range.

Read-only against the repository. Writes two evidence files under
docs/v1.6/audit-final/evidence/:
  - commit-classification.tsv   (one row per commit: primary class + counts)
  - commit-file-lists.txt       (per-commit file list with per-file class)

Run from the audit worktree root (kel-v16-final-audit).
"""
import collections
import os
import subprocess

RANGE = "8a2b25d..08f56673ea93ed84568018937bb190e0a5acd71b"
EVID = "docs/v1.6/audit-final/evidence"


def git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def classify(path):
    p = path.replace("\\", "/")
    if p.startswith("docs/") or p.endswith(".md"):
        return "docs"
    if p.startswith("runtime/tests/"):
        return "test"
    if p.startswith("runtime/"):
        return "engine"
    if p.startswith("desktop/tests/"):
        return "test"
    if p.startswith("desktop/"):
        return "desktop"
    if p.startswith("scripts/") or p.startswith("packaging/"):
        return "tooling"
    if p.startswith("third_party/"):
        return "third_party"
    return "meta"


def commit_files(sha, parents):
    if len(parents) > 1:  # merge commit: union of per-parent diffs
        files = set()
        for p in parents:
            out = git("diff", "--name-only", p, sha)
            files.update(f for f in out.splitlines() if f.strip())
        return sorted(files)
    out = git("show", "--name-only", "--format=", sha)
    return [f for f in out.splitlines() if f.strip()]


def main():
    shas = git("rev-list", "--reverse", RANGE).split()
    tsv_path = os.path.join(EVID, "commit-classification.tsv")
    files_path = os.path.join(EVID, "commit-file-lists.txt")
    rows = []
    with open(files_path, "w", encoding="utf-8") as ff:
        for sha in shas:
            subj = git("show", "-s", "--format=%s", sha).strip()
            parents = git("show", "-s", "--format=%P", sha).strip().split()
            date = git("show", "-s", "--format=%ci", sha).strip()
            files = commit_files(sha, parents)
            classes = collections.Counter(classify(f) for f in files)
            prod_like = [f for f in files if classify(f) in ("engine", "desktop", "tooling", "third_party", "meta")]
            if prod_like:
                primary = "PROD"
            elif classes.get("test"):
                primary = "TEST"
            else:
                primary = "DOCS"
            cls = "+".join(f"{k}:{v}" for k, v in sorted(classes.items()))
            rows.append((sha, date, primary, cls, len(files), subj, " ".join(parents)))
            ff.write(f"=== {sha} | {date} | {primary} | {subj}\n")
            for f in files:
                ff.write(f"    [{classify(f)}] {f}\n")
    with open(tsv_path, "w", encoding="utf-8") as ft:
        ft.write("sha\tdate\tprimary\tclass-counts\tnfiles\tsubject\tparents\n")
        for sha, date, primary, cls, n, subj, parents in rows:
            ft.write(f"{sha}\t{date}\t{primary}\t{cls}\t{n}\t{subj}\t{parents}\n")
    counts = collections.Counter(r[2] for r in rows)
    print(f"commits classified: {len(shas)}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    print("wrote:", tsv_path)
    print("wrote:", files_path)


if __name__ == "__main__":
    main()
