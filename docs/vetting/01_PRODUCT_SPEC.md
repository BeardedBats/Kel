# Design Vetting Sessions — product specification

## One-line goal

Kel turns an incomplete product/UI idea into a serious, developer-ready design specification through
rapid structured questioning, without the user waiting for Kel between answers.

## Governing principles (from the program brief)

> The user controls the decisions. Kel expands the design space, explains tradeoffs, visualizes
> possibilities, remembers everything, and removes the friction of turning ideas into a real
> specification.

> Input method is replaceable. Answer understanding is not part of the composer.

> Kel should expose goals, work, results, and decisions — not its machinery.

## What the experience is

- It lives inside the normal conversation. Batches render as chat content; answers are typed in the
  same composer (`12: A`, `13: D`), quickly and out of order, with no assistant turn in between.
- A companion **Vetting tab** in Kel's "Work & context" drawer shows the batch, decisions, open
  questions, conflicts, spec preview, and greybox directions. It is a mirror of the conversation
  state, not a separate workspace.
- It never looks like a popup form, a slow interview, a rigid wizard, an agent control panel, or a
  three-choice AI template.

## First template

`Product / UI Design Vetting` (id `product_ui_design`): 28 questions across 9 sections — goals,
audience, information architecture, modules, interactions/density, edge states, responsive behavior,
visual direction, and developer handoff — with 4–9 materially distinct options per question, one
open-ended question, `Recommended` tags only where a real default exists (each with its reason), and
alternative tags ("Best for new users", "Best for power users", "Strong alternative") where several
directions are genuinely better for different goals.

Adaptation is dependency-driven, not phase-locked: progressive-density answers pull the
progressive-disclosure questions forward; a dense command-center choice pulls status-taxonomy and
alert-budget questions forward; desktop-only answers drop the narrow-screen question; rare-use
answers pull re-orientation affordances forward.

Additional templates (dashboards, features, game mechanics, marketing pages, architecture decisions,
product requirements) are intended to reuse the same engine: a template is a question bank + the
same ingestion, decision, spec, and greybox machinery. One engine, many templates.

## Batch shape

Batches target 10–16 questions (heuristic, not a cap) and are cognitively related. Batch 1 opens with
goals, audience, and the first architecture decisions; later batches are ordered by what the recorded
decisions make relevant.

## Out of scope for this release

Live transcription, multi-template authoring UI, LLM-driven question generation (a hook exists but the
shipped path is deterministic and provider-free), and final polished comps (greyboxes are
decision-support wireframes).
