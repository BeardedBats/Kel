# 05 — Routing (Kel V1.5)

Status: **skeleton** — lands with the G5 routing work (Workstreams 14–15).

Two layers: deterministic routing over real signals (capability, health, auth, quota, cost,
latency, session continuity, tool needs) and bounded learned weighting from recorded outcomes
(task class, worker, success/failure, escalation, verification result, cost, latency). Learned
signals advise deterministic routing and never silently override hard capability rules.
