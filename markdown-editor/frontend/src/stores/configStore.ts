/**
 * Config Store - Manages user settings
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { EditorConfig } from '@/types'
import { configApi } from '@/api/configApi'
import i18n from '@/i18n'

const defaultConfig: EditorConfig = {
  theme: 'light',
  fontSize: 14,
  autoSaveInterval: 30,
  previewTheme: 'github',
  showLineNumbers: true,
  tabSize: 2,
  useSpaces: true,
  language: (localStorage.getItem('markdown-editor-language') as 'zh-CN' | 'en-US') || 'zh-CN'
}

export const useConfigStore = defineStore('config', () => {
  // State
  const config = ref<EditorConfig>({ ...defaultConfig })
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Watch for language changes
  watch(() => config.value.language, (newLang) => {
    i18n.global.locale.value = newLang
    localStorage.setItem('markdown-editor-language', newLang)
  })

  // Actions
  async function loadConfig() {
    isLoading.value = true
    error.value = null
    try {
      const loadedConfig = await configApi.getConfig()
      config.value = { ...defaultConfig, ...loadedConfig }
      // Ensure language is set correctly if loaded from backend, or keep local default
      if (!loadedConfig.language) {
        config.value.language = defaultConfig.language
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load config'
      // Use default config on error
      config.value = { ...defaultConfig }
    } finally {
      isLoading.value = false
    }
  }

  async function saveConfig() {
    isLoading.value = true
    error.value = null
    try {
      await configApi.saveConfig(config.value)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to save config'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function updateConfig(updates: Partial<EditorConfig>) {
    config.value = { ...config.value, ...updates }
  }

  function setTheme(theme: 'light' | 'dark') {
    config.value.theme = theme
  }
  
  function setLanguage(lang: 'zh-CN' | 'en-US') {
    config.value.language = lang
  }

  function setFontSize(size: number) {
    config.value.fontSize = Math.max(8, Math.min(32, size))
  }

  function setAutoSaveInterval(interval: number) {
    config.value.autoSaveInterval = Math.max(5, Math.min(300, interval))
  }

  function resetToDefaults() {
    config.value = { ...defaultConfig }
  }

  return {
    // State
    config,
    isLoading,
    error,
    // Actions
    loadConfig,
    saveConfig,
    updateConfig,
    setTheme,
    setLanguage,
    setFontSize,
    setAutoSaveInterval,
    resetToDefaults
  }
})
