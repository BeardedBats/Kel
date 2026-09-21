# V2-04b evidence — the OAuth foundation, proved end to end (2026-09-21)

The framework is one reusable sign-in for account-authorization services: providers as data
(`runtime/kel/connection_oauth.py`), the flow in `oauth_flows` (migration 28 — single-use state and
the PKCE verifier; never a token), the token trade through `perform_request` (the single outbound
choke point), and the tokens in the same in-memory custody every connection value uses. Durability
works the way every other value works: the shell claims a finished authorization **once** into the
OS-backed custody and pushes it back (`supply`); the engine keeps only its working copy. Google
Drive is the reference implementation (`gdrive-files`, scope `drive.metadata.readonly`).

## What was proven (all green on this commit)

Engine — `runtime/tests/test_v2_oauth.py`, **10/10**:

1. Whole lifecycle, engine level, against a local stand-in provider: disconnected → connect (a real
   authorize URL with state + S256 challenge) → callback → **connected** → Test Connection (`ok`)
   → authorized read action (the provider's own record shows it accepted `Bearer at-1`) → refresh
   on expiry (serves the call with `at-2`) → revoke (the provider's revoke endpoint is told) →
   **disconnected**.
2. Security set, each refused in plain words and never traded: state mismatch, empty state, missing
   code, replay of a used state, expired flow; PKCE verifier mismatch (the stand-in performs a REAL
   S256 check and answers `invalid_grant`); failed refresh → `needs_reconnect` and every caller
   stays refused with the reconnect sentence; one connection's token never rides another's request
   (the provider saw **no** Authorization header for the other connection); missing granted scopes
   are named in plain words when an action needs them.
3. No-leak sweep: `at-*`, `rt-*` and the client secret are absent from messages, approvals,
   approval actions, access history, guardrail decisions, `oauth_flows`, jobs and submissions.
4. Real HTTP journey (engine `serve()` in-process, exactly like the desktop path): `oauth-initiate`
   over bearer HTTP → **the browser callback is fetched with no bearer at all** and answers the
   plain page (no token in the HTML) → `oauth-claim` hands the values over **exactly once** → the
   V2-04a bridge `catalog`/`call` path serves `gdrive-files` with the sign-in → `oauth-revoke`
   returns the connection to disconnected and empties custody. Untrusted callbacks (missing state,
   wrong state, user-refused) answer "not finished" and never trade.

Desktop — `connections-surface.test.ts`, **5 new tests** (whole suite 43 files / 363 passed,
`tsc` clean): the main-process sign-in opens the browser at the engine's authorize URL, waits
boundedly, claims once into OS-backed custody field by field, records only the pointer + field names
in the engine, pushes the values to engine memory, and returns an outcome that contains no token;
honest refusal when the person does not finish; bounded timeout; sign-out tells the provider,
clears shell custody and engine memory; a spoofed sender is refused before any call.

Migration ledger: `v20-oauth` (28) — fresh-database and idempotency suites updated and green.

## Honest limits (recorded in `KNOWN_LIMITATIONS.md`)

- **Real Google *sign-in* was not exercised** (see the live check below for what was). Everything
  above runs against a local stand-in provider over real HTTP with a real S256 PKCE check. A real
  sign-in needs Nick's own OAuth client ID stored for the connection (`client_id` field in custody)
  and one browser visit.
- **The phone cannot finish a sign-in yet**: the callback lands on the engine's own loopback, which a
  remote browser cannot reach. The desktop is where sign-ins complete today.
- **Between callback and claim, the sign-in lives in engine memory only** — an engine restart in
  that window means signing in again (never a stale "connected").
- A pasted token still works exactly as before for `oauth` connections that were never signed in.

## Live check against the real provider (2026-09-21, engine on `prepared/engine`)

With the current code running, one sign-in was started against **Google itself**
(`C:/Users/Nick/KelV2Runs/prepared/devtools/live-oauth-check.py`):

- `oauth-initiate` produced a real `https://accounts.google.com/o/oauth2/v2/auth` address carrying
  `access_type=offline`, `prompt=consent`, a 256-bit `state`, an S256 `code_challenge` and the
  engine's own loopback redirect (`http://127.0.0.1:55800/oauth/callback`).
- The callback was fetched **with no bearer** and a deliberately invalid code: the engine performed
  the real token exchange against `https://oauth2.googleapis.com/token`, and Google's own answer came
  back in plain words — “Google did not accept the sign-in — The OAuth client was not found.” (the
  client id was a local placeholder).
- The page carried **no token** (`token in page? False`); the connection read `disconnected`
  afterwards; replaying the same state answered “That sign-in answer was already used.”

This proves initiate, the public callback, the real provider exchange and the honest failure path
live — and it explicitly does **not** claim a successful Google sign-in.
