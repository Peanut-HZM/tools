import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

export type Theme = 'dark' | 'light' | 'system';

interface ThemeContextValue {
  theme: Theme;
  resolved: 'dark' | 'light';
  setTheme: (t: Theme) => void;
}

const STORAGE_KEY = 'tk-theme';
const DEFAULT_THEME: Theme = 'dark';

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function resolveTheme(theme: Theme): 'dark' | 'light' {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: light)').matches
      ? 'light'
      : 'dark';
  }
  return theme;
}

function applyTheme(theme: Theme): void {
  const resolved = resolveTheme(theme);
  document.documentElement.setAttribute('data-theme', resolved);
  localStorage.setItem(STORAGE_KEY, theme);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === 'undefined') return DEFAULT_THEME;
    return (localStorage.getItem(STORAGE_KEY) as Theme) || DEFAULT_THEME;
  });

  const [resolved, setResolved] = useState<'dark' | 'light'>(() =>
    resolveTheme(theme)
  );

  const setTheme = (t: Theme) => {
    setThemeState(t);
    applyTheme(t);
  };

  // 初次挂载：应用 localStorage 中的主题
  useEffect(() => {
    applyTheme(theme);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 监听系统主题变化（仅 theme='system' 时响应）
  useEffect(() => {
    if (theme !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: light)');
    const onChange = () => {
      const r = resolveTheme('system');
      setResolved(r);
      document.documentElement.setAttribute('data-theme', r);
    };
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [theme]);

  // 同步 resolved 状态
  useEffect(() => {
    setResolved(resolveTheme(theme));
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, resolved, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within <ThemeProvider>');
  }
  return ctx;
}