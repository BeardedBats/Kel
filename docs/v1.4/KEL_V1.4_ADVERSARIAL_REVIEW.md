# KEL V1.4 — ADVERSARIAL ACCEPTANCE REVIEW (Gate 10)

Status: v1 (2026-09-15). Produced by `packaging/adversarial-review.py` (repeatable in one command):
it checks the **shipped tree** against the criteria this project committed to — the design system's
do-not-ship list, the packaged-app contract, ledger honesty, evidence coverage, and the code smells a
hostile reviewer looks for first. Findings below are the sweep's own output, not a recollection.

    python packaging/adversarial-review.py

## 1. Sweep result

| Severity | Area | Finding |
|---|---|---|
| INFO | ledger | 200 rows; statuses `IMPLEMENTED 58 · EXTEND 85 · NEW 29 · ALREADY_PRESENT 28` |
| INFO | ledger | rows advanced past triage: **58/200** (each cites the artifact that delivered it) |
| LOW | ledger | 142 rows remain at triage — detail lives in the per-gate blocks and the `surface` column; advancing them row-by-row is a freeze-time task (§3.2) |
| INFO | engine-hygiene | **3** silent `except Exception: pass` sites, **every one carrying an inline justification** |
| INFO | evidence | 20 acceptance-matrix rows · **527** capture files on disk |

**Blocking findings (high + medium): 0.**

## 2. Criteria checked, and what the sweep proves

1. **Do-not-ship list** — emoji in Kel UI sources: `0`. Gradients in renderer styles: `0` (the six
   gradient/cream toast fills were flattened in G9). Bounce/overshoot easing: `0`. Reduced-motion
   fallback present: yes (global `*` rule in `kel-tokens.css`).
2. **Engine hygiene** — `print()` in V1.4 modules: `0`. TODO/FIXME markers in V1.4 sources: `0`.
   Silent catches: 3, each justified inline (diagnostics span, quota observation, handoff enrichment).
3. **Packaged-app contract** — `KelService.ts` still carries the route allowlist, and all five V1.4
   routes (`brief`, `team`, `providers`, `autonomy`, `diagnostics`) are present in it; the credential
   custody module `kelCredentials.ts` exists.
4. **Evidence coverage** — 20 acceptance-matrix rows and 527 captures on disk (baseline, directions, G4–G9,
   dark, dense, populated, pets, comparisons).
5. **Ledger honesty** — 200 rows, correct triage distribution (81 NEW / 91 EXTEND / 28 ALREADY_PRESENT at
   G0 → 29 NEW / 85 EXTEND after 58 rows advanced), every advanced row citing its delivering artifact.

## 3. Findings that are *not* blockers, recorded rather than smoothed over

### 3.1 Ledger granularity (LOW, freeze-time task)
Rows advanced to `IMPLEMENTED` are exactly the surface families whose delivery is unambiguous because both
the module and its tests exist, or because the page renders in a capture:

| Surface family | Rows | Delivering artifact |
|---|---|---|
| `runtime:solution` | 17 | `runtime/kel/solution.py` + `tests/test_v14_solution.py` (G3) |
| `runtime:team` | 12 | `runtime/kel/team.py` + `tests/test_v14_team.py` (G3) |
| `runtime:provider` | 6 | `runtime/kel/providers.py` + `tests/test_v14_providers.py` (G6) |
| `runtime:autonomy` | 4 | `runtime/kel/autonomy.py` + `tests/test_v14_autonomy.py` (G6) |
| `shell:team` | 8 | `pages/kel/team` + captures `g4` (G4) |
| `shell:autonomy` | 3 | `pages/kel/autonomy` + captures `g6` (G6) |
| `shell:diag` | 8 | `pages/kel/diagnostics` + captures `g8` (G8) |

The remaining 142 rows stay at their triage status **on purpose**: `shell:work` alone holds 57 rows and
only some shipped (verification panel, continuation chooser, dense mode), so a blanket advance would
over-claim. The remediation is a row-by-row pass surface-family by surface-family (with the capture or
test that proves each) before the package is frozen — deliberately left visible rather than silently done.

### 3.2 Carried limitations (stated in earlier gates, restated here for the release record)
- Engine shutdown on app close still needs the harness's bounded kill.
- A profile migrated from V1.3 sees the first-run flow once (documented deviation of the flag-only rule).
- Provider live calls remain donor-dependent; no real API keys were exercised.
- Unused lazy imports remain declared in `Router.tsx` after the G7 redirect rewiring (the sweep lists them
  when present).

## 4. What this review does *not* claim

- It is a **static + evidence sweep**, not a vision-based aesthetic verdict. Aesthetics were argued from
  measured contrast, type, focus and density evidence, and from the earlier independent design review.
- It does not re-run the packaged harnesses; their results live in `KEL_V1.4_TEST_MATRIX.md` and the
  screenshot manifests.
- Absence of a finding is not proof of absence of a defect — it is proof that the named checks passed on
  the tree as it stands at this commit.
