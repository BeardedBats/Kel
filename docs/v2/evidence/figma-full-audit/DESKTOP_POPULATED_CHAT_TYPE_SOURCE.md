# Desktop populated Chat typography — 2026-09-26

Live Chat `185:4284` was refreshed directly. Its five-step assistant reply exposed three scoped differences: list rows used a 7px collapsed gap instead of 14px; Light timestamps used 12px body type instead of 13px/16px heading type; the assistant mark lacked the 24px slot and 22×23 geometry. This increment repairs those differences on desktop. Mobile retains its original mark and type behavior.

The existing isolated native conversation temporarily held three stored text messages matching the reference structure. Native message reads remained real; only the protected legacy-history prefix was intercepted for that source-preview conversation. No provider or renderer-only text injection supplied the messages. The original native records were journaled and restored in both isolated databases after each probe. Canonical Data was never opened.

Dark and Light passed at 1440px and 800px. All five list rows measured a 14px gap; timestamps measured 500 13px/16px Instrument Sans; the avatar slot measured 24×24 and the existing mark 22×23. User text retains its right alignment, 390px width and 16px/25px body type. The assistant spans 920px at the wide width and contracts at 800px. Wheel scrolling reached the last turn without hiding its text beneath the composer. Document overflow and renderer errors were zero. Dark was restored and each app closed.

TypeScript, source build and six focused tool/plan/menu tests across two files passed. The latest broader desktop suite remains 63 files / 443 tests from Setup. Package proof waits for the next larger milestone. This is typography/scroll evidence, not complete frame acceptance: overall thread positioning, turn rhythm, native header/composer differences, populated sidebar and truthful model/project/footer facts still need disposition. No live model, chat submission or fork ran.

Captures: [Dark 1440](DESKTOP_POPULATED_CHAT_TYPE_DARK_1440.png), [800](DESKTOP_POPULATED_CHAT_TYPE_DARK_800.png); [Light 1440](DESKTOP_POPULATED_CHAT_TYPE_LIGHT_1440.png), [800](DESKTOP_POPULATED_CHAT_TYPE_LIGHT_800.png).

Canonical App remains `8c67121`; Data untouched. Latest disposable package remains `0b49b56` and predates this source batch. Mobile stays paused. `request_review` was unavailable; no independent review is claimed.
