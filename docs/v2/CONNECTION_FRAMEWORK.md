# The Connection Framework

*V2.0 / V2-04. Small on purpose: this is the page a developer reads before adding the next service or the
next thing Kel can do with one.*

## The four words

| Word | What it is | Where it lives |
| --- | --- | --- |
| **Connection** | Nick's own grant: Kel has credentials for this service and can use its API. One row per service he connected. | `runtime/kel/connections.py` (table `connections`) |
| **Service** | What Kel already knows about a service Nick uses: address, header, how the credential is presented, documentation, what to go and fetch, how sure Kel is. | `runtime/kel/connection_services.py` |
| **Template** | One of the three kinds of credential — API key, Account authorization, Bot or webhook — with the words a person reads and the credential field name. | `runtime/kel/connection_framework.py` |
| **Action** | One thing Kel can do with a service: the request it makes, what it returns, whether it changes anything. | `runtime/kel/connection_actions.py` |

Services and actions are **rows of data**. Connections and their checks are **state**. Nothing in this
framework is a module, table, worker or workflow per service — that is the whole point of it existing.

## The rules, and what enforces them

1. **One place makes the request.** `connections.perform_request` is the only function that opens a socket
   to a service. The network rules of V2-14 (no internet / approved domains / ask before a new domain / show
   contacted domains) go there and nowhere else. A test pins that there is exactly one `urlopen` in the
   module.
2. **The engine never holds a credential.** The shell keeps values in the OS-backed store under
   `connection:<id>`, and the main process hands the engine the values for one request. The engine records
   field names and a `kel:connection:<id>` pointer, refuses any other pointer, and scrubs the value out of
   anything that could become durable. A test searches a whole stored row for the value.
3. **The answer comes back; it is never written down.** A check reads only the status. An action asks for
   its answer, which is bounded, scrubbed, and handed to the caller. What is stored is the fact of the call:
   connection, action, domain (never the path or a query string), status, attempts, duration.
4. **A refusal is a result, not an error.** `refused` (401/403) is information and is never retried. A
   failed check never silently clears the credential record, and a recorded credential never silently
   claims the service works.
5. **Retries are bounded and honest.** Try again only for 429/5xx or a dropped connection; bounded per
   attempt by the timeout and overall by a budget; the record says how many times Kel tried.
6. **Anything that changes something waits for Nick.** An action with `mutating: True` is refused unless he
   confirmed. Today every action in the catalogue is a read.
7. **Kel says how sure it is.** A service row carries `documented`, `assumed` or `to-confirm`, and the
   surface repeats that sentence. An address Kel does not know is not invented.
8. **No switch a service could not honour.** A capability (the plain-word toggles in `capabilities.py`) is
   offered only when a production path can honour it. That is why there is no Connections switch yet: the
   assistant cannot call a connection action (see *Not in the framework* below).

## Adding a service

Append one row to `KNOWN_SERVICES` in `runtime/kel/connection_services.py`:

```python
{
    'id': 'example',                     # must equal the slug of the name (a test proves this)
    'name': 'Example',                   # what Nick calls it
    'kind': 'api_key',                   # api_key | oauth | bot  (the framework's templates)
    'base_url': 'https://api.example.com',
    'auth_method': 'header',             # header | bearer | query | basic
    'auth_header': 'Authorization',      # the header (or query parameter) the credential goes in
    'auth_prefix': 'Bearer ',            # null = Kel works it out; '' = exactly as it is; a word = added
    'docs_url': 'https://example.com/docs',
    'test_endpoint': 'https://api.example.com/me',
    'credential': 'the API key from your Example account',   # what Nick has to go and fetch
    'source': 'documented',              # documented | assumed | to-confirm
}
```

Use only addresses the service's own documentation publishes. If you do not know them, say `to-confirm`
and explain it in `note` — never guess. Then run `python -m unittest tests.test_v2_connections`: the
catalogue tests check the shape, the id/name agreement and that the addresses are http(s).

## Adding an action

Append one row to `ACTIONS` in `runtime/kel/connection_actions.py`:

```python
{
    'id': 'example-list-things',         # unique; prefix with the service
    'service': 'example',                # the catalogue id it belongs to
    'name': 'List your things',          # a plain sentence a person reads
    'description': 'One line about what it does.',
    'method': 'GET',                     # a write must also set 'mutating'
    'path': '/v1/things',                # relative to the service's base_url
    'params': ('limit',),                # the only query parameters a caller may pass; anything else is dropped
    'returns': 'A page of things.',
    'mutating': False,                   # True = Kel asks Nick before it runs
    'source': 'documented',              # documented | assumed
}
```

The action then works through `Connections.run(connection_id, action_id, credentials, params, confirmed)`
and `POST /api/connections {action: 'run', …}` with no further code. There is no per-service function to
write, and there must never be one.

## Testing it

| What | Command |
| --- | --- |
| The model, the framework and the actions | `cd runtime && python -m unittest tests.test_v2_connections` |
| The migration inventory (a new migration number must not collide) | `python -m unittest tests.test_v16_r8_migrations` |
| Everything, before committing | `python -m unittest discover -s tests` |
| The renderer types and the Connections surface | `cd desktop && bunx tsc --noEmit && bunx vitest run` |

Tests use a local stand-in service on the loopback interface (`LocalService` in
`runtime/tests/test_v2_connections.py`) — no test may contact a real service. Add a case for every new
rule; a rule without a test is a rule that will be broken by the next change.

## Not in the framework (and why)

- **A tool the assistant can call.** The engine and the Connections page can run an action when Nick asks;
  nothing in a conversation can yet. The assistant's tools come from the coding runtime the desktop agent
  runs, so this is a bridge to build deliberately — with the same one-request rule, the same mutating
  confirmation, and a capability switch added only when it can be honoured. Until then no Connections
  switch is offered.
- **The OAuth account sign-in step.** The template exists and says so: a Google Drive token has to be
  pasted until the sign-in flow is built.
- **Network rules.** V2-14 owns them; they belong inside `perform_request`.
- **Actions that change things.** The machinery and the confirmation gate are built and tested, but no
  write action is shipped yet: that is a product decision Nick should make explicitly.
