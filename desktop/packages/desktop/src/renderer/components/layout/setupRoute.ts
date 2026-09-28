/** Configuration pages used by the first-run flow remain available until setup is finished. */
export const setupRouteAllowed = (pathname: string, _desktop = false): boolean =>
  // D-70: Permissions, Providers and Diagnostics live under /settings/*; their old routes only
  // redirect there, so they stay allowed while setup is open. The Work page is retired.
  pathname === '/onboarding' ||
  pathname.startsWith('/settings/') ||
  pathname === '/settings' ||
  pathname === '/providers' ||
  pathname === '/connections' ||
  pathname === '/autonomy' ||
  pathname === '/projects' ||
  pathname === '/projects/knowledge' ||
  pathname === '/projects/map';
