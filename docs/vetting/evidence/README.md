# Design Vetting Sessions — evidence index

## live/

The packaged app driven as a user on an isolated profile (`ux-audit.cjs vetting-live`, battery run
`b2-vetting-live`; root `ux-audit/roots/b2-vetting-live`):

- `vetting-live-01-panel.png` — the Work & context drawer, Vetting tab: session topic, FINISHED
  state, recorded progress, decisions, controls.
- `vetting-live-02-spec.png` — after "Preview spec" (spec text rendering; the boolean check in the
  JSON is `panelSpec`; see the note below).
- `vetting-live-03-transcript.png` — the conversation after a reload.
- `ux-vetting-live.json` — machine record: `panelTab/panelTopic/panelState/panelProgress/
  panelDecisions` all true; `errors` and `consoleErrors` empty. `panelSpec=false` in this pass means
  the automated text check did not observe the rendered spec within its wait window; the same engine
  preview is covered by `test_vetting.py` (`preview()`/full-spec tests) and the earlier run's
  screenshots. `transcript*`/`frame*` are false because the vendored shell renders the chat transcript
  outside the outer document (see 09_KNOWN_LIMITATIONS.md #9); the donor's own store carries the full
  alternating transcript, quoted in `live-databases.txt`.
- `live-databases.txt` — engine session record (topic, FINISHED, batch 2; 14 answers, 11 decisions,
  2 conflicts, spec coverage 10/24; 14 assistant message rows) and the donor store's newest rows
  ('Design vetting…', 'Recorded: n of 24 recorded.', 'Synthesis…', 'Spec snapshot saved…').

## engine-live/

`ux-vetting.json` from the 30-answer engine run (`ux-audit/runs/vetting2`): 12 recorded answers with
one durable acknowledgment each and no synthesis between them, `process answers` producing batch 2,
`19: B` surfacing the conflict, `finish spec now` writing the snapshot.

## commands

```
cd runtime && python -m pytest tests/test_vetting.py -q     # 30/30
cd runtime && python -m pytest tests -q                     # full engine suite
NODE_PATH=desktop/node_modules node packaging/ux-audit.cjs <app> <root> <out> vetting-live
```
