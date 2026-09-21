# V2-14 — Network permissions (2026-09-21)

Increment: directive §19 (“NO INTERNET / APPROVED DOMAINS / FULL INTERNET; per-tool rules;
per-Project rules; show contacted domains; block unexpected domains; ask before a new domain; access
history — keep this practical”), built as the **rule source behind the seam that already existed**,
never as a second path.

## What was already true (measured, not assumed)

- `kel.connections.network_rule(host)` is the one hook every outbound Connection path shares: asked
  about the host **before anything leaves the computer** and again about the host a redirect landed
  on; a hook that cannot answer fails closed with its own sentence; `NETWORK_RULES = None` meant
  “open” (V2-04 hardening, D-36).
- All outbound traffic already flows through `perform_request` (single opener, bounded redirects,
  capped Retry-After), and every performed call is recorded in `connection_events`
  (`at, connection_id, action, domain, status, state, attempts, ms`).

## What this increment added

| Piece | Where | What it does now |
|---|---|---|
| The rule source | `kel/network_policy.py` (new) | Modes `none` / `approved` / `full` (`DEFAULT_MODE = 'full'`: with no policy rows, behaviour is exactly as before until a person chooses); scopes `default` and `project:<id>`; per-tool rules keyed by the tool string (`connection.action`); approved-domain matching exact or parent (`github.com` covers its subdomains). |
| Ask before a new domain | `decide()` + `network_requests` | In `approved`, an unlisted host is **not sent**: it is recorded as a pending request and refused with one plain sentence naming the fix (“Approve it in Connections, or change that scope to full internet, then ask again.”). `resolve_request` approves (adds the exact host to that scope's list) or denies. One pending ask per (host, scope, tool). |
| Access history | `network_events` + `history()` | Every decision is recorded with host, tool, project, scope, decision (`allowed` / `blocked` / `ask`) and reason; `connection_events` still records the calls that were actually made. |
| Context through the seam | `network_rule(host, context)`, `perform_request(..., context=…)`, `Connections.test/run(..., context=…)` | The tool and project travel with the call, so per-tool and per-Project rules are possible without a second choke point. A one-argument rule source keeps working (arity fallback). |
| Per-store binding | `bind()` / `unbind()` around `Connections.test/run` | The policy is bound to one engine store only around the outbound call, and **an explicitly configured hook always wins** (the seam's own hardening tests keep their deliberate hooks). |
| Surface | `/api/connections {action:'network', op: get/set_mode/set_tool/clear_tool/requests/resolve/history}` | The person sets the modes and lists; the pending asks are resolved with the same approve/deny vocabulary. |
| The bridge | `connection_tools` passes `context={'tool': '<connection>.<action>', 'project': …}` | An assistant-driven call obeys the same rules, with its project attached. |

## Verification (on the final code of this increment)

- `tests/test_v2_network.py` (new, 14 tests) — default is `full` (nothing changes); `none` blocks with
  the sentence and records it; `approved` matches exact and parent domains; an unlisted host **asks**
  (pending request, plain sentence); approving adds the exact host and the next decision allows
  (including subdomains); denying keeps it blocked; per-Project scopes beat the default and per-tool
  rules beat the project; a tool-scope approval updates the tool rule; `perform_request` refuses
  before any network I/O; bind/unbind never leaks a store; history and requests list newest-first; a
  one-argument hook keeps working.
- Bounded group on the final code (one stack at a time): `test_v2_network test_v2_connections
  test_v2_oauth test_v2_connection_bridge test_capabilities test_v16_r8_migrations` → **155 OK**
  (101 s). Two existing hardening pins failed on the first run because `bind()` initially overrode a
  deliberately patched hook; the fix (an explicit rule source wins) is the recorded evidence that the
  seam's own pins still hold.
- Live loop (engine restarted on this code, `C:\Users\Nick\KelV2Runs\prepared\engine`, driven through
  `/api/connections`): `policy get → default mode=full`; a probe connection saved with an unroutable
  base (`http://203.0.113.9/`); mode `none` → the test refused **“You set Kel to no internet for
  default, so nothing is sent.”**; mode `approved` + `['example.com']` → **“203.0.113.9 is not on the
  approved list for default. Approve it in Connections, or change that scope to full internet, then
  ask again.”** with `pending asks → 1 for 203.0.113.9`; `history` showed `[ask, blocked]`
  newest-first; mode restored to `full`. The engine was stopped by its own pid and its port released.

## Honest limits (also in `KNOWN_LIMITATIONS.md`)

- **The rules govern Kel's own outbound paths**, not the operating system: an installed CLI with its
  own network stack is governed by the provider's sandbox, not by this table (V2 keeps this practical;
  §19 is about Kel's traffic, and every Connection path shares the one function).
- **Contacted domains are visible for Connection traffic** (`network_events` + `connection_events`);
  traffic from an installed CLI is not enumerated here.
- **A pending ask is resolved on the Connections surface** — there is no chat notification for it yet.
- **Approval adds the exact host** a request named (its subdomains then match); a person who wants a
  whole domain adds the parent domain on the list directly.
- **The probe left a connection named “V2-14 probe”** in the V2 test root (test data).
