# Consolidation status — 2026-09-24

Status: COMPLETE. Core migration and the final canonical layout are verified.

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

## Final verification — 2026-09-24

Nick manually removed `Kel-Repo` and `kel-v2-integration`. Both paths are absent.
The project root contains exactly four directories: `Kel`, `App`, `Data`, and `Tools`.
`Kel` is the only registered Git worktree, on `main`.
Before this status update, local HEAD matched GitHub `main` at `d3d6b8098cd1aba909daf8b3bdddffbeac6ab744`.
The only pending tracked change was this status document. This final update is committed and pushed separately.

Desktop and Start Menu shortcuts target `App\Kel.exe`, with `App` as their working directory.
Windows uninstall registration also points into `App`.
The executable, app archive, and engine hashes match the previously verified installed artifacts.

Read-only checks returned `ok` for both canonical databases, with no foreign-key issues.
Current counts remain 70 conversations, 12 messages, two jobs, eight projects, six Kibble fixes, and two transcripts.
The six screenshots, two prompts, and two audio files remain present. Backups and recovery archives remain present.
Prior byte-level preservation evidence is retained above; no migration or app launch was repeated.

The obsolete roots in both cleanup manifests are absent, except the empty `Roaming\kel-desktop` bootstrap directory.
No Kel candidate folders remain under the user home. No stale Kel test roots were found in the checked temporary locations.
No historical registered worktrees or old release roots remain.

Per Nick's final instruction, no further deletion occurred.
Ignored source build output, bundled packaging resources, dependencies, and caches remain inside the canonical repository.
They are not separate installations, worktrees, or data roots. Their removal is outside this final verification scope.
Preserved user data and Git history were not changed.
The separate `request_review` tool remains unavailable; no independent review is claimed.

Detailed local evidence is in `Tools\consolidation`, especially `final-verification.json`,
`after-cleanup-smoke.json`, `installed-data-preservation.json`, and the cleanup manifests.
