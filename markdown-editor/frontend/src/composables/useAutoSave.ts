/**
 * Auto-save composable
 */
import { ref, watch, onUnmounted } from 'vue'
import { useFileStore, useEditorStore, useConfigStore } from '@/stores'

export function useAutoSave() {
  const fileStore = useFileStore()
  const editorStore = useEditorStore()
  const configStore = useConfigStore()
  
  let autoSaveTimer: number | null = null
  const lastEditTime = ref<number>(0)
  
  function startAutoSave() {
    stopAutoSave()
    
    const interval = configStore.config.autoSaveInterval * 1000
    
    autoSaveTimer = window.setInterval(async () => {
      // Only save if there are unsaved changes and enough time has passed
      if (editorStore.isDirty && fileStore.currentFilePath) {
        const timeSinceLastEdit = Date.now() - lastEditTime.value
        
        // Wait at least 2 seconds after last edit before auto-saving
        if (timeSinceLastEdit >= 2000) {
          try {
            editorStore.setSaving(true)
            await fileStore.saveCurrentFile(editorStore.content)
            editorStore.markAsSaved()
          } catch (e) {
            editorStore.setSaveError('Auto-save failed')
          } finally {
            editorStore.setSaving(false)
          }
        }
      }
    }, interval)
  }
  
  function stopAutoSave() {
    if (autoSaveTimer) {
      clearInterval(autoSaveTimer)
      autoSaveTimer = null
    }
  }
  
  function recordEdit() {
    lastEditTime.value = Date.now()
  }
  
  // Watch for config changes
  watch(
    () => configStore.config.autoSaveInterval,
    () => {
      if (autoSaveTimer) {
        startAutoSave()
      }
    }
  )
  
  // Watch for content changes
  watch(
    () => editorStore.content,
    () => {
      recordEdit()
    }
  )
  
  onUnmounted(() => {
    stopAutoSave()
  })
  
  return {
    startAutoSave,
    stopAutoSave,
    recordEdit
  }
}
