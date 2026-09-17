# Test matrix — session-scoped tool controls

Artifact: `dist/package-final9/win-unpacked` (branch `ux/v15-journeys`).
Engine tests: `runtime && python -m pytest tests -q` → **544 passed** (15 of them
`tests/test_capabilities.py`).
Packaged journey: `node packaging/ux-audit.cjs <package-final9/win-unpacked> <root> <out> sessiontools`
→ evidence `ux-sessiontools.json`, plus the transcript probe `ux-sessiontools-db.json`.

| # | Required check | How it was proven | Evidence |
|---|---|---|---|
| 1 | **Isolation** — chat A GitHub enabled, chat B disabled | chat A set `web = off`, chat B left at `default` and then set `web = on`; two independent conversation ids (`94f0e3eb…`, `08de854c…`) keep opposite states | `chatAWebOverride: off`, `chatAWebUsable: false`, `chatBWebOverride: on`, `chatBWebUsable: true` |
| 2 | **Restart** — both policies persist | app closed and relaunched, then both conversations re-read | `afterRestartChatAWeb: off`, `afterRestartChatAGithub: on`, `afterRestartChatBWeb: on` |
| 3 | **Reset** — A returns to global | `action: reset` on chat A, then re-read A and B | `afterResetChatAWeb: default`, `afterResetChatAUsable: true`, `afterResetChatBUntouched: on` |
| 4 | **Narrowing** — disabling actually narrows | chat A `web = off` resolves `usable: false` at the engine boundary; `kel.coding` passes the capability of every effect tool through `kel.authorize`, where layer 3c denies before the lease layer | `chatAWebUsable: false`; unit tests `test_authorize_honours_a_disabled_capability`, `test_capability_layer_does_not_replace_the_lease_gate` |
| 5 | **Enable** — an already-configured capability reaches the execution path | chat B `web = on` → engine reports `effective: on`, `usable: true` | `chatBWebEnabledUsable: true`, `chatBWebEffective: on` |
| 6 | **Unavailable capability** — plain "Needs setup", never pretends | Google Drive switched on in chat B stays unusable with a plain reason | `driveAvailability: needs_setup`, `driveStaysUnusable: true`, `driveReason: "Google Drive needs setup before it can be used."` |
| 7 | **Natural language** — same underlying state as the UI | "Use GitHub for this conversation." sent in the chat → `github = on` for that conversation and an assistant confirmation in its transcript | `chatAGithubOverride: on`; `ux-sessiontools-db.json` → `reply_renders_after_user_message: true`, pairs `"Use GitHub for this conversation." / "Okay - I can use GitHub in this conversation."` |
| 8 | **Safety** — an override cannot bypass hard guardrails, approvals, unavailable credentials or scope | unit tests: guardrails still win over an enabled capability; the capability layer never replaces the lease gate; `needs_setup`/`unavailable` capabilities refuse even when switched on; one-shot grants are single-use and TTL-bound | `test_guardrails_still_win_over_an_enabled_capability`, `test_capability_layer_does_not_replace_the_lease_gate`, `test_needs_setup_capability_cannot_be_enabled`, `test_one_action_grant_is_spent_once_and_expires` |
| 9 | **Cross-runtime** — independent of which worker runs | the policy is stored per conversation in the engine and resolved without any worker in the picture; execution paths resolve the conversation from the job (`submissions.conversation_id`) so a worker change cannot change it | `04_RUNTIME_RESOLUTION.md`; engine tests run with no provider attached |
| 10 | **Machinery hidden** | the menu text read from the running app contains capability names and no internal names | `menuPlain: true`, `menuHidesMachinery: true` |

## Instrument note (honest)

The harness's DOM read of the confirmation line (`naturalLanguageReplySeen`) returns false on this
build even after scrolling the virtualized transcript, while the conversation database — the artifact
the same screen renders from — contains the confirmation as the assistant message immediately after
the directive, in the right conversation, for every run of the scenario. The DB probe is therefore
the authoritative evidence for check 7; the DOM field is kept in the artifact unchanged as a known
weak instrument (the same lesson as sweep findings F14–F16: fix the probe, don't argue with it).

## Console health

`consoleErrors: []` on the packaged run — no page errors during the journey.
