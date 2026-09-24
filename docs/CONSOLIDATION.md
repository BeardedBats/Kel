# Kel operating layout

The current source lives in `C:\Users\Nick\Desktop\Kel\Kel` on `main`.
GitHub `main` is its backup and normal exchange point. A coherent increment
ends only after its commit is pushed and the remote head matches the local head.

The current installed app lives in `C:\Users\Nick\Desktop\Kel\App`.
The app uses `C:\Users\Nick\Desktop\Kel\Data` for its engine, UI store,
and host state. It honors explicit data-root environment variables for tests.
Do not put real Data in Git or in a test fixture.

Use one bounded stack per increment:

1. Implement the change in the canonical repository.
2. Start only the engine, gateway, or app required for the check.
3. Run focused checks, then the relevant product checks.
4. Stop the stack and confirm its databases closed.
5. Commit and push the source change and safe evidence.
6. Remove the temporary test root and candidate.

Build output belongs in `dist/package`, which is disposable. Install the
verified package into `App`. For a side-by-side check, use only
`Temp/Candidate-<short-id>` and delete it after the comparison. Never leave
numbered candidate installs or historical releases on disk.

The 2026-09-24 migration receipt lives in `Data/migration-receipt.json`.
It records source and destination database hashes and record counts without
storing user content in Git. Keep encrypted credentials in their existing
per-user custody path and verify access through the app.
