# Phase 9 — Profiles vs Projects: V1.6 PRODUCT DECISION

Date: 2026-09-18 · Decider: Program Director (Campaign A) · Status: **DECIDED — NO PROFILES CONCEPT
IN V1.6; PROJECTS REMAIN THE SINGLE ISOLATION CONCEPT**

## Decision

V1.6 keeps ONE isolation concept: **Projects**. No "Profiles", no isolated-workspace sibling, no
per-identity providers/theme container. Terminology across the product stays "Projects". Nothing is
merged or renamed; nothing new is built for this phase.

## Evidence considered

- **Donor matrix item 21** (`docs/basic-ux-sweep/16_DONOR_PATTERN_MATRIX.md`): "Projects already
  scope conversations, files, knowledge, artifacts and recipes. A Profile concept would mostly
  duplicate Projects plus per-profile providers/theme; the justifying use case (two unrelated lives
  with different provider accounts) is real but narrow." → decision **REJECT (Projects are the
  simpler answer)**.
- **Donor remediation** (`docs/basic-ux-sweep/18_DONOR_FEATURE_REMEDIATION.md` §4): profiles listed
  under "deliberately not implemented (with reasons)" — optional/future; Projects provide the
  isolation.
- **Current-repo verification (2026-09-18):** no `/profiles` route, no Profiles nav or locale
  surface. The only "profile" strings are unrelated: AWS-profile auth labels (donor legacy), the
  Firefox/browser-profile guardrail line, the engine-internal lease `profile`, the WSL permission
  profile. The donor `AssistantSettings` page is hidden by `HIDE_DONOR_AGENT_SURFACES = true`
  (`Router.tsx:61,112` → `/guid` redirect).
- **Sprint directive §35**: "Resolve semantics using actual product behavior. Prefer fewer concepts.
  Implement bounded V1.6 decision. Record user-model reasoning in the breadcrumb corpus."

## User-model reasoning (recorded for the audit corpus)

Kel's user model: a **project** is the unit of "my work here" — it owns conversations, files,
knowledge (memory), artifacts and recipes. Identities (who I am to the provider) are a
provider-account concern, not a workspace concern; the narrow "two unrelated lives with different
provider accounts" case does not justify a parallel container that duplicates project scoping.
Fewer concepts win; if the case becomes real, the fix is per-project provider overrides later, not
a second container.

## Bounded V1.6 actions

- **None required in code** — reality already matches the decision (verified above). The held visual
  batch 3 (Work / Projects / Permissions) must keep "Projects" language (context recorded in
  VISUAL_EVIDENCE_INDEX).
- Keep the donor assistant surface hidden. The `AgentBadge` "navigate to the assistant editor when
  `assistantId` is provided" path is donor-dead under the flag for Kel conversations — recorded as
  audit target 46 (confirm it can never render for a Kel conversation).

## Release impact

None. This decision removes an optional concept from the release conversation; it blocks nothing.

## Re-entry criteria (post-V1.6)

A real, user-stated need for two provider identities in one install → design per-project provider
overrides (reusing Projects), not a Profiles container; product decision required.
