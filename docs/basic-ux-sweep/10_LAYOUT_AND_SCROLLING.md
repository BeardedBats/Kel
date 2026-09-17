# Layout and scrolling

## The contract

App shell → fixed page-level controls where needed → one flexible main region → one owned vertical
scroll container → every interactive control physically reachable. Content existing in the DOM is
not proof of usability.

## Verified (packaged)

- Route matrix (`sweep2`): every main region either fits one viewport (empty states — nothing to
  scroll) or owns a scroll container that reaches its bottom; no horizontal overflow anywhere.
- Seeded-content matrix: the rich chat (~15 messages incl. tables/code) scrolls to the last message;
  Settings · System grew with the new Data/Backup cards and its last control is reachable.
- Providers regression (the DeepSeek key case): the provider form's API-key field is scrolled to,
  focused and typed into (`sweep4`).
- Narrow window (980px): `/guid` and `/transcription` report 0px horizontal overflow (`hardening`);
  drawers/modals stay reachable.
- Zoom: the scale control and Ctrl/Cmd +/-/0 behaviour are probed in `sweep3`/`sweep4`.

## Notes

The old blanket “overflow: hidden” suspects were re-audited: Kel pages render inside the shell's
single scroll owner; no magic heights were added per screen.
