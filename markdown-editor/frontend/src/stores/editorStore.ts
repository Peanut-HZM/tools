/**
 * Editor Store - Manages editor state and dirty flag
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useEditorStore = defineStore('editor', () => {
  // State
  const content = ref('')
  const originalContent = ref('')
  const cursorLine = ref(1)
  const cursorColumn = ref(1)
  const isSaving = ref(false)
  const lastSaveTime = ref<Date | null>(null)
  const saveError = ref<string | null>(null)

  // Getters
  const isDirty = computed(() => content.value !== originalContent.value)
  const saveStatus = computed(() => {
    if (isSaving.value) return 'saving'
    if (saveError.value) return 'error'
    if (isDirty.value) return 'unsaved'
    return 'saved'
  })

  // Actions
  function setContent(newContent: string, isOriginal: boolean = false) {
    content.value = newContent
    if (isOriginal) {
      originalContent.value = newContent
    }
  }

  function updateContent(newContent: string) {
    content.value = newContent
  }

  function setCursorPosition(line: number, column: number) {
    cursorLine.value = line
    cursorColumn.value = column
  }

  function markAsSaved() {
    originalContent.value = content.value
    lastSaveTime.value = new Date()
    saveError.value = null
  }

  function setSaving(saving: boolean) {
    isSaving.value = saving
  }

  function setSaveError(error: string | null) {
    saveError.value = error
  }

  function reset() {
    content.value = ''
    originalContent.value = ''
    cursorLine.value = 1
    cursorColumn.value = 1
    isSaving.value = false
    lastSaveTime.value = null
    saveError.value = null
  }

  return {
    // State
    content,
    originalContent,
    cursorLine,
    cursorColumn,
    isSaving,
    lastSaveTime,
    saveError,
    // Getters
    isDirty,
    saveStatus,
    // Actions
    setContent,
    updateContent,
    setCursorPosition,
    markAsSaved,
    setSaving,
    setSaveError,
    reset
  }
})
