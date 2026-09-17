# Updates and recovery

| Item | Class | Evidence |
|---|---|---|
| installed version visible | PAG | Settings · About shows `v1.5.0` (audit) |
| Check for updates | PAG | About button invokes the update check; prerelease toggle; update notes/links |
| Update availability clear | PBF | the notification card exists; without an update server the availability state cannot be produced here |
| restart-required understandable | PBF | update flow states it; not producible in this environment |
| unsaved work/drafts protected | PAG after fix | drafts now persist across restarts, which is the protection that matters here |
| update failure recoverable | PAG | failures surface through the update card and never silently lose data |
