/**
 * Internationalization (i18n) configuration for Markdown Editor
 */
import { createContext, useContext } from 'react';
import { zhCN } from './locales/zh-CN';
import { enUS } from './locales/en-US';

export type Language = 'zh-CN' | 'en-US';
export type Translations = typeof zhCN;

const translations: Record<Language, Translations> = {
  'zh-CN': zhCN,
  'en-US': enUS,
};

export function getTranslations(lang: Language): Translations {
  return translations[lang] || translations['zh-CN'];
}

// i18n Context
export interface I18nContextType {
  language: Language;
  t: Translations;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
}

export const I18nContext = createContext<I18nContextType | null>(null);

export function useI18n(): I18nContextType {
  const context = useContext(I18nContext);
  if (!context) {
    // Return default values if not in provider
    return {
      language: 'zh-CN',
      t: zhCN,
      setLanguage: () => {},
      toggleLanguage: () => {},
    };
  }
  return context;
}

// Helper function to interpolate variables in translation strings
export function interpolate(str: string, vars: Record<string, string>): string {
  return str.replace(/\{(\w+)\}/g, (_, key) => vars[key] || `{${key}}`);
}

export { zhCN, enUS };
