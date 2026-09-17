# 08 — Release timing

The V1.6 program has an immutable checkpoint: `v1.6.0-pre1` (tag on `f24d9c2`, artifact source
`0fb095f`), frozen at `Kel Releases\Kel-V1.6.0-Pre1-Frozen`, verified 3/3. Nothing here proposes
touching it. Program state is Phase 0–3 complete and committed; Phase 4 (i18n / donor-string
cleanup) is the next unstarted phase.

The question for each candidate is not "is it good" but **"is it worth spending release stability
on"**.

## 8.1 Answers per candidate

| Candidate / action | Required before final V1.6? | Safer immediately after? | Behind an adapter? | Destabilises this release? |
|---|---|---|---|---|
| **A1** — validate engine on reuse | **No, but it is cheap and it closes a real defect.** Recommend in-window if the program has room; otherwise first patch after | Also fine after — but the defect stays open until then | Yes — one pure `reuse \| restart` decision function | **Low.** Touches one boot branch; verifiable against existing packaged smoke and acceptance |
| **A2** — stop swallowing restore failure | **No.** Recommend in-window; it is an error-reporting fix | Fine after | Yes — one error path | **Low.** Surgical |
| **A3** — assert the shutdown handshake | **No.** Before the final freeze if there is room, because it improves freeze evidence quality | Fine after | n/a — harness only | **Very low.** Test-side only; no product code |
| **A4** — record memory/CPU | **No.** Before final freeze if room; it is instrumentation | Fine after | n/a | **Very low.** Additive fields + existing Diagnostics surface |
| **A5** — fix `freeze-release.ps1` duplicate nesting | **Yes — before the final freeze.** The freeze tool is *used by* the final release, and the nesting broke candidate↔frozen byte identity at pre1 and was corrected by hand | Too late — the freeze is the moment | n/a | **Low**, but it removes a manual step whose omission silently corrupts the release record |
| **TARGET-2** — native supervisor (Rust) | **No. Explicitly not before final V1.6.** | **Yes** — this is the right window *if* a trigger ever fires | **Yes** — that is exactly what B0 buys | **Yes, materially.** It would replace startup, shutdown, spawn and the engine boundary on the release's critical path |
| **Anything touching SQLite / IPC payloads / authorization** | **No, at any time.** | Not recommended after V1.6 either | Only nominally | **Severe** |

## 8.2 The timing argument, stated plainly

**Nothing in this audit belongs before the V1.6 final freeze, except `A5`, and `A2`/`A1` if the
program wants them.**

`A5` is the exception because it is *release-record integrity*, not product behaviour: a freeze
tool that silently nests an inert duplicate forces a manual correction, and a manual correction
during a final freeze is precisely how a candidate stops being byte-identical to its frozen copy.
The pre1 record already had to do this by hand; the instruction to fix the tool is recorded in
`docs/v1.6/AUTO_RESUME.md`.

`A1` and `A2` are small and independent of the freeze. They close the audit's two architectural
findings, both of which are real defects in the shipped line. If the program has no room, they are
not release blockers — neither one has produced an observed user-facing failure yet — but they
should not be forgotten after the freeze either.

`TARGET-2` is **not** a pre-freeze candidate under any reading. It would put new, unproven,
compiled code on the boot path, the quit path, and the engine boundary, immediately before a
release that already carries an immutable checkpoint and a validated packaged battery. That is the
worst available trade: taking on maximum risk to deliver benefit that has not been demonstrated to
exist.

## 8.3 Why "after V1.6" is the right window *if* a trigger fires

The post-release window has properties the current one does not:

- The packaged acceptance battery and frozen artifact stay available as a fixed regression baseline.
- The adapter seam (`B0`) is pure refactor and can land with the release's normal cadence, with no
  native code at all.
- A supervisor swap is then a *contained* change behind an existing seam, with a clean revert.
- No frozen checkpoint depends on it.

That is the sequence: **seam now or later, native only on evidence.** Adopting Rust before a
measurement exists inverts the audit's whole method.

## 8.4 Interaction with the frozen checkpoints

- `v1.6.0-pre1` — untouched by this audit; verified untouched.
- V1–V1.5 frozen releases — untouched; read only.
- The audit's own work is confined to `kel-rust-audit` (branch `audit/rust-runtime`, pinned at
  `ffeef73`). Nothing has been merged, and merging is not this audit's call.

## 8.5 Recommendation to the V1.6 Integration Coordinator

For the release in front of you: **schedule `A5` before the final freeze; consider `A1`/`A2` if
there is room; defer `A3`/`A4` to taste; do not schedule any Rust work.**

For after the release: **if and only if** a re-open trigger in `07` fires, run `B0` then `B1` then
`B2`. If no trigger fires, the correct outcome is that `TARGET-2` is never built — and that is a
successful audit result, not a missed opportunity.
