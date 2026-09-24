# Desktop Dark System — r61

**Authority:** Kel Design System, Screens FINAL `188:1620`, Data panel `188:1856`, General panel `188:1884`, and the danger button `188:1881`. **Source:** `integration/v2` at `62f957c1b49500b4f3ce59c3dfb491e973246b1a`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r61`, isolated from the protected stable app.

The [r59 baseline](key/r59-system-1440.png) had a 664px Data card and 273px height. The desktop scrollbar consumed 6px. Its Restore action used the blue secondary control and longer copy. General lacked the FINAL row dividers and used 160px language and 120px number controls.

The [r61 packaged capture](key/r61-system-1440.png) measures the Data card at x613/y183, 670×297.39px. Its rows start at y230, y298, and y366 with heights 68, 68, and 97.39px. The three actions measure 126.22×36, 115.75×36, and 196.73×36px. Restore now uses the Foundation danger gradient `#a6443f` to `#8b312d`, `#fff1f0` text, and the FINAL sentence: “Restores a backup folder. Current data is kept; Kel restarts.”

General starts at x613/y492.39 and measures 670×463px. Its nine rows have FINAL heights `51, 39, 39, 39, 39, 51, 51, 51, 39`. Language is 200×34px; the number controls are 80×34px with the Dark field border and fill. [The geometry and interaction record](r61-system-check.json) includes the 800px pass: document width stays 800px. Backup and Restore dialogs opened and closed with Escape. Neither operation was submitted.

The first packaged r60 pass confirmed Data but exposed 50px General switch rows. Its [capture](key/r60-system-1440.png) and [measurements](r60-system-check.json) remain as the intermediate. r61 was packaged after that source correction. The native theme picker was not part of this System pass; r29 already recorded two adjustments in one popup.

Typecheck, package build, Windows unpacked builder, archive manifest/bundle gate, and `git diff --check` passed. The archive main build matched source (`1815dcc992e94cbd`); renderer index matched (`d6e53ffc9a360d72`). The r61 app tree used root PID 49176, CDP port 9405, and disposable `r43-populated` data. Its root and child paths matched `C:\Users\Nick\KelV2Candidate.r61` before stop. The protected stable engine PID 26544 remained under `C:\Users\Nick\KelDogfoodCandidate`; the original r20 process was absent. PIDs can change.

The layout claim covers this desktop Dark System state and its opened dialogs. It does not claim a backup or restore, changed system setting, live service response, or product-wide parity. Faint Light-mode labels and phone layout remain outside this pass. No independent review occurred because `request_review` was unavailable.
