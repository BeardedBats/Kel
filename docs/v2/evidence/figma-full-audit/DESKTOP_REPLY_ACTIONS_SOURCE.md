# Desktop reply actions after tool rows — source repair

Current desktop Figma 273:12914 places reply actions after its tool group. Desktop now renders the same reply action row beneath the adjacent tool summary. Ordinary replies, user messages, teammate messages, scheduled-message badges, and mobile ordering retain their existing paths. The original message id, copy payload, reaction key, fork anchor, and last-message eligibility remain attached to the row.

Reaction state now belongs to the rendered action component. Moving the row does not leave a second hidden reaction state behind. The row reuses existing copy and fork handlers. MessageText's teammate-color hook now runs before its empty-content return, preserving stable hook order. Light neutral action images receive the existing dark-tint treatment. No accent rail was added.

Source checks passed at 1440px and 800px in Dark and Light. Exactly one action row belongs to `figma-plan-1`, under the tool group; the original text row contains no duplicate. Copy through More reached the original assistant reply, excluding the user prompt and tool inputs. Clipboard write was intercepted. Helpful toggles wrote the real isolated localStorage key and matched aria-pressed. The prior reaction value was restored. Tool/plan expansion, full neutral detail borders, current-step space, contrast, and overflow checks also passed. Every probe had zero renderer errors. No provider reply, fork, command, patch, or search ran.

Screenshots: [Dark 1440](DESKTOP_REPLY_ACTIONS_DARK_1440.png), [800](DESKTOP_REPLY_ACTIONS_DARK_800.png); [Light 1440](DESKTOP_REPLY_ACTIONS_LIGHT_1440.png), [800](DESKTOP_REPLY_ACTIONS_LIGHT_800.png). Source-preview legacy-prefix interception remains scoped to this fixture, as described in [Chat state evidence](DESKTOP_CHAT_PLAN_LIGHT_STATES_SOURCE.md). Package history loading is not claimed here.

TypeScript, the final source build, and the full desktop regression passed: 63 files / 440 tests. The existing MaxListenersExceededWarning remains, without test failures. The React review checked stable hooks, original message identity, actual action callbacks, and desktop-only ordering. Independent request_review is unavailable; no independent review is claimed.

Package proof waits for the next larger milestone. Broader populated Chat positioning/typography, the fixture's right-panel header, remaining Light Workspace/dialog states, live providers, and durable plan recovery remain open. Canonical App remains 8c67121. App and durable Data were untouched.
