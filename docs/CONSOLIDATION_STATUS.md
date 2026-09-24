# Consolidation status — 2026-09-24

Core source, installation, and data migration are verified. Final cleanup is blocked; do not report full completion.

## Authoritative layout

- Source: `C:\Users\Nick\Desktop\Kel\Kel`, branch `main`.
- Installed app: `C:\Users\Nick\Desktop\Kel\App`.
- Durable state: `C:\Users\Nick\Desktop\Kel\Data`.
- Tools and local verification records: `C:\Users\Nick\Desktop\Kel\Tools`.

The installed product was built from source commit `842c01d`. Later changes concern documentation and test portability only.
All prior local branches were ancestors of that source. Branches, tags, and Git history were retained.
The canonical repository has one registered worktree. Git's full object check passed after relocation.
The repository dependency links were repaired with `bun install --frozen-lockfile --ignore-scripts`.

## Verification

The existing desktop build and engine regression had finished before this session began.
The existing engine run recorded 1,281 passes and three failures. Its two Windows liveness failures exposed unsafe process inspection.
The fix uses read-only Windows process handles. The remaining failure pinned removed UI wording; the test now checks the shipped safety claims.
Both affected test files passed: 16 tests, including child-process survival and invalid-PID coverage.
The full regression was not repeated. Its 1,281 completed passes were retained as prior evidence.

The engine was rebuilt because its source changed. Packaging reused the completed desktop bundle.
All 67 embedded engine modules matched source, including the installed executable.
Copied-data and installed-app checks passed at widths 1440 and 800, with no page errors or horizontal overflow on the checked routes.
The final check ran after removal of the old AppData roots. It verified all three canonical data paths and a connected engine.
The verification app and engine exited afterward.

The installer initially reused its old registered location despite `/D`.
The complete installed runtime was moved to `App`. Windows registration, protocol registration where present, and Desktop/Start Menu shortcuts were updated.

## Data preservation

All 68 original conversations, 12 messages, two jobs, six Kibble fixes, and two transcripts remain unchanged.
Eight projects remain. Startup checks added two empty conversations, giving 70 total conversation records.
All six Kibble screenshots, two prompts, and two audio files matched their original bytes.
All 34 UI-store tables matched before the path correction.
Four project roots and ten UI workspace references were redirected to the preserved canonical files.
One already-missing workspace remained missing in both the original and copied data; no existing file was lost.
All 29 migration records are present. Integrity and foreign-key checks passed.

Original database backups and recovery archives stay under `Data`.
Recovery archives preserve unique loose source, artifacts, uncertain old records, and unreproducible Git metadata.
They are not alternate running profiles. Reproducible donor copies were reduced to provenance records.
No credentials, private data, or new screenshots were added to Git.

## Cleanup performed

Removed 62 obsolete candidate, release, source-reference, and data roots, plus 86 temporary or old profile roots.
Removed obsolete registered worktrees while retaining all their committed history.
Kept one repository dependency installation. Restored its junctions to the canonical path.
Removed temporary recovery archives and reproducible donor-history bundles after verifying the smaller retained archives.

## Remaining blockers

1. `C:\Users\Nick\Desktop\Kel\kel-v2-integration` is empty but locked by Claude and its PowerShell terminal.
   Observed owners were PowerShell PID 43276 and Claude PID 63316. Recheck ownership before any future action.
   Automatic approval review rejected stopping the terminal. Nick was asked to close the terminal/workspace.
2. `C:\Users\Nick\Desktop\Kel\Kel-Repo` contains only an empty `.git` directory, `.pytest_cache`, and old `dist` output.
   The source and complete Git metadata are already in `Kel\Kel`. The old runtime output totals 21,783,679 bytes.
   Automatic approval review rejected deletion of this residue.
3. `Kel\desktop\out` contains an old generated desktop bundle, totaling 28,019,754 bytes.
   Automatic approval review rejected its deletion. Other ignored build caches remain visible through Git's ignored-file inventory.

The review rejection supplied only "blocked by policy". Do not work around it or call cleanup complete.
The separate `request_review` tool required by AGENTS.md was unavailable; no independent review occurred.

Detailed local evidence is in `Tools\consolidation`, especially `final-verification.json`,
`after-cleanup-smoke.json`, `installed-data-preservation.json`, and the cleanup manifests.
