# Desktop ACP Chat footer — source evidence

Reference: current populated Chat `185:4284`. The ACP path used by the isolated Kel conversation had no desktop footer, unlike Aionrs. This increment adds the existing shared usage component to ACP with actual messageState.tokenUsage and messageState.context_limit. Missing reports stay unknown. No screenshot cost/token/cache/context values enter live state.

The existing AgentModeSelector moves into the desktop footer and stays in mobile's composer. The same backend, session, team propagation, warmup and runtime configuration callbacks remain. Its availability guard remains: the isolated backend has no selectable mode catalog, so a permission control is not fabricated. Existing context diagnostics remain available. The workspace label reads the real conversation scope; it is a static label, not a new picker.

Dark/Light source checks pass at 1440/800px. At 1440, composer is x388/y786, 920×60px; footer x388/y852, 920×36px, ending at y888 with a 12px bottom inset. Chips use 13px/20px body type, 28px height, 8px horizontal padding and 16px gaps. The existing 160×6px context track uses the Dark reference warm fill and muted label. At 800, the footer wraps its metrics into another row, with no chip/document overflow. Four absent usage fields remain unknown. Populated three-turn/list/avatar checks, last-turn wheel access and 24px bottom spacing still pass. No renderer errors.

Sidebar bottom padding now measures 16px; Settings ends at y884. Existing navigation icons use 15px artwork centered inside 16px slots. Header width/alignment and native title/model controls were inspected; the missing reference Planning subtitle, full populated sidebar status variants and exact icon/glass acceptance remain open.

TypeScript and source build pass. Nine focused tests pass, including three new footer tests covering missing reports, reported counters/cost/window, zero cost, unknown denominator and exhausted context. The full suite passes 64 files / 446 tests in 43.98s. Existing MaxListenersExceededWarning persists without failures. Tests supply synthetic usage props; live provider-reported usage is not claimed.

Source probe uses scoped legacy-history interception. Native fixture messages were restored in both stores, Dark restored, all probe apps closed. No provider/send/permission-change/fork action ran. The first extraction placed the shared mode node inside a nested file callback; TypeScript and rendered source caught it, then it was moved to component scope. A CP1252 dash in the probe assertion caused a false missing-report failure; an ASCII Unicode escape repaired the assertion without changing product values. Final checks pass.

Package proof waits for the next larger desktop milestone. Latest disposable package b8c84ae; canonical App 8c67121, canonical Data untouched. Mobile remains paused. request_review unavailable; no independent review claim. This is scoped footer/layout completion, not full populated Chat acceptance.

Captures: [Dark 1440](DESKTOP_CHAT_FOOTER_DARK_1440.png), [Dark 800](DESKTOP_CHAT_FOOTER_DARK_800.png), [Light 1440](DESKTOP_CHAT_FOOTER_LIGHT_1440.png), [Light 800](DESKTOP_CHAT_FOOTER_LIGHT_800.png).
