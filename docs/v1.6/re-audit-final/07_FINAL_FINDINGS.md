# 07 — FINAL FINDINGS (final re-audit)

Every `RA-*` item found by this independent re-audit is recorded here. Nothing was repaired
(absolute no-repair rule honored). Counts: **RA-BLOCK 0 · RA-MAJOR 0 · RA-MINOR 3 · RA-SUG 4**.

---

## RA-MINOR-001 — Budget reservation aggregation is not atomic (concurrent oversubscription)

- **Severity:** MINOR (latent; NOT production-reachable in V1.6 as shipped — escalates to MAJOR
  the day the delegation/pods feature is wired without a transactional reservation)
- **Related:** AUD-MINOR-002 (sibling path of the same invariant)
- **Subsystem:** runtime — `kel/assignment.py::reserve_budget` ("authoritative budget" for
  Phase-5.3 delegation; job envelope = `budget - spent - reserved - committed`)
- **Reproduction (first-party):** `probes/ra_attack_engine2.py` section C8 — five threads, one
  barrier, five `reserve_budget(cost=3)` calls against an envelope of 8. In **15/15 rounds**,
  4–5 calls passed the check (each read `committed = 0` before any insert) and committed
  12.0–15.0 — e.g. round 0: 5 successes, committed 15.0 > 8. Sequential battery C1–C7 is green,
  so the campaign's "successive reservations can no longer sum past" claim holds only for
  non-concurrent callers. Raw output: `evidence/ra-attack-major2.txt` (C8).
- **Why reachable in principle:** the service runs a `ThreadingHTTPServer`; the check (one
  connection) and the insert (another connection) are not a single transaction and are not
  serialized by a lock. The finding's own text ("every reservation that has not been explicitly
  released narrows the same envelope") is false under concurrency.
- **Why not release-blocking today:** the only callers are the dormant delegation/pods helpers
  (`delegate()`/`run_d1`/`run_d2` — module docstring: "Nothing live calls these functions yet";
  gated by `KEL_WORKFORCE`, default off; no service route reaches them). The shipped V1.6
  scheduler budget (run slots in `core.py`) is separate and transaction-guarded.
- **Acceptance criteria:** (1) make reservation atomic — single transaction (`BEGIN IMMEDIATE`)
  or a conditional insert that re-validates `SUM(cost) + cost <= remaining` inside the write;
  (2) a storm test (the C8 shape) must fail pre-fix and pass post-fix; (3) keep C1–C7 green;
  (4) when the delegation feature is wired, add settle/release on completion and failure
  (`release_budget` currently has no production caller — fail-closed today).

---

## RA-MINOR-002 — Installer failure/repair UX still carries donor branding (AionUi)

- **Severity:** MINOR (user-visible branding on error/repair paths of the release artifact; no
  security or functional impact)
- **Related:** C-DISC-001 (neighboring-scan sibling), AUD-MINOR-007 family (donor surfaces)
- **Subsystem:** packaging — `desktop/resources/windows/installer-messages.nsh` (compiled into
  the NSIS installer via `windows-installer-x64.nsh -> installer-common.nsh`), plus
  lock-dialog strings in `installer-repair-heal.nsh` / `installer-remove-registry.nsh` /
  `installer-process-control.nsh`
- **Reproduction:** read the compiled set (`grep -n "AionUi" installer-messages.nsh` — dozens of
  bilingual strings), or trigger any failure/repair path (extract failure, verify failure,
  locked files, reinstall-over) and observe dialogs such as "AionUi installation failed",
  "Please reinstall AionUi…", "Close AionUi, terminals…", and the consent prompt "Send this
  installer failure report to the AionUi team?". Evidence:
  `evidence/ra-installer-donor-strings.txt`.
- **Report-path note (checked, not a security hole):** the consent prompt runs
  `support/report-installer-failure.ps1` with the build-time DSN; this audit's build (and the
  repair build) bake an EMPTY DSN (`support/_sentry-dsn.generated.nsh`), and the script's
  `if ([string]::IsNullOrWhiteSpace($Dsn))` branch writes `status=skipped, reason=empty-dsn`
  with **no network call**. The prompt text is nevertheless donor-branded and promises a report
  to a team that does not exist.
- **Release impact:** violates the release-artifact branding gate on reachable (failure) paths;
  success path is Kel-branded. No blocker; polish before shipping.
- **Acceptance criteria:** every user-visible installer string uses the Kel product name (or is
  product-name-driven); the report consent prompt names Kel and states truthfully what happens
  with no DSN configured; installer failure-path smoke (forced extract failure or locked-file
  path) shows no "AionUi" anywhere; a grep gate over `desktop/resources/windows/**.nsh` for
  donor-visible strings passes.


---

## RA-MINOR-003 — Desktop Pet settings: the enable toggle "lies" until reload (silent refusal)

- **Severity:** MINOR (user-visible misleading control on a donor surface; the security property
  "cannot enable" HOLDS — nothing activates; the main process state stays honest)
- **Related:** AUD-MINOR-008 (settings surface cannot enable the pet)
- **Subsystem:** desktop — `renderer/pages/settings/PetSettings.tsx` +
  `process/bridge/systemSettingsBridge.ts` (`setPetEnabled` provider)
- **Reproduction (first-party, installed product):** open `#/settings/pet` (the sider lists
  "Desktop Pet" on desktop builds); the enable Switch (`pet.enable`, switch #1) reads
  `aria-checked=false`; click it — it reads `true` and STAYS true. The main process's refusal
  branch (`enabled && !KEL_PET_SUBSYSTEM_ENABLED`) persists `pet.enabled=false` and **returns
  normally (no rejection)**, while the renderer only reverts inside `.catch()`. Decoded
  `kelwork/host/config/aionui-config.txt` shows persisted `"pet.enabled":false`; after a route
  change the switch re-syncs to `false` (`afterReload` in the results JSON; screenshots
  `ra-pet-before/after/reload.png`). Evidence: `evidence/ra-isolation/out/ra-stunt-results.json`,
  `ra-pet-*.png`.
- **Analysis:** the campaign's own comment ("never fall back to ON, which would reintroduce the
  'UI lies' state this fix eliminates") shows the intent; the refusal path resolves silently and
  reintroduces exactly that state until reload. No pet window is created (the refusal branch does
  not call `createPetWindow`; policy + guards verified), so this is a UI/UX + donor-branding
  defect, not a security regression.
- **Release impact:** polish-grade; objective dead-control on an advertised surface.
- **Acceptance criteria:** on refusal, reject the invoke with a reason so the toggle reverts AND
  the user sees why; add a renderer test (policy off -> toggle returns to OFF, feedback shown);
  optionally hide the Desktop Pet section when the subsystem is disabled; keep the
  "cannot enable" property pinned by the existing donor-policy tests.

---

## RA-SUG-001 — Universal-root containment wording vs behavior (delegation path validator)

- **Severity:** SUG (documentation + latent-boundary note; no reachable effect today)
- **Related:** AUD-MINOR-006
- **Subsystem:** runtime — `kel/workforce.py::_path_within` (universal root `.`) /
  `authority_within`
- **Reproduction:** `_path_within('..', '.') → True`, `('../x', '.') → True`, `('C:/x', '.') →
  True`, `('/x', '.') → True`; `authority_within({'write_scope': ['..']},
  {'write_scope': ['.']}) → None` (no gap reported). Evidence: `ra-attack-major2.txt` E5.
- **Analysis:** the campaign documents root `.` as "universal by design" and pins relative-path
  behavior (`tests/test_v16_r1_authority.py::test_a_dot_root_stays_universal_by_design`), but the
  same docstring states absolute/drive/escaping paths "can never be contained in a relative
  scope" — false for the universal root; the `root == '.'` early return precedes the `None`
  (un-representable path) check. Consequence: when a delegator's scope is `.`, the narrowing
  validator does not flag `..`/absolute scope entries. The intended safety net is an
  "effect-time filesystem boundary" that does not exist yet (the feature is dormant and
  `write_scope` has no enforcement consumer today).
- **Release impact:** none reachable; latent for the delegation feature wiring.
- **Acceptance criteria:** either (a) reorder the checks so un-representable spellings are refused
  even under a `.` root, or (b) keep universal semantics but pin the `..`/absolute case
  explicitly in tests and document the effect-time boundary requirement at the validator; fix the
  docstring sentence; add pins `('..','.')`, `('../x','.')`, `('C:/x','.')`, `('/x','.')`.

---

## RA-SUG-002 — Donor names in installer fallback lists and internal artifacts

- **Severity:** SUG (hygiene; no user-visible path, no behavior change)
- **Related:** C-DISC-001 (sibling scan)
- **Subsystem:** packaging — `support/query-lockers.ps1` (`'AionUi.exe'`, `'Uninstall
  AionUi.exe'` in the known-files fallback list; the script enumerates all top-level files
  anyway), `installer-observability.nsh` fallback log name `aionui-installer-*.jsonl`,
  `installer-repair-heal.nsh` temp `AionUi-fixed-uninstaller.exe`.
- **Reproduction:** `grep -n "AionUi.exe" support/query-lockers.ps1` (lines 81–82). Evidence:
  `evidence/ra-installer-donor-strings.txt`.
- **Release impact:** none (behavior rename-proof); record for consistency.
- **Acceptance criteria:** fallback entries use `${PRODUCT_NAME}`-derived names (`Kel.exe`,
  `Uninstall Kel.exe`); optional: rename temp/log artifacts; re-run installer smoke after.

---

## RA-SUG-003 — Name the Work-surface exception in the approval-ownership documentation

- **Severity:** SUG (documentation precision of the security model)
- **Related:** AUD-MAJOR-001 (adjacent-surface determination)
- **Subsystem:** docs/runtime — the recorded claim "the resolution authority boundary is the
  scoped write path" (Campaign C `01_FINDING_DISPOSITIONS.md` context) vs the reproduced
  `/api/autonomy` by-id resolve that settles any boundary request without a conversation
  parameter (`ra-attack-major1.txt` B7, `status=GRANTED`).
- **Analysis:** the chat-path invariant ("resolution requires declaring the owning conversation;
  omission acts as `main`") is enforced and verified. The autonomy route is a deliberate Work
  surface with global reach; the declaration it skips is a scope assertion, not authentication,
  so the exception does not widen the practical capability model (ids are listable). The claim
  reads as if ALL resolution paths carry the ownership check, which is only true of the chat and
  legacy paths.
- **Release impact:** none functional; improves auditability of the model.
- **Acceptance criteria:** document the Work-surface exception beside INV-APPROVE-002 (or its
  successor): chat resolve + legacy `/api/approval` are conversation-scoped; `/api/state` is an
  unscoped read list; `/api/autonomy` resolve is an unscoped by-id admin action. Optionally add
  a future-hardening note (require conversation context on the Work surface too).


---

## RA-SUG-004 — Uninstaller leaves an empty dir + dead shortcuts when the install directory is held

- **Severity:** SUG (robustness note; NOT reproduced in supported flows)
- **Related:** C-DISC-001 sibling (uninstall lifecycle); §24 shortcut-cleanup battery item
- **Subsystem:** packaging — NSIS uninstaller cleanup behavior
- **Reproduction matrix (first-party, 5 cycles):** all supported invocations clean everything
  (install dir, both shortcuts, ARP; data roots retained) —
  `Uninstall Kel.exe /currentuser /S` (the ARP-registered command), bare `/S` from a neutral cwd,
  and bare `/S` with a held file handle inside the tree. Only when a foreign process keeps its
  working directory pinned **inside the install dir** through the uninstall (reproduced 2/2) does
  the uninstaller exit 0 while leaving an EMPTY install dir plus both dead shortcuts. Evidence:
  `05_INSTALLED_PRODUCT.md` matrix.
- **Analysis:** the condition is a harness/edge construction (the uninstaller itself relocates to
  TEMP; normal uninstalls do not have a foreign cwd held there), but any real equivalent
  (a process pinning the directory) would leave dead shortcuts with no warning.
- **Release impact:** none for supported flows; record for uninstaller robustness.
- **Acceptance criteria:** delete shortcuts even when the install-dir removal fails (or retry /
  deferred cleanup), optionally surface a residue warning; add the cwd-pinned cycle to the
  battery as a known condition.

---

**No other final re-audit findings were identified.** `NO NEW FINAL RE-AUDIT FINDINGS` does NOT
apply (5 items above); no BLOCK or MAJOR was found. Nothing here was fixed — all items are for a
future campaign or Nick's disposition decision.
