# Desktop Chat bottom inset — source evidence

Reference: current populated Chat `185:4284`, thread bottom padding 24px. This follows the source turn-rhythm increment. The former 32px inset is repaired without removing user Copy/Fork controls.

Desktop content padding is 14px plus the existing outer 10px. Native user hover controls now use 24px rows/buttons rather than 32px rows/28px buttons. Their callbacks and labels are unchanged. Hover and focus-within continue to reveal them. Mobile stays unchanged. This control sizing uses the existing desktop component scale; the reference frame does not display its user hover row, so exact hover-variant parity is not claimed.

A single stored synthetic user turn passes Dark/Light at 1440/800px: 24px row-bottom inset; scrollHeight/clientHeight 692/692; no unnecessary scrollbar, document overflow or renderer errors. Hover controls remain inside the scroller. User Copy sends the original fixture text through an intercepted clipboard; focus-within keeps the row visible. Fork was not executed. Three stored turns pass 30px row gaps, existing type/list/avatar assertions, last-turn wheel access and exactly 24px bottom spacing in both themes and widths. Both native message stores were journaled and restored afterward.

The mixed tool/plan/reply probe also passes Dark/Light at both widths: actions follow tools, original reply Copy uses the intercepted clipboard, a real isolated reaction write is restored, tool/plan expansion remains accessible, and no overflow/errors occur. Its runtime/tool/plan states are injected; no provider or tool ran. All apps closed and Dark was restored.

TypeScript, source build and six focused tests pass. Combined task/Chat full desktop regression passes 63 files / 443 tests in 43.99s. The existing MaxListenersExceededWarning appears without a failure. No engine regression was repeated for these local styles.

This closes the retained-control bottom-spacing difference. Full Chat sidebar/footer/header/composer acceptance and remaining task icons/glass/catalog variants stay open. Package proof waits for the next larger milestone; latest disposable package b8c84ae predates Chat rhythm, Model and task field work. App stays 8c67121; canonical Data was untouched. Mobile paused. request_review unavailable; no independent review claim.

Interaction captures: [Dark 1440](DESKTOP_CHAT_BOTTOM_INSET_DARK_1440.png), [Light 800](DESKTOP_CHAT_BOTTOM_INSET_LIGHT_800.png). A native Copy confirmation may appear after the intercepted copy action.
