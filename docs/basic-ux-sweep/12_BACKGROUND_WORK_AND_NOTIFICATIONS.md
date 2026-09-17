# Background work and notifications

| Item | Class | Evidence |
|---|---|---|
| Work continues when navigating away | PAG | engine jobs run detached from pages (architecture + work states) |
| Status discoverable | PAG | Work page: waiting / needs-you / finished groups with plain-language states |
| Completion discoverable | PAG | Work page + `system.notificationEnabled` gate for desktop notifications |
| Return directly to a result | PAG | palette job entries + Work rows |
| Failures that need attention | PAG | “Waiting to continue” surface with the exact reason (audit copy) |
| Desktop notifications | PBF | Electron notification plumbing + settings toggles exist; with no runnable provider nothing could complete to notify about — classified honestly |
| Notification spam control | PAG | notification + cron-notification toggles live in Settings · System |
| Recent activity surface | MO | the Work page already answers “what happened / what needs me”; a separate activity feed would duplicate it for current flows |
| Work cancellation | PBF | cancel path exists; unverifiable live without a provider |
