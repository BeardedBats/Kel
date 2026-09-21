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
