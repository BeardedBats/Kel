# CP-10a — One chat store

Status: **stages 0 and 1 built, 2026-09-28; the D-80 switch (fresh start, default `engine`) and stage 3's
state writes built, 2026-09-29** (see the two "Built" notes below). Stage 2's read path and the
engine-sourced sidebar list are still design. Base read: `main@b091df1` (desktop, engine and
docs), plus read-only copies of Nick's `Data\store\aionui-backend.db` and `Data\engine\kel.sqlite3`
taken into a scratch folder. Nothing was written to `Data` or `App`.

Inputs: handoff §13 ("reuse authoritative systems instead of creating second systems … a second task
database"); DECISIONS D-45, D-51, D-53, D-57, D-58, D-75.2, D-76; KNOWN_LIMITATIONS; the fix commits
`44d4115` (chats past 20), `467c1ff` (kel_meta and the normaliser), `80d4105` and `7a3c257` (LIVE-7,
FN-10), `3bfda61` (FN-02), `7d79d4b` and `1607c81` (D-75.2); and `third_party/AIONUI-PROVENANCE.md`.
No doc in `docs/` mentioned CP-10a before this one. The item comes from the Phase 3 queue: "Merge the
two chat stores (CP-10a) — design first, careful migration".

Paths: `KelService.ts` and `reconcileHistory.ts` are in `desktop/packages/desktop/src/process/services/kel/`.
Other desktop paths are relative to `desktop/packages/desktop/src/`, and engine paths to `runtime/kel/`.

---

## 0. The short version

- **Today a Kel chat lives in two databases.** The donor host (`aioncore.exe`) owns the chat row the
  sidebar shows and the rows that were streamed through it. The engine owns the words Kel actually
  said and heard, the work, and the details (`meta`). Three mapping files and a JSON field join the
  two. The main process rebuilds a merged view by matching text prefixes on every read.
- **aioncore cannot be changed.** It is a downloaded release binary (v0.2.2). Its Rust source is not
  in this repository.
- **Recommendation: option (a), in stages.** The engine becomes the one store for chat history and
  chat state. aioncore keeps two jobs: running the live ACP turn, and holding a "session handle" row
  per chat, which it needs in order to run that turn. Nothing reads aioncore's copy of a finished
  turn any more. Every stage is additive and sits behind a switch, so it can be reversed. It runs on a
  copy of Data first. Nick's chats are carried over by a one-time import that is reviewed before it
  is kept.
- **Effort:** stages 0–3 are about 7–12 agent-days (M–L). A later optional stage 4 would take chats
  off aioncore altogether (L, 1–2 weeks). That needs Nick's decision.

---

## 1. The architecture today

### 1.1 The stores and the glue

| # | What | Where | Owner / writer | Contents |
|---|---|---|---|---|
| A | Donor chat DB | `Data\store\aionui-backend.db` | aioncore.exe (bundled binary) | `conversations` (id, name, `extra` JSON, pinned, `archived_at`, project/folder ids), `messages` (id, `msg_id`, type `text`/`acp_tool_call`/`tips`, `content` JSON, position, status, hidden), `acp_session`, `conversation_assistant_snapshots`, `projects`, `folders` |
| B | Engine DB | `Data\engine\kel.sqlite3` | KelEngine (`core.py` Store) | `conversations(id, project_id, title, created)` (`projects.py:46`; "never altered", `projects.py:6`); `messages(seq, conversation_id, role, text, job_id, at, meta)` (`core.py:184-197`); side tables `schedule_conversations`, `conversation_hidden` (`schedules.py:47-49`), `project_meta.utility_conversation` (`projects.py:48-49`), `project_bindings(donor_id, …)` (`projects.py:51`), `rewound_messages`, `hidden_rows`, `pending_amendments` (`rewind.py:22-26`), `submissions`, `submission_acks`, `jobs`, `publications` |
| C | Legacy map | `Data\engine\aion-conversations.json` `{donorId: engineId}` | desktop main (`KelService.ts:436-444`); the engine only reads it | Mappings from before the per-session files existed, plus chats adopted by the main process |
| D | Session map | `Data\engine\aion-session-map\<sha256(donorId)>.json` | ACP host (`acp_host.py:338-346`) | One `{donorId: engineId}` per chat, written when the ACP session starts |
| E | Donor link field | `conversations.extra.kel_conversation_id` / `kel_project_id` in A | desktop main on adopt (`KelService.ts:479-484`) | The engine id, for chats the main process created |
| F | History projection | `Data\engine\aion-history.json` `{donorId: HistoryMessage[]}` | desktop main (`KelService.ts:486, 529-532, 607-608, 644-645`) | Rows the donor does not have (engine-only messages, overlays that carry `kel_meta`, synthetic work cards and approval anchors) |
| G | Hidden rows | `hidden_rows` in B | engine, driven by the renderer (`kelRewrite.ts:119`) | Donor or merged row ids to hide after an edit or "Answer again" |
| — | Vestigial | `aionui-chat-history\<id>.txt` (`process/utils/initStorage.ts:250-283`) | nothing | The old AionUI JSON message files. `ProcessChatMessage` has no callers, and Nick's Data has no such folder. Not a live store. |

**aioncore is fixed.** `App\resources\bundled-aioncore\win32-x64\provenance.json` records
`aioncore.exe` v0.2.2 downloaded from the iOfficeAI/AionCore GitHub release (source revision
`47e66d0d…`, Apache-2.0, per `third_party/AIONUI-PROVENANCE.md`). The repository has no `Cargo.toml`
and no AionCore source. Kel's changes to the donor are all in the AionUI TypeScript (renderer, main,
preload). The only ways to reach aioncore's store are its HTTP and WS API (`common/adapter/ipcBridge.ts:259-360`,
`:1300-1330`) and the ACP stdio protocol toward the agent it spawns.

Among the routes Kel uses there is none that appends a finished message to a chat without running a
turn. `POST /api/conversations/{id}/messages` is "send". That is why engine-only messages are kept in
the side file F rather than written into A (`KelService.ts:486`). aioncore's full API is not
documented in the repository, so this is only verified for the routes Kel calls (see Q6).

### 1.2 Who reads and writes what

| Component | Reads | Writes |
|---|---|---|
| **aioncore.exe** | A | A: every chat row; every streamed ACP update as `messages` rows; archive, pin, rename and delete through its API. It spawns `KelEngine --acp` per chat with `AIONUI_CONVERSATION_ID` (`acp_host.py:315`). |
| **ACP host** (`acp_host.py`, a KelEngine process spawned by aioncore) | C and D to find the engine id (`:320-325`); B through the engine HTTP API | D (`:338-346`); B through `/api/conversation` (first prompt, `:490`) and `/api/send` (`:540-541`) |
| **Engine daemon** (`service.py`, `core.py`) | B; C and D only through `projects.conversation_for_donor` / `donor_for_conversation` (`projects.py:676-710`) | B only |
| **Desktop main** (`KelService.ts`) | A (HTTP), B (HTTP), C, D, F | A (adopt creates rows, `:479-484`; workspace repair PATCH, `:419-422`; schedule sweep DELETE, `:731`); C and F (`:436-444`, `:607-608`, `:644-645`) |
| **Renderer** | A through `ipcBridge` (list, messages, search); B through `kel:request`; F through `kel:history`; the link through `kel:conversation` | A (create, send, rename, pin, archive, delete); B (rename `/api/conversation-title`, `/api/rewind`, `/api/projects` bind, office `/api/send`) |
| **Backup** (`backup.py`) | A, B, C, D, F and the rest of `Data` | — (restore swaps `engine`, `store` and `host` together: `:46`, `:842-861`, `:957-1041`) |

### 1.3 The flows

**New chat and first send.**
1. The renderer creates the donor row: `ipcBridge.conversation.create` (`renderer/pages/guid/hooks/useGuidSend.ts:252-268`). Its `extra` has `kel_project_id` but no engine id.
2. `bindNewChat` → `/api/projects` bind writes `project_bindings(donor_id)` in B (`useGuidSend.ts:26-32, 298`).
3. The first message is kept in `sessionStorage` and sent after navigation (`useAcpInitialMessage.ts:77`).
4. aioncore spawns the ACP host. `session/new` reads C and D. With no mapping, it reserves a new uuid and writes D (`acp_host.py:313-347`). It creates nothing in B yet (ST-04).
5. The prompt goes aioncore → ACP → `prompt`. On the first prompt it calls `POST /api/conversation {donor, id}` (`acp_host.py:490` → `projects.py:807-820`), then `POST /api/send` (`:540-541`). The engine inserts the user message (`service.py:318`).
6. aioncore writes its own user row in A at the same time. **The same words now exist in both stores, with unrelated ids.**

**Streaming (D-75.1).** The ACP host polls `GET /api/draft` (`acp_host.py:448-467`; `service.py:822-829`). It sends only the unshown remainder as `agent_message_chunk` (`:469-481`) and watches `/api/state` for new assistant `seq` values (`:547-554`). aioncore turns the chunks into a donor text row. The renderer shows it through aioncore's WS (`useAcpMessage.ts:276, 305`). The engine stores the finished reply as one `messages` row with its `meta`. aioncore may **merge several Kel replies into one donor row** (`reconcileHistory.ts:83-84`).

**Hand-off (D-53).** Once `ack_seq` is seen, the ACP host emits a `tool_call` with `toolCallId: 'kel-work:<submission>'` and ends the turn (`acp_host.py:557-566`). aioncore stores it as an `acp_tool_call` row. `MessageList.tsx:303-313` renders it as `KelWorkCard`, which polls `/api/handoff` (`service.py:1763`). If the stream dropped or the window was closed, the main process makes a synthetic card row in F (`ensureWorkCards`, `reconcileHistory.ts:128-168`). Job progress rows use `toolCallId = job id` (`acp_host.py:606-624`). On reconcile, the main process projects their live status over the stale donor row (`KelService.ts:568-594`).

**Result.** `Store.publish` inserts the checked result as an assistant message in B with `meta` (`core.py:733-799`). No ACP turn is running, so **the result never reaches A**. It exists for the renderer only because F gets it:
- at reconcile (`KelService.ts:504-595`, run on every `kel:history` read, `:635-649`);
- through the LIVE-7 watcher, which polls `/api/messages/since` every 1.2 s (`KelService.ts:655-705`; `service.py:1882-1891`), waits until aioncore says the chat is not processing (`:684`), then reconciles and sends `kel:history-updated` (`:690-696`) so the open chat re-reads (`Messages/hooks.ts:1025-1033`).

The renderer also polls `/api/state` per open chat and reloads when its fingerprint changes (`hooks.ts:981-1021`). The same B-only path carries scheduled runs (D-57), office sends (`officeApi.ts:302` → `/api/send`), approvals (`KelService.ts:535-567`) and replies that finished while the window was closed.

**Opening a chat (the merge).**
1. `loadConversationMessagePage` calls `kel:history` (`utils/chat/messagePagination.ts:26-39`).
2. That runs `reconcile`. It pages every donor message 200 at a time, up to 1000 pages (`KelService.ts:504-527`), reads `/api/state` (`:528`) and runs `recoverHistory` (`reconcileHistory.ts:74-120`):
   - each engine message is matched to a donor row **by position and text prefix**;
   - unmatched engine messages become `kel-history-<seq>` rows;
   - matched rows that carry `meta` get a `kel_overlay` copy with `kel_meta` that replaces the donor row.
3. The renderer merges these with every donor page by id and sorts by `created_at` (`utils/chat/kelHistory.ts:31-82`).
4. It then removes `hidden_rows` (`kelHiddenRows.ts:15-40`).
5. It normalises the rows (`hooks.ts:777-785`; `chatLib.ts:475-549` keeps `kel_meta`, fixed in `467c1ff`).
6. It merges with live rows (`hooks.ts:787-822`).

**Edit and "Answer again" (D-75.2).**
1. `MessageText.tsx:296-314` emits `kel.message.rewrite`.
2. `kelRewrite.ts:82-126` resolves the engine id and calls `/api/rewind` `edit` or `regenerate` (`rewind.py:176-193`). The edited message is found **by text and position from the end**. Nothing is deleted: seqs go into `rewound_messages`.
3. It picks the donor rows to hide by text match (`kelRewrite.ts:45-63`) and records them through `/api/rewind hide`.
4. It resends through the donor (`AcpSendBox.tsx:487-495`).

Donor rows are never truncated. The donor has no per-message fork for Kel chats, so the branch is replaced in place (commit `7d79d4b`).

**Rename, pin, archive, delete** (`GroupedHistory/hooks/useConversationActions.ts`):

| Action | Where | Donor (A) | Engine (B) |
|---|---|---|---|
| Rename | `:137`, `:144`; `useTitleRename.ts:67, 74` | yes | best effort through `engineConversationTitle.ts:12-26`; a failure is only logged (`:23`) |
| Pin | `:173-182` | yes (`extra.pinned`) | no |
| Archive / unarchive | `:305`, `:311`, `:103`, `:278` | yes | no |
| Delete | `ChatHistory.tsx:122`; `ArchivedSettings/index.tsx:412, 449, 452` | yes | no. The pair is dropped from C and F only at the next start, when the donor answers 404 (`KelService.ts:596-606`). The engine conversation and its messages remain. |

The engine hides chats only for deleted schedules (`schedules.py:815-837`). The main process mirrors that with a donor DELETE (`KelService.ts:719-755`).

**Sidebar list.** It comes from the donor only (`useConversationListSync.ts:359-395`, `limit: 10000`). Engine ids become donor routes through `extra.kel_conversation_id` (`:343-357`). Chats that exist only in B become donor rows through **adoption**, `adoptEngineConversation` (`KelService.ts:465-492`), which runs:
- at start-up for every non-empty, non-hidden, non-utility engine chat with no mapping (`:493-501`);
- every 20 s for chats created by a schedule (`:719-765`);
- on demand (`kel:open-engine-conversation`, `:707-713`).

Utility chats are filtered at `:475` and `:496` (FN-10).

**Search.** `kelHistorySearch.ts:10-61` searches F in memory (`kel:history-search`, `KelService.ts:621-633`) and the donor (`searchConversationMessages`), then calls `conversation.get` per engine hit to drop chats the donor no longer has. The command palette uses that, plus engine `/api/search` for transcripts and vetting (`KelCommandPalette.tsx:229-278`; `search.py:34-99`). **F only holds chats reconciled since start-up**, so an engine message that was never projected is not found by the chat search.

**Start-up** (`KelService.ts:404-608`). Reads C, D and F. Repairs workspace paths across *all* donor chats, active and archived, paged (`repairWorkspacePaths.ts:96-132`). Folds every `extra.kel_conversation_id` into the mapping (`KelService.ts:425-426`; the fix for chats past 20 in `44d4115`). Adopts. Then **reconciles every mapped chat before any window opens** (`:596-606`).

**Backup and restore.** A backup (format 2) copies A through SQLite's backup API with its secrets blanked, copies B hot, and copies C, D and F as ordinary engine files (`backup.py:456-500`). A restore swaps all three parts by journaled renames at the very start of launch (D-76; `process/startup/pendingRestore.ts:1-15`; `backup.py:957-1041`). **Restoring one side without the other is not a supported state.** Before D-76, a partial swap re-applied on every launch (FN-02).

**Phone and WebUI.** The same renderer runs in a browser through the gateway. `readKelHistory` calls `window.kelAPI.history`, which only the Electron preload provides (`kelHistory.ts:15-19`). In a browser it returns `[]`, and the page falls back to donor rows (`messagePagination.ts:31-35`). So a phone shows none of the engine-only messages (results, scheduled runs, adopted chats) and no `kel_meta`. This comes from reading the code; it was not checked live.

### 1.4 Every sync point

| # | Sync point | Direction | Trigger | Code |
|---|---|---|---|---|
| S1 | Donor id → engine id at session start | D/C → ACP host | `session/new` | `acp_host.py:313-347` |
| S2 | Reserve and create the engine conversation | ACP host → B | first prompt | `acp_host.py:490`; `projects.py:807-820` |
| S3 | Donor chat → project binding | renderer → B | new chat | `useGuidSend.ts:298`; `projects.py:645-674` |
| S4 | Start-up mapping merge (C + D + E) | files and A → main memory | launch | `KelService.ts:404-427` |
| S5 | Adoption (B chat → new A row + E + C + F) | B → A | launch, 20 s sweep, open | `KelService.ts:465-501, 719-765, 707-713` |
| S6 | Reconcile (A pages + B state → F) | A + B → F | launch, every `kel:history` read, LIVE-7 | `KelService.ts:504-608, 635-649`; `reconcileHistory.ts:74-168` |
| S7 | LIVE-7 watcher | B → F → renderer | 1.2 s poll after the turn ends | `KelService.ts:655-705` |
| S8 | Renderer engine poll | B → renderer | per open chat | `hooks.ts:981-1021` |
| S9 | Rename mirror | renderer → A and B | rename | `engineConversationTitle.ts:12-26` |
| S10 | Rewind plus row hiding | renderer → B (`rewound_messages`, `hidden_rows`) | edit, Answer again | `kelRewrite.ts:82-126`; `rewind.py` |
| S11 | Schedule hide → donor delete | B → A | schedule deleted | `KelService.ts:719-755` |
| S12 | Stale mapping clean-up | A 404 → C and F | launch | `KelService.ts:596-606` |
| S13 | Workspace path repair | main → A | launch | `KelService.ts:416-423` |
| S14 | Job status projected over stale donor tool rows | B → F | reconcile | `KelService.ts:568-594` |
| S15 | Merged search | A + F | palette, search | `kelHistorySearch.ts`; `KelService.ts:621-633` |
| S16 | Backup and restore of A, B, C, D and F together | — | backup, restore | `backup.py`; `pendingRestore.ts` |

Two sync points are missing. **Nothing propagates a donor delete, archive or pin to B.** And
**nothing ever writes an engine-only message into A**, because it cannot.

### 1.5 What Nick's data looks like (read-only copy, 2026-09-28)

Counts only; no titles or text.
- **Donor (A):** 35 chats, 2 of them archived. 25 carry `extra.kel_conversation_id`. 25 message rows: 21 text, 2 `acp_tool_call`, 2 `tips`.
- **Engine (B):** 8 conversations, 15 messages. 16 donor chats are mapped by C or D.

| Class | Chats | What it means |
|---|---|---|
| Live link, both sides have messages | 6 | Normal. Content is duplicated; one chat has 2 donor rows against 1 engine message. |
| Live link, engine only (donor 0 rows) | 1 | Its history exists only in B and F. On a phone it is empty. |
| Live link, both empty | 1 | — |
| Dead link: engine conversation missing, donor empty | 23 | Mostly audit and test chats whose engine rows are gone. They show in the sidebar as empty chats. |
| Dead link, **donor has 2 text rows** | 1 | **These words exist only in A.** |
| No link at all, donor has 1–2 text rows | 3 | **Words only in A.** The engine never saw them, or they came from an older store. |
| **Conflicting links**: E disagrees with D | 7 | See B-9 below. |

Engine conversations not linked from any donor chat: 0.

**So neither store is a superset of the other.** Some of Nick's chats have words only in A, one has
words only in B and F, and most show the same words twice. Any migration has to take the union.

---

## 2. Bugs and complexity caused by two stores

| ID | Symptom | Two-store cause | Status |
|---|---|---|---|
| B-1 (fixed in `44d4115`) | Chats past the first 20 lost their engine link | The mapping read the donor catalog, which is capped at 20 rows | Fixed by reading the full paged list. It is one of three places that must page the donor correctly (`repairWorkspacePaths.ts:96-132`, `kelHistory.ts:40-50`, `KelService.ts:510-523`). |
| B-2 (fixed in `467c1ff`) | Results, scoping cards and Details never showed | `kel_meta` rides on a donor-shaped row, and the donor normaliser dropped the unknown field | Fixed in `chatLib.ts:475-549`. Still exposed elsewhere: `preferTextMessageVersion` keeps the longer text row (`chatLib.ts:391-400`), so a longer live row can replace the overlay and drop `kel_meta` (`hooks.ts:801-822`); `normalizeDbTipsMessage` whitelists fields (`hooks.ts:680-734`). |
| B-3 LIVE-7 (mitigated in `80d4105`, `7a3c257`) | The scoping card appeared only after leaving and reopening the chat | Details live in B; the chat reads A plus F, and F was refreshed only on reconcile | Mitigated by a 1.2 s engine poll, a wait for `is_processing` to clear, reconcile, and an IPC push. That is three polls (S7, S8, and the donor's own), and the card still waits for the donor turn to end. |
| B-4 FN-10 (fixed in `80d4105`) | The "Recipe runs" utility chat appeared as a user chat | Adoption copied every engine chat into A. What counts as a chat is decided in two places. | Fixed by a filter at `KelService.ts:475, 496`. Every future engine-only kind needs the same filter. |
| B-5 FN-02 and FN-15 (fixed in `3bfda61`, D-76) | A restore failed partway and re-applied on every launch; renames reverted and jobs came back | A restore must swap A, B and the glue files together while aioncore holds A open | Fixed by applying the restore before anything opens the data. The underlying coupling remains: A, B, C, D and F must match or chats fork (see B-9). |
| B-6 D-75.2 (built in `7d79d4b`) | Edit and Answer again need both stores | The engine rewinds by seq; donor rows cannot be removed, so they are hidden by id, **chosen by text match** (`kelRewrite.ts:45-63`); the edited message is found in B by text and position from the end | Works, but two chats with repeated text, or an overlay row, can hide the wrong row. A fourth id space (`hidden_rows`) was added. |
| B-7 | One job showed as two "View steps" cards | Donor and stream row ids differ | Fixed by keying on `tool_call_id` (`hooks.ts:787-799`) |
| B-8 | Several Kel replies merged into one donor row | aioncore concatenates ACP messages | Handled by text-prefix consumption (`reconcileHistory.ts:83-111`). This makes every B↔A match fuzzy. |
| **B-9 (new, latent)** | A chat can map to two different engine conversations | The main process lets E win (`KelService.ts:425-426`); the ACP host never reads E and lets D win (`acp_host.py:320-325`) | 7 chats in Nick's data. All are empty or dead today, so nothing is visible yet. The first chat where both have content will show one conversation's history while Kel answers in the other. |
| **B-10 (new)** | Deleting a chat leaves its engine conversation, messages and jobs; archive and pin are unknown to the engine | No donor → engine propagation | Engine search can return deleted chats: the palette drops them (`kelHistorySearch.ts:39, 46`). Engine counts include them. |
| **B-11 (new)** | Chat search misses engine messages the renderer has not projected yet | `kel:history-search` scans F in memory only (`KelService.ts:621-633`) | Also FN-08 (the palette filters on a 79-character hint). |
| **B-12 (new, from code reading)** | Phone and WebUI chats lack results, scheduled-run messages, adopted history and `kel_meta` | F is served only through the Electron preload (`kelHistory.ts:15-19`) | Not verified live |
| B-13 | Dead and empty chats in the sidebar | Engine rows were deleted (D-58 clean-up, test runs) while donor rows stayed | 23 in Nick's data |
| B-14 | A rename can diverge | Best-effort engine mirror; the failure is only logged (`engineConversationTitle.ts:23`) | Open |
| B-15 | Start-up cost and fragility | Reconcile pages *every* message of *every* mapped chat before the window opens (`KelService.ts:596-606`); a 404 or throw aborts `initializeKel` for anything but a missing chat (`:600`) | Grows with history |
| B-16 | `aion-history.json` rewritten whole on each change | `persistMapping` JSON-serialises every chat's projection (`KelService.ts:436-444`) | Grows with history |

**Complexity cost.** About 900 lines exist only to join the stores:
- `reconcileHistory.ts` (184 lines);
- about 300 lines of `KelService.ts` (`:404-765`);
- `kelHistory.ts` (82), `kelHistorySearch.ts` (61), `kelHiddenRows.ts` (41), `kelRewrite.ts` (154);
- the engine side of rewind's `hide` action;
- `repairWorkspacePaths.ts`;
- `conversationCounts.ts`.

There are three pollers (S7, S8, and the renderer's list refresh) and four id spaces:
- donor message ids;
- `kel-history-<seq>`;
- overlay copies;
- `kel-work-<submission>` and `kel-approval-*` synthetic rows.

---

## 3. Options

aioncore cannot be changed in any option: its store, schema and API stay as they are. The options
differ in which store Kel treats as the truth and what it stops doing.

### (a) The engine is the single source of truth; aioncore's store becomes a cache

**What changes.** B holds every chat's messages, links and state: title, archived, pinned, deleted.
The renderer reads history and the chat list from the engine. aioncore keeps:
- running the ACP turn;
- the WS live stream during a turn;
- one donor row per chat as the **session handle** that `/messages` send and `acp_session` need.

Nothing reads donor message rows for a finished turn. A **stage 4**, optional and later, would stop
using aioncore for Kel chats altogether: the renderer sends through the engine's `/api/send`
(already used by `officeApi.ts:302`) and streams from the engine's draft. At that point aioncore's
store holds no chat content.

**Migration.**
- A one-time, idempotent import of the union: A-only text rows go into B, marked
  `meta.source='donor-import'`; links from C, D and E go into one engine table, with conflicts
  resolved by content.
- Flags on the engine chat state.
- Glue files C, D and F are kept read-only for rollback, then retired.

**Risk.**
- *Turn-end hand-over flicker*: the streamed donor row gives way to the engine row. Mitigation: a
  stable rule. During a turn, show engine rows plus donor rows newer than the turn's user message.
  After the turn, show engine rows only.
- *Donor-only row kinds*: tips and error notes from aioncore have no engine twin. Mitigation: pass
  through donor `tips` rows for turns that have no engine reply.
- *Performance*: `/api/state` returns every message of a chat. It needs a paged messages route.
- *The first run on real Data*: mitigated by the staged plan in §4.

**Effort.** Stages 0–3: about 7–12 agent-days (M–L). Stage 4: L (1–2 weeks). It rewires the donor
send box and stream hooks, which are the most-modified donor files.

**For aioncore.** Nothing changes in the binary. Its DB keeps growing with streamed rows that Kel
ignores after the turn. They are disposable, and backups still carry them. With stage 4, aioncore
keeps files, workspaces and settings but no Kel chats.

**Fit.** Handoff §13 and D-51 ("no second history store"): the engine already owns work, messages,
meta, rewind and search. It is the authoritative system; A is the second one.

### (b) aioncore is authoritative; the engine keeps references

**What changes.** A would hold all messages. The engine would keep only donor ids and read A for
context.

**Why it fails.**
1. aioncore has no route Kel knows of that appends a message without running a turn. So results,
   scheduled runs, approvals and anything written while the window was closed cannot be put there.
   F would stay, as a second store.
2. The engine needs messages *inside* its own transactions: `submission_acks` written with the ack
   (D-53), `publications` → message (`core.py:733-799`), rewind, context building, `messages_since`,
   search. Reading them over HTTP from a donor process that may not be running (the engine outlives
   the window, D-74.4) breaks durability.
3. The schema cannot be changed: `kel_meta`, `job_id`, hidden and rewound flags would all ride on
   `extra` or content JSON that the donor's normaliser and cache may drop (B-2).

**Migration.** Large: engine code paths that read `messages` become remote reads.
**Risk.** High.
**Effort.** L+.
**For aioncore.** It would become load-bearing for Kel's work engine, which is the opposite of
AIONUI-PROVENANCE's "Kel retains its existing Python work engine".

**Not recommended.**

### (c) Keep both, harden the sync

**What changes.**
- Move C, D and E into one engine table, `chat_links`, so B-9 and B-1 cannot recur.
- Resolve on one rule.
- Propagate delete, archive and pin to the engine.
- Serve F through the gateway for the phone (B-12).
- Make search read the engine (B-11).
- Replace the start-up full reconcile with a lazy reconcile (B-15).
- Store F in SQLite rather than one JSON file (B-16).

**Migration.** Small: the links import only.
**Risk.** Low per change.
**Effort.** S–M, 2–4 agent-days.
**For aioncore.** Nothing changes.

**What it does not fix.** Every message is still matched across stores by text prefix (B-6, B-8).
`kel_meta` still rides on donor-shaped rows (B-2). There are still three pollers (B-3), and still
two stores to restore consistently (B-5). Each new feature — attachments (FN-04), streaming,
branching — pays the join again. Most of it is **also stage 1 of option (a)**, so it is not wasted
work if (a) follows.

---

## 4. Recommendation and migration plan

**Recommendation: option (a), stages 0–3 now; stage 4 only if Nick wants it (Q2).** Stage 1 is
option (c)'s core, so the plan pays off even if it stops after stage 1.

Rules for every stage:
- **Additive in the engine DB.** New side tables only; the "never altered" `conversations` table is
  left alone (`projects.py:6`). Imported rows are marked.
- **Behind a switch.** Engine setting `chat_store` = `legacy` | `engine`, read by the main process;
  the env `KEL_CHAT_STORE` overrides it for checks. The default flips only after a stage's acceptance
  passes.
- **Nothing is deleted in A, C, D or F** until the retirement step, which needs Nick's OK. Rollback
  is setting the switch back.
- **First on a copy.** Robocopy `Data` into a scratch folder and launch an off-screen instance with
  `KEL_DATA_DIR`, `AIONUI_DATA_DIR` and `KEL_HOST_DATA_DIR` pointed at the copy (WORKER_BRIEF). Real
  `Data` is touched only at an install point with Nick's Kel closed, after an automatic backup
  (`backup.py` format 2, which carries A, B, C, D and F).

### Stage 0 — inventory (read-only). S, about 0.5–1 day.

`python -m kel.chatstore inventory --data <root> [--store <dir>]`.

For every donor chat it records:
- all of its links (C, D, E, `project_bindings`);
- donor text, tool and tips row counts, and engine message counts;
- a class from §1.5;
- a per-row plan: `same` (matched by the existing `recoverHistory` rules, run **once, offline**),
  `donor-only → import`, or `engine-only`.

It writes a JSON report with no message text by default, and `--show-text` for Nick's review. It
exits non-zero on any class it does not know.

*Acceptance:* on the copy, the report's totals equal the counts in §1.5, and every chat has exactly
one class.

### Stage 1 — one link table (fixes B-1 and B-9; = option (c) core). S–M, 1–2 days.

- Engine table `chat_links(donor_id PK, conversation_id, source, created, retired)`, written only by
  the engine.
- The ACP host's `session/new` asks the engine (`/api/chat-link`) instead of reading or writing files,
  and falls back to C and D when it is missing.
- The main process's adoption writes the table too.
- The start-up merge (`KelService.ts:404-427`), `kel:conversation` (`:610-619`) and `projects.py:676-710`
  read the table.
- Import once from D, then C, then E. **On a conflict, the side whose engine conversation exists and
  has messages wins.** When neither does, both are kept as retired rows and the chat is treated as
  unlinked. Every conflict is logged in the report.

*Rollback:* the switch set to `legacy` reads files again. The files were never modified.

**Built (2026-09-28).** Stage 0 is `runtime/kel/chatstore.py` (`--json`, `--markdown`, `--show-text`); on the
read-only copy its totals equal §1.5, and the plain-words report for Nick is
`Desktop\Kel\Tools\chat-store-report-2026-09-28.md`. It also found 3 linked chats with one assistant row each that
has no engine twin by the reconcile rule; they are listed in the report for the stage 2 review. Stage 1 is
`runtime/kel/chat_links.py` (engine), `/api/chat-link` (GET lookups, POST `import`, `link`, `retire`, `mode`,
`conflicts`), the ACP host's `session/new`, `projects.conversation_for_donor` / `donor_for_conversation`, and
`desktop/.../kel/chatLinks.ts` for every reader and writer in `KelService.ts` and `reconcileHistory.ts`. Two
deviations from the text above: `chat_links` keys on `(donor_id, conversation_id)` with a unique index on the live
row per donor, so both sides of a conflict can be kept as retired rows; and several sides that all have messages
resolve by precedence D, C, E (none in Nick's data). In `engine` mode the ACP host still writes a session record
for a new chat, only when none exists, so a switch back to `legacy` finds it; C is only added to by adoption. A
table link to a conversation with no row yet counts as reserved, so a dead link's first message creates it. The
same work fixed the archived-chat read (`repairWorkspacePaths.ts` asked aioncore for 200 rows a page; it allows 100),
which had left archived chats out of the start-up link fold.

### Built (2026-09-29): the switch with a fresh start (D-80), and stage 3's state writes

- **The switch.** `chat_store` now defaults to `engine`. On the first launch of this build the main
  process (`chatStoreMigration.ts`) asks the engine (`/api/chat-store`, not in the renderer's allowlist)
  to `backup` (kel.sqlite3 and aionui-backend.db through SQLite's backup API, plus C, D and F, into
  `Data\engine\chat-store-migration\<stamp>\`; left out of user backups because the app database there
  still holds its keys), to `freeze` every chat that exists (active and archived) as `legacy` and
  archived in `chat_state`, then archives every active chat and team in aioncore until the sidebar is
  empty, then `complete` (the marker, and `chat_store = engine`). Each step is idempotent; a switch cut
  short keeps the legacy links for that run and finishes on the next launch with the first backup.
  `KEL_CHAT_STORE=legacy` skips it. Nothing is imported (D-80) and nothing is deleted.
- **Stage 3, part.** Engine table `chat_state(donor_id PK, conversation_id, title, archived_at,
  pinned_at, deleted_at, legacy, updated)`, keyed by the app chat because chats from before the switch
  may have no conversation. Rename, pin, archive, unarchive, delete and "empty the archive" are written
  there first (`common/adapter/kelChatState.ts` wraps those `ipcBridge` calls; an engine refusal stops
  the change), then to aioncore. Engine search leaves deleted chats out (B-10). With the one store,
  start-up adopts nothing and reconciles no chat (AC-6); a chat is reconciled when opened, and a
  scheduled run from before the switch is not brought back into the sidebar.
- **The Memory mirror** (D-81) reads a chat's conversation from `chat_links`, marks a chat archived when
  aioncore or `chat_state` says so, and leaves out chats deleted in the app. Every chat, the ones
  archived at the switch too, is still mirrored.
- **Not built, and why.** The sidebar list still comes from aioncore's grouped read model (kept in step
  by the writes above), and stage 2's read path is not built: the ACP host says several things only
  into aioncore's stream — vetting answers, capability confirmations, stop, pause, cancel, failure and
  approval sentences (`acp_host.py`, the `self.text` calls outside `_say_message`) — so "engine rows
  only after the turn" would drop them. Stage 2 first needs those recorded in the engine (or stage 4).
  Legacy code paths are not removed (retirement still needs a week on `engine` and Nick's OK).

### Stage 2 — history from the engine (fixes B-2, B-3, B-6, B-8, B-11, B-12, B-15, B-16). M, 3–5 days.

**Import.** For each `donor-only` row in the stage 0 plan, insert an engine message
`(role, text, at = donor created_at, meta {source:'donor-import', donor_msg_id})`. It is idempotent
on `donor_msg_id`. A chat with no live engine conversation gets one, created with the donor title and
bound to its project.

**Read path.** A paged engine route, `GET /api/chat/messages?conversation=&before=&limit=`, returns
display rows built in Python:
- text rows with `kel_meta`;
- work cards from `submissions`;
- approval anchors;
- job progress from `jobs`.

These are the same shapes `reconcileHistory.ts` builds today, ported with its tests. It excludes
rewound messages. `kel:history` and the gateway (`/kel/…`, which covers the phone) both serve it.

**During a live turn:**
- engine rows, plus the donor rows created after the turn's user message (streamed text, tool
  updates), plus donor `tips` rows that have no engine reply;
- at turn end (`turnCompleted`) the list re-reads the engine;
- the LIVE-7 watcher, the renderer poll and F become unused.

**Edit and Answer again** use engine seqs directly. Rows are engine rows, so `hidden_rows` and text
matching go away. Rewind already filters by `VISIBLE`.

**Search** uses engine `/api/search` for chat text (`search.py:84-96`).

*Rollback:* the switch set to `legacy` gives today's path. F is left in place, frozen at the stage
switch, and on rollback reconcile rebuilds it. Imported rows are marked and harmless in legacy mode:
they appear once, because `recoverHistory` matches them to their donor twin by text. That rule is
covered by a test.

### Stage 3 — chat state from the engine (fixes B-4, B-10, B-13, B-14). M, 2–4 days.

- Engine side table `chat_state(conversation_id PK, archived_at, pinned_at, deleted_at, title_source)`.
- The sidebar list comes from engine `/api/conversations` joined with `chat_links`, filtered by the
  engine's own hidden and utility rules. Engine filters decide what is a chat, so FN-10-type
  filtering lives in one place.
- Rename, pin, archive and delete write the engine first, then mirror to the donor handle best
  effort. **Delete hides** (`deleted_at`) and keeps work records, pending Q3.
- Adoption becomes "ensure a handle": a donor row is created lazily when a chat is opened for a turn,
  never at start-up.
- Start-up does no reconcile at all.

*Rollback:* the switch. The donor rows were kept current by the mirror, and the legacy list reads them.

### Retirement (after at least one week of daily use on `engine`, and Nick's OK)

- Stop writing C, D and F; move them to `Data\engine\retired-chat-glue-<date>\`; delete the legacy
  code paths.
- Donor message rows stay; aioncore owns them.

### Stage 4 (optional, Q2) — Kel chats off aioncore. L.

The send box and stream hooks talk to the engine. aioncore is no longer spawned for Kel chats. This
is decided after stage 3, on evidence.

### Test strategy

1. **Fixture corpus.** A generator builds a synthetic A plus B plus C, D, E and F with every class in
   §1.5:
   - dead link, conflict, A-only, B-only;
   - utility, schedule-hidden, archived, pinned;
   - more than 20 chats, more than 200 messages in one chat;
   - several replies merged into one donor row;
   - a rewound message, a hand-off, a published result, an approval, a tips row.

   It holds no real text. This is the base for every test below.
2. **Engine (pytest):**
   - `chat_links` import: precedence, conflicts, idempotency;
   - donor import is idempotent and marks its rows;
   - `/api/chat/messages` paging, ordering and rewind exclusion;
   - hand-off card, result and approval shapes, which must equal today's `reconcileHistory` output for
     the same fixture (golden test);
   - search finds imported and engine-only text;
   - backup and restore round-trip with the new tables (extends D-45's pins).
3. **Desktop (vitest, DOM):**
   - `kel:history` in `engine` mode;
   - the live-turn overlay rule, with no flicker and no duplicate at turn end;
   - edit and Answer again hide the right row with repeated text;
   - sidebar list, archive, pin and delete in engine mode;
   - switch flip both ways;
   - the phone path (no preload) shows results.
4. **Equivalence check on the Data copy.** For every chat, the rendered sequence of
   (position, text, `kel_meta.kind`, card ids) in `legacy` equals the one in `engine`, except the
   differences listed in the stage 0 report: imported rows now visible on the phone, dead empty chats
   hidden. It runs as a script against two off-screen instances.
5. **Live off-screen journeys on the copy.** Send and stream; hand-off and result arriving in an open
   chat (LIVE-7); scoping card; edit; Answer again; rename, pin, archive, delete; search; a scheduled
   run's chat; restart mid-turn; a backup and restore round-trip; the phone gateway.
6. **Full suites** before each stage's commit: `bun run test` and `python -m pytest tests -q`.

### Acceptance checks (all on the Data copy before real Data)

- **AC-1.** Every chat that had words before still shows the same words, in the same order, after
  migration. Nothing is lost from the union of A and B. This is checked by the equivalence script on
  Nick's copy, with a zero-diff report reviewed by Nick for his real chats.
- **AC-2.** No chat maps to two engine conversations. There are no unresolved rows in `chat_links`,
  and the 7 conflicts are resolved and logged.
- **AC-3.** A result or scoping card appears in an open chat within 2 s of the engine writing it, with
  no reopen, on the desktop and the phone.
- **AC-4.** Edit and Answer again in a chat with repeated identical messages rewind and hide exactly
  the chosen message.
- **AC-5.** Deleting, archiving or pinning a chat is reflected in engine search and counts.
- **AC-6.** Start-up does no per-chat history read (measured in `desktop.log` `KEL-BOOT` spans).
- **AC-7.** Flipping the switch back to `legacy` after each stage gives today's behaviour with no data
  change (checksums of A, C, D and F unchanged, and B changed only by the new tables and marked rows).
- **AC-8.** A backup taken before migration restores to a working legacy state. A backup taken after
  restores to a working engine state.
- **AC-9.** The utility chat and schedule-hidden chats never appear in the sidebar or search.
- **AC-10.** On the full suites, only new tests are added and none are weakened.

### Risks, in order

1. **Losing A-only words** (4 chats in Nick's data). Mitigations: the stage 0 report, a reviewed
   import, marked rows, and A never deleted.
2. **Turn-end flicker or duplicates.** Mitigations: one explicit rule, and a DOM test with the
   merged-reply fixture.
3. **aioncore behaviour Kel cannot see** (row merging, tips, WS timing). Mitigation: keep donor rows
   for live turns only, so a surprise affects one turn and not history.
4. **Concurrent agents editing `KelService.ts` and `hooks.ts`.** Mitigation: land the stages as
   separate small commits.
5. **The first real-Data run.** Mitigations: only at an install point with Kel closed; automatic
   backup first; the switch.

---

## 5. Open questions for Nick

1. **Engine as the one chat store (option a), with aioncore's copy as a disposable cache.** Agree?
   Recommended: yes.
2. **Stage 4.** Should Kel chats stop going through aioncore altogether later? This is the larger
   rewire of the send box and stream. Recommended: decide after stage 3 has run for a week.
3. **Delete.** When you delete a chat, should Kel keep its work records and results (hide the chat)
   or erase them? Recommended: hide, and keep the work in Activity.
4. **The 23 empty chats whose engine side is gone** (mostly audit and test chats). Hide them from the
   sidebar after migration? Recommended: hide, not delete. And may the 4 chats whose words exist only
   in aioncore be imported? Recommended: yes, after you look at the stage 0 report.
5. **aioncore's error notes** ("tips" rows, e.g. a runtime failed to start). Keep showing them in
   history? Recommended: yes, for turns with no reply.
6. **Building aioncore from its source** (upstream GitHub, Apache-2.0) to add an append-message
   route. Recommended: no. It adds a Rust toolchain and a fork to maintain, and option (a) does not
   need it.
7. **When to migrate real Data.** Recommended: at the Phase 4 install point, with Kel closed, after
   the automatic backup.
