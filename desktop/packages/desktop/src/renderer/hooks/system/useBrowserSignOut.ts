/**
 * CP-12: signing out of Kel in a browser (WebUI). Only offered away from the desktop app — the
 * desktop window has no sign-in. The old hidden Ctrl/Cmd+Shift+L chord is gone; sign-out is a
 * visible button in Settings → Remote / WebUI.
 */
import { useCallback } from 'react';
import { usePreviewContext } from '@renderer/pages/conversation/Preview/context/PreviewContext';
import { useAuth } from '@renderer/hooks/context/AuthContext';
import { blurActiveElement } from '@renderer/utils/ui/focus';

export const useBrowserSignOut = () => {
  const { closePreview, clearPreviewForScope } = usePreviewContext();
  const { logout, status } = useAuth();
  const available =
    typeof window !== 'undefined' && !(window as { electronAPI?: unknown }).electronAPI && status === 'authenticated';

  const signOut = useCallback(async () => {
    blurActiveElement();
    // Hide the panel now so the page responds at once; the tabs are discarded after sign-out.
    closePreview();
    try {
      await logout();
    } catch (error) {
      console.error('Sign-out failed:', error);
      return;
    }
    // PreviewProvider lives at the app root and survives sign-out; drop this account's tabs so
    // they are not written back and shown to whoever signs in next.
    clearPreviewForScope();
  }, [clearPreviewForScope, closePreview, logout]);

  return { available, signOut };
};
