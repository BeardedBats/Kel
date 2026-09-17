# Phase 4 — i18n / donor-string cleanup: completion status

Phase: 4 of the V1.6 program (completed 2026-09-17, autonomous Main increment after the P1
capability gate closed). Work originated in the interrupted Phase 4 WIP preserved in git stash
`MAIN-PHASE4-WIP-BEFORE-P1-CAPABILITY-REMEDIATION` and was restored safely on top of `267364e`
(zero file overlap with the P1/CAP2 remediation — verified before apply; the stash was kept until
restoration was proven, then dropped after this increment committed).

## Scope delivered

1. **Donor app-name cleanup across all 12 locale catalogs** (de-DE, en-US, es-ES, fa-IR, fr-FR,
   ja-JP, ko-KR, pt-BR, ru-RU, tr-TR, uk-UA, zh-CN, zh-TW; 247 JSON files):
   - `AionUi` / `AionUI` / `Aion UI` → `Kel`; `AionCore` → `Kel Engine`; `Aion CLI` → `Kel`;
     `AionHub` market strings rewritten per locale; `iOfficeAI/OfficeCLI` → `OfficeCLI`.
   - The donor Butler key block (`settings.talkToButler.*`, 15 keys) and
     `settings.webui.letButlerSetup` removed from every locale and from `i18n-keys.d.ts`.
   - Stale locale-only orphan keys pruned (donor-era guid scanner, old cron drawer, dropped
     chat notices, etc.); functional localized error content kept.
   - Validation: the audited transform re-run reports **zero remaining changes and zero donor
     residuals**; all 247 locale files parse; no locale contains the removed keys.
2. **Butler removal end-to-end** (donor feature, one-assistant scope conflict): `ButlerDiagnoseButton`
   and `useTalkToButler` deleted; `TalkToButlerButton` replaced by the Kel-native
   `SettingsCreateMenu`; all 11 call sites migrated (chat error chips keep FeedbackButton; Model/Tools/
   Scheduled/WebUI/Feedback-modal flows keep their real capabilities); help/default strings cleaned.
3. **Reachable code-literal sweep** (user-visible strings, not comments):
   - About modal: donor wiki/contact/official-site rows and donor GitHub link removed; update-log and
     GitHub icon now point at the product repository `github.com/BeardedBats/Kel`.
   - Boot dialogs: "download latest" link → Kel releases; tray/login/titlebar/notifications already
     cleaned in the WIP.
   - Model settings: donor wiki configuration-guide link removed (no Kel equivalent exists).
   - Tools/MCP: donor wiki image-generation guides removed.
   - Channels: assistant descriptions and guide copy → "Kel assistant"; DingTalk credential links now
     point at DingTalk's own developer console (`open.dingtalk.com`) instead of a donor wiki.
   - Welcome/guid: the GitHub quick action points at Kel's repository; the unreferenced donor
     Skills-Market banner (donor discussion links) deleted.
   - Channel-conflict warning literals token-swapped to Kel (OpenClaw remains named as the
     third-party gateway it is).
   - Updates: default repo → `BeardedBats/Kel`; release links → Kel releases; no donor CDN is ever
     consulted (check fails closed on GitHub until Kel publishes release assets — final release
     wiring tracked for Phase 15).
   - Theme background markers are generated as `/* Kel Theme Background … */` with a legacy matcher
     so existing user CSS keeps replacing cleanly.
4. **Internal identifiers kept intentionally** (implementation details, not user-facing): DB enums
   and CHECK constraints (`'aionui'` conversation source, error ownership), internal error-code key
   names (`AIONUI_*`, `MCP_*`), `cleanAionUITimestamp` helper name, legacy built-in MCP alias
   (`'AionUi Image Generation'`, needed to recognize pre-existing stored config), dev single-instance
   names, and the installer-failure marker path contract (`<appdata>/AionUi/…`, written outside this
   tree).
5. **Legal attribution preserved**: `third_party/AIONUI-PROVENANCE.md`, license files, packaged
   license resources, and the per-file `Copyright … AionUi … SPDX-License-Identifier: Apache-2.0`
   headers in donor-derived source remain untouched.

## Documented dormant boundaries (not normal UI; recorded, not rewritten)

- `UpdateMigrationDialog` and its migration-letter flow render only under
  `IS_DISCONTINUED_BUILD` (false in Kel builds; catalog copy already Kel-named).
- OpenClaw remote-agent strings (hidden remote-agents panel, gateway error code) describe the
  dormant donor integration; the feature is not reachable in this release.
- Hidden donor pages (LocalAgents setup-guide URL, AgentHub PR link) stay behind
  `HIDE_DONOR_AGENT_SURFACES`.
- `OfficeWatchViewer` keeps the upstream OfficeCLI releases URL: it is the genuine install source of
  a third-party component, not product identity.

## Verification

- Locale transform replay: 0 changes / 0 residuals; 247 files valid; no removed keys anywhere.
- Desktop: `tsc --noEmit` 0 errors; vitest 76/76.
- Engine: full runtime suite 613 passed (+10 subtests) — runtime untouched by this phase.
- Packaged: `package-final17` with the copy-scan probe over the reachable routes (zero donor tokens)
  plus the standing approvals/lineage journeys.
