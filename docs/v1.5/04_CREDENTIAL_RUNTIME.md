# 04 — Credential Runtime (Kel V1.5)

Status: **skeleton** — lands with the G4 credential-injection work (Workstream 7).

Target flow to implement and prove: trusted runtime → OS secure store → injected only into the
intended process/request → never persisted in the engine DB, never returned to the renderer, never
written to logs. Process-scoped environment injection and request-scoped headers are preferred;
global environment mutation, renderer exposure, DB storage, plaintext files, and debug logging are
prohibited. Leak-detection tests are part of the acceptance evidence.
