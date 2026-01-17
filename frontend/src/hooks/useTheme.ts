/**
 * useTheme Hook - Manages theme state and provides theme utilities
 */
import { useCallback, useMemo } from 'react';
import { themes, Theme, ThemeStyles, commonStyles } from '../styles/markdownEditor';

interface UseThemeOptions {
  theme: Theme;
  onThemeChange?: (theme: Theme) => void;
}

export function useTheme({ theme, onThemeChange }: UseThemeOptions) {
  const currentTheme = useMemo(() => themes[theme], [theme]);

  const toggleTheme = useCallback(() => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    onThemeChange?.(newTheme);
  }, [theme, onThemeChange]);

  const setTheme = useCallback((newTheme: Theme) => {
    onThemeChange?.(newTheme);
  }, [onThemeChange]);

  // Helper to get class names for a specific element type
  const getClasses = useCallback((
    category: keyof ThemeStyles,
    variant: string
  ): string => {
    const categoryStyles = currentTheme[category] as Record<string, string>;
    return categoryStyles?.[variant] || '';
  }, [currentTheme]);

  // Combine multiple theme classes
  const combineClasses = useCallback((...classes: (string | undefined | null | false)[]): string => {
    return classes.filter(Boolean).join(' ');
  }, []);

  return {
    theme,
    styles: currentTheme,
    common: commonStyles,
    toggleTheme,
    setTheme,
    getClasses,
    combineClasses,
    isDark: theme === 'dark',
    isLight: theme === 'light',
  };
}

export default useTheme;
