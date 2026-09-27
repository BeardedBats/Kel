/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

/** A diagnostics profile the engine understands (a module tag or `global-summary`). */
export type FeedbackDiagnosticsProfile = string;

export type FeedbackDiagnosticsExplicitContext = {
  agentId?: string;
  assistantDefinitionId?: string;
  assistantId?: string;
  conversationId?: string;
  mcpServerId?: string;
  mcpServerName?: string;
  messageId?: string;
  modelId?: string;
  msgId?: string;
  providerId?: string;
  routePath?: string;
  slotId?: string;
  teamId?: string;
};

export type FeedbackDiagnosticsContextInput = {
  explicitContext?: FeedbackDiagnosticsExplicitContext;
  explicitProfiles?: FeedbackDiagnosticsProfile[];
  routeAtOpen?: string;
  routeAtSubmit?: string;
  selectedModule?: string;
};
