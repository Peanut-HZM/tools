/**
 * Cursor 历史工具主题配置
 */

export interface Theme {
  id: string;
  name: string;
  colors: {
    primary: string;
    primaryLight: string;
    primaryDark: string;
    background: string;
    surface: string;
    surfaceElevated: string;
    text: string;
    textSecondary: string;
    border: string;
    userMessageBg: string;
    aiMessageBg: string;
    accent: string;
  };
}

export const themes: Theme[] = [
  {
    id: 'deep-space',
    name: '深空紫',
    colors: {
      primary: '#8B5CF6',
      primaryLight: '#A78BFA',
      primaryDark: '#7C3AED',
      background: '#0F0A1F',
      surface: '#1A142D',
      surfaceElevated: '#251E3A',
      text: '#F5F3FF',
      textSecondary: '#C4B5FD',
      border: '#4C1D95',
      userMessageBg: '#7C3AED',
      aiMessageBg: '#1A142D',
      accent: '#F472B6',
    },
  },
  {
    id: 'ocean-blue',
    name: '海洋蓝',
    colors: {
      primary: '#0EA5E9',
      primaryLight: '#38BDF8',
      primaryDark: '#0284C7',
      background: '#082F49',
      surface: '#0C4A6E',
      surfaceElevated: '#155E75',
      text: '#F0F9FF',
      textSecondary: '#BAE6FD',
      border: '#075985',
      userMessageBg: '#0284C7',
      aiMessageBg: '#0C4A6E',
      accent: '#2DD4BF',
    },
  },
  {
    id: 'forest-green',
    name: '森林绿',
    colors: {
      primary: '#22C55E',
      primaryLight: '#4ADE80',
      primaryDark: '#16A34A',
      background: '#052E16',
      surface: '#14532D',
      surfaceElevated: '#166534',
      text: '#F0FDF4',
      textSecondary: '#BBF7D0',
      border: '#15803D',
      userMessageBg: '#16A34A',
      aiMessageBg: '#14532D',
      accent: '#EAB308',
    },
  },
];

export const defaultTheme = themes[0];

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const colors = theme.colors;

  root.style.setProperty('--theme-primary', colors.primary);
  root.style.setProperty('--theme-primary-light', colors.primaryLight);
  root.style.setProperty('--theme-primary-dark', colors.primaryDark);
  root.style.setProperty('--theme-background', colors.background);
  root.style.setProperty('--theme-surface', colors.surface);
  root.style.setProperty('--theme-surface-elevated', colors.surfaceElevated);
  root.style.setProperty('--theme-text', colors.text);
  root.style.setProperty('--theme-text-secondary', colors.textSecondary);
  root.style.setProperty('--theme-border', colors.border);
  root.style.setProperty('--theme-user-message-bg', colors.userMessageBg);
  root.style.setProperty('--theme-ai-message-bg', colors.aiMessageBg);
  root.style.setProperty('--theme-accent', colors.accent);
}

export function getSavedTheme(): Theme | null {
  const savedThemeId = localStorage.getItem('cursor-theme');
  if (savedThemeId) {
    return themes.find(t => t.id === savedThemeId) || null;
  }
  return null;
}

export function saveTheme(themeId: string) {
  localStorage.setItem('cursor-theme', themeId);
}
