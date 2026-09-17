# Memory proposals — known limitations

1. **Exact-topic matching only (v1).** The vetting trigger only reconciles decisions with stored
   records that share the exact topic key (`vetting.<question id>`). Semantic matching between
   differently-worded rules requires a model and is out of scope; the queue never guesses.
2. **No live provider on this machine.** The packaged journey proves the full lifecycle through the
   real Design Vetting path, the review surface and the database; it does not exercise a live model
   turn producing proposals. Proposal *creation* from model output will be validated when a real
   provider is available (release program Phase 10).
3. **Chat shows the first pending item.** The pill opens the first pending proposal; the rest wait in
   Work ("and N more waiting for review in Work"). Keeps chat quiet by design.
4. **Stale proposals need source digests.** Only records written with a `source_digest` can be flagged
   by `revalidate()`; records without one are never stale-proposed (their source cannot be re-checked).
5. **Kel-native English strings.** The new surfaces are not wired into the 13 donor locale bundles
   (same limitation as the session-tools control); the release program's locale pass (Phase 4) covers
   the cleanup.
6. **Work-panel history loads on drawer open.** It refreshes after decisions and on open; it is not
   live-pushed while the drawer stays open on another tab.
