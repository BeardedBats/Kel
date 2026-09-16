# Design Vetting Sessions — known limitations

Recorded honestly; none of these block the shipped flow.

1. **Batch generation is deterministic, not LLM-authored.** Batches come from a curated template bank
   (28 questions, 9 sections, 4–9 options each) plus explicit adaptation rules driven by recorded
   answers. An LLM hook can enrich or regenerate questions later; the shipped path deliberately works
   with **no provider configured**, which is also what made the feature verifiable on this machine.
2. **One template.** `Product / UI Design Vetting` ships; other templates reuse the engine but are not
   authored yet.
3. **Acknowledgments are one short durable message each.** The batch and every
   `Recorded: n of m recorded.` line are stored as conversation content — enough for the live
   transcript and for scroll-back — while synthesis never happens between answers (`process answers`
   / `finish spec now` produce the substantive messages). Control replies that are purely navigational
   (`view decisions`, `preview spec`) are streamed without being stored.
4. **Interruption "answer normally" depends on the model layer.** With a usable provider the
   interruption is answered and then prompts resurface; without one, the engine reports honestly
   ("Kel could not plan this request…") and the prompts still resurface. Verified live in both shapes.
5. **Greyboxes are decision-support wireframes**, not comps: deterministic SVG skeletons on four
   layout axes, biased by session answers. Six directions is typical, never capped at three, but they
   do not depict branding, type, or real data.
6. **No live transcription yet.** The ingestion service is transcript-ready (sources include
   `transcript`, confidence classes, proposals); only the recording/transcription front end is out of
   scope for this release.
7. **Composite directions merge four trait axes** (nav, density, hero, rail). Role names outside the
   mapping (`Direction 4 -> base, Direction 2 -> header`) are accepted; unknown roles map onto their
   own trait key or are ignored in the SVG.
8. **The Vetting panel lives in the Work drawer.** A dedicated page was deliberately avoided: the
   feature lives in the conversation, and the drawer mirrors it. Panel copy is English-only, matching
   the rest of Kel's Kel-owned surfaces.
