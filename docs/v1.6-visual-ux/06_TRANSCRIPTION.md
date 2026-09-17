# 06 — Transcription

The user has chosen the standalone Transcriptions information architecture as the target for Kel's transcription
surface. This doc audits the donor **from source**, audits the current Kel page **from source + measurement**, and
states the exact target structure. It does not change any code.

## The decision (taken as given)

* Keep the standalone information architecture: left column (library) + main (document).
* **API Key is clickable text**, not a gear — it replaces the donor's gear button.
* It opens the *Meta API key* modal with no helper paragraph below *Save and Verify*.
* Ignore the donor's light-mode styling; use Kel's dark design.
* Preserve the proven interaction architecture.

## The donor, from source

Extracted tree: `C:\Users\Nick\Desktop\Kel\ux-audit\transcription-src` (from
`C:\Users\Nick\Desktop\Kel\Transcription App\Transcriptions-Source.zip`, a Tauri `muse-transcribe-desktop` app).

| Donor file | What it establishes |
|---|---|
| `src/components/Sidebar.tsx` (87 lines) | Left column: `<h1>Transcriptions</h1>` + one header button (`aria-label="Preferences"`, gear icon) → then `FolderSection` → divider → `TranscriptList`. Drag-to-folder uses `document.elementFromPoint` + `data-folder-id` with a floating drag ghost. |
| `src/components/FolderSection.tsx` (144) | FOLDERS section, New Folder, expand/reveal, rename, drop targets. |
| `src/components/TranscriptList.tsx` (36) | RECENT: a compact chronological list. |
| `src/components/ActionBar.tsx` (36) | Top-right actions in a fixed order: **Upload Audio · Record More · Record**. Record is a stateful button: `Starting…`, `Stop Recording · mm:ss`, `Saving…`, `Retry Save`. |
| `src/components/TranscriptWorkspace.tsx` (85) | Main: `h2.document-title`, a status chip (`Saved` / `Recording` / `Saving` / `Save failed` with spinner/dot/check), an edit (pencil) button, the transcript body (`aria-live`), and a footer of exactly four actions: **Copy Transcript · Download Transcript · Download Audio · Combine**. Empty state: mic mark + "Start a transcription" + one explanatory line. |
| `src/components/SettingsSheet.tsx` (63) | The key modal, verbatim: title **"Meta API key"**, body **"Replace the key used for Muse transcription."** (when a key exists) or "Add a Model API key to begin transcribing.", label **"API key"**, password input placeholder **"Paste your Meta Model API key"**, button **"Save and Verify"** (→ `Verifying…` → `Verified`), then a `<small>` helper line. |
| `src/App.tsx` (365) | Autosave on stop (`showToast('success','Transcription saved')`), auto-open of the key sheet when no key is configured, one `messageFromError()` mapper that turns raw failures into plain language. |

## The target structure (from the decision)

```
LEFT COLUMN
  Transcriptions                API Key      <- plain clickable text, not a gear
  FOLDERS
    New Folder
  RECENT
    compact chronological transcript list

MAIN
  top-right:  Upload Audio   Record More   Record
  content:    large title · Saved/edit state · readable transcript (scrollable body)
  bottom:     Copy Transcript · Download Transcript · Download Audio · Combine

API KEY MODAL (from the API Key text button)
  Meta API key
  Replace the key used for Muse transcription.
  API key
  [ Paste your Meta Model API key ]
  Save and Verify
  (no helper paragraph below Save and Verify)
```

## Current Kel: measured divergence

Files: `desktop/packages/desktop/src/renderer/pages/kel/transcription/index.tsx` (1109 lines) and
`index.module.css` (173 lines). Live text captured from the running build:

> `FOLDERS` / "Group recordings into folders — drag a transcript onto one." / `Add` / `RECENT TRANSCRIPTIONS` /
> "Nothing here yet." / "Practice mode" `Source` / `Record` `Upload Audio` / "Your transcripts live here…"

| # | Divergence | Severity | Where |
|---|---|---|---|
| T1 | **No "Transcriptions" column title.** The column starts directly with `FOLDERS`. | S3 | `index.tsx:618` |
| T2 | **The key entry point is a bottom "Source" text button**, not a top-right **API Key** affordance, and it opens a modal titled **"Transcription source"** with a "Connect" button and a Muse/practice-mode paragraph. | S2 | `index.tsx:930-960` (Modal), `:849` (`Source`) |
| T3 | Section titles are `FOLDERS` / `RECENT TRANSCRIPTIONS` (uppercase via CSS `text-transform`), not `FOLDERS` / `RECENT`. | S4 | `index.module.css:24-31`, `index.tsx:714` |
| T4 | Main action order is **Record (primary, filled) → Upload Audio → Record more**, i.e. reversed from the donor, and `Record more` appears only when the selected transcript has `source_type === 'recording'`. | S2 | `index.tsx:759-777` |
| T5 | The document title is `<strong class='text-16px'>` + a `Rename` button — not a large title with a Saved/edit state. | S2 | `index.tsx:826-856` |
| T6 | Actions row is **eight wrapping buttons**: Copy Transcript, Download Transcript, Download Audio, "Combine with…", **Send to chat**, **Use as vetting answers**, **Think out loud**, **Delete** (danger). The donor's four are buried among Kel-specific additions. | S2 | `index.tsx:884-929` |
| T7 | A **folder `<Select>` ("move-select")** and a metadata line sit between the title and the transcript — the donor moved transcripts by dragging in the sidebar. | S3 | `index.tsx:858-882` |
| T8 | Everything is a rounded panel **inside** the page: `.sidebar` and `.workspace` are both `border 1px + radius 10px + bg-2`, plus a bordered `.recordBar` — i.e. panels-in-a-page rather than a column + a document. | S2 | `index.module.css:9-23, 90-104` |
| T9 | Styling uses **donor tokens** (`--color-bg-2`, `--color-border-2`, `--color-text-3`, `--color-fill-*`, `--color-primary-light-*`), not the Kel dark set. | S2 | `index.module.css` throughout |
| T10 | **Measured contrast failures** on this page: light `3.24:1` for section titles and meta text (needs 4.5); dark `2.21:1` for the `Source` button. | S1/S2 | see `08_DARK_LIGHT_READABILITY.md` |
| T11 | Folder rows expose always-visible `✎` and `✕` glyph buttons, and the "New folder" input + `Add` button sits at the **bottom of the folder scroll area** rather than under the FOLDERS header. | S3 | `index.tsx:668-712` |

**What is already right and must be preserved:** the data layer (`library`, `folders`, `recent`, `status`,
`keyDraft`, drag-to-folder with `data-folder-id`, upload/record/live-text, restart-visible rows), the
autosave/live-text behaviour measured green in the main thread's own scenario, `aria-live` on the live bar,
`prefers-reduced-motion` handling for the recording dot, and the drag drop overlay.

## What to change (implementation view — no code written yet)

1. `index.tsx`: add the column header row — `Transcriptions` (title) + a plain **API Key** text button that opens
   the key modal; delete the bottom `Source` row (`index.tsx:845-853`) and keep the connection status as a
   quiet line only where it is actionable.
2. `index.tsx`: replace the whole `Modal title='Transcription source'` block with the donor's key modal copy
   (title **Meta API key**, body **Replace the key used for Muse transcription.**, label **API key**,
   placeholder **Paste your Meta Model API key**, submit **Save and Verify**) and **no helper paragraph**.
3. `index.tsx`: move the main action row to the top-right of the workspace and reorder to
   **Upload Audio · Record More · Record**; make `Record More` always present but disabled when there is no
   recording to append to (donor behaviour), instead of appearing conditionally.
4. `index.tsx`: promote the document title to a large title with the saved/edit state beside it, and
   demote rename to a hover/secondary action.
5. `index.tsx`: keep Copy / Download Transcript / Download Audio / Combine as the primary bottom group, and
   move **Send to chat · Use as vetting answers · Think out loud · Delete** into a secondary group
   (hover-revealed or an overflow menu) so the donor's four read first.
6. `index.module.css`: retarget every donor variable to the Kel token set, and reduce the page to
   **column + document** (one border between them, not two floating panels).
7. Rename the second section title to **RECENT**.

## Risk notes

* The transcription page is **renderer-only** for this change: the engine API (`/api/transcription`), the
  store, and the composer mic hand-off are untouched, so the blast radius is one page + one CSS module.
* The page carries the main thread's E2E selectors (`data-testid='transcription-page'`, `record-button`,
  `upload-button`, `folder-create`, `transcript-row`, `live-text`, `stop-button`, …). Every rename/move above
  must keep those test ids or update the scenario in the same change — otherwise the 'transcription'
  scenario in `packaging/ux-audit.cjs` breaks.
* `--color-primary-light-*` is the donor blue; Kel's accent is green. Any element still using it (drop
  targets, `rowActive`) will look like a different product until retargeted.
