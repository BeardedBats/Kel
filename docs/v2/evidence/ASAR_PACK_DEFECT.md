# The `app.asar` pack defect (measured 2026-09-22, twice)

An intermittent archive-write defect in this packaging path. It must be *checked for* after every
pack, because it is invisible in a directory listing, in the archive size, and in `asar list`.

## What happens

`resources/app.asar` comes out with one file's *bytes* taken from a **4096-byte-aligned offset of
another file's stream**, while its size and its header entry stay correct.

Measured, twice, on `bunx electron-builder --config kel-builder.json --x64 --dir`:

| Observation | Value |
| --- | --- |
| Entry | root `package.json` (size 4,402 — the size electron-builder intends for the app manifest) |
| Content | 4,402 bytes starting at **offset 4096** of a stream that contains `public/sw.js` text |
| Effect | Electron refuses to boot: *"Error launching app / Unable to parse package.json / Unexpected token 'ACHE_NAME)' is not valid JSON"* |
| Frequency | 2 of 4 `--dir` packs today (one of them while the manifest input was also corrupt, one with a byte-verified-good input) |

Because the mis-offset is **per entry**, a valid manifest does not prove the rest of the archive, and
a file-listing or string search proves nothing either.

## How to check a pack (do this before anything is copied or launched)

1. Extract the root `package.json` from the archive **into a scratch directory** (`@electron/asar
   extract-file` writes into the current directory — never run it in a source checkout) and parse it:
   `name` / `version` / `main` must match what the build intended.
2. Compare the archive's copies of the build's own outputs against the source tree byte-for-byte —
   at minimum `out/main/index.js`, the preload bundle, `out/renderer/index.html`, and one renderer
   bundle. Equal SHA-256 on all of them is the evidence that the archive is sound.
3. Only then copy `win-unpacked` to the candidate path, and launch it.

## Known-good reference

The protected dogfood install's `resources/app.asar` parses correctly (`name Kel`,
`main ./out/main/index.js`) with the same extractor, so neither the extractor nor the tool version is
the problem; the defect is in how this pack produced the archive.

## Rejected artefacts kept

`C:\Users\Nick\KelV2Candidate.rejected-manifest-20260922` — the first corrupt copy (kept as evidence,
disposable).
