# V2-05 deep-link destination retention — measured, repaired, and verified

Measured on the **packaged** candidate and on the WebUI of the same build (2026-09-22).

## The requirement

An unauthenticated visitor who follows a conversation (or Work) deep link must end up on the thing
they asked for: link → sign-in → **that** conversation → and it must survive a refresh.

## What was measured, and the repair

| Step | Before | After the repair |
| --- | --- | --- |
| `#/conversation/<id>` while signed out | reached `#/login` ✓ | unchanged ✓ |
| destination on the sign-in page | `history.state` carried no `from` (the entry holding it was replaced while the session check ran) → sign-in landed on `#/guid` ✗ | `sessionStorage['kel:login-return-to'] = '/conversation/<id>'` observed in the page ✓ |
| sign-in | dropped the destination ✗ | the sign-in route and the login page resolve `state.from ?? pendingLoginReturnTo() ?? '/guid'` ✓ |
| refresh after arriving | — | the destination is consumed once the visitor is inside a protected route (`clearLoginReturnTo`) ✓ |

Files: `renderer/utils/loginReturnTo.ts` (new), `renderer/components/layout/Router.tsx` (guards
remember/clear), `renderer/pages/login/index.tsx` (resolves the destination).

## The second defect this exposed — repaired in the same area

A deep link to a conversation the store does not know used to show a toast and **silently replace the
route with home** (`navigate('/', { replace: true })` → `#/guid`), so the visitor could not tell a
mistyped link from a deleted conversation. Measured evidence: `GET /api/conversations/<id> → 404`
followed by the hash being replaced with `#/guid`, with only a transient toast.

Now the conversation route keeps the visitor where they are and says what happened: an Arco `Result`
(status 404) with `conversation.notFound`, the id, and one action (“New conversation”). One pass per
id; no redirect loop.

## Live checks on the same build (WebUI, signed in, 390×844 phone viewport unless noted)

| Check | Result |
| --- | --- |
| `#/guid` cold navigation | ready in **454 ms** (TTFB 9 ms, DOMContentLoaded 309 ms, load 387 ms) |
| open a conversation from the drawer | composer usable, `#/conversation/main` |
| `#/projects/knowledge` | renders the Knowledge grid with real rows |
| `#/work` | renders the Work surface with real jobs and Kibble findings |
| `#/activity` | "Happening now / Nothing is running right now … Waiting on you …" |
| `#/dogfood` (Kibble) | "What Ctrl+Shift+F captured while you were using Kel …" |
| console on an authenticated page | 2 errors (the earlier 40+ were the stale-session 401 storm) |

## Still open (recorded, not fixed)

When the SPA still believes it is signed in while the session is gone, protected calls answer `401`
and the app can end on the home route instead of being sent through the sign-in gate (which now
remembers the destination). The gate itself is correct; the trigger is the stale session state.
