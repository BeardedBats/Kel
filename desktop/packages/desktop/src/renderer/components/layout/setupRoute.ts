/** Configuration pages used by the first-run flow remain available until setup is finished. */
export const setupRouteAllowed = (pathname: string, desktop = false): boolean =>
  // Figma 273:13646 shows existing Work with Setup still open. Chat remains gated.
  (desktop && pathname === '/work') ||
  pathname === '/onboarding' ||
  pathname.startsWith('/settings/') ||
  pathname === '/settings' ||
  pathname === '/providers' ||
  pathname === '/connections' ||
  pathname === '/autonomy' ||
  pathname === '/projects' ||
  pathname === '/projects/knowledge' ||
  pathname === '/projects/map';
