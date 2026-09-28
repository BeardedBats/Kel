/**
 * VIS-21 / D-60: which skills Kel shows and offers.
 *
 * The bundled aioncore unpacks its own donor skill set into `store/builtin-skills` on every start
 * (recruiting, WeChat, role-play, OpenClaw, AionUi set-up and so on) and reports them all as
 * `source: 'builtin'`. None of them is Kel's: the Kel agent has no skill delivery configured, the
 * Kel assistant switches the auto-inject ones off, and nothing in the engine reads them. So a
 * built-in skill is shown (and offered for a chat) only when it is on Kel's own allowlist, which is
 * empty until Kel ships a skill of its own. Skills the person added stay visible.
 */

type SkillLike = { name: string; source: string; is_auto_inject?: boolean };

/** Kel's own built-in skills. Add a name here only when Kel actually ships and uses that skill. */
export const KEL_BUILTIN_SKILLS: readonly string[] = [];

export const isKelVisibleSkill = (skill: SkillLike): boolean =>
  skill.source === 'custom' || (skill.source === 'builtin' && KEL_BUILTIN_SKILLS.includes(skill.name));

export const kelVisibleSkills = <T extends SkillLike>(skills: readonly T[]): T[] => skills.filter(isKelVisibleSkill);

/**
 * Donor skills that aioncore would add to a new chat on its own (auto-inject) — always excluded, so
 * they can never reach Kel's prompts even if a future aioncore adds more of them.
 */
export const donorAutoInjectSkills = (skills: readonly SkillLike[]): string[] =>
  skills.filter((skill) => skill.source === 'builtin' && skill.is_auto_inject && !isKelVisibleSkill(skill)).map((skill) => skill.name);
