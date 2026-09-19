# REPAIR RESUME — Campaign C

**Fresh-context re-entry map.** Campaign C repairs the 12 Campaign B findings; nothing is released.

## Where the work lives
- Repair worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-final-repair`, branch `repair/v16-final` (base = audit head `a3490095889222862ea13b4b696166c0ddc5bf0f`).
- Repair record: `docs/v1.6/repair-final/` (this directory); findings ledger: `docs/v1.6/audit-final/MASTER_FINDINGS.md` (Campaign C fields appended, never rewriting audit history).
- Read-only references: `kel-v16-final-audit` (audit records + probes + evidence), `kel-ux-v15` (RC @ `08f5667`), `Kel-Repo` (`main` @ `5e76b21`).

## State at initialization
- Integrity verified end-to-end (see `00_REPAIR_BINDING.md` §1): all checks YES; nothing missing.
- 0 findings dispositioned; first finding in progress: `AUD-MAJOR-001`.

## Next actions (ordered)
1. `AUD-MAJOR-001`: capture pre-fix attack replay + failing discriminating tests; apply the narrow fix (`chat_approvals.require_owned` unconditional with `main` default; `/api/approval` route scoped with the same helper); re-run focused + adjacent + replay; commit.
2. `AUD-MAJOR-002` (privileged IPC sender validation): read pass docs `07`/`13`/`15` + desktop main-process code; design one shared sender guard; per-channel tests.
3. MINORs in severity order (`002`, `003`, `006` security-adjacent; `004`, `005` evidence/corpus; `007`, `008`, `009` donor; `001` ledger), then `AUD-SUG-001`.
4. Full regression, package build + installed battery, migrations/persistence, isolation checks; finalize `docs/v1.6/POST_REPAIR_RELEASE_CANDIDATE.md`.

## How to verify current state
- `git -C kel-v16-final-repair log --oneline -8`; `git status` clean except declared build artifacts.
- Engine suite: `cd runtime && python -m pytest tests -q`; probes under `kel-v16-final-audit/docs/v1.6/audit-final/probes/`.

## Hard rules (still binding)
- No release, no freeze, no `main` movement, no final independent audit; `HUMAN_VISUAL_GATE` stays PENDING.
- Every repair needs: reproduction, discriminating test, attack replay, evidence, commit — then continue.
