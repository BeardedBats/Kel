# 08 — V2+ Backlog

Broader ambitions kept out of V1.x. Each item notes why it belongs beyond V1.5 and what it depends on.
V1's deliberate scope decisions (project-scoped memory, flat Kel→Worker delegation, one local user) are
respected here rather than reversed.

## Assistant scope
- **Personal-life memory (calendar, contacts, personal context):** V1 memory is deliberately
  project-scoped with a trust/provenance ladder (`memory.py`). Broad personal memory needs new consent,
  provenance, and retention models on top of V1's trust ladder — V2+.
- **Proactive behaviors** (scheduled watch tasks, inbox/calendar awareness): requires the personal
  context layer above and stronger autonomy enforcement (D-01) first.

## Orchestration
- **Supervised agent trees** (beyond the flat Kel→Worker model): V1 pins a bounded, flat topology with
  no worker-spawning (test-enforced per-tool denial). Trees need per-node leases, budgets, and
  supervision semantics — and only once enforcement is real, not checker-only.
- **Fleet-level quota/cost optimization** across providers and accounts on top of the V1.4 provider
  state model.
- **OS-level sandboxing for native workers** (Windows sandbox/containers/VM) to make containment claims
  structural rather than snapshot-topological.

## Ecosystem & product surface
- **MCP/plugin ecosystem** and a shareable recipe/skill marketplace (V1 recipes are project-local).
- **Cross-device continuity / sync** and **multi-user or shared workspaces** (V1 is single-instance,
  single-user, loopback-only by design).
- **Analytics and cost dashboards** built on V1.4's measured diagnostics pipeline.
- **Vision/aesthetic self-review tooling** so future gates can carry visual sign-off instead of the
  recorded "no vision-based aesthetic verdict" limitation.
