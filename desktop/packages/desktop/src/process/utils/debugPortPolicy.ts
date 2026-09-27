/**
 * CP-13 — a packaged Kel refuses to start with a remote debugging port.
 *
 * `--remote-debugging-port` (or `--remote-debugging-pipe`) lets any local program drive every Kel
 * window, including the pages that hold Kel's permissions and Connections. A packaged build starts
 * with it only when the environment says so explicitly: `KEL_ALLOW_DEBUG_PORT=1` (used by the
 * off-screen audit runs, which drive a scratch copy of Kel over CDP). Development builds are
 * unaffected.
 */
export const DEBUG_PORT_ALLOW_ENV = 'KEL_ALLOW_DEBUG_PORT';

const DEBUG_SWITCHES = ['--remote-debugging-port', '--remote-debugging-pipe'];

export const hasRemoteDebuggingSwitch = (argv: readonly string[]): boolean =>
  argv.some((arg) => DEBUG_SWITCHES.some((name) => arg === name || arg.startsWith(`${name}=`)));

/** The refusal to print, or null when Kel may start. */
export const debugPortRefusal = (options: {
  isPackaged: boolean;
  argv: readonly string[];
  env: Record<string, string | undefined>;
}): string | null => {
  if (!options.isPackaged || !hasRemoteDebuggingSwitch(options.argv)) return null;
  if (options.env[DEBUG_PORT_ALLOW_ENV] === '1') return null;
  return `[Kel] Refusing to start with a remote debugging port. Set ${DEBUG_PORT_ALLOW_ENV}=1 to allow it for an audit run.`;
};
