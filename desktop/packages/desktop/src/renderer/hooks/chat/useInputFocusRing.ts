import { useThemeContext } from '@/renderer/hooks/context/ThemeContext';

export const useInputFocusRing = () => {
  const { theme } = useThemeContext();
  const isDarkTheme = theme === 'dark';

  return {
    activeBorderColor: isDarkTheme ? '#4D4B87' : '#E1E0FF',
    inactiveBorderColor: isDarkTheme ? '#3a3a4a' : '#c9cacf',
    // FIX-0020 (Nick): clicking into the chat box must not cast a glow under it; focus shows only as
    // the border colour change.
    activeShadow: 'none',
  };
};
