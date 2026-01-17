/**
 * Markdown Editor Theme Styles - Tailwind CSS class definitions
 */

export const themes = {
  light: {
    // Background colors
    bg: {
      primary: 'bg-white',
      secondary: 'bg-slate-50',
      tertiary: 'bg-slate-100',
      hover: 'hover:bg-slate-100',
      active: 'bg-slate-200',
    },
    // Text colors
    text: {
      primary: 'text-slate-900',
      secondary: 'text-slate-600',
      muted: 'text-slate-400',
      accent: 'text-cyan-600',
    },
    // Border colors
    border: {
      primary: 'border-slate-200',
      secondary: 'border-slate-300',
      accent: 'border-cyan-500',
    },
    // Editor specific
    editor: {
      bg: 'bg-white',
      text: 'text-slate-900',
      lineNumbers: 'text-slate-400 bg-slate-50',
      selection: 'selection:bg-cyan-100',
    },
    // Preview specific
    preview: {
      bg: 'bg-white',
      text: 'text-slate-900',
      code: 'bg-slate-100 text-slate-800',
      codeBlock: 'bg-slate-800 text-slate-100',
      blockquote: 'border-cyan-500 bg-cyan-50 text-slate-700',
      link: 'text-cyan-600 hover:text-cyan-700',
    },
    // Sidebar
    sidebar: {
      bg: 'bg-slate-50',
      itemHover: 'hover:bg-slate-100',
      itemActive: 'bg-cyan-50 text-cyan-700',
    },
    // Buttons
    button: {
      primary: 'bg-cyan-500 hover:bg-cyan-600 text-white',
      secondary: 'bg-slate-200 hover:bg-slate-300 text-slate-700',
      ghost: 'hover:bg-slate-100 text-slate-600',
    },
    // Status
    status: {
      success: 'text-green-600',
      error: 'text-red-600',
      warning: 'text-yellow-600',
      info: 'text-cyan-600',
    },
  },
  dark: {
    // Background colors
    bg: {
      primary: 'bg-slate-900',
      secondary: 'bg-slate-800',
      tertiary: 'bg-slate-700',
      hover: 'hover:bg-slate-700',
      active: 'bg-slate-600',
    },
    // Text colors
    text: {
      primary: 'text-slate-100',
      secondary: 'text-slate-300',
      muted: 'text-slate-500',
      accent: 'text-cyan-400',
    },
    // Border colors
    border: {
      primary: 'border-slate-700',
      secondary: 'border-slate-600',
      accent: 'border-cyan-500',
    },
    // Editor specific
    editor: {
      bg: 'bg-slate-900',
      text: 'text-slate-100',
      lineNumbers: 'text-slate-500 bg-slate-800',
      selection: 'selection:bg-cyan-900',
    },
    // Preview specific
    preview: {
      bg: 'bg-slate-900',
      text: 'text-slate-100',
      code: 'bg-slate-700 text-cyan-400',
      codeBlock: 'bg-slate-800 text-slate-300',
      blockquote: 'border-cyan-500 bg-slate-800 text-slate-300',
      link: 'text-cyan-400 hover:text-cyan-300',
    },
    // Sidebar
    sidebar: {
      bg: 'bg-slate-800',
      itemHover: 'hover:bg-slate-700',
      itemActive: 'bg-cyan-900/50 text-cyan-400',
    },
    // Buttons
    button: {
      primary: 'bg-cyan-500 hover:bg-cyan-600 text-white',
      secondary: 'bg-slate-700 hover:bg-slate-600 text-slate-200',
      ghost: 'hover:bg-slate-700 text-slate-400',
    },
    // Status
    status: {
      success: 'text-green-400',
      error: 'text-red-400',
      warning: 'text-yellow-400',
      info: 'text-cyan-400',
    },
  },
};

export type Theme = 'light' | 'dark';
export type ThemeStyles = typeof themes.light;

export function getTheme(theme: Theme): ThemeStyles {
  return themes[theme];
}

// Common styles that don't change with theme
export const commonStyles = {
  // Transitions
  transition: {
    fast: 'transition-all duration-150',
    normal: 'transition-all duration-200',
    slow: 'transition-all duration-300',
  },
  // Shadows
  shadow: {
    sm: 'shadow-sm',
    md: 'shadow-md',
    lg: 'shadow-lg',
    xl: 'shadow-xl',
  },
  // Rounded corners
  rounded: {
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    full: 'rounded-full',
  },
  // Focus states
  focus: {
    ring: 'focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2',
    outline: 'focus:outline-none focus:ring-2 focus:ring-cyan-500',
  },
};
