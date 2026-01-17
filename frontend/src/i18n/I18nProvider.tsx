/**
 * I18n Provider Component - Provides internationalization context
 */
import { useState, useCallback, ReactNode, useMemo, useEffect } from 'react';
import { I18nContext, Language, getTranslations } from './index';

interface I18nProviderProps {
  children: ReactNode;
  defaultLanguage?: Language;
}

export function I18nProvider({ children, defaultLanguage = 'zh-CN' }: I18nProviderProps) {
  const [language, setLanguageState] = useState<Language>(() => {
    // Try to get language from localStorage
    const stored = localStorage.getItem('markdown-editor-language');
    if (stored === 'zh-CN' || stored === 'en-US') {
      return stored;
    }
    return defaultLanguage;
  });

  const t = useMemo(() => getTranslations(language), [language]);

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('markdown-editor-language', lang);
  }, []);

  // Sync with localStorage changes
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'markdown-editor-language' && e.newValue) {
        if (e.newValue === 'zh-CN' || e.newValue === 'en-US') {
          setLanguageState(e.newValue);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const value = useMemo(() => ({
    language,
    t,
    setLanguage,
  }), [language, t, setLanguage]);

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  );
}

export default I18nProvider;
