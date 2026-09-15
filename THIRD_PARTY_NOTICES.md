# Third-party notices and provenance

This repository contains original Kel code (Apache-2.0) plus the components below.
Packaged binaries are never stored in git; see the README for the binary/release policy.

## Components included in this repository

| Component | Upstream | Pinned revision | License | Role in Kel | Status |
|---|---|---|---|---|---|
| AionUI (Aion Donor Shell) | https://github.com/iOfficeAI/AionUi | 6744099b279b991c17e31c243f0920477bd31cb6 (2.2.2) + local Kel modifications | Apache-2.0 | Desktop shell source (`desktop/`) | Modified fork (see `third_party/AIONUI-PROVENANCE.md`) |
| AionCore (KellShell) | https://github.com/iOfficeAI/AionCore | 47e66d0d151123e973b3fd1e77afcb5671b3f8c5 (bundled v0.2.2) | Apache-2.0 | Conversation/ACP host in packaged builds | License record only; binary not in repo |

Attribution requirements: retain the Apache-2.0 license texts (`third_party/AionUI-LICENSE.txt`,
`third_party/AionCore-LICENSE.txt`), the `NOTICE` file, and the modification notes above in any
redistribution. The desktop fork remains Apache-2.0 and is not an official AionUI release.

## Build and tool dependencies (obtained separately; not committed)

| Component | License | Role |
|---|---|---|
| Electron / Chromium | MIT / BSD-style | Desktop runtime frame (installed by the desktop build) |
| @electron/asar | MIT | asar packing/inspection tooling used by `packaging/` |
| PyInstaller | GPL-2.0 with bootloader exception | Runtime packaging tool (build-time only) |
| Python standard library | PSF | Runtime engine |

## Evaluated donors (reference-only; no code copied)

These projects were studied during development. **None of their code is present in this
repository.** Records are kept for auditability; the full audit is
`docs/v1.3/KEL_V1.3_DONOR_AUDIT.md` on the `v1.3-dev` branch.

| Donor | License | Use |
|---|---|---|
| NousResearch/hermes-agent | MIT | Patterns only (memory interfaces, context fencing) |
| Untrivial-ai/agent-orchestrator | Apache-2.0 | Patterns only (derived status, fail-closed observations) |
| ephor/warpforge | MIT | Patterns only (wake/attach semantics) |
| Chuzom/Chuzom | MIT | Patterns only (freeze frontier, bounded escalation) |
| Orkas-AI/Orkas | MIT | Patterns only (context budget) |
| microsoft/conductor | MIT | Patterns only (schema validation, terminate step) |
| pioneerdotai/pioneer | MIT | Patterns only (self-review ban, evidence classes) |
| Adulari/forge | **AGPL-3.0** | **Ideas only — zero copied code** |
| ryderderder/orchestrator | MIT | Patterns only (exact-session resume) |
| xopcai/xopc | MIT | Patterns only (worker budgets) |
| block/goose | Apache-2.0 | Patterns only (recursion refusal) |
| agentscope-ai/CoPaw (ex-QwenPaw) | Apache-2.0 | Patterns only (ACP lifecycle) |
| iOfficeAI/AionUi + AionCore | Apache-2.0 | Adopted (fork/bundled component; see above) |
| orthogonalhq/nous-core | AGPL-3.0 | Ideas only; zero code |
| eric-cielo/moflo | (reference) | Rejected (learned routing) |

Note on AGPL donors: `Adulari/forge` and `orthogonalhq/nous-core` are AGPL-3.0 and remain
ideas-only. No code, text, or assets from them may be copied into Kel. Any future contribution
that copies or adapts donor code must first update this file with the exact repository,
revision, license, adopted files, and required notices; AGPL/LGPL code must never be copied.
