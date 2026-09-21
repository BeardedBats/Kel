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
