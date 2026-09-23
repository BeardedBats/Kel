# KEL V2.0 — ROADMAP

Phase map. Scope may be re-cut when implementation evidence supports it (recorded in `DECISIONS.md`);
scope never silently disappears. Phase numbers are the directive's; the table below adds each phase's
intent so a resume run does not have to guess.

| Phase | Scope | Status |
| --- | --- | --- |
| V2-00 | Developer line + durable program state (this worktree, these documents) | **DONE** |
| V2-01 | **Connections model + central management** — one product term ("Kel has credentials for this service and can use its API"), one place to see/manage them, no per-service app/db/worker/workflow | QUEUED |
| V2-02 | Generic REST Connection — service name, base URL, API key, auth method/header, optional docs URL, optional test endpoint, Test Connection | QUEUED |
| V2-03 | Personal Connections — Pitcher List/WordPress REST, Stripe, Raptive, Google Drive (OAuth), GitHub, ClickUp (useful actions only), Figma (context retrieval only), Discord (webhook/bot first) | QUEUED |
| V2-04 | Connection Framework — API-key / OAuth / bot-webhook templates; standardised credentials, authenticated requests, actions/tools, permissions, Test Connection, errors, retries, tests; the "Kel, add Raptive. Here are the API docs." developer goal | QUEUED |
| V2-05 | iPhone Kel PWA V1 — login, history, create/continue conversation, text/paste, voice → Muse → send, Project switching, conversational Project routing, create/add/infer/ask; home shows running/recent/failed work + Needs Your Attention; answer/approve/deny/grant/review/resume/stop. No uploads, camera, share sheet, push, Swift/Android | QUEUED |
| V2-06 | Needs Your Attention 2.0 — derive from authoritative state; Project grouping, priority, age, reason, related work, direct action, filtering, sorting, resolution; Snooze/Later only if consistent with authoritative state | QUEUED |
| V2-07 | Recipes 2.0 — library, search, favourites, recent, categories, create/edit/duplicate, attach to Project, run, run again, run history, last result, success/failure, reopen output; suggest a Recipe only after repeated behaviour | QUEUED |
| V2-08 | Activity 2.0 — historical timeline, Project/date/type/failure filters, search, open result, open evidence, retry/recovery history; never raw worker ids, leases, staffing graphs or cockpit controls | QUEUED |
| V2-09 | Routing intelligence — learn from outcomes (latency, completion, provider/model failure, task type, tool reliability, approximate cost, review outcome); improve Automatic routing; optional "Why this model?" on demand | QUEUED |
| V2-10 | Learning 2.0 — what Kel learned (format, model-by-task, review depth, autonomy, recurring workflows/tasks, file locations, tools, frequent Connections/Recipes); inspect/correct/remove/disable/explain; never silently learn permission grants, spending authority, filesystem access or irreversible authority | QUEUED |
| V2-11 | Long-running work 2.0 — continuation, dependency/provider recovery, stalled-work detection, progress summaries, resume briefs, completion recognition, escalation; Kel works until Nick is genuinely required | QUEUED |
| V2-12 | Adaptive staffing 2.0 — large bench / small mission team / central command / independent verification; Kel is Commander; Architect is the only retained subordinate manager; D0–D4 levels; builders never final-certify; fresh-context Verifier; Sentinel for security/privacy/data; Oracle read-only review preferably on a different provider; Red Team on justified artifacts; learn when solo/specialists/review/parallelism/high-assurance actually help | QUEUED |
| V2-13 | Local execution isolation — filesystem path restrictions, sensitive-folder protection, read-only execution, temporary writable workspace; child-process restrictions, full process-tree kill, restricted environment, disposable sessions. No VM platform, no Rust rewrite, no container orchestration | QUEUED |
| V2-14 | Network permissions — NO INTERNET / APPROVED DOMAINS / FULL INTERNET; per-tool and per-Project rules, show contacted domains, block unexpected ones, ask before a new domain, access history | QUEUED |
| V2-15 | Real dogfood integration pass — bring real Fix Capture batches in, group by root cause, repair, regression coverage, verify the affected UI | QUEUED |
| V2-16 | Performance + UX polish — what Nick feels: startup, conversation opening, Project switching, first response, routing delay, Remote load, transcript search, Recipe load, Needs Your Attention, memory retrieval | QUEUED |
| V2-17 | Manual upgrade reliability — safe manual upgrade preserving Projects, conversations, memory, credentials, settings, transcripts, Recipes, Connections, Fix Capture data where appropriate; safe migrations; failure without data loss; practical developer rollback. No updater infrastructure | QUEUED |
| V2-18 | Synthetic V2 acceptance journeys | QUEUED |
| V2-19 | Full V2 regression (engine + desktop + installed) | QUEUED |
| V2-20 | V2 release candidate (evidence, package, install, report) | QUEUED |

## Cross-cutting rules (always on)

- North star: *one capable personal assistant with hidden orchestration.*
- Fix Capture: built and verified — never rebuilt, four statuses only, never Jira.
- Visual rules: never single-side coloured borders or accent rails; typography, spacing, background
  tone, subtle full-perimeter neutral borders; ~8px geometry; 16px body floor, 14px nav/meta/code floor;
  no generic AI-dashboard treatment.
- Disk hygiene: temporary trees die once their findings are committed; no obsolete `node_modules`,
  build output, duplicate installers, or accumulating data roots.
- Dogfood feedback from the stable candidate outranks synthetic tests; priority changes are recorded.

- **V2-05 — iPhone Kel PWA V1: partial.** Real-browser phone journeys now exist and pass
  (`docs/v2/evidence/v2-05/`); the phase closes when browser voice reaches Muse, a connected model makes
  send real, and the job-driven attention actions are exercised on the phone. PWA plumbing itself was
  already pinned and stayed green.

- **V2-05 voice: done.** Mobile dictation now reaches the production Muse family through the gateway
  (real browser, real speech, real transcript). V2-05 stays partial only for the physical-device pass (send with a connected model was proved; history, attention actions and conversational routing landed on the integration line):
  conversation history from the phone, job-driven attention actions, conversational project routing.
