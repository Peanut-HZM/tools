/**
 * File Store - Manages directory tree and current file state
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { FileNode, FileContent } from '@/types'
import { fileApi } from '@/api/fileApi'

export const useFileStore = defineStore('file', () => {
  // State
  const directoryTree = ref<FileNode | null>(null)
  const currentFile = ref<FileContent | null>(null)
  const currentFilePath = ref<string>('')
  const rootPath = ref<string>('')
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const expandedNodes = ref<Set<string>>(new Set())

  // Getters
  const hasCurrentFile = computed(() => currentFile.value !== null)
  const currentFileName = computed(() => {
    if (!currentFilePath.value) return ''
    const parts = currentFilePath.value.split('/')
    return parts[parts.length - 1]
  })
  const hasRootPath = computed(() => rootPath.value !== '')

  // Actions
  async function loadRootPath() {
    try {
      const result = await fileApi.getRootPath()
      rootPath.value = result.path
      return result
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load root path'
      throw e
    }
  }

  async function setRootPath(path: string) {
    isLoading.value = true
    error.value = null
    try {
      const result = await fileApi.setRootPath(path)
      rootPath.value = result.path
      // Clear current file when changing root
      currentFile.value = null
      currentFilePath.value = ''
      directoryTree.value = null
      // Load new directory tree
      await loadDirectoryTree()
      return result
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to set root path'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function loadDirectoryTree(subPath: string = '') {
    isLoading.value = true
    error.value = null
    try {
      directoryTree.value = await fileApi.getDirectoryTree(subPath)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load directory tree'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function openFile(path: string) {
    isLoading.value = true
    error.value = null
    try {
      currentFile.value = await fileApi.readFile(path)
      currentFilePath.value = path
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to open file'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function saveCurrentFile(content: string) {
    if (!currentFilePath.value) return
    
    isLoading.value = true
    error.value = null
    try {
      await fileApi.saveFile(currentFilePath.value, content)
      if (currentFile.value) {
        currentFile.value.content = content
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to save file'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function createFile(path: string, content: string = '') {
    isLoading.value = true
    error.value = null
    try {
      await fileApi.createFile(path, content)
      await loadDirectoryTree()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create file'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteFile(path: string) {
    isLoading.value = true
    error.value = null
    try {
      await fileApi.deleteFile(path)
      if (currentFilePath.value === path) {
        currentFile.value = null
        currentFilePath.value = ''
      }
      await loadDirectoryTree()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete file'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function renameFile(oldPath: string, newPath: string) {
    isLoading.value = true
    error.value = null
    try {
      await fileApi.renameFile(oldPath, newPath)
      if (currentFilePath.value === oldPath) {
        currentFilePath.value = newPath
      }
      await loadDirectoryTree()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to rename file'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function toggleNode(path: string) {
    if (expandedNodes.value.has(path)) {
      expandedNodes.value.delete(path)
    } else {
      expandedNodes.value.add(path)
    }
  }

  function closeCurrentFile() {
    currentFile.value = null
    currentFilePath.value = ''
  }

  return {
    // State
    directoryTree,
    currentFile,
    currentFilePath,
    rootPath,
    isLoading,
    error,
    expandedNodes,
    // Getters
    hasCurrentFile,
    currentFileName,
    hasRootPath,
    // Actions
    loadRootPath,
    setRootPath,
    loadDirectoryTree,
    openFile,
    saveCurrentFile,
    createFile,
    deleteFile,
    renameFile,
    toggleNode,
    closeCurrentFile
  }
})
