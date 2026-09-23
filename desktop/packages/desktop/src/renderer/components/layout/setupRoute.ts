/** Configuration pages used by the first-run flow remain available until setup is finished. */
export const setupRouteAllowed = (pathname: string): boolean =>
  pathname === '/onboarding' ||
  pathname.startsWith('/settings/') ||
  pathname === '/settings' ||
  pathname === '/providers' ||
  pathname === '/connections' ||
  pathname === '/autonomy' ||
  pathname === '/projects' ||
  pathname === '/projects/knowledge' ||
  pathname === '/projects/map';
