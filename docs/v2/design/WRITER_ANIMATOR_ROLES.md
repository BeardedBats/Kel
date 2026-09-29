# Writer and Animator — two new staff roles, the HTML-page pattern, and Nick's motion taste library

Status: **design for Nick's approval, 2026-09-29.** No code has changed. Nothing here is decided until
Nick records it (proposed as D-84).

Nick asked for three things:
1. "Writing work: research an agent specifically for prose. I don't think Builder and Writer overlap."
2. "I'm a big fan of creating HTML files, which should be a combination of Writer and Builder (Writer
   for the copy, Builder for the code)."
3. "I also want an agent dedicated to motion animation that I can feed all the 'good motion design'
   I've collected, to create an animator tuned to my taste."

Inputs read: handoff §§3, 15–16; DECISIONS D-66..D-83; `D-66_WORKFORCE_LIVE.md`; `ROUTING_2.md`;
`MOTION.md`; `runtime/kel/assignment.py`, `staff.py`, `role_models.py`; the workforce research in the
recovery archive (`workforce-os/03, 04`, `workforce-role-charters/03, 05, 09, 14, 15, 17`); the
installed skills `animate`, `review-animations`, `improve-animations`, `emil-design-eng` and
`apple-design` (read only); `Tools\motion\` (the prototype, its README and key-frame sheets); and
`renderer/motion/layoutProbe.ts`. Web sources are listed at the end.

---

## 0. The recommendation in one page

- **Writer becomes a new role.** Kel's own ladder allows it: a role is justified when the *evidence
  needed to finish* differs from an existing role (workforce-os doc 03 §3). A Builder finishes on
  diffs and passing tests. A Writer finishes on sourced claims, a voice match and an editor's pass,
  and tests don't apply. Its failure modes are also different: slop, burying the point, made-up facts
  and generic voice, against the Builder's scope creep and broken tests. Nick's instruction ranks
  first in the decision hierarchy (handoff §36). The ladder still runs as a check, and the Writer
  starts in **shadow** status (§4). **Starting model: Claude Fable 5.1**, reasoning Auto, with Opus
  5.5 as the fallback. **Reviewer: an Editor pass**, which is a new *editorial lens* on the Verifier
  running GPT-6 Astra (a different family). Fact claims go to Discovery when the piece makes them.
- **The Editor is a lens, not a role.** It reviews and never rewrites, which is the same authority as
  the Verifier. By the ladder's rules that makes it a lens (charters doc 14).
- **Animator becomes a new role, provisional.** It writes code like a Builder, but it needs a browser
  and vision to capture and inspect its own motion (the Builder's tool policy denies `browser`). Its
  evidence is also different: frame strips and motion measurements instead of test runs. The most
  valuable asset is **Nick's taste library**, not the charter. If validation shows that "Builder +
  motion pack + library" does as well, the Animator demotes and the library stays. **Starting model:
  Claude Opus 5.5**, reasoning High. **Reviewer:** automated motion checks first, then the Verifier
  with a *motion lens* on GPT-6 Astra, which looks at side-by-side frame strips.
- **HTML pages become a mixed task with a fixed hand-off:** Writer (copy) → optional Designer
  (direction) → Builder (code, with the copy locked) → optional Animator (motion) → Verifier (works,
  copy matches) + Editor (copy in context) + visual check. Kel recognises these tasks through a new
  task class, `page`.
- **The taste library** lives at `Desktop\Kel\Memory\Taste\Motion\`. Nick drops a link, clip, GIF or
  file into an inbox, or tells Kel in chat or through Ramble, along with a sentence on why it's good.
  Kel files it, cuts a frame strip, *measures* its timing, and keeps a short, cited `rules.md`. Each
  task uses the rules, the 3–5 closest references and 1–2 "not this" examples, followed by a critique
  against them. Timing is judged by numbers, not by a model watching video: the research shows vision
  models copy how motion *looks* but lose its *timing* (Animation2Code).
- **Effort:** about 12–16 working days in total, plus about 4 hours of Nick's time for blind ratings.
  This needs the Memory folder (D-81), which doesn't exist on disk yet.

---

## 1. Recommendations and charters

### 1.1 Is each one a role, a skill pack or a lens? (Kel's own ladder)

The rules (workforce-os doc 03 §3; charters doc 14 §2):
- Something that differs **only in subject matter** is a pack.
- Something that differs **only in model** is routing policy, not even a pack.
- Something that differs in **authority, independence, completion evidence or escalation** is a role
  or a lens.
- A **reviewer with the Verifier's authority** is a lens.

| Candidate | Differs from the nearest role by | Verdict |
|---|---|---|
| Writer (vs Builder) | Completion evidence (claims mapped to sources, voice match, editor pass; no tests). Failure class (slop, fabrication, burying the point). Escalation (taste and voice questions go to Nick, not contract defects). Authority is narrower: it writes only its own document. | **Role** (Nick's instruction; the ladder agrees on evidence). Starts in shadow. |
| Editor | Nothing: read-only, fresh context, reviews and doesn't fix, the Verifier's authority | **Lens** `editorial` on the Verifier |
| Fact-checker | Nothing: this is Discovery's source discipline | **Lens** `source-eval` (already in doc 14), run as a Discovery step when the piece makes checkable claims |
| Copywriter / technical writer / post writer | Subject only | **Packs** on the Writer (`copy-web`, `docs`, `post-longform`, `email-draft`) |
| Animator (vs Builder) | Tools and evidence: needs a browser and vision to capture its own output, and finishes on frame strips and motion measurements. Escalation: taste pivots go to Nick, the Designer charter's rule. | **Role, provisional.** Demotes to "Builder + `motion-craft` pack + taste library" if validation says so. |
| Motion reviewer | The Verifier's authority | **Lens** `motion` on the Verifier, plus automated checks |

The research's own history is honest about this. It demoted "Documentation writer" to a writing pack
(charters doc 03 row "Documentation writer") and "Design Engineer" to Builder + pack. The new evidence
since then:
1. **Kel's staff are now model-bound per role (D-67/D-69).** A Settings row per role is how Nick
   chooses a model. The best prose model (§1.4) isn't the best coding model, and a writing row that
   borrows the Builder's model is exactly what Nick is objecting to.
2. **Prose is judged on evidence the Builder charter doesn't ask for.** A writing job that passes
   the Builder's tests (there are none) and its rubric can still be slop.

The ladder is how the claim gets tested (§4), and demotion stays possible. Demotion keeps the rules
and, for writing, a separate model row (routing policy).

### 1.2 Charter: Writer (`kel.writer`)

Every field follows `charter-schema/1` (charters doc 05). Code-level v2 fields (`assignment.py`
`ROLE_V2_FIELDS`) are shown in the last block.

| Field | Writer |
|---|---|
| `role_id` / `display_name` | `kel.writer` / Writer |
| `branch` / `reports_to` / `manages` | Design (prose is part of the user-facing surface) / `kel.commander` / none |
| `mission` | Write the words: prose that says the most important thing first, in Nick's voice, where every factual claim is supported and nothing reads as filler. |
| `activation_conditions` | The deliverable is mainly words a person will read: a post, article, document, page copy, announcement, brief, letter or email draft (never sent, D-66 authority), README or guide. Also the copy step of every `page` task (§2). **Not activated:** one-paragraph answers (Kel replies, D0); code comments and commit messages (Builder); mechanical rewording, formatting, translating or tidying at ≤ D1 (Utility); research reports (Discovery writes its own synthesis unless Nick asks for polished prose); UI microcopy inside Kel's own app (Designer + D-79 wording rules). |
| `responsibilities` | 1. Restate the reader, purpose and one-sentence point before drafting. 2. Draft to the brief and length. 3. Load the voice samples for the register and match them. 4. Run the self-edit passes (§1.3) in order. 5. Mark every factual claim with its source or `[needs source]`. 6. Run the deterministic slop scan and fix what it finds. 7. Answer each Editor finding once: fixed, or kept with a reason. 8. For `page` tasks, deliver `copy.md` with every visible string, including alt text, buttons, meta title and empty states. 9. Record the brief's open taste questions for Kel to batch to Nick. |
| `non_responsibilities` | Doesn't research (asks Discovery through Kel). Doesn't write or change code, HTML or CSS. Doesn't publish or send anything (Release or Nick). Doesn't certify its own draft. Doesn't invent quotes, numbers, names or sources. Doesn't widen scope or change the brief's point. |
| `decision_rights` | Alone: structure, wording, cuts, headline options, which voice sample to follow. Consults Kel: length changes over ±25%, tone changes from the brief, dropping a requested section. |
| `delegation_rights` | none |
| `staffing_request_rights` | May ask Kel for a Discovery fact pass, a Designer pass (for page structure), or a second draft on another model when the brief asks for options. These are proposals, not grants. |
| `skill_pack_types` | `writing-core` (always: the passes, anti-slop list, point-first rule), `voice-nick` (always: Nick's samples and style sheet from `Memory\Taste\Writing\`), plus one of `copy-web`, `post-longform`, `docs`, `email-draft`, `announcement`. |
| `tool_policy` | read + write (its own output folder only). Denied: shell, install, git, browser, external_api, run_tests. Facts come in through Discovery's artifact. |
| `authority_policy` / `write_boundaries` | `workspace-write` (max). Writes only `<job output>/draft.md`, `copy.md` and `notes.md` inside the project under `Memory\Projects\` (D-81). |
| `model_policy` | Strongest prose tier. It needs no coding capability, and reasoning isn't the bottleneck, so the dispatch tier is `standard`. |
| `provider_policy` | The reviewer must be from another family (`different_family_if_available`). Self-preference and family-preference bias in LLM judges is measured and persistent (sources 8–10). |
| `runtime_policy` | Any runtime that can read and write files. Today that's Claude Code on the subscription. No repository edit needed. |
| `context_policy` | Gets the brief, audience, Discovery's facts with sources, voice samples (4–5 per register; more helps little, source 6), the style sheet and, on a revision, the Editor's findings. Never gets the Editor's reasoning trail, other drafts' narrative or Nick's unrelated chats. |
| `input_contract` | Needs a reader, a purpose, a length (or "your call") and the register. A missing reader or purpose → `contract_error` back to Kel, which asks Nick in the scoping card (D-70.4) or picks the recorded default. |
| `output_contract` | `draft.md` (or `copy.md` for pages) + `notes.md` holding the one-sentence point, the claim→source table, the slop-scan result, and the open questions. |
| `evidence_standard` | Claim table complete (every checkable claim has a source or is marked). Slop scan at or below the threshold (§1.3). Editor verdict recorded. A missing check is "not verified", never clean. |
| `completion_authority` | The Verifier with the editorial lens (Editor pass). The Writer's "done" is a claim. |
| `required_review` | Always: Editor (editorial + requirements-coverage lenses). When the piece makes external factual claims: Discovery `source-eval` pass. When it'll be published under Nick's name (Pitcher List, a public page): the Oracle rule applies only if Nick opts in, so the ceremony stays small. |
| `escalation_conditions` | The brief conflicts with the facts. The voice samples conflict with each other. Nick's taste isn't covered by the style sheet. The Editor and Writer disagree twice on the same point: Kel decides, or asks Nick when it's taste. |
| `retry_failure_policy` | At most 2 revision rounds after the Editor. On the 3rd failure the step stops (`EXHAUSTED`, D-71 style) with the open findings shown. |
| `memory_policy` | Reads `Memory\Taste\Writing\`. Writes nothing there itself. Nick's edits to a delivered draft are captured by the taste intake (§3.6) as new voice evidence. |
| `budget_policy` | `standard` class. Long documents over about 3,000 words go `deep`. Overrun → stop and report. |
| `communication_policy` | Status comes from the engine. It talks to no agent directly. Findings arrive as ledger entries. |
| `anti_patterns` | 1. Throat-clearing openings ("In today's fast-paced world…"). 2. Burying the point (Opus 5.5 took 37–39 sentences where a human took 21, source 4). 3. Rule-of-three padding and "not just X, but Y" contrasts (sources 1–2). 4. Vague attribution ("experts say"). 5. Invented specifics (numbers, quotes). 6. Summary endings that repeat the piece. 7. Uniform sentence rhythm and stacked hedges. 8. Rewriting the Editor's finding away instead of fixing the text. |
| `examples` | Good: "Weekly Pitcher List post from these notes." It pulls 4 voice samples from past posts, puts the point in line one, marks two stats `[needs source]`, Discovery fills them, the Editor passes on round 1. Rejected: a draft that invents an ERA to fill a gap. That fails `evidence_standard` whatever the prose quality. |
| `evals_required` | `W-01` point-first rewrite · `W-02` voice match (blind, Nick) · `W-03` seeded fact traps (3 unsupported claims in the notes must not be carried as fact) · `W-04` slop density · `W-05` page copy completeness. Falsification in §4. |

Code-level fields (for `ARCHETYPES`): `authority_max: 'workspace-write'`,
`capability_requirements: ['long_context', 'structured_output']`, `dispatch_tier: 'standard'`,
`budget_class: 'standard'`, `default_skill_packs: ['writing-core', 'voice-nick']`,
`independence: {may_not_review_own: True, reviewer_family: 'different_family_if_available'}`,
`tool_policy: {allow: ['read', 'write'], deny: ['shell', 'install', 'git', 'browser', 'external_api', 'run_tests']}`.

### 1.3 What makes AI prose good: the Writer's passes and the Editor's lens

This is the content of the `writing-core` pack, built from the research:

1. **Brief first.** Reader, purpose and the one sentence they should leave with. Most weak AI drafts
   fail here, not at sentence level. "Buries the point" is the documented weakness even of Opus 5.5
   (source 4), and Anthropic's own note on 5.5 is about putting the important information first
   (source 3).
2. **Voice from examples, not adjectives.** Zero-shot "write like Nick" fails. Studies found few-shot
   examples essential and saw diminishing returns past about 4–5 (source 6). So `voice-nick` keeps
   4–5 short, *real* samples per register (post, doc, note), plus a one-page style sheet of the rules
   Nick has stated.
3. **Self-edit passes, in this order:** (a) structure: point first, one idea per paragraph, cut any
   section that doesn't serve the reader; (b) cut: aim for 15–30% shorter; (c) specifics: replace
   vague claims with a concrete fact, or delete them; (d) slop: remove the patterns in the anti-slop
   list; (e) rhythm: vary sentence length and read the ending last.
4. **Anti-slop list, deterministic.** A small script, not a model, counts over-represented words,
   "not X but Y" contrasts and slop trigrams per 1,000 words, the way EQ-Bench's Slop Score does. The
   human baseline there is about 7 per 1,000 words, and most models score 10–40 (source 1). Add
   Wikipedia's "Signs of AI writing" patterns: promotional tone, rule of three, vague attribution,
   formulaic em dashes, "it's important to note" (source 2). Add Nick's own banned list. Start with a
   threshold of ≤ 12 per 1,000 words, and tune it from Nick's ratings.
5. **Facts: claim → source.** Break the draft into checkable claims and verify each one, the way SAFE
   does for long-form factuality (source 7). In Kel, Discovery does this when a piece makes external
   claims. The Writer never fills a gap with a plausible number.
6. **An editor from another family.** LLM judges prefer text from themselves and their own family.
   The bias is tied to how familiar (low-perplexity) the text is to the judge (sources 8–10). An Opus
   or Fable draft judged by Sonnet is the weakest possible check.

**The editorial lens** (Verifier on GPT-6 Astra, fresh context, read-only). It gets the brief,
`voice-nick` samples, the style sheet, the draft, the claim table and the slop-scan result. It returns
findings `{severity, where, rule, why, suggested direction}`. It **doesn't rewrite**. That matters
here: testers found Astra a *weaker writer* than its predecessor, "boring" and visibly
machine-written, while it did well at clarity edits of reports (sources 11–12). Its job is critique
against a checklist, which is the part it does well. It blocks on: an unsupported factual claim,
missing required content, a slop score over the threshold, or a wrong reader or purpose. Style
findings are advisory, and the Writer must answer each one once.

### 1.4 Models for prose (evidence as of September 2026)

| Model (Kel can run) | Prose evidence | Use |
|---|---|---|
| **Claude Fable 5.1** | Ranked the top raw writer by writers, ahead of GPT-5.6 Sol and Opus. Output tends to be dense and needs editing passes (source 13). $10/$50 per M tokens (`role_models.PRICES`). | **Writer starting model** |
| Claude Opus 5.5 | Positioned as fixing "Claudish" writing: more important information first, less jargon, follows writing instructions more closely (source 3). A reviewer still found it buries the point (source 4). 40% of Fable's cost. | **Writer fallback.** Second route in validation. |
| Claude Sonnet | Rated a strong value writer that needs little cleanup (source 13, for Sonnet 5; Kel's `claude-sonnet` alias may resolve to an older Sonnet). | Not the default. Reasonable for short, high-volume drafts. |
| GPT-6 Astra | A drop of about 80 Elo on creative writing versus its predecessor; called boring and machine-like; good for making reports clearer (sources 11–12). Different family from Claude. | **Editor** (critique, not drafting) |
| GPT-6 Luna | No prose evidence found. It's Kel's cheap Commander model. | Not for prose |
| DeepSeek Flash (V4.1) | About 250× cheaper than Fable in one script-draft test "for very similar results", but another hands-on test found it stylised and flat. No public creative-writing benchmark covers it (sources 14–15). No adapter installed yet (D-66). | Utility only (taste-library intake, §3.5) |

**Reasoning level: Auto.** The tier sets it: standard → the model default, and long `deep` documents
→ High. Prose quality is limited by taste and editing, not reasoning depth, so there's no reason to
pay for `max`. Validation (§4) runs both Fable and Opus and settles the default.

### 1.5 Charter: Animator (`kel.animator`)

| Field | Animator |
|---|---|
| `role_id` / `display_name` | `kel.animator` / Animator |
| `branch` / `reports_to` / `manages` | Design / `kel.commander` / none |
| `mission` | Make things move the way Nick likes: motion with a purpose, built from his taste library and Kel's motion rules, and proven with frame captures and measurements. |
| `activation_conditions` | The request asks for motion, animation, transitions, micro-interactions or "make it feel alive". Or a `page` task's design brief lists motion moments. Or a Kel UI change touches `renderer/motion/` or a MOTION.md §10 moment. **Not activated:** static pages with no motion asked for; a CSS hover colour (Builder); video or 3D rendering (out of scope); React Native (a different pack, `animate-expo`, would be needed). |
| `responsibilities` | 1. Decide *whether* each moment should move at all (frequency and purpose gate, `animate` skill steps 1–2). 2. Retrieve the 3–5 closest taste references and 1–2 anti-references. 3. State each moment's plan: purpose, properties, spring or duration and bounce, stagger, interruption, exit, reduced-motion path. 4. Implement it on the house system (Kel UI: `renderer/motion/`; standalone HTML: a small spring core with a seekable clock, §3.7). 5. Capture frame strips and measurements for every moment. 6. Run the automated checks and fix failures. 7. Answer the motion-lens findings once. 8. Propose (never apply) taste-rule changes that the work revealed. |
| `non_responsibilities` | Doesn't change copy (Writer) or layout and visual design beyond what motion needs (Designer/Builder). Doesn't add a motion library when the house system covers it. Doesn't loop anything forever (MOTION.md §9). Doesn't delay information. Doesn't edit `rules.md` or the library directly. Doesn't certify its own motion. |
| `decision_rights` | Alone: curves, durations and springs *within* `rules.md` and MOTION.md bounds; choreography. Consults Kel (then Nick if it's taste): anything outside the bounds, a new motion token, motion on a moment the rules say stays still. |
| `delegation_rights` | none |
| `staffing_request_rights` | May ask Kel for a Designer pass (the moment's intent is unclear) or a Builder (non-motion code is broken). |
| `skill_pack_types` | `motion-craft` (always: MOTION.md, the house motion API, the "should it animate" gate; in Claude runtimes this includes the installed `animate`, `emil-design-eng` and `apple-design` skills), `taste-motion` (always: the retrieved library slice + `rules.md`), and `motion-web` or `motion-kel-ui` depending on the target. |
| `tool_policy` | read, write, run_tests, **browser** (headless capture), git (Kel repo work only). Denied: install (no new dependencies without Kel), shell outside the capture script, external_api. |
| `authority_policy` / `write_boundaries` | `leased-write` (max). Kel UI: the lease covers `renderer/motion/**` and the component files of the moments in scope. Pages: the page's own files. Evidence goes to `<job>/motion/`. |
| `model_policy` | Strong coding tier with vision. Needs `repository_edit`, `code_execution` and `vision`. |
| `provider_policy` | The motion-lens reviewer comes from another family. The automated checks are family-free. |
| `runtime_policy` | Repository edit + a headless Chromium it can drive with a frozen, stepped clock (§3.7). |
| `context_policy` | Gets the brief, the moment list, `rules.md`, the retrieved references (notes, *measured numbers*, frame strips, snippets), the anti-references and MOTION.md when working on Kel UI. Never gets the reviewer's reasoning trail. |
| `input_contract` | Needs the target (file, component or page), the moments and the "feel" words, or Kel's inference from the library. A missing target → `contract_error`. |
| `output_contract` | Code + `motion/plan.md` (per moment: purpose, values, the refs it follows) + `motion/strips/<moment>.png` + `motion/metrics.json` (per moment: duration, settle time, overshoot %, max drift after settle, fps, reduced-motion result). |
| `evidence_standard` | Every moment has a strip and metrics. All hard checks (§3.7) pass. A moment without a capture is "not verified". |
| `completion_authority` | The Verifier with the motion lens, after the hard checks pass. |
| `required_review` | Always: hard checks, then the motion lens. For Kel UI: also the existing Verifier functional review, because the code touches the app. |
| `escalation_conditions` | The brief's feel conflicts with `rules.md`. The best reference breaks a MOTION.md hard rule. The checks can't pass without changing layout (a Builder or Designer question). Two failed revisions on the same moment. |
| `retry_failure_policy` | At most 2 revision rounds after review. A deterministic check failure (no-shift) gets one informed retry, then `EXHAUSTED` (D-71). |
| `memory_policy` | Reads `Memory\Taste\Motion\`. Writes rule *proposals* to `Memory\Taste\Motion\proposals\`. Nick's reactions to its output are captured as new references (§3.6). |
| `budget_policy` | `standard`. `deep` for more than 5 moments or new house primitives. |
| `communication_policy` | As for the Writer. |
| `anti_patterns` | 1. Animating a keyboard or 100+/day action. 2. Timing copied from how a clip "looks" instead of its measured numbers. 3. A layout that settles, then shifts (D-78). 4. An end state that snaps instead of using the settling fade (D-78). 5. `transition: all`, or layout properties animated. 6. Decorative loops. 7. A parallel token system next to the house one. 8. "Delight" on frequent UI. |
| `examples` | Good: "Make the pricing cards on this page arrive nicely." It retrieves the 3 closest "stagger-enter" refs (measured 30 ms stagger, 200 ms enter), builds with the page's spring core, captures, passes the no-shift and settle checks, and Astra flags one origin issue that gets fixed. Rejected: a bouncy 800 ms entrance because the reference GIF "looked bouncy". The measured reference had 0.8% overshoot. |
| `evals_required` | `AN-01` purpose gate (seeded "should not animate" briefs) · `AN-02` taste match (blind, Nick) · `AN-03` numeric fidelity to references · `AN-04` hard-check pass rate · `AN-05` Kel UI moment rebuild vs the approved prototype. |

Code-level fields: `authority_max: 'leased-write'`,
`capability_requirements: ['repository_edit', 'code_execution', 'vision']`,
`dispatch_tier: 'standard'`, `budget_class: 'standard'`,
`default_skill_packs: ['motion-craft', 'taste-motion']`,
`independence: {may_not_review_own: True, reviewer_family: 'different_family_if_available'}`,
`tool_policy: {allow: ['read', 'write', 'run_tests', 'browser', 'git'], deny: ['install', 'shell', 'external_api']}`.
The capture script runs through `run_tests`, so the Animator doesn't need general `shell`.

### 1.6 Models for motion

| Model | Evidence | Use |
|---|---|---|
| **Claude Opus 5.5** | Opus 5 ranked #3 in HeyGen's Code2Video motion-design benchmark, within 12 Elo of first (source 16). Opus 5.5 matches Fable on most tasks at lower cost (sources 3, 17). It runs in Claude Code, where the installed motion skills load. Kel's whole motion language (MOTION.md, `renderer/motion/`) was built this way. | **Animator starting model**, reasoning **High**. Motion is exact numeric work and interruption logic, so depth pays off here. |
| GPT-6 Astra | Tied first in the same benchmark (source 16). Different family from Claude. Strong on spatial and visual work (source 11). | **Motion-lens reviewer.** Also the second route in validation: if Astra *builds* better, swap the pair (Astra builds, Opus reviews). |
| Claude Fable 5.1 | The Designer's model. No motion evidence either way. | Not by default. |
| Luna, DeepSeek Flash | Open-weight models were within 50 Elo on Code2Video (source 16). Cheap. | Library intake only (tagging, filing). |

Two findings shape the design more than the model choice does:
- **Every model got timing and easing wrong most often, and human references beat all models by a
  wide margin** (source 16).
- **Vision models copy how an animation looks from video but don't preserve its timing, even after
  fine-tuning and iterative refinement** (source 18, Animation2Code).

So references must carry **measured numbers**, and review judges timing **numerically**. The vision
reviewer judges choreography, origin, composition and "does this feel like the refs".

### 1.7 Changes to existing decisions

- **D-69 item 4** ("Writing work staffed as Builder is kept as the default") would be **superseded**
  by D-84: writing goes to the Writer.
- **D-67 table:** add Writer → Claude Fable 5.1 (Preferred, fallback Opus 5.5) and Animator → Claude
  Opus 5.5 (Preferred, fallback Codex/Astra).
- **D-79:** two more pale role colours (Writer, Animator) in the Team list.
- **ROUTING_2 §5.1:** the `writing` task class names the **Writer** row. There are new classes
  `motion` (→ Animator) and `page` (a plan, §2).

---

## 2. HTML pages and other mixed deliverables

### 2.1 How Kel recognises them

- **Primary:** the turn classifier (ROUTING_2 §5.5) gets one more class, `page`: the deliverable is a
  web page or HTML file whose words matter.
- **Floor regex** (can only add `page`, never remove work): `\.html\b`, "html (page|file)", "web
  page", "landing page", "one-pager", "microsite", "artifact", "newsletter", "page for/about", or a
  site or publish verb with an audience ("for readers", "for the team").
- **Not `page`:** a change to Kel's own UI (that's coding, with the Designer or Animator by hint), or
  an HTML file that is only a data dump or a tool output ("export this table as HTML" is Utility or
  Builder).
- Signals for the optional roles:
  - **Designer joins** when there's no existing design system or reference in the project, or the
    request says design, look or brand.
  - **Animator joins** when motion is asked for, or the Designer's brief lists moments.
  - **Discovery joins** when the page makes external factual claims.

### 2.2 The plan (frozen into `contract['staffing']` like every staffed job)

```
            ┌──────────────┐
(Discovery)─┤ 1. Writer    │ copy.md: outline + every visible string (title, meta, headings,
 facts      │   copy       │ body, buttons, alt text, empty/error text), claim→source table
            └──────┬───────┘
                   │  parallel with (2) when both run: independent outputs, one combine step
            ┌──────┴───────┐
            │ 2. Designer  │ brief.md: layout per breakpoint, type scale, colour tokens, the
            │  (optional)  │ motion moments list, the references it follows
            └──────┬───────┘
            ┌──────┴───────┐
            │ 3. Builder   │ index.html (+ css/js). COPY LOCK: words are imported from copy.md,
            │   build      │ never retyped or edited. A copy-fit problem → a copy request to Writer
            └──────┬───────┘
            ┌──────┴───────┐
            │ 4. Animator  │ motion on the moments listed; strips + metrics
            │  (optional)  │
            └──────┬───────┘
            ┌──────┴────────────────────────────────────────────────┐
            │ 5. Review team (fresh context, other family where it  │
            │    matters): Verifier functional (links, 360/768/1440, │
            │    a11y, copy-fidelity diff) · Editor on the rendered  │
            │    copy in context · visual check on screenshots ·     │
            │    motion checks if (4) ran                            │
            └───────────────────────────────────────────────────────┘
```

- **Tier:** D2 pod by default (Writer + Builder + Verifier). With Writer and Designer running in
  parallel it's a D3 plan in `parallel.plan_streams` terms: two independent parts with disjoint
  outputs (`copy.md`, `brief.md`) and the Builder as the combine step. That's within R8/R9 and the
  existing 3-stream cap.
- **Copy lock (the key hand-off rule).** The Builder places the copy but doesn't write it. A check
  compares the page's visible text (from the headless render) with `copy.md`, whitespace-normalised.
  Any difference is a finding assigned to whoever caused it. If a headline doesn't fit the layout,
  the Builder files `copy_request{where, max_chars, why}`, and the Writer revises it once. That keeps
  Nick's split: Writer for the words, Builder for the code.
- **Routing findings:** copy findings → Writer. Layout, code and a11y → Builder. Motion → Animator.
  Visual direction → Designer (only if it ran). Each role fixes only its own part (lease rules).
- **The visual check** is the Verifier with the `design-visual` lens (doc 14) on GPT-6 Astra. It gets
  screenshots at 360, 768 and 1440 against `brief.md`. The Designer runs Fable, so Astra keeps the
  review in a different family.
- **Where it lands:** the project folder under `Memory\Projects\` (D-81). The done card's "Open" opens
  it (D-79).
- **The same pattern generalises.** Any deliverable with both words and a build (a slide deck as
  HTML, an email template, a README site) uses Writer → Builder with the copy lock.

### 2.3 What the card shows (D-66/D-79)

Title, then "Team · 4 agents: Writer (Fable 5.1 · Auto), Builder (Opus 5.5 · Auto), Animator (Opus
5.5 · High), Verifier (GPT-6 Astra · High)". Steps, one line each: "Writing the copy", "Building the
page", "Adding motion", "Review Team". The Review Team status is simple (D-79).

---

## 3. The motion taste library

### 3.1 Principles

1. **Nick's note is the most valuable field.** "Why is this good?" in his own words is kept verbatim
   and never rewritten by a model.
2. **Measure, don't eyeball.** Every clip gets numbers (duration, settle, overshoot, stagger), cut by
   a deterministic tool. Models copy the look and lose the timing (source 18).
3. **Negatives count.** "Not this" examples (anti-references) come from Nick's reactions and sharpen
   the taste faster than more positives.
4. **Rules are short and cited.** `rules.md` stays under about 60 lines. Every rule cites the
   references behind it, so Nick can see where it came from and delete it.
5. **Curation is a pipeline, not a persona.** The research rejects a "Curator" agent because it
   invites unsupervised self-modification (workforce-os doc 04). Intake is mechanical; rule changes
   are proposals.
6. **Precedence.** For Kel's own UI: MOTION.md / D-78 > `rules.md` > generic skills. Elsewhere:
   `rules.md` > generic skills. The generic skills conflict with Nick's taste in known places, and
   Nick wins. Examples: `review-animations` treats UI motion over 300 ms as a finding, but D-78's
   settling fade is 520 ms; the skills allow symmetric fades where MOTION.md specifies asymmetric
   exit/enter.

### 3.2 Folder layout (inside D-81's Memory, so every staff member can read it)

```
Desktop\Kel\Memory\Taste\
  README.md                     how to add things (one screen, plain words)
  Motion\
    inbox\                      drop anything here: .mp4 .webm .mov .gif, .html, .url, .txt, .md,
                                code files, or a folder; an optional same-name .txt is the note
    refs\
      2026-09-30-linear-sheet\  one folder per reference
        ref.md                  front matter + Nick's note (verbatim) + Kel's description
        clip.webm | clip.gif    the media (if any)
        strip.png               contact sheet, 50 ms steps (like Tools\motion\keyframes)
        curve.json              measured position/scale/opacity per frame for the tracked element
        snippet.css|js|tsx      code, if it came with code or was reconstructed and verified
    anti\                       same shape as refs\, "not this" — mostly from Nick's reactions
    rules.md                    the distilled taste rules (cited, Nick-approved)
    proposals\                  rule changes waiting for Nick (from intake and from Animator work)
    index.json                  generated: tags, moment types, measured numbers, text for search
    CHANGELOG.md                what was added or changed, when, and why
  Writing\                      the Writer's voice-nick pack (same idea, smaller)
    samples\<register>\*.md     4–5 real samples per register (post, doc, note)
    style.md                    Nick's stated writing rules + banned words and phrases
    anti\                       "not this" drafts with Nick's reason
```

`ref.md` front matter:

```yaml
id: 2026-09-30-linear-sheet
title: Linear — command sheet opening
source: https://…            # or "file: <original name>", or "Kel UI: MOTION.md §10.3"
captured: 2026-09-30
kind: clip | gif | link | code | site | kel-ui
moments: [sheet-open, enter]  # from a fixed list: enter, exit, morph, sheet, list-reorder,
                              # stagger, toast, loader, progress, number-roll, text-change,
                              # hover, press, drag, page-transition, scroll-linked, indicator
feel: [crisp, weighty]        # Nick's words when he gave them; Kel's suggestion marked (kel)
loved: true                   # Nick said "love" / starred it; weights retrieval
measured:                     # from curve.json; absent = not measured (never guessed)
  duration_ms: 280
  settle_ms: 340
  overshoot_pct: 0.6
  stagger_ms: null
  properties: [transform, opacity]
local_only: false             # true = media never leaves this PC (§3.8)
status: active | retired
```

Kel's own motion language gets **seeded** into the library at build time: the 15 MOTION.md moments
and their `Tools\motion\keyframes` sheets, marked `kind: kel-ui, loved: true`. The Animator starts
with about 15 measured references Nick has already approved.

### 3.3 How Nick adds references (easiest first)

1. **Tell Kel.** In any chat, or through Ramble by voice (Muse transcription, handoff §22): "Save to
   motion taste: <link or attached file>. I like how the panel lands with no bounce, and the content
   arrives just after." Kel recognises the intent ("motion taste", "save this motion", "good
   motion"), files it and answers in one line: "Saved to your motion taste as 'Linear — command sheet
   opening'."
2. **Drop it in `Memory\Taste\Motion\inbox\`.** Any file, plus an optional `.txt` note with the same
   name. Or no note: Kel asks once, in the next chat reply ("Why did you like the Linear clip? One
   line is enough"), and skips asking if Nick ignores it.
3. **Phase 2: a capture hotkey, Kibble-style.** Kibble is Ctrl+Shift+F → click the problem → record
   feedback → Muse → Save (handoff §3). Taste capture would be a different hotkey (proposed
   Ctrl+Shift+M) → drag a screen region → record 3–8 s of screen *plus* a spoken note → Save to
   Taste. That catches motion Nick sees in any app, not just links. It reuses the Kibble capture
   layer (`fixCapture/*`) and Muse. It's phase 2 because it needs screen recording.
4. **React to Animator output.** On a result card with motion, a reply like "too bouncy" or "love
   this" is saved as an anti-reference or a loved reference, with the output's strip and metrics
   attached. This is the fastest way the taste sharpens.
5. **From the phone (later).** Share a link to Kel's chat with "motion taste: …". It's the same as
   route 1.

Nothing asks Nick to fill in a form, choose tags or pick categories. Tags, moment types and numbers
are Kel's job.

### 3.4 How Kel keeps it current (the intake pipeline)

The steps run in order. None of them rewrites Nick's words.
1. **File:** make the `refs\<date-slug>\` folder, move the media there, and write `ref.md` with
   Nick's note verbatim. For links, save the URL and title. If the page is capturable, record the
   moment (step 3).
2. **Cut a strip:** frame-extract at 50 ms steps into `strip.png`. This is the same format as
   `Tools\motion\keyframes`, so Nick can compare at a glance.
3. **Measure:** for clips, track the moving element across frames (frame difference plus a bounding
   box) and fit duration, settle time (0.2% band, MOTION.md §1), overshoot % and stagger. For live
   pages and code, run them in headless Chromium with a frozen clock (§3.7) and record exact boxes and
   opacity. The result goes to `curve.json` and `measured`. If measuring fails, `measured` stays
   empty and the reference is used for look only.
4. **Tag:** a cheap model (Utility: DeepSeek Flash when its adapter exists; Luna until then) proposes
   `moments` and `feel (kel)`. Nick's own words always win.
5. **Index:** regenerate `index.json` (tags, numbers, note text). Search is tag filter + BM25 over the
   notes. No embeddings service is needed (no Anthropic API key, D-83 note), and it's deterministic
   and explainable.
6. **Propose rules:** after every 5 new references, or when an Animator job ends with a Nick
   reaction, the Animator drafts rule changes as a diff with citations in `proposals\`.
   - A proposal that only *adds* a rule directly quoted from Nick's notes is applied and listed in
     `CHANGELOG.md` and in the next result ("Added to your motion rules: …").
   - A proposal that *changes or contradicts* an existing rule waits for Nick: one Needs-you
     question, batched.
7. **Retire:** Nick can say "forget the Linear one", or delete the folder. The next index rebuild
   drops it, and rules citing only retired references are flagged for removal.

### 3.5 How the Animator uses it on each task

1. **Always in context:** `rules.md` (short) and, for Kel UI, MOTION.md.
2. **Retrieved per moment:** the top 3–5 references by moment type, then feel words from the brief,
   then `loved`, then note similarity. Also 1–2 anti-references for the same moment type. Each is
   given as the **note + measured numbers + strip image + snippet**, as few-shot examples.
3. **Plan against references:** `plan.md` names the references each moment follows, and the target
   numbers inside their measured range ("stagger 30 ms — refs A and C are 28–35 ms").
4. **Build, capture, compare:** the checks (§3.7) run. The numeric comparison with the chosen
   references is part of the metrics ("overshoot 0.7% vs refs 0.4–0.9%: in range").
5. **Critique loop:** the motion-lens reviewer (Astra) gets, per moment, the output strip *next to*
   the reference strips and the anti-reference strips, the numbers, and `rules.md`. It returns
   findings tied to a rule or reference. It judges choreography, origin, composition and feel. Timing
   is settled by the numbers, not by its eye (source 18). At most 2 rounds, then Nick sees it.
6. **Learn:** Nick's reaction to the result feeds back through intake route 4.

### 3.6 Writing taste, briefly

The same mechanism, smaller. "Save to my writing voice: <text or file>" adds a sample. Nick's edits to
a delivered draft (when he edits the file Kel produced) are diffed. Recurring edits become style-sheet
*proposals*, applied the same way as motion rule proposals. Samples are capped at 4–5 per register
(research shows little gain beyond that, source 6), and newer or loved ones replace older ones.

### 3.7 Verifying the Animator's output (automated checks)

**The capture harness.** The existing pieces are the prototype's seekable clock
(`Tools\motion\src\kel-motion.js`), Kel's `motionClock` (`window.__kelMotion`) and `layoutProbe.ts`.
Note: MOTION.md §8.1 names `Tools\motion\capture-app.ts`, but **that file isn't in the repo or in
`Tools\motion\`**, so it has to be built here.
- **Kel UI:** step `window.__kelMotion` at 16.7 ms (60 fps) and 50 ms (strip), recording key element
  boxes, words and computed opacity, transform and filter per frame.
- **Standalone pages:** the house spring core the Animator ships exposes the same seekable clock
  (`window.__motion`), which is a charter requirement for pages. For third-party or CSS-only motion,
  fall back to Chrome DevTools Protocol control of animation playback and virtual time.

**Hard checks** (these block, and are deterministic):

| # | Check | How | Bound |
|---|---|---|---|
| H1 | **No layout shift after settle (D-78)** | `layoutViolations(frames, {settledAfter})` from `layoutProbe.ts` | nothing moves > 1 px or re-words after settle; no snap jumps (> 12 px and > 4× neighbours) |
| H2 | **Settling fade (D-78 §2.1)** | `classifyTransition({final, staysMs})` decides which transitions must settle; the opacity/blur series is measured on those | final states that stay: ~520 ms ±60, eased out, blur 3 px → 0; intermediate states ≤ 220 ms; never an instant swap |
| H3 | **Spring overshoot** | peak beyond target ÷ distance | Kel UI 0.15–1.1% (D-78); pages: `rules.md` range |
| H4 | **Total duration** | trigger → last element settled | ≤ ~650 ms; hand-off ≤ ~900 ms (MOTION.md §2.1) |
| H5 | **Reduced motion** | recapture with `prefers-reduced-motion: reduce` | no transform movement; cross-fades only (100/140–150 ms, settle 360 ms) |
| H6 | **Allowed properties** | per-frame computed style diff | only transform, opacity, filter, clip-path (+ the morph surface's size, MOTION.md §8) |
| H7 | **No endless loops** | a moment still animating after 3 s | only the Thinking indicator may loop |
| H8 | **Frame rate** | real-time capture (unstepped) | ≥ 55 fps median at 1440×900 |
| H9 | **No replay on re-render** | trigger a re-render with the same state | no entrance replays (MOTION.md §8) |

**Soft checks (findings, not blocks):** numeric distance from the chosen references, and the motion
lens's feel findings.

**Evidence:** strips, `metrics.json` and the probe log are stored with the job. The detail panel shows
only the Review Team status (D-79).

### 3.8 Privacy and ownership

- **Local by default.** The library is plain files in `Memory\Taste\`: outside Git, outside Data, and
  covered by the normal backup. Nothing is uploaded on its own.
- **What leaves the PC:** when a reference is used in a task, its note, numbers, strip and snippet go
  to the model provider running that step (Anthropic or OpenAI, on Nick's subscriptions), like any
  other context. `local_only: true` (set by saying "keep this one private") means only the note and
  numbers are sent, never media.
- **Screen captures** (hotkey, phase 2) can contain private content. The capture step shows the
  region before saving, and a captured clip defaults to `local_only: true` until Nick says otherwise.
- **Third-party material** (clips of other apps and sites) is for Nick's private reference. Kel keeps
  the link and a short clip, and never republishes it in a deliverable. Snippets copied from public
  code keep their source URL.
- **The installed skills** (`animate`, `emil-design-eng` and others) load only inside Claude Code.
  They aren't copied into Memory or into prompts for other providers. The Astra reviewer's motion
  lens is written fresh from MOTION.md and `rules.md`.
- **Staff access:** per D-81, all staff can read Memory. Only the intake pipeline writes to `refs\`,
  `anti\` and `index.json`. The Animator writes only to `proposals\`.

---

## 4. Validation on Kel's ladder

The method is charters doc 15 §0: arms A / B / C / C′, paired items, blind scoring, cost columns and a
pre-registered falsification rule. It's scaled to one person: **20 paired items per role** is
shadow-signal size (doc 15 says n = 20 is signal only). Promotion from shadow needs Nick's approval
after 20 items *and* 10 real jobs (doc 17's trailing-10 rule). Nick is the primary judge because this
is his taste.

### 4.1 Writer

| Arm | Setup |
|---|---|
| A | Builder charter (Opus 5.5), no writing pack: today's D-69.4 behaviour |
| B | Builder + `writing-core` + `voice-nick` packs (Opus 5.5) |
| C′ | B + fresh context + the same Editor loop (Astra), still the Builder charter |
| C | Writer charter + packs + Editor loop, on **Fable 5.1**, and repeated on **Opus 5.5** (doc 15 asks for at least 2 model routes) |

- **Items (20):** 8 from Nick's real writing (posts, docs, notes; the exact briefs he'd give), 6
  page-copy briefs, 3 seeded fact traps (the notes contain 3 unsupported claims), and 3 "point-first"
  rewrites of long drafts.
- **Scoring:**
  - Nick's blind pairwise preference (C vs C′, C-Fable vs C-Opus), about 2 hours in total.
  - Slop score per 1,000 words.
  - Carried fact traps (any carried trap fails the item).
  - Words before the point.
  - Tokens, time and cost.
- **Promote if:** C beats C′ in ≥ 60% of Nick's blind pairs, with fact-trap carries ≤ C′ and cost
  ≤ 2× C′.
- **Demote if** C doesn't beat C′. The Writer becomes the `writing-core` pack on the Builder charter,
  but **the `writing` class keeps its own model row** (routing policy, doc 14 rule 2). The better of
  Fable and Opus becomes that row's default either way.
- **No-evidence deadline:** 30 days (doc 17). Unmeasured means it auto-demotes to a pack, and Nick is
  told.

### 4.2 Animator

| Arm | Setup |
|---|---|
| A | Builder (Opus 5.5) + the request |
| B | Builder + `motion-craft` pack (MOTION.md + skills) |
| B+L | B + taste library retrieval (rules + refs) |
| C′ | B+L + fresh context + the capture/check/critique loop, Builder charter |
| C | Animator charter + packs + library + loop, on **Opus 5.5** and on **GPT-6 Astra** (with the reviewer swapped to the other family) |

- **Items (20):**
  - 5 rebuilds of approved Kel moments. Ground truth is the prototype and its metrics.
  - 10 motion briefs on standalone HTML pages from Nick's real wishes.
  - 3 seeded "should not animate" briefs (keyboard-triggered, 100+/day).
  - 2 seeded layout-shift traps.
- **Scoring:**
  - Nick's blind side-by-side playback: the prototype-style page with ×4 slow motion.
  - Hard-check pass rate (H1–H9).
  - Numeric distance to the references.
  - Correct "don't animate" calls.
  - Cost.
- **The library question is B+L vs B.** If the library doesn't win Nick's blind pairs, the capture and
  retrieval design is revisited before anything else.
- **The charter question is C vs C′.** If C doesn't beat C′ in ≥ 60% of pairs at ≤ 2× cost, the
  Animator demotes to "Builder + `motion-craft` + `taste-motion`, with motion jobs routed to the
  Builder row". The library, the checks and the critique loop all stay.

### 4.3 The editorial and motion lenses

Lenses are credited like the Verifier (doc 15 V-05/V-06):
- They must catch seeded problems: an unsupported claim; a slop-heavy paragraph; a layout shift; a
  snapped end state.
- They must raise **zero fabricated findings** on 5 clean items.
- A lens that nitpicks clean work is retuned before it can block.

---

## 5. Implementation steps and effort

The prerequisite is **the Memory folder (D-81)**, which is decided but not built:
`Desktop\Kel\Memory\` doesn't exist yet, and neither do the Claude Code guard or the Codex sandbox
allow-list. The steps below assume it lands first, or they put `Taste\` there and the enforcement
follows.

| # | Step | Where | Effort |
|---|---|---|---|
| 1 | Record D-84 (roles, models, supersede D-69.4, D-79 colours). Nick answers §6. | DECISIONS.md | 0.5 h |
| 2 | Writer and Animator archetypes (v2 fields as in §1.2/§1.5); role rows and defaults (`role_models.ROLES/DEFAULTS/FALLBACKS/ROLE_LABELS`); `staff.ROLE_LABELS`, `EXECUTOR_TEMPLATES`; `_role_for_step`: `hint == 'writing'` → writer, new `motion` hint → animator; status `shadow` recorded in the staffing reason | `assignment.py`, `role_models.py`, `staff.py`, tests | 1 day |
| 3 | Task classes: `writing` → Writer row, new `motion` and `page`; classifier prompt + floor regexes | `task_routing.py`, `router.py`, turn prompt, tests | 1 day |
| 4 | `writing-core` pack: passes, anti-slop list, Editor lens prompt (Verifier, `editorial`); deterministic slop scanner (word/trigram/contrast counts per 1,000 words); claim-table format | `runtime/kel/packs/…`, `slop.py`, tests | 1–1.5 days |
| 5 | `Memory\Taste\Writing\` scaffold + "save to my writing voice" intent | Memory + service intent | 0.5 day |
| 6 | `page` plan template: Writer ∥ Designer → Builder (copy lock, `copy_request`) → Animator → review team; copy-fidelity check; screenshots at 360/768/1440 | `staff.plan_job`, compile, Verifier lens, tests | 2 days |
| 7 | `Memory\Taste\Motion\` scaffold + seed with the 15 Kel moments; intake pipeline (inbox watcher, chat/Ramble intent, strip cutter, measurement, tag, index, CHANGELOG) | engine service + `Tools` script (ffmpeg if present; else strip only) | 2–3 days |
| 8 | Retrieval (tag + BM25 over `index.json`) and the Animator's context builder; rule proposals flow (auto-add quoted rules, Needs-you for changes) | engine | 1 day |
| 9 | Capture harness: build the missing `capture-app.ts`; seekable clock for pages; checks H1–H9 over `layoutProbe.ts` and `settling.ts`; `metrics.json` + strips as evidence | `Tools\motion\`, `renderer/motion/`, runtime check | 2–3 days |
| 10 | Motion lens prompt (Verifier on Astra, side-by-side strips) | runtime | 0.5 day |
| 11 | Settings rows, D-79 role colours, card labels | renderer | 0.5 day |
| 12 | Shadow validation runs (§4): 20 + 20 items; Nick's blind ratings | harness + Nick | 2 days of compute + about 4 h of Nick |
| 13 | Phase 2 (after validation): Ctrl+Shift+M taste capture on the Kibble capture layer + Muse | renderer + main | 2 days |

**Total: about 12–16 working days** for steps 1–12. Step 13 adds about 2 days. Steps 2–6 (Writer)
are useful on their own and can ship first. Steps 7–10 (Animator) follow.

---

## 6. Questions for Nick

1. **Writer takes all writing now staffed as Builder** (this supersedes D-69.4)? Recommended: yes,
   except code comments, commit messages and the Discovery research synthesis.
2. **Writer model:** Fable 5.1 (best raw prose, 2.5× Opus's price, heavier on your Claude quota) or
   Opus 5.5 (cheaper, clearer than before, still wordy)? Recommended: Fable, and let validation
   decide.
3. **Your voice samples:** which writing is "you"? Pitcher List posts, emails, notes, docs? Name 4–5
   pieces per kind, or a folder.
4. **Should the Editor block?** Recommended: it blocks only on unsupported facts, missing content,
   slop over the threshold, or the wrong reader or purpose. Style notes are advisory, and the Writer
   must answer each one.
5. **Animator model pair:** Opus 5.5 builds and Astra reviews (recommended), or the reverse? Both are
   tested in validation anyway.
6. **Taste library scope:** motion only now, with writing voice as a small sibling? Or also visual
   and layout taste for the Designer later?
7. **Capture:** are "tell Kel / drop in the inbox" enough for now, with the Kibble-style hotkey
   (Ctrl+Shift+M, screen region + voice) in phase 2? Or do you want the hotkey first?
8. **Rule changes:** auto-add rules quoted straight from your notes and ask only when a rule changes
   or contradicts another (recommended), or ask every time?
9. **Privacy:** may reference clips and frames go to Anthropic/OpenAI when used as examples (default
   yes, except items marked private), and should screen captures default to private (recommended)?
10. **Seed the library with Kel's 15 approved moments** as "loved" references (recommended)?
11. **Designer on HTML pages:** only when there's no existing look or you ask for design
    (recommended), or on every page?

---

## Sources

1. EQ-Bench, "Slop Score" (method and human baseline): https://eqbench.com/slop-score.html ·
   code: https://github.com/sam-paech/slop-score · Antislop framework: https://arxiv.org/pdf/2510.15061
2. Wikipedia, "Signs of AI writing" (WikiProject AI Cleanup):
   https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing · TechCrunch coverage:
   https://techcrunch.com/2025/11/20/the-best-guide-to-spotting-ai-writing-comes-from-wikipedia/
3. The Decoder, "Claude Opus 5.5 matches Fable 5.1 … promises less 'Claudish' writing" (2026-09-22):
   https://the-decoder.com/claude-opus-5-5-matches-fable-5-1-at-40-percent-lower-cost-as-anthropic-promises-to-fix-claudish-writing/
4. The AI Career Lab, "Claude Opus 5.5 vs Fable 5.1 (Sept 2026)":
   https://theaicareerlab.com/blog/claude-opus-5-5-vs-fable-5-1-for-professionals
5. Techzine, "Claude Opus 5.5 beats Fable 5.1 at a much lower cost":
   https://www.techzine.eu/news/applications/144462/claude-opus-5-5-beats-fable-5-1-at-a-much-lower-cost/
6. "Catch Me If You Can? Not Yet: LLMs Still Struggle to Imitate the Implicit Writing Styles of
   Everyday Authors": https://arxiv.org/pdf/2509.14543 · "How Well Do LLMs Imitate Human Writing
   Style?": https://arxiv.org/pdf/2509.24930
7. Wei et al., "Long-form factuality in large language models" (SAFE):
   https://arxiv.org/abs/2403.18802
8. "Self-Preference Bias in LLM-as-a-Judge": https://arxiv.org/abs/2410.21819
9. "Who Judges Matters: Measuring Family-Conditioned Preference in LLM-as-Judge Panels":
   https://arxiv.org/html/2609.17857
10. "Self-Preference Bias in Rubric-Based Evaluation of Large Language Models":
    https://arxiv.org/abs/2604.06996
11. Decrypt, "OpenAI's GPT-6 Astra Is Shockingly Good at Almost Everything":
    https://decrypt.co/377514/openai-gpt-6-astra-review-shockingly-good
12. Layer3 Labs, "How Writers Can Use GPT-6 Astra for Drafting & Editing":
    https://www.layer3labs.io/guides/gpt-6-astra-for-writing
13. BuildMVPFast, "Best AI for Writing September 2026":
    https://www.buildmvpfast.com/articles/best-llms-2026-guide/content-writing-ai
14. Louis-François Bouchard, "DeepSeek V4.1 Flash: … Cheaper Writing Drafts":
    https://www.louisbouchard.ai/deepseek-v41-flash-kv-cache-writing-benchmark/
15. Regolo, "DeepSeek V4.1 Flash vs V4 Flash":
    https://regolo.ai/deepseek-v4-1-flash-vs-v4-flash-which-open-weight-model-should-your-company-run/
16. HeyGen Research, "Code2Video Benchmark: Evaluating AI Agents on Motion Design" (2026-09-18):
    https://www.heygen.com/research/introducing-code2video-benchmark
17. The Rundown, "Claude Opus 5.5 vs Opus 5 vs Fable 5.1":
    https://app.therundown.ai/guides/claude-opus-5-5-vs-opus-5-vs-fable-5-1
18. Animation2Code, "Evaluating Temporal Visual Reasoning in Video-to-Code Generation":
    https://pith.science/paper/2606.28593
19. senlindesign, "taste-skill" (encoding the *why* behind design tokens):
    https://github.com/senlindesign/taste-skill

Internal: workforce research in `Data\recovery\recovered-source-and-artifacts.zip`
(`ux-audit/workforce-os/03, 04`; `ux-audit/workforce-role-charters/03, 05, 09, 14, 15, 17`), read
only. Installed skills in `C:\Users\Nick\.claude\skills\` (`animate`, `review-animations`,
`improve-animations`, `emil-design-eng`, `apple-design`), read only.
