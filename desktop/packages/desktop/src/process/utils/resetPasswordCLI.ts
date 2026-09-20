/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 *
 * Reset password CLI utility for packaged applications
 * 打包应用的密码重置命令行工具
 */

// Color output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

const log = {
  info: (msg: string) => console.log(`${colors.blue}i${colors.reset} ${msg}`),
  success: (msg: string) => console.log(`${colors.green}OK${colors.reset} ${msg}`),
  error: (msg: string) => console.log(`${colors.red}ERR${colors.reset} ${msg}`),
  warning: (msg: string) => console.log(`${colors.yellow}WARN${colors.reset} ${msg}`),
  highlight: (msg: string) => console.log(`${colors.cyan}${colors.bright}${msg}${colors.reset}`),
};

export function resolveResetPasswordUsername(argv: string[]): string {
  const resetPasswordIndex = argv.indexOf('--resetpass');
  if (resetPasswordIndex === -1) {
    return 'admin';
  }

  const argsAfterCommand = argv.slice(resetPasswordIndex + 1);
  return argsAfterCommand.find((arg) => !arg.startsWith('--')) || 'admin';
}

// D3: Kel keeps one admin account whose scrypt hash lives in <data>/webui.config.json (owned by
// the web-host auth store). This writes a fresh random password there; the next browser login
// uses it. No donor backend route is involved.
export async function resetPasswordCLI(username: string): Promise<void> {
  log.info(`Target user: ${username} (advisory — Kel keeps one admin account)`);
  try {
    const { generateReadablePassword, setWebUiPassword } = await import('@aionui/web-host');
    const { getDataPath } = await import('./utils');
    const password = generateReadablePassword();
    const result = setWebUiPassword(getDataPath(), password);
    if (!result.ok) throw new Error(`Could not set a new password (${result.code})`);
    log.success('Password reset successfully.');
    log.info('New password:');
    log.highlight(password);
    log.info('');
    log.warning('Please change this password after next login.');
  } catch (error) {
    log.error(error instanceof Error ? error.message : 'Password reset failed');
    process.exit(1);
  }
}
