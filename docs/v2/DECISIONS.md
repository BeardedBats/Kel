# KEL V2.0 — DECISIONS

Meaningful product/architecture decisions, newest first. Each one records the decision, the reason, and
what it forbids so a later run cannot quietly undo it.

## V2-00 (setup)

1. **V2 is a worktree of the existing repository, not a clone.** `C:\Users\Nick\Desktop\Kel\kel-v2` is a
   worktree on branch `dev/v2` of the shared object database in `Kel-Repo\.git`, based exactly on
   `a471e17ac25590369e74824ebed0dd7b54e4b00b`. *Reason:* one history, no duplicate object database, and
   `dev/daily-driver` stays untouched as the predecessor line. *Forbids:* clones, manual copies, a second
   object database, any change to `main` (`5e76b21…`) or to historical refs.

2. **V2 development data and installs live outside the source trees.** Test data goes to
   `C:\Users\Nick\KelV2Runs\prepared`; the V2 candidate, when a checkpoint needs one, goes to
   `C:\Users\Nick\KelV2Candidate`. *Reason:* the stable dogfood build is in daily use and must never be
   the V2 scratch surface. *Forbids:* pointing V2 runs at `KelDogfoodCandidate` or
   `KelDogfoodRuns\prepared`, and installing a candidate per phase.

3. **Disk hygiene is a program rule, not advice.** Temporary review/audit worktrees are created only
   when isolation materially helps, and are removed once their findings are committed; obsolete
   `node_modules`/build/dist copies, duplicate installers and accumulating data roots are not allowed to
   pile up; temporary trees are recorded in `MARATHON_STATE.md`. *Reason:* the predecessor program
   accumulated >80 GB of disposable trees. *Forbids:* indefinite temporary worktrees and generated bulk
   treated as durable.

4. **"Connections" is the product term** for "Kel has credentials for this service and can use its API".
   *Forbids:* plugin marketplaces, one mini-app/database/worker/workflow system per service.

5. **Gmail and Slack are out of V2 scope.** Removed from the intended connection list by the directive.
   *Forbids:* re-adding them without a recorded decision.

6. **V2 mobile is a PWA tether, desktop may stay on.** iPhone → Remote/WebUI → Nick's desktop Kel;
   cloud Kel is V2.5 and desktop-as-execution-node is V3.0. *Forbids:* implementing cloud or V3 scopes
   during this marathon, native apps, phone uploads, camera, share sheet, push notifications.

7. **Fix Capture is done and stays as built.** Four statuses (OPEN/BATCHED/FIXED/DISMISSED), never Jira,
   never rebuilt. Its feedback is an *external* input that outranks synthetic tests and may change V2
   priorities (recorded in `DOGFOOD_FINDINGS.md`).

8. **The visual rule is absolute**: never single-side coloured borders or accent rails; use typography,
   spacing, background tone, subtle full-perimeter neutral borders, restrained icon/state differences.
   Floors: body/conversation 16px, navigation/metadata/settings 14px, code 14px; ~8px geometry.

9. **Transcription stays shared, not re-invented.** V2 keeps the single Muse path (with the credential
   read from the copied Transcriptions app) and the explicit-only practice mode; no new provider, key
   field, setup flow or migration.

## V2-01 (Connections model + central management)

10. **A Connection is one row in one store.** `runtime/kel/connections.py` (migration 23,
    `v20-connections`) owns the record: service name, kind (API key / OAuth / Bot or webhook), API
    address, how the credential is sent, documentation and test addresses, notes. *Reason:* the
    directive forbids a marketplace and one mini-app/database/worker/workflow per service. *Forbids:*
    per-service tables, modules named after a service, seeding the store with services, and any code
    that branches on a service name (pinned by `runtime/tests/test_v2_connections.py`).

11. **The engine never holds a credential value.** It records the field names and a pointer
    (`kel:connection:<id>`), and `set_credential` refuses a pointer that is not in that namespace. The
    value lives only in the OS-backed store the main process already owned
    (`desktop/.../process/services/kel/kelCredentials.ts`). *Reason:* one custody implementation, one
    encrypted file, no value in a process that logs, exports or backs up its database. *Forbids:* a
    value column, a value getter, and connection secrets in the engine's backups.

12. **Connections share the custody file under their own namespace.** Connection credentials are stored
    as `connection:<id>:<field>`, and that namespace is a separate key space from a model provider id, so
    a service named "internal" cannot collide with the model provider `internal`. The providers surface
    lists the provider namespace only; Connections are listed by the Connections surface.

13. **Connections are a configuration surface, not a primary destination.** Route `/connections`,
    reachable from the command palette and from the Providers page's integrations card. *Reason:* the
    primary nav is places Nick does something; Providers, Diagnostics and Team are already configuration
    surfaces outside it.

14. **State is derived, and a disagreement is said out loud.** A connection is `ready` when the engine
    has a credential record and `needs_credentials` otherwise; the page also asks the shell what it holds
    and says so plainly if the computer has a value the engine has no record of. *Forbids:* showing
    "Ready" for a connection Kel cannot actually use, and showing a saved value again anywhere.

15. **V2-01 deliberately stops at the model.** Test Connection, real requests, service templates and the
    developer-facing framework are V2-02 and V2-04; `test_endpoint` is stored now but nothing is called
    by V2-01. *Forbids:* a hidden network call from this phase.

16. **The migration inventory covers every module.** `runtime/tests/test_v16_r8_migrations.py` now
    includes `dogfood` (22) and `connections` (23) and expects 23 as the maximum, so a new migration
    cannot collide with an existing number unnoticed.

## V2-02 (Generic REST Connection — Test Connection)

17. **Test Connection is a real request, made only when Nick asks for it.** One click on the Connections
    page is the only trigger: nothing is called on save, on load, or in the background. *Forbids:* any
    hidden or scheduled call to a service, and any "check all connections" behaviour that Nick did not ask
    for.

18. **One place makes the request.** `runtime/kel/connections.py:perform_request` is the only function
    that opens a socket to a service, so V2-14's network rules (no internet / approved domains / ask
    before a new domain / show contacted domains) have exactly one place to live. *Forbids:* a second
    HTTP client for Connections and network code inside the desktop renderer.

19. **The credential is used once, in memory, and never travels back.** The main process decrypts the
    value and sends it with the check; the engine uses it for that request, never stores it, and scrubs
    it out of anything that can become durable. The renderer receives the *record* of the check, not the
    value. *Forbids:* a value in the engine's rows, notes, events or backups; a value returned over IPC.

20. **What is recorded is the result, in plain words.** State (`ok`, `refused`, `not_found`, `busy`,
    `error`, `unreachable`, `timeout`), the HTTP status when the service answered, the elapsed time, and
    one fixed sentence. The response body is not read at all. *Forbids:* storing a service's payload, and
    showing a raw status code or a stack trace as the explanation.

21. **A refusal is a result, not a failure of the connection.** A 401/403 is recorded as `refused` and
    does not silently clear the credential record; the surface says "Ready, but the check was refused"
    rather than hiding either fact. *Forbids:* quietly marking a connection broken because a check failed,
    and quietly claiming it works because a credential exists.

22. **Every migration step must be safe to re-run.** Migration 24 (`v20-connection-tests`) adds five
    nullable result columns and checks for them before altering; the module's migrations are now named
    steps rather than one DDL blob, because a resumed upgrade can legitimately re-apply the newest step
    when its marker was lost. *Forbids:* a step that only works on a database that has never seen it.

## V2-03 (Personal Connections — the services Nick uses)

23. **Known services are data, not features.** `runtime/kel/connection_services.py` holds rows — address,
    header, how the credential is presented, documentation, and what Nick has to go and fetch — and
    nothing else: two functions that hand out the list and one row, no branching on a service name, and
    `connections.py` still contains no service name at all. Adding Pitcher List by hand is exactly the
    same kind of connection as picking GitHub from the list. *Forbids:* per-service modules, tables,
    workers, workflows, or behaviour switched on a service id.

24. **Kel says how sure it is.** Every entry carries `documented`, `assumed` or `to-confirm`, and the
    surface repeats that sentence to Nick. Raptive's API address is not invented: Kel says the address
    comes with the credential. *Forbids:* a guessed URL presented as fact.

25. **How a service wants its credential is part of the connection.** `auth_prefix`: `null` means Kel works
    it out (a scheme for `Authorization`, the value untouched in a custom header), `''` means send the
    value exactly as it is (ClickUp, Figma, Raptive), and a word means put that word in front (GitHub and
    Stripe `Bearer `, Discord `Bot `). The trailing space is significant and is preserved. *Forbids:*
    per-service auth code, and normalising a prefix into `Bearerthe-value`.

26. **A known service's id is the slug of its name.** `Pitcher List` produces `pitcher-list`, which is the
    id the catalogue uses, so nothing has to carry an id around and the catalogue and the store cannot
    disagree about which connection is which. *Forbids:* an id scheme that needs to be kept in step by
    hand.

27. **The eight services still need their credentials from Nick.** Kel knows their addresses and shapes;
    what it cannot do is test them without his keys, so live checks against the real services are V2-03/V2-15
    evidence that does not exist yet and is not claimed anywhere. *Forbids:* describing a service as
    "working" because it is listed.

## V2-04 (Connection Framework — standard parts, partial)

28. **One place holds the standard parts.** `runtime/kel/connection_framework.py` holds the three credential
    templates and re-presents the request policy whose numbers live in `connections.py`; every service gets
    the same treatment, and the module knows no service by name (a test pins that). *Forbids:* a per-service
    framework, per-service auth code, or a second request path.

29. **Retries are bounded and honest.** A GET is tried again only when the service is busy (429 or a 5xx) or
    the connection dropped — never when the service answered, because a 401 or a 404 is information and
    asking again risks a lockout. Every attempt is bounded by the timeout, the whole request by a budget,
    and the record says how many times Kel tried. *Forbids:* retrying a refusal, retrying without a limit,
    and hiding a retry from Nick.

30. **The renderer keeps no kind vocabulary.** Labels, hints and the credential field name come from the
    framework with the list, so the engine's words and the engine's behaviour cannot drift apart (the
    renderer's own copy was deleted, and a test fails if one grows back). *Forbids:* a second source of
    truth for what a kind of credential means.

31. **V2-04 is partial, and says so.** Built: the three templates, the request policy with retries, one
    choke point, one honest result. Not built: what Kel can *do* with a service (actions/tools) and the
    OAuth account sign-in step. Google Drive therefore stays uncheckable beyond a pasted token, and the
    ledger, the state and this entry all say PARTIAL rather than claiming the framework is done.
    *Forbids:* marking V2-04 built, moving `next_item` past it, or implying Kel can act on a service.

## V2-04 (Connection actions — what Kel can do with a service)

32. **An action is a row, not a code path.** `runtime/kel/connection_actions.py` declares each one —
    name, description, method, path, params, what it returns, whether it changes anything, and how sure
    Kel is about the address. `connections.run()` reads a row and makes the request through the same choke
    point as everything else. *Forbids:* per-service functions, a second request path, and an action for a
    service whose address Kel does not know (Raptive) or that needs the sign-in step that does not exist
    yet (Google Drive).

33. **The answer comes back; it is never written down.** What is recorded is the fact of the call:
    connection, action, domain (never the path or a query string), status, attempts and duration — plus a
    bounded, credential-scrubbed copy of the answer handed straight to the caller. *Forbids:* a service's
    payload in Kel's database, logs, exports or backups; and a credential reaching an answer or a record.

34. **Nothing Kel can do changes anything yet.** Every action in the catalogue is a read, and `run()`
    refuses a `mutating` action unless Nick confirmed it — a gate proven with a mutating row rather than
    assumed, and a rule that stays even after write actions exist. *Forbids:* shipping a write action in
    the same increment that introduces the machinery, and running a mutating action on a guess.

35. **The assistant cannot use a connection yet, and that is the next increment.** The engine and the
    surface can do these things when Nick asks; nothing in chat can, because no tool exposes an action.
    V2-14 owns the network rules, and they belong inside `perform_request` — not in a second client.
    *Forbids:* claiming V2-04 is finished while that link is missing from the phase record.

## V2-04 (framework scope, and the developer page it needed)

36. **A tool the assistant can call is not part of the framework, and V2-04 does not claim it.** The
    assistant's tools come from the coding runtime the desktop agent runs, not from the engine: exposing a
    connection action to it means a deliberate bridge (with the same one-request rule, the credential path
    through the main process, and the mutating confirmation) rather than one more row. `capabilities.py`
    already states the rule this follows — a switch is offered only when a production path can honour it —
    so **no Connections capability switch is added** until that bridge exists, and the item is carried in
    the ledger as an explicit follow-up rather than dropped. *Forbids:* adding a capability toggle that
    would do nothing, and reading "framework built" as "the assistant can use a connection".
37. **The framework ships with the page a developer reads.** `docs/v2/CONNECTION_FRAMEWORK.md` states the
    four words, the rules and what enforces each of them, how to add a service and an action as data, and
    what is deliberately not in the framework. *Reason:* §8 asks for a developer-facing framework, and the
    rules in this program are the part most likely to be broken by the next change; each one names the test
    that catches it. *Forbids:* a rule that exists only in a commit message.

## V2-04 (closed)

V2-04 is the framework, not the consumer: templates, one request path, data-declared actions, the
confirmation gate, honest errors, bounded retries, the access history, and the developer page. What it
deliberately leaves open is named in `FEATURE_LEDGER.md` (the assistant bridge) and in
`KNOWN_LIMITATIONS.md` (no real service contacted, no OAuth sign-in flow, no write action shipped).

## D-29 — the gateway reaches the engine the way the desktop does

The engine authorizes a request only when `Host` is its own and `Origin` is absent or its own origin —
a deliberate local-session guard. A browser on a phone always sends the *gateway's* origin, which can
never satisfy that, so forwarding it verbatim turned every mutating Kel route into 403 and the shell into
"Kel is not answering right now (403)". We do **not** widen the engine's guard (that would weaken the
only thing standing between a local web page and the engine) and we do **not** rewrite the Origin to the
engine's own (that would assert something false). The gateway is already the trusted local client — it
holds the bearer, it is session-gated, and it already strips the browser's session cookie — so it strips
`origin`/`referer` too and presents itself exactly as the desktop does.

## D-30 — the standalone webui performs the same Kel assistant bootstrap as the desktop

The browser profile a phone uses is hosted by `bun run webui`, which never runs Electron main — so
`initializeKel`'s assistant seeding never happened there: no `kel` assistant existed, the guid page's
catalog (filtered to `kel`) was empty, and the composer's send could never enable (measured: zero pills
while `/api/assistants` answered with donor entries). We do not add a renderer fallback (that would be a
second product rule about which assistant exists) and we do not leave it to operators. The standalone
host does the same integration the desktop does — register the Kel ACP agent, create the single `kel`
assistant, leave exactly it enabled — right after the backend is healthy
(`web-host/src/kel-integration.ts`). *Forbids:* seeding "some assistant" when `kel` is missing, and any
second definition of the assistant catalog.

## D-31 — the Kel ACP agent spawns in module form (`python -m kel.acp_host`)

Measured: the script-path form (`python <source>/kel/acp_host.py --data <root>`) answers ACP
`initialize` with "attempted relative import with no known parent package" — the host's initialize
handler imports `from .service` — while the module form initializes cleanly from any cwd with
`PYTHONPATH` set. The packed engine (`--acp`) never hit this; the desktop's source branch did, and the
new webui bootstrap would have. Both now register the module form. *Forbids:* registering the
script-path form as the agent command again.

## D-32 — the assistant calls a Connection action through the existing systems (V2-04a)

The runtime's door is the shell command it already has, not a new tool system: `python -m kel.conn
list` / `call <id> [--param k=v] [--confirm auto|id]` asks the engine (`catalog` / `call` on
`/api/connections`), and every call runs through the systems that already exist — the capability
control (`connections`, a switch offered only because a production path can now honour it), the
approval rows (`request_approval` + `announce_approval`, resolved through `/api/approval`; mutating
actions wait for the exact action digest), and the one-request rule in `connections.run()` (the only
outbound path; answers stay parsed, bounded and credential-scrubbed). Reads run under the resolved
capability; a one-shot grant is consumed atomically at execution time, never at the ask. Provenance
gains a `source` fact per call (`shell` | `runtime`, migration 27). *Forbids:* an MCP subsystem, a
second action catalogue, a second permission path for connection effects, and any helper output that
could carry a credential or an unbounded answer.

## D-33 — connection values live in engine memory, pushed by the shell (V2-04a)

A runtime-initiated call happens with no click, so the value has to reach the engine somehow. The
shell (Electron main) pushes every stored connection value into the engine's memory at boot and after
each credential change (`supply` on `/api/connections`, `kelCredentialIpc.ts` + `initializeKel`);
the engine keeps them in `kel.connections` custody — memory only, never a column, never a file, never
a log — and every call still uses a value once, in memory. The renderer still never receives a value,
and the runtime receives none at all. Lines without a shell (the standalone webui/phone profile) have
no custody, and the bridge says so in plain words instead of guessing. *Forbids:* persisting a value
on the engine side, expanding custody beyond the connection namespace, and any bridge path that
accepts a credential from the caller.

## D-34 — the OAuth foundation: providers as data, the flow in the store, tokens in the same custody (V2-04b)

One reusable sign-in for account-authorization services: no per-service auth app, no second
credential store. A provider is a row of data (`kel.connection_oauth.PROVIDERS`: authorize / token /
revoke addresses, whether PKCE applies, the permissions in plain words). The flow lives in
`oauth_flows` (migration 28): one single-use state, its 10-minute window, the PKCE verifier the trade
needs, the redirect URI, the requested scopes — and **never a token**. The engine completes the trade
through `perform_request` (the single outbound choke point, now with a bounded form body); the tokens
land in the same in-memory custody every connection value uses. The finished authorization reaches
durability the same way every other value does: the shell claims it **once** (`oauth-claim`) into the
OS-backed custody and pushes it back (`supply`); the engine keeps only its working copy. The
connection row carries the sign-in state in plain words (`auth_state`, `auth_scopes`, `auth_expires`,
`oauth_provider` — never a token). Expiry refreshes engine-side from the refresh token; a failed
refresh reads `needs_reconnect` and every caller gets the plain reconnect sentence. Sign-out hits the
provider's revoke endpoint when it has one, then clears shell custody and engine memory. *Forbids:*
tokens in any column, log, message, approval, access-history row, model prompt, tool output or
renderer state; a second credential database; a per-service auth path.

## D-35 — the callback is public by state, not by bearer (V2-04b)

A browser cannot hold Kel's bearer token, so `/oauth/callback` (the only public route the engine
serves) trusts nothing but the single-use `state`: 256-bit random, ten-minute TTL, bound to one
connection and one redirect URI, marked USED **before** any trade so a replay can never trade twice,
and paired with PKCE S256 whenever the provider supports it (the fixture suite proves a verifier
mismatch is refused by a real S256 check). The page shows a plain sentence — no script, no token,
no connection data beyond what the person just did. *Forbids:* any other public route; resolving a
callback by anything but state; putting a code, token or verifier into the page.

## D-36 — the choke point's own rules (V2-04 hardening)

Everything a Connection says outbound, and every rule that could stop it, lives in
`perform_request`. The hardening keeps that single door and gives it teeth: one opener is built once
(never `urlopen` ad hoc) and the redirect chain is bounded to `MAX_REDIRECTS`; a service that answers
429/5xx with `Retry-After` gets exactly that pause, capped by `RETRY_AFTER_CAP`; the configured
network rules (`NETWORK_RULES`, V2-14's seam) are asked about the host **before anything leaves the
computer** and again about the host a redirect landed on, and a rule source that cannot answer fails
closed; an answer that hits the reading cap says so in the note instead of pretending to be whole.
A refusal raised here is a `PolicyError` and reaches the person as its own sentence — `test()` and
`run()` re-raise it instead of folding it into a generic failure. *Forbids:* opening a URL anywhere
but the single opener; honouring an unbounded Retry-After; letting a redirect smuggle a host the
rules would refuse; silently allowing traffic when the rule source errors.

## D-37 — routing evidence is decayed, floored, and read back (V2-09)

Kel keeps **one** routing-evidence store — the `routing_outcomes` table V1.5 already writes — and
V2-09 makes it answer properly. Every finished run contributes one fact row (verdict, task kind,
attempts, escalation, model, observed span, when, source, reviewer provenance) and never a payload:
no prompt, no answer, no path, no credential. An outcome’s influence **halves every seven days**
inside a thirty-day window, so a provider that failed last month is not punished today and recovery
is real; below ~three fresh runs of decayed weight **no rate is reported at all**, so small samples
can never overrule the safe cost/health defaults; and a reviewed verdict (`source='review'`) may
refine an inferred failure (`source='milestone'`) but never the other way round. Evidence may only
*reorder otherwise-eligible* models: an explicit choice and a preference are protected, nothing is
excluded by evidence, and demotion is applied after the existing cost/latency/quota ordering so the
defaults stand when evidence is thin. The decision the engine stores on `run.claimed` now carries its
own explanation (`why`, `chain`, `demoted`, `evidence`, `excluded`), and “Why this model?” reads
**that** back instead of computing a second opinion. *Forbids:* a second outcome store; evidence
influence without decay or a sample floor; demoting a person’s explicit choice or preference;
explaining a routing decision from anything but the stored route.

## D-38 — a tool request is a work request (V2-09)

Measured gap: a phone turn that asked Kel to run `python -m kel.conn list` and use a connected service
was answered conversationally by the saved-context path, so nothing ran. `needs_work()` (in
`kel/router.py`) recognises a command-shaped or connected-service request, and `service._plan` keeps
such a message out of the conversational branch so it becomes a real work turn — the only path in Kel
that can actually run something. The patterns are deliberately narrow (a known runner in backticks,
`python -m …`, `git/npm/bun/… <verb>`, “run the tests/the command”, “use the connected service”,
“check the repository”) and pinned by tests that include the exact measured sentence; ordinary chat
is proved to stay conversational (a live probe: **no** job for the chat control). *Forbids:* treating
a tool request as chit-chat; widening the predicate for ordinary prose without a measured case.

## D-39 — learning has a person's side, a floor, and a fence (V2-10)

Learnings were already memory records (one store, the V1.3 trust ladder, decay, corrections) and the
proposal queue already refused to propose `decision`/`preference`. V2-10 adds exactly three things and
no new store. **A floor:** `suggest_learnings` proposes only from measured evidence — three or more
decided runs (model-by-task, read from the V2-09 `routing_outcomes` store), three or more repeated
user corrections, or three or more Connection uses in the last thirty days — and every suggestion is a
proposal in the existing review queue, so nothing is ever applied by the learner. **A person's side:**
a learning can be switched off without being deleted (a superseding equal-trust record carries
`enabled`; the chain keeps every step), a disabled learning never reaches model context
(`Memory.select`), stays inspectable with `include_disabled`, and comes back with one call; and
`explain_learning` reports source, trust, decayed confidence, evidence, provenance, the chain and a
plain `effect` sentence. **A fence:** any non-user source whose insight asserts a permission grant,
spending authority, filesystem access or irreversible authority is refused outright — not stored, not
even suggested — because those are the person's decision every time. *Forbids:* suggesting from thin
evidence; applying a suggestion without review; deleting a learning to silence it; recording or
suggesting authority from any non-user source.

## D-40 — runtime recovery is narrow, and the brief never guesses (V2-11)

The V1.6 liveness truths already said what recovery must never do (no automatic replay of an
interrupted attempt). V2-11 gives them a runtime: `Store.recover_abandoned` fences only runs that
**nothing durable can carry** — an expired lease, no broker row, and not active in this engine — and
`Engine.tick` runs it on every tick. A run a broker owns is left for adoption, a live lease is left
alone, and an unreadable recovery question fences nothing (conservative failure). Fencing keeps the
old semantics exactly: ORPHANED + fresh epoch, milestone UNCERTAIN with the reconciliation sentence,
job WAITING_RESOURCE; continuing stays the person's decision through `execute_resume`. The person's
side is one brief built only from persisted facts (`Continuation.resume_brief`, surfaced in
`_work()['work']`): what shipped, what is open, why it stopped, the exact next step, and `needs_you`
true only when no automatic step can move the job. *Forbids:* auto-retrying a fenced attempt; fencing
a broker-backed, in-process or unexpired run; briefing from anything but persisted state.

## D-41 — staffing learns from what happened, one bounded step (V2-12)

The rule table decided from the mission's shape; V2-12 adds the directive's other half — outcome
history. `staffing.outcome_advice` reads settled missions at the *same decided tier* (the
`staffing.decided` / `contract.issued` / `task.closed` streams that already exist; blockers from
`findings`) and offers **exactly one** step: three or more settled missions with blocker-class findings
→ one tier up; three or more all clean → one tier down; mixed or thin history → nothing, with the
counts said out loud. The step can never cross a hard rule's floor (R3–R6), never pass `tier_max`, R1
or the D3+ decomposability gate, and callers apply it only where their path can honour it: the D1 path
applies a step down to D0 and merely records a step up; the D2 path applies a step down and then
refuses with its own explicit routing sentence. Every `staffing.decided` event now carries the advice
beside the decision, so a recorded staffing decision always shows both what the shape said and what
the history said. *Forbids:* more than one tier of movement; acting on thin or mixed history; a raise
smuggled past the path's own support; any advice that outranks R1–R10, the caps or `tier_max`.

## D-42 — containment is a rule at the seams, not a claim of sandboxing (V2-13)

Kel already runs native leaves read-only with tools disabled, kills through an identity-bound handle,
snapshots coding work into an isolated copy and applies changes transactionally. V2-13 adds the three
things that were missing, all in `kel/containment.py` and wired at the seams that perform autonomous
work: **sensitive folders** (`assert_usable_root`: Windows/Program Files, credential folders, the
engine's own data root, and `KEL_PROTECTED_PATHS` for the desktop's stable-app folders) refuse a
snapshot source (`coding.snapshot` for every caller, `CodingAdapter.execute` on every execute) and an
apply destination (`apply_changes.apply_checked` before any staging); **disposable sessions** (one
temp directory per native run, pointed at by the child's TMP/TEMP/TMPDIR, removed on return); and a
**widened env scrub** (secret-*shaped* names are dropped from a native child unless they are its own
provider credential — the R7 rule by shape instead of by list). *Forbids:* snapshotting or applying
into a sensitive root; leaving a run's temp behind; handing a child another service's token; treating
this as an OS-level sandbox — it is a rule enforced where Kel itself acts.

## D-43 — network permissions are the rule source behind the one seam (V2-14)

`NETWORK_RULES` was already the single hook every outbound path shares (asked before anything leaves
the computer, again for a redirect's host, fail-closed when the source errors). V2-14 makes
`kel/network_policy` its default source: modes `none`/`approved`/`full` per scope (`default`,
`project:<id>`) with exact-string per-tool overrides; with no rows the default stays `full`, so
nothing changes until a person chooses. In `approved`, an unlisted host is **never sent** — it is
recorded as one pending request and refused with a sentence naming the fix; `resolve_request`
approves (adding the host to that scope's list) or denies, and every decision lands in
`network_events` for the access history (performed calls stay in `connection_events`). The tool and
project travel with the call (`perform_request(context=…)` from `Connections.test/run`), and the
policy binds per store around exactly that call — **an explicitly configured rule source always
wins**, so no test or embedding loses its own hook. *Forbids:* a second outbound path; sending an
unapproved host “just once”; a policy that silently replaces a deliberately installed hook; blocking
or allowing anything without a recorded decision.

## D-44 — Kibble is undefined in the directive; the gate gets a door, the concept waits (Priority 9)

The queue item “Kibble Build Update backend foundation (dev mission schema, candidate model,
promotion gate)” is resolved against the durable record, honestly: `Kibble` appears nowhere in
`MARATHON_DIRECTIVE.md` or `ROADMAP.md` and nowhere in the runtime/desktop source; its only in-repo
placement is Ramble/Kibble **presentation** in Astra's Shell lane. Two of its three terms (what a dev
mission is, what a candidate is) describe a product concept, and inventing them would be exactly the
kind of invented subsystem the directive forbids. What the third term names already exists as
recorded-never-applied machinery (`learning.queue_promotion` → `proposal.queued`;
`learning.shadow_proposal` → `staffing.proposed` with predictions). This increment therefore adds only
the missing **door**: `Team.apply({action:'promotions'})` and `{action:'shadow'}` read those queues,
project-scoped, newest-first, with honest notes (“recorded, never applied”), and write nothing
(pinned). The dev-mission/candidate-model definition is **deferred pending Nick's definition** in the
same way V2-05-history is deferred for Shell integration — the requirement stays in MARATHON_STATE and
RESUME, and nothing here marks the item complete. *Forbids:* inventing the Kibble concept; a second
promotion system; a read door with side effects.

## D-45 — the manual upgrade gets a before/after, and V2 state is proved to survive it (V2-17)

§22 forbids updater infrastructure and asks for a safe manual upgrade, safe migrations, failure
without data loss and a developer rollback — all of which the existing machinery already provides
(identity-proofed legacy migration, hot-copy backups that **never** carry credentials, staged restore
with a marker and `apply_pending_restore` at start, a `…pre-restore-<timestamp>` rollback copy). What
was missing was the proof that the **new V2 state** survives and a way to see it: `table_inventory`
(every table's row count plus the migration ledger) surfaced as `/api/backup {action:'inventory'}`, a
richer backup summary, and pins that a backup→restore cycle returns every table and the ledger
**exactly** (post-backup mutations gone), that a staged restore touches nothing live until applied,
the second apply is a no-op, the live credentials file survives, and re-opening with every V2 module
ensuring its schema changes no count and no ledger row. *Forbids:* an updater, an update server or
background update checks; a backup that carries credentials; a restore that deletes the live
credentials file; claiming survival from a count of one table (the inventory is all of them).

## D-46 — Kibble is defined; the Build Update backend contract is the real work (corrects D-44)

D-44's deferral was **wrong**, and this decision corrects it: it concluded Kibble was undefined
because the directive, roadmap and source never use the name. The authoritative definition lives in
Nick's session handoff — **Kibble is the user-facing name for the existing Fix Capture / Dogfood
behavior**, and every internal identifier stays unchanged (`dogfood_fixes`, `Dogfood`, migration 22
`v20-fix-capture`, `/api/dogfood`). The workflow: Nick captures issues in Kibble; selects findings
and chooses **Build Update**; Kel creates an **isolated development mission**; a coding runtime
repairs Kel's source; Kel runs bounded tests and verification; Kel produces a **separate candidate
build**; Nick reviews it; **promotion or installation requires explicit human approval**. Build
Update authorizes creating and verifying the candidate — never installing, never modifying the
running app. The dev mission rides the existing machinery (a `compile_coding` contract claimed and
dispatched by the engine, an isolated `repositories/<job_id>` worktree, `code_evidence` +
`check_evidence`, the `manual_review` rubric, the existing approval vocabulary); findings carry
their screenshot/route/transcript/version context; the candidate lives under `candidates/<id>/` with
its own revision, test/verification evidence, fixed and unresolved findings, limitations and review
state. Team `promotions`/`shadow` views are **not** candidate approval — their mapping must be
proved, never assumed. *Forbids:* editing installed files in place; automatic promotion or a
consumer update platform; a second workflow, task or permission system; concluding a feature is
absent because its product name is not in the repository.

## D-47 — Build Update was built on the existing machinery; a candidate is a record, and nothing installs

D-46 named the contract; this decision records how it was built and what is deliberately absent. The
mission is **not a new subsystem**: `start()` records the selected findings (route, version, page
title, the screenshot fact and a bounded transcript excerpt), then proves its ground before anything
is created — the folder must be the Git top level itself, `containment.assert_usable_root` must accept
it, the baseline must be **clean** (a dirty tree is refused in plain words; that refusal was observed
live while this very increment was uncommitted), and the revision is recorded. What it creates is an
ordinary `compile_coding` contract (`kind='coding'`, root, test command, the `manual_review`
milestone) through the existing `Store.create`, so the engine claims and dispatches it and the coding
machinery works in the existing isolated `repositories/<job_id>` copy; the source checkout is never
edited and the running app is never touched. The candidate is a **separate record** (migration 29
`v21-build-update`, table `build_candidates`) whose artifact lives under the engine data root's
`candidates/<id>/` with its revision, verbatim bounded test/verification evidence and a `verified`
flag, fixed and unresolved findings as **candidate claims only** (Fix Capture's own statuses are never
rewritten), limitations, a `build-report.json`, and an explicit review state. `candidate()` answers
`BUILDING` and creates nothing until the job is `CLOSED`, and re-assembly never overwrites an
`APPROVED`/`REJECTED` review; `review()` moves the state only for `actor='user'`; `promote()`
**always** raises, and the no-promotion proof is structural (no install path exists) rather than a
promise. D-46's caution is realized rather than assumed: Team `promotions`/`shadow` are not candidate
approval, and the tests pin that mapping. Surface: `/api/dogfood {action:'build_update',
op:start|status|candidate|review|promote}`; the future UI contract is in `PARALLEL_SHELL_TOUCHES.md`.
*Forbids:* a second workflow, task or permission system for Build Update; a mission that edits the
source checkout or any installed path; installing, promoting or updating anything from this backend; a
candidate that overwrites an existing human review; treating Team `promotions`/`shadow` as candidate
approval; starting a mission on a dirty, unverified or sensitive baseline.

## D-48 — acceptance is a walked checklist on real paths, and its claims stay separate (V2-18)

§27 lists what V2.0 must validate; V2-18 turns that list into
`docs/v2/evidence/v2-18/ACCEPTANCE_MATRIX.md` — one row per requirement with the real entry point,
the expected result, the evidence that already exists, the journey still missing, and whether the
Shell must land first — and then walks it with **synthetic inputs on real paths** (the engine on
`C:\Users\Nick\KelV2Runs\prepared\engine`, its own HTTP surface and store, the isolated coding
workspaces, the installed runtimes, the real containment and backup machinery). Three rules make the
results worth something. **A journey that refuses for the wrong reason proves nothing**: the first
J-SEC “passed” because the finding id was unknown, not because the root was protected, and was
rewritten until the sentence named the real boundary and the finding was real. **Identity before
use**: `desktop-session.json` is a file, not a fact, so the runner attaches only when the recorded
pid is alive, its command line names this data root, and the recorded port is owned by that pid.
**Claims stay separate**: for the Kibble Build Update journey, mission creation and promotion
refusal, candidate-record creation, an actual built artifact with verified source provenance, and
the complete repair-to-candidate journey are recorded one by one — a CLOSED job or a candidate row
alone never proves a build, and failed tests, a missing artifact or unresolved findings never yield a
ready claim. Shell-owned presentation is recorded as *pending — Shell integration required* and is
never marked passed from a backend journey; an external service that cannot be exercised is a
labelled fixture. *Forbids:* calling a requirement accepted because a unit suite or an earlier
increment was green; asserting only that *something* was refused; re-using another run's evidence as
this run's; marking a phone or renderer check passed from a backend journey.

## D-49 — a verified build claim comes from the mission's verdict, not from one run's evidence (V2-18)

Found by the V2-18 negatives journey, on the real root: a mission whose test command could never
pass (`python -c "import sys; sys.exit(1)"`) was given four attempts. On the fourth, the runtime added
a `sitecustomize.py` that monkeypatches `sys.exit`, so that run's recorded evidence read
exit code 0 — and the milestone's own reviewer caught it (the recorded finding names the monkeypatch)
and left the milestone `NEEDS_REPAIR`, so the job settled `CLOSED`/**FAILED**. But
`BuildUpdate._assemble` read *that single run's* `code_evidence` (`check_evidence == 'VERIFIED'`) and
assembled a candidate claiming `verified: true` and the finding as fixed. One run's evidence is not
the mission's verdict. `_assemble` now requires the mission to have actually passed — the job's
`verdict == 'VERIFIED'` **and** the milestone `ACCEPTED` — before any verified claim; otherwise the
evidence is still recorded verbatim (with `mission_verdict` naming what the job and milestone said),
`verified` stays false, no finding is claimed repaired and the limitations say so. The same journey
confirmed the positive direction: a mission that really passed (codex-code repair, green bounded
tests, `VERIFIED`) still claims its build, and `promote` refuses before and after approval in both
cases. *Forbids:* treating `check_evidence` on one run as the mission's outcome; a candidate that
claims a repair the mission's own verdict never accepted; relaxing the gate to make a journey pass.

## D-50 — Three missing surfaces ride the records the line already keeps (V2-06/V2-07/V2-08)

V2-06, V2-07 and V2-08 asked for surfaces that mostly existed as *records* with no way to read them,
so this increment adds reads, not systems. **Attention (V2-06):** every `/api/work` row now carries why
it is here, its age, its priority (`now` / `soon` / `running` / `later`), what belongs with it (project,
conversation, pending approvals, milestones) and the *one* action that resolves it — pointing at the
route that already does that work (`answer` → `/api/approval`; `resume` → `/api/send` for a fenced run
or `/api/control` for a paused job; `stop` → `/api/control`; `retry` → `/api/retry`); rows group by
project and the surface names its filters and sort orders. **Recipes (V2-07):** migration 30
(`v2-recipe-library`) adds `recipe_marks` (favourite, what was opened, how often it ran, the last job)
and the library gains search, categories (with an optional `category` field on a recipe), recent,
duplicate (a draft copy — never saved by itself), run history and last result, all read from the
`recipes` and `jobs` tables the line already keeps. **Activity (V2-08):** `kel/activity.py` and
`/api/activity` turn the durable `events` stream into one timeline with project/date/type/failure
filters, search, and per-row result/evidence/recovery hints. Two rules hold across all three: a row
may only say what authoritative state supports (no snooze the state cannot honour, no “verified” a
mission did not earn), and nothing leaks inward plumbing — no payload, contract, run id, lease or
worker id ever reaches a row or a sentence. *Forbids:* a second attention/recipe/activity store; a
surface that resolves, snoozes or re-runs work itself; hiding an unmapped event instead of reporting
it; and any row that offers an action whose route does not exist.

## D-51 — Phone conversation history rides the Shell's existing list; an empty one is a place to start

**Decided 2026-09-22.** The phone's history is not a new surface: the Shell already renders the
conversation list in its sider, that sider becomes the mobile drawer, and every row opens
`/conversation/<id>` through the same store the desktop uses. The gaps that remained were
behavioural, and each is fixed at its cause: (a) a PWA is backgrounded constantly, so the list now
re-reads on `visibilitychange` and `focus` — a conversation deleted elsewhere stops being offered
instead of leading to a dead link; (b) an *empty* history gained the one action it was missing
(“New conversation”), which on a phone is the only way back in; (c) opening a conversation that no
longer exists keeps the visitor on the route with the honest state added in `43a934f` rather than
bouncing home. Path-style deep links are already translated to their hash form by the gateway
(`deepLinkLocation`), so the phone reaches the same route the desktop does.
*Forbids:* a second history store or a phone-only list; hiding a conversation because it failed to
load; and any control that promises a conversation exists before the store says so.

## D-52 — Multi-utterance dictation is outside V2 scope (recorded, not dropped)

**Decided 2026-09-22.** The directive's mobile requirement (§10) is “voice-record prompt; Muse
transcription; send transcript” — one recorded prompt, transcribed, sent. That path is built and
evidenced (V2-05: a real browser's voice through the gateway to Muse, the transcript landing in the
composer and sending). *Multi-utterance dictation* — several utterances accumulating inside one
recording — is not required by §10, and the recorded limitation is a Muse endpointing behaviour (the
first utterance's partial is lost when Muse never marks it final) rather than a Kel defect.
**Decision:** keep it out of V2; keep the limitation documented in `KNOWN_LIMITATIONS.md`; revisit it
with the V2.5 realtime work. Nothing in V2 acceptance depends on it.

## D-53 — Real work is handed to the background conversationally; the chat stays usable

**Decided 2026-09-26.** Measured gap: a real-work message held the ACP turn open until the job
settled, so the composer blocked new sends for minutes, and a plain question could queue behind a
planner on the shared two-thread pool. **Decision:** one turn decision (`kel/turn.py`) either
answers directly (`reply`) or starts background work (`start_background_work`) with a short, warm
acknowledgement that offers to keep talking about one related topic. The service's deterministic
floors stay authoritative (status, recipe, continuation, coding-without-project; and as work:
`needs_work` (D-38), a named file in a named folder, explicit research openings / research kind,
greenfield coding, a coding verb inside a rooted project, an explicit client kind) — a floor forces
work even when the model says reply. With no turn model (or `KEL_TURN_MODEL=none`) the old keyword
gate decides and a template acknowledgement is used. The acknowledgement is written in one
transaction with a `submission_acks` row (a new table: several places insert seven positional values
into `submissions`), the work is started on its own `planning` pool, and the ACP turn ends with a
`kel-work:<submission>` tool call that the desktop renders as a live card (`/api/handoff`).
`Store.publish` posts the checked result into the same conversation; only a VERIFIED result may say
"it passed its checks". A start failure, a boot that interrupted a start, and a hand-off job that
stalls (waiting for a worker, blocked) each say so once, in the chat. The reply model follows the
saved model choice (conversation, then default, then Kel's fallback). A named file in a named folder
runs as file work inside a saved project; anywhere else its text result says plainly that no file
was created. Deviation from the planning pass: `needs_research()` alone is **not** a floor — it
matches "current"/"latest"/"today", so "what's the current state of my job?" would have become a web
research job; explicit research openings and the research kind are floors, and the turn model decides
the rest. *Forbids:* an acknowledgement that claims the work is done, ready, verified or passed; a
work card or result that says "done and checked" for anything but a VERIFIED verdict; the composer's
Stop cancelling handed-off work (the card's Stop does that, after a confirmation); and a second
acknowledgement on retry.

## D-54 — "Projects" is the one term; the header chip is the Project switcher

**Decided by Nick 2026-09-27** (explicit instruction outranks the Figma "Workspace" label, handoff
§36). The product uses **Projects** everywhere a user sees the context boundary. The header chip is
a Project switcher backed by the engine (not per-device renderer state); new chats are created in
the active project; Work, Activity, Knowledge, Recipes and Scheduled read the active project (with
an "All projects" view). There is one Projects list (open, rename, folder, test command). The word
"Workspace" leaves the user interface; the sidebar item that opened Set up Kel no longer carries
that name. Figma geometry and styling still apply; only the label differs.

## D-55 — Kel asks before it starts, never after

**Decided 2026-09-27** (Nick asked for the recommendation that best fits the goal). If a request is
missing a detail that would change the result, Kel asks one short question *before* starting work.
Once work is handed off, the acknowledgement offers a related next-step topic, never a detail that
would change the running work. If Nick nevertheless sends a change for running work, Kel restarts
that work with the change and says so plainly ("Restarting with that change"). *Forbids:* claiming a
change was "folded in"/"added"/"updated" unless the running work was actually restarted with it; a
second independent job created from an amendment.

## D-56 — No consumer updater and no Desktop Pet

**Decided by Nick 2026-09-27.** Remove every update surface (About "Check for updates", update card
and dialog, tray and menu items, auto-updater start-up, prerelease channel) per handoff §26; About
shows version and build only. Remove the Desktop Pet page, route, tray submenu and nav item (§34).
The Figma "Update available" and "Settings — Desktop Pet" frames are retired.

## D-57 — Scheduled tasks become scheduled Recipes in the engine

**Decided by Nick 2026-09-27.** Scheduled work runs through the engine's existing job/recipe path
(one workflow system, handoff §13/§35) so it appears in Activity, Needs you and Work. The donor
aioncore cron scheduler is retired once existing tasks are migrated.

## D-58 — Data and repository clean-up approved

**Decided by Nick 2026-09-27.** Delete the empty engine conversations created at launch and the four
practice Kibble fixes (FIX-0001..FIX-0004) from the real Data root (after a backup); move evidence
screenshots out of the tracked tree; keep the SF Pro fonts.

## D-59 — Reactions removed

**Decided by Nick 2026-09-27.** The thumbs up/down controls on replies are removed (they only wrote to
local storage and had no effect — JR-49). Nothing replaces them for now.

## D-60 — Settings show only what Kel has built

**Decided by Nick 2026-09-27.** Kel is the only assistant and there is no plugin marketplace (handoff
§35). Settings pages are trimmed to what exists: no assistant catalog or marketplace (Assistants shows
Kel only, or is folded away), no Extensions page or external extension tabs, Skills and Tools show only
what Kel actually ships and uses (built-in skills, the MCP servers Kel manages) without hub/market/
install-from-store flows.

## D-61 — English only

**Decided by Nick 2026-09-27.** Remove the language selector; the app ships en-US only. Other locale
bundles are removed.

## D-62 — The General project gets a default folder

**Decided by Nick 2026-09-27.** General (`default`) gets a default folder so coding recipes and the
project map work there: `%USERPROFILE%\Documents\Kel Projects\General` (created on demand; the person
can change it in Projects). No default test command.

## D-63 — Repository history rewrite and branch pruning approved

**Decided by Nick 2026-09-27.** Rewrite git history to drop the evidence screenshots/recordings that
were moved out of the tracked tree (D-58) and force-push `main`; prune branches already merged into
`main` (local and remote). Done at a quiet point with no agents committing, after a full backup bundle
of the old history is kept under `Tools`.

## D-64 — Full access by default: Kel acts without asking

**Decided by Nick 2026-09-27** (explicit grant of authority, so handoff §18's "authority must not
silently grow" is satisfied: it grows because Nick said so). Kel's default authority is **Full access**:
file changes in any project folder, terminal commands, web/network (network mode `full`), Connection
reads and writes, and project grants run without approval prompts. The Set up Kel "Autonomy" choice is
settled as Full access; Settings shows the mode plainly with one switch back to "Ask first".
**Unchanged by this decision (constitution rules, not permissions):** running Kel never edits its own
installed files or its Data root (handoff §21 — self-improvement goes through Kibble → build → Nick's
explicit install); credentials stay in custody and never appear in prompts, renderer state or logs (§12);
every action is still recorded in Activity and reported truthfully (§4). Kel may not silently *learn*
new authority beyond this explicit grant (§3 Memory).

## D-65 — Full access applies verified changes on its own

**Decided by Nick 2026-09-27.** In Full access, a finished coding change that passed Kel's
verification is applied to the project folder automatically; Nick no longer clicks "Apply checked
changes". The result message says what was applied, where, and how verification was done, and the
change stays undoable (the pre-apply snapshot is kept and the card offers "Undo"). **Still waits for
Nick:** a change that failed or skipped verification, a change touching a protected place (D-64), and
any change while the mode is "Ask first" — those keep the existing Apply button. Every automatic
apply is one Activity line.

## D-66 — Hidden orchestration means no managing agents, not no visibility

**Decided by Nick 2026-09-27** (clarifies handoff §1). "Hidden orchestration" means Nick never has to
talk to, direct or manage a spawned agent: every instruction goes to Kel, and Kel alone manages the
staff. It does **not** mean the work is invisible. Kel gives an open, always-available live update:
at a glance in the main chat, a macro view of each piece of work in progress (what it is, roughly how
far along, what state it is in); one click opens the detail (the team on it, each member's role,
model, version and reasoning level, the steps done and in progress, review findings, files changed).
The detail view is read-only apart from "Talk to Kel about this". Staff are spawned on demand; the
same role may run several times at once (no fixed roster or bench). Everything shown must be real
engine state (truth over convenience) — no decorative workers.

## D-67 — Starting model for each staff role; the "Council" is the Oracle

**Decided by Nick 2026-09-27.** The "Council to review decisions" Nick described is the Oracle:
Independent Assurance's fresh, read-only second opinion (intent doc §9, handoff §16), not a new role.
Starting model per role (Preferred mode — each row stays changeable in Settings, and Automatic
routing may still fall back on health/availability, truthfully shown):

| Role | Starting model |
|---|---|
| Kel (Commander) | ChatGPT Luna · Auto |
| Discovery (research) | Claude Sonnet |
| Designer | Claude Fable 5.1 |
| Builder (coding) | Claude Opus 5.5, falling back to Codex |
| Verifier | GPT-6 Astra |
| Oracle (Independent Assurance) | GPT-6 Astra |
| Utility work | DeepSeek Flash |

Verifier and Oracle deliberately sit in a different model family from the Builder (independence,
handoff §16). The detail view (D-66) shows each staff member's model, version and reasoning level.
Architect, Sentinel and Release have no stated preference yet and start on Automatic.

## D-68 — Work cards across the top of the chat

**Decided by Nick 2026-09-27** (chooses the D-66 presentation after the Figma explorations on page
"Office — D-66 explorations"). At the top of the chat, each piece of work Kel's staff is doing is
its own card in one row, with a general progress bar (from real milestones) and the agents on it.
Cards that don't fit go in a dropdown at the end of the row. Finished work stays at the top — done,
failed or stopped — until Nick removes it himself (a remove control on the card). Clicking a card
drops a detail panel down from the top (team with role · model · version · reasoning level, steps,
review and Oracle findings, files changed, verification, "Talk to Kel about this", Stop while
running); clicking anywhere outside closes it. The chat keeps the rest of the height.

## D-69 — Staff always use their role models; the Oracle always gets a reviewer

**Decided by Nick 2026-09-27** (answers the D-66 design note's "Needs Nick" list).
1. **A model picked in a chat applies to Kel's own replies only.** Staff always run on their role
   model (D-67 table, or whatever Nick sets per role in Settings). This supersedes CH-2 for staff work.
2. **Claude Code updated** to 2.1.283 on this PC (global npm install used by Kel's coding runtime);
   it knows `claude-opus-5-5` and `claude-fable-5-1`. Kel still records what actually ran.
3. **If the Oracle's model can't run, Kel hands the Oracle to another model** instead of stopping:
   the next available model, preferring a different family (and provider) from the Builder; if only
   the same family is available it still runs and the record says independence was reduced (coverage
   debt, workforce-os doc 10 §3). Only when no model at all can run does a triggered change wait for Nick.
   The Oracle's triggers (over 10 files / 400 changed lines, security-flagged work, high-assurance)
   are kept.
4. Writing work (posts, documents) staffed as Builder is kept as the default (no objection raised).

## D-70 — Five UI changes that follow from the work cards

**Decided by Nick 2026-09-27.**
1. **Answer "Needs you" inside the card.** A needs-you card's detail shows Kel's question with an
   answer box; the answer goes to Kel in that work's conversation (never to an agent) and the work
   continues. The separate Needs-you surfaces defer to the card.
2. **One live view.** The in-thread work card shrinks to one line pointing at the top card while work
   runs; the thread receives the final result as a done card (verified state, Undo, Open folder).
3. **"Staff & models" in Settings** (per-role mode, model, reasoning level over `/api/model` roles);
   the composer's picker is labelled as Kel's own model (D-69).
4. **Scoping before big work.** When Kel needs details first (D-55), a brief card with 2–3 questions,
   quick-pick answers and "Start"; the top card shows "Scoping" until started. Starting threshold
   (until Nick sets one): work Kel would staff as a Builder + Verifier pod or larger, or any request
   whose plan has open questions that change the result.
5. **Navigation clean-up.** Retire the Work page (the cards replace it); move Permissions, Providers
   and Diagnostics into Settings; one Recipes entry; Projects keeps its chats, folder, Knowledge and
   scheduled tasks.
Items 1, 2 and 4 are drawn in Figma first; 3 and 5 follow existing patterns.

## D-71 — "Existing tests preserved" means the original tests still pass, not that test files are untouched

Found in a live test (packaged main@467c1ff, Full access): asked to "add a multiply(a, b) function to
calc.py and a pytest test for it in test_calc.py", Claude Opus 5.5 did exactly that — and Kel failed
it, because the gate demanded every existing test file stay byte-identical. It then retried the same
deterministic failure four times across models (about $1) and said "failed check repository_evidence:
expected None". The gate's purpose (D-49: a Builder must not weaken, delete or bypass existing tests)
is kept; its definition changes. A change now preserves the existing tests when **(1)** every original
test file still exists, **(2)** the configured test run passes, and **(3)** a second trusted run passes:
the same command, sandbox request, scrubbed keys and time budget, in a throwaway copy of the changed
project where every original *test file* and *test setup file* is put back to its original bytes.
Test setup files are anything that changes what the command collects or how it starts — conftest.py,
sitecustomize.py, pytest.ini/tox.ini/setup.cfg/pyproject.toml, package.json, jest/vitest/mocha/karma
configs, Makefiles, and a module that would shadow a `-m` runner (`pytest.py`). **Stricter choice,
recorded:** new setup files are left out of that copy, and so are new test files whenever the project
already had tests (a new test module can patch the code under test when it is imported); new tests
are covered by the first run. The second run is skipped only when the copy would equal the project
(nothing test-related changed). Both runs are recorded in the evidence with plain summaries ("Your
existing tests still pass" / "An existing test was changed or removed: test_calc.py::test_add no
longer passes in its original form"), which the result, the Office detail and the verification
summary show instead of check ids. **Retries:** an original test that fails, or a removed test file,
is deterministic, so the next try is told exactly what failed and how Kel checks; if that one informed
try fails the same way the step stops (`EXHAUSTED`) instead of cycling models, and the result says so.
*Known limits:* a test deleted while the code it checks still works is not caught by the runs (the
independent review's rubric still asks for intact tests); an intended behaviour change that an
existing test pins cannot pass — Nick updates that test himself first (no allowance mechanism yet);
older isolated (non-native-host) runtimes keep the byte-for-byte rule. *Forbids:* accepting a change
because its own edited tests pass; test setup that only exists in the change deciding the verdict.

## D-72 — Routing defaults (recommended values, adopted under Nick's "execute everything" instruction)

**Adopted 2026-09-28.** Nick asked Claude to execute all remaining work without stopping; these six
open routing choices (docs/v2/design/ROUTING_2.md "Needs Nick") take Claude's recommended values.
They are recommendations, not Nick's explicit picks — each is one setting to change.
1. "Auto" reasoning follows the dispatch tier: fast → low, standard → the model's default,
   deep and assurance → high.
2. Budget classes keep their starting values (standard: 3M tokens, 90 min, $10 API-equivalent) and are
   re-tuned from recorded cost data once enough runs exist.
3. Model strength ranks start from the list-price estimate; outcome evidence adjusts them.
4. OpenRouter carries only DeepSeek Flash for now.
5. Codex and Claude Code subscription calls count as $0 marginal cost when ranking (quota still counts).
6. Kel's own turn, reply and plan calls are recorded in usage.

## D-73 — Visual-audit questions (recommended values, adopted under the "execute everything" instruction)

**Adopted 2026-09-28** (Claude's recommendations, not Nick's explicit picks; each is easy to change).
1. **Notifications switch.** Settings → System gets a Notifications switch, and the setting reaches the
   main process (same sync pattern as Close to tray) so it really stops Kel's attention notifications.
2. **Light mode.** The work cards, panel, scoping card and chips get light tokens and meet contrast in
   Light mode (no dark-only exception).
3. **One "Kel's model".** Settings → Model and the Kel row in Staff & models edit the same value; the
   composer picker is a per-chat override of it (D-69). No second, conflicting control.
4. **Card row scope.** In an open chat, the card row shows that chat's project's work; on Home / new
   chat it follows the active project (or All projects).
5. **Save as a recipe** is offered only for work that finished and passed its checks.

## D-74 — Live-audit questions (recommended values, adopted under the "execute everything" instruction)

**Adopted 2026-09-28** (Claude's recommendations, not Nick's explicit picks; each is easy to change).
1. **Web research runs through the coding runtimes' own web tools** (Claude Code / Codex web search on
   Nick's subscriptions) when no Anthropic API key is present; when no route can do research, the
   Discovery row and the card say so plainly.
2. **Kel never creates a separate new project while a project with a folder is active**, unless the
   request explicitly asks for a new or separate project. "This/the/my project" means the active one.
3. **An open scoping card can be dismissed** ("Not now"), which cancels the scoping without starting work.
4. **The engine keeps running if the app window dies** so work isn't lost (durability), and exits on
   its own once its work is settled and no app has reattached for 10 minutes.

## D-75 — Functional-audit questions (recommended values, adopted under the "execute everything" instruction)

**Adopted 2026-09-28** (Claude's recommendations, not Nick's explicit picks; each is easy to change).
1. **Replies stream** word by word in the chat, as in ChatGPT and Claude (where the runtime supports it);
   the Thinking indicator stays until the first words arrive.
2. **Edit and regenerate.** Nick can edit a message he sent (Kel answers again from there) and ask Kel to
   regenerate its last reply — ChatGPT/Claude parity. Work already handed off is not silently re-run.
3. **One key flow.** The Muse (Ramble) key is managed where the other keys are (Settings → Providers),
   through the same credential custody; Ramble links there instead of keeping its own paste box.

## D-76 — Restores apply once, all or nothing, before anything opens the data

**Decided 2026-09-28** (fixes FN-02; supersedes D-45's in-engine `apply_pending_restore` at start with a
`…pre-restore-<timestamp>` rollback copy). The desktop main process applies a staged restore at the very
start of launch — before storage, aioncore, the engine and the window — through the engine's applier
(`KelEngine.exe --apply-restore`). Every part is swapped by journaled renames; any failure rolls back the
parts already swapped; every attempt clears the pending marker and records one plain-words outcome
(JR-8), so a restore is never re-applied. One "Kel data before restore <date>" folder is kept per applied
restore (newest two kept). Keys and sign-ins stay on this PC across a restore.

## D-77 — One chat store: the engine (staged; recommended values under the "execute everything" instruction)

**Adopted 2026-09-28** (Claude's recommendation from docs/v2/design/CP-10a_ONE_CHAT_STORE.md, not
Nick's explicit pick). Kel's engine becomes the single source of truth for chats; aioncore keeps running
live turns and becomes a disposable cache. Stages 0 (read-only report) and 1 (one link table in the
engine) proceed now behind the `chat_store` switch (`legacy` rolls back; nothing is deleted). Stages 2–3
(history and chat state from the engine) wait for Nick to review the stage-0 report of his real chats
(4 chats exist only in aioncore; 23 empty chats point at missing engine chats). Deleting a chat hides it
and keeps its work in Activity. Stage 4 (bypassing aioncore) is decided after stage 3 has run a week.
Real Data migrates only at an install point, after the automatic backup.

**D-63 executed 2026-09-29.** Old evidence media (docs/**/*.png|jpg|jpeg|gif|webm|mp4|webp) and
/packages/ were removed from all history with git filter-repo (pack 507 MB → 64 MB; the tree of main
is byte-identical before and after). 11 fully merged branches were deleted on GitHub; `main` and the two
unmerged `claude/*` branches remain; release tags were re-pointed. Commit IDs quoted in these docs
before this date are pre-rewrite IDs: look them up in `Tools\kel-history-commit-map-D-63.txt`
(old → new). The complete old history is kept in
`Tools\kel-history-backup-2026-09-29-before-D-63.bundle` (verified).

## D-78 — Motion language approved (docs/v2/design/MOTION.md)

**Decided by Nick 2026-09-29** after the stage-1 prototype (Tools\motion\kel-motion-prototype.html).
Build the motion language into Kel's interface: springs keep the tiny overshoot (0.15–1.1%); the
hand-off line waits ~0.4 s before flying up into its work card; a step's loader turns once when the step
starts (no looping); reduced motion follows the Windows setting only (no in-app switch).

**D-78 addition (Nick, 2026-09-29) — settling fade.** Anything that changes state in the same place
never snaps. When the new state (A) will stay on screen for more than ~5 seconds and (B) is the final
item of a chain (the resting end state), it fades in with a longer, gentle transition — e.g. Undo /
"Undone", a card reaching Done, "Done and checked", "You answered … · Kel is continuing". Intermediate
states and anything gone within 5 s keep the quicker timing. Reduced motion still cross-fades gently.

**D-78 addition (Nick, 2026-09-29) — no layout shift.** Nothing may shift or change after a motion
settles: the final layout (size, text, lines) is computed before animating; text changes cross-fade in
place inside the morph, never after the container arrives; icons render in their own final row from the
first frame and only their state animates; space for arriving content is reserved. Verified by recording
element positions frame by frame (no movement > 1 px after a transition ends).

## D-79 — Simplify the work-card detail panel

**Decided by Nick 2026-09-29** (from an annotated screenshot of the panel). Goal: simplify.
- **Header:** title with an **"Open"** button beside it (opens the project folder on the desktop).
  "Remove" top right. **No Undo** in the panel (Nick asks Kel instead). "Talk to Kel about this" moves
  to the bottom right.
- **Status:** "Done and checked" becomes **"Complete"**; no "5 of 5", no finish time. Hovering "Complete"
  shows the date and time (MM/DD/YY hh:mm AM/PM).
- **Team:** heading "Team · N agents" (no "Kel + 3 on it"). No avatar circles. Each role has its own pale
  colour (Kel stays white; Builder, Verifier, Oracle, Sentinel, Red Team, Designer, Discovery… each
  distinct). Each row shows role, model and reasoning only; what it did moves to a hover tooltip.
- **Steps:** one line each (never wrapped), no per-step times, no "5 of 5".
- **Review Team** (replaces "Review and checks"): one simple status — not started, in progress, failed or
  passed — and, when there's a problem, what the issue is and who is working on it. Nothing else.
- **Removed:** the Files changed section (a "View Diff Report" button comes later) and the footer text
  "Finished work stays at the top…".
The same simplification applies to the phone bottom sheet and the in-thread result card where they
repeat these parts (the button is labelled "Open" everywhere). Engine data stays as is; this is presentation only.

## D-80 — Start the one chat store fresh

**Decided by Nick 2026-09-29** (answers the D-77 chat-store report). Nick has no need for previous
chats. Nothing is imported from the old (aioncore-only) store: the 4 aioncore-only chats and the 3
unmatched replies are left behind. When `chat_store` switches to `engine` (at an install point, after the
automatic backup), every existing chat is archived — moved to Settings → Archived, nothing deleted — so
Kel starts with an empty sidebar. This removes the reviewed-import step from CP-10a stage 2.

## D-81 — The Memory folder: the agents' world

**Decided by Nick 2026-09-29.** AI tools (Claude Code, Codex and every staff member) read and write
**only inside `Desktop\Kel\Memory\`**, and anywhere inside it — including across projects. Nothing outside
it: App, Data (the real data and all keys), Kel (source; self-improvement stays through Kibble) and Tools
are off-limits.
- `Memory\Projects\` — every new project is a subfolder here (new projects only; existing ones stay where
  they are, D-62/D-80 unchanged otherwise). Any project may read or write another.
- `Memory\Kel\` — a read-only mirror Kel keeps current for the agents: settings (no keys, passwords or
  tokens), **all chats** (including chats outside any project, and archived ones) as readable files, and
  project knowledge. Agents never change Kel's settings.
- Enforcement is real, not instruction: Claude Code's guard and Codex's sandbox confine reads and writes to
  Memory; this needs Codex's stronger Windows sandbox (one Windows admin approval by Nick).
Supersedes the D-62 projects root (`Documents\Kel Projects`) for new projects, and D-64's protected-list
approach becomes an allow-list (Memory only).

## D-82 — Kel is dark only

**Decided by Nick 2026-09-29.** Nick will not use Light mode. All Light-mode development and Light-mode
bug fixing stops. Kel ships dark only: the theme/colour choice is removed from Settings → Appearance,
which from now on holds only non-colour controls (text size, zoom, density and similar). Existing light
tokens may stay in code but are no longer maintained or tested. Supersedes D-73.2.

## D-83 — Recipes: save when sending, create ahead of time

**Decided by Nick 2026-09-29.** Nick can save a request as a recipe at the moment he sends it (an option
in the composer), and can create a recipe before ever using it (in the Recipes settings/page). "Save as a
recipe" is no longer limited to work that passed its checks. Supersedes D-73.5.

Also confirmed by Nick 2026-09-29: all other adopted defaults in D-72..D-77 stand. No Anthropic API key
will be added.

## D-84 — Kel owns the tests; Nick never touches verification

**Decided by Nick 2026-09-29** (answers the D-71 limit). Nick never names, edits or approves tests. When a
requested behaviour change contradicts an existing test, the Builder may change that test — and only such
tests. Every changed or removed existing test must be approved by the independent Verifier (different
model family) as necessary for, and faithful to, the request; the Oracle and Sentinel also see test
changes on changes they review. A test change that isn't justified by the request fails the step (the
D-49/D-71 protection against weakening tests stays). The result tells Nick in one plain line which tests
Kel changed and why. Supersedes D-71's "Nick updates the test himself first".

## D-85 — Proportional verification: don't over-test or over-validate

**Decided by Nick 2026-09-29.** Verification effort must match what's at stake. Skip or lighten checking
when the thing (A) is going to change anyway, (B) can be verified by Nick later just by using it, or
(C) isn't worth the effort. Project bloat from slow, heavy validation is itself a defect.

**In Kel (runtime):** the default is the lightest check that fits.
- Small, reversible or exploratory work: run the project's own tests if they exist; no independent
  reviewer. Undo covers the rest.
- A Verifier (independent review) only for real code changes of meaningful size or risk.
- The Oracle only for large or hard-to-undo changes; Sentinel only for genuine security / data-migration
  work; the Red Team only for high-assurance (D4) work. Never three reviews on routine work.
- Prototypes, drafts and throwaway work get a quick sanity check, not the full chain.
- Speed matters: a check that adds minutes must earn its place.

**In building Kel (development process):** focused tests for what changed; one full suite before an
install, not after every edit; live model runs and frame-by-frame captures only for risky or
user-visible behaviour, not by default; no audits of things about to be redesigned; Nick's own use is a
valid way to verify polish.
Refines D-66/D-67 review triggers and D-84 (the Verifier still approves test changes when a Verifier runs).
