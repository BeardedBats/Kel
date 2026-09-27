/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { resolveAgentLogo, useAgentLogos } from '@/renderer/utils/model/agentLogo';
import { iconColors } from '@/renderer/styles/colors';
import { Robot } from '@icon-park/react';
import React from 'react';
import ThemedLogo from './ThemedLogo';

export type AgentBadgeProps = {
  /** Agent backend type */
  backend?: string;
  /** Display name for the agent */
  agent_name?: string;
  /** Custom agent logo (SVG path or emoji string) */
  agentLogo?: string;
  /** Whether the logo is an emoji */
  agentLogoIsEmoji?: boolean;
  /** Whether the explicit assistant logo is intentionally empty. */
  agentLogoIsFallback?: boolean;
};

/** Render agent logo from custom logo, backend logo, or fallback Robot icon */
export const AgentLogoIcon: React.FC<
  Pick<AgentBadgeProps, 'backend' | 'agentLogo' | 'agentLogoIsEmoji' | 'agentLogoIsFallback' | 'agent_name'>
> = ({ backend, agentLogo, agentLogoIsEmoji, agentLogoIsFallback, agent_name }) => {
  const logos = useAgentLogos();
  const logoContent = (() => {
    if (agentLogoIsFallback) {
      return <Robot theme='outline' size={16} fill={iconColors.primary} />;
    }
    if (agentLogo) {
      if (agentLogoIsEmoji) {
        return <span className='text-14px leading-none'>{agentLogo}</span>;
      }
      return (
        <ThemedLogo
          src={agentLogo}
          alt={`${agent_name || 'agent'} logo`}
          className='block w-16px h-16px object-contain'
        />
      );
    }
    const logo = resolveAgentLogo(logos, { backend });
    if (logo) {
      return <ThemedLogo src={logo} alt={`${backend} logo`} className='block w-16px h-16px object-contain' />;
    }
    return <Robot theme='outline' size={16} fill={iconColors.primary} />;
  })();

  return (
    <span className='inline-flex w-16px h-16px items-center justify-center shrink-0 leading-none'>{logoContent}</span>
  );
};

