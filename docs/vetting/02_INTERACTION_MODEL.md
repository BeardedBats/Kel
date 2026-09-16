# Design Vetting Sessions — interaction model

## The hard rule

> Never require an assistant turn between consecutive answers to active vetting questions.

```
Kel generates a logical batch
        ↓
questions render inline in chat
        ↓
user answers Q1, Q2, Q3, Q4 … (any order, no waiting)
        ↓
Kel silently records each answer (one short "Recorded: n of m recorded." line)
        ↓
user chooses  process answers  or  finish spec now
        ↓
Kel synthesizes once and publishes the next adaptive batch
```

## Answering

- Stable question ids (`Q12`, `Q13`, …) are shown as plain numbers; answers are typed `12: A`,
  `13: D`, `14: C` — several per message, any order (`18: D  12: A  20: skip`).
- One message may carry the whole batch (`12: A\n13: D\n14: C`), or a pasted block of natural
  answers (see 05_ANSWER_INGESTION.md).
- Control words are conversational: `skip`, `defer`, `I'm not sure`, `not sure, show examples`,
  `none of these …`, `make greyboxes, I'll decide later`, `change 14 to D`.
- After every recorded message the user gets one short progress line and nothing else; no
  synthesis, no assistant commentary, no extra turn. That line is durable conversation content
  (one message per answer), so it is visible live and still there when you scroll back.

## Batch controls (chat words and panel buttons)

`process answers` · `show unanswered only` · `finish spec now` · `pause vetting` ·
`view decisions` · `view open questions` · `preview spec` · `show greyboxes 19` ·
`explain 12` · `more options for 12` · `challenge 12`.

There is no floating form above the composer; the panel mirrors the same state.

## Inline actions

- **Explain simply** — translates the decision into plain language ("This is basically asking whether
  the dashboard should feel like a focused checklist or a dense command center."), then reproduces
  the original question and options. The active batch is never lost.
- **More options** — generates genuinely new directions (cross-axis combinations not present in the
  current space), marked as generated, never paraphrases of existing choices.
- **Challenge this** — strongest downside, meaningful tradeoff, one important alternative, then three
  answers: Keep decision · Revise · Defer.
- **I'm not sure** — explains, offers examples, or deferrs; recorded as `UNSURE`/`NEEDS_EXAMPLES` and
  never fabricated into a resolution.
- **Skip for now** — recorded as `SKIPPED`; the question stays visible under Deferred and skipped.
- **None of these** — the free-text tail becomes the recorded custom answer.

## Interruptions

An unrelated question ("Is this technically possible with the Yahoo API?") is answered normally by
Kel; when that reply finishes, the still-open vetting prompts are re-surfaced automatically
("Still waiting on N answer(s): `Q3`, `Q4` …"). Session state is never lost.

## Finish early

`finish spec now` works at any point. The spec is honest about what is missing: resolved decisions,
open decisions, deferred/skipped questions, and explicitly labeled recommended assumptions. Kel never
invents answers.

## Unclear answers

A low-confidence guess is never applied silently. It is proposed ("Possible match: `Q6 → A`. Say
"yes" to confirm, or correct it.") and the user confirms or corrects.

## Contradictions

Choosing a value on one side of a philosophy-level opposition (e.g. a minimal focused opening screen
vs. a dense command center) after the other side was already chosen surfaces a conflict instead of
silently overwriting: **Keep earlier · Use newer · Show tradeoff · Resolve later**. Keeping the
earlier choice parks the newer answer as deferred rather than dropping it.

## Progress language

Progress counts *recorded* states (answered, unsure, skipped, deferred, awaiting visual), because a
counter that says "10 of 12" while every question has been handled is a defect. Strict coverage
(answered vs. everything else) is what the spec reports.
