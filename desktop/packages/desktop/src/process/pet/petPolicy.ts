/**
 * Kel V1.6 donor-surface policy (Campaign C AUD-MINOR-008).
 *
 * The desktop-pet subsystem is donor-derived (AionUi) and has no Kel V1.6 product surface.
 * It is retained in the tree — donor infrastructure is not deleted on donor naming alone —
 * but DISABLED: no reachable path may create pet windows and the settings surface cannot
 * enable it. The shipped assets stay inert. Full disposition + reachability list:
 * docs/v1.6/repair-final/06_DONOR_DISPOSITIONS.md.
 */
export const KEL_PET_SUBSYSTEM_ENABLED = false;
