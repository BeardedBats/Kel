import React from 'react';
import model from '@renderer/assets/figma/nav-model.svg';
import assistants from '@renderer/assets/figma/nav-assistants.svg';
import tools from '@renderer/assets/figma/nav-tools.svg';
import skills from '@renderer/assets/figma/nav-skills.svg';
import connections from '@renderer/assets/figma/nav-connections.svg';
import appearance from '@renderer/assets/figma/nav-appearance.svg';
import webui from '@renderer/assets/figma/nav-webui.svg';
import pet from '@renderer/assets/figma/nav-pet.svg';
import system from '@renderer/assets/figma/nav-system.svg';
import archived from '@renderer/assets/figma/nav-archived.svg';
import about from '@renderer/assets/figma/nav-about.svg';
const icons: Record<string, string> = { model, assistants, tools, skills, connections, appearance, webui, pet, system, archived, about };
export default function ShellSettingsIcon({ name }: { name: string }) {
  return <img className='kel-shell-source-icon' src={icons[name]} alt='' width={16} height={16} />;
}
