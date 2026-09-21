# Shell shared changes

Base: dev/v2 772b2c357943cf9793639bbf660171c49d809c38.

No engine architecture, provider execution, routing backend, learning, staffing, security or network policy changes. The isolated startup and socket-lifecycle repairs are recorded below.

- Ramble calls the existing `kelRequest` helper. Its local bridge-only wrapper failed in WebUI before making a request. The shared helper already handles desktop and authenticated browser transport. Endpoint names, payloads and storage remain unchanged.
- Projects shows its three existing sections together. Deep links scroll to the requested section. Memory, map and recipe actions retain their handlers.
- Mobile navigation closes the existing drawer after a route selection. Desktop navigation stays open.
- The attachment dropdown opens on click. The mobile control sheet remains unchanged.
- Message copy/fork controls use native buttons and remain available on touch. Existing capability checks and handlers remain intact.
- Theme application maps explicit saved color overrides to shell paint aliases. Removing overrides removes aliases. It does not change persisted settings or built-in theme defaults.
- The fix-capture source assertion accepts whitespace across line endings. It tests the same no-automatic-development sentence.

- Native source startup failed before creating a window. `runtime/kel/acp_host.py` used a relative import inside its standalone `initialize` entry point. The exact desktop command returned `attempted relative import with no known parent package`; aioncore reported this as `Authentication required`. Use the absolute `kel.service` import, consistent with the script's existing path setup. A subprocess regression test covers the actual standalone entry point. No engine behavior or protocol changes.
- Conversation composers start in the existing single-line mode and expand through the existing content measurement. Desktop-only controls remain in that row. Draft, paste, IME, queue and send handlers remain unchanged.

- Onboarding displays all five existing setup sections together. Completion persistence and Skip/Next/Back remain. Project and permission edits open their established routes.
- Provider details now expand within integration rows. Existing key operations and readiness calls are unchanged. Advanced credential controls remain available in a disclosure.
- Permission guardrail summary is visible in the third source card. Existing scope checks and detailed explanations remain under Advanced details.
- The composer keeps its command hints in its accessible title. Its default visible prompt follows the Figma. Model-unavailable copy remains.
- Model controls use the existing authenticated `kelRequest` transport in WebUI. Desktop still uses the same preload bridge. No model API, choice semantics or provider execution changed. A DOM regression verifies reading and saving the default model without a desktop bridge.
- The chat size default is now 16px. Shadow message rendering uses a 25px default line height on desktop and phone. Empty CSS variable values are omitted from the shadow document so they cannot mask the 16px fallback. Explicit saved font sizes still apply.
- The WebUI raw TCP listener keeps its early error handler through rejected upgrades. Browser resets after a 401 previously caused an unhandled ECONNRESET and stopped the server. A socket-reset regression confirms that anonymous upgrades remain rejected and subsequent static requests succeed. Authentication and network policy remain unchanged.
- The Work & context drawer uses the same authenticated request helper in WebUI. Its bridge-only request wrapper prevented all drawer reads on phones. Routes and state handling remain unchanged. The affected mobile journey checks that this bridge error is absent. Populated conversation continuity remains unverified without a live seed.
