<template>
  <div class="search-dialog">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="File Search" name="files">
        <el-input
          v-model="fileQuery"
          placeholder="Search file names..."
          clearable
          @input="searchFiles"
        />
        <div class="search-results">
          <div
            v-for="result in fileResults"
            :key="result.path"
            class="result-item"
            @click="selectFile(result.path)"
          >
            <el-icon><Document /></el-icon>
            <span class="result-name">{{ result.name }}</span>
            <span class="result-path">{{ result.path }}</span>
          </div>
          <el-empty v-if="fileQuery && fileResults.length === 0" description="No files found" />
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="Content Search" name="content">
        <div class="search-options">
          <el-input
            v-model="contentQuery"
            placeholder="Search content..."
            clearable
            @keyup.enter="searchContent"
          />
          <el-checkbox v-model="useRegex">Regex</el-checkbox>
          <el-checkbox v-model="caseSensitive">Case Sensitive</el-checkbox>
          <el-button type="primary" size="small" @click="searchContent">Search</el-button>
        </div>
        <div class="search-results">
          <div v-for="result in contentResults" :key="result.file" class="result-group">
            <div class="result-file">
              <el-icon><Document /></el-icon>
              {{ result.file }}
            </div>
            <div
              v-for="(match, idx) in result.matches"
              :key="idx"
              class="result-match"
              @click="selectMatch(result.file, match.line)"
            >
              <span class="line-number">Line {{ match.line }}:</span>
              <span class="match-content">{{ match.content }}</span>
            </div>
          </div>
          <el-empty v-if="contentQuery && contentResults.length === 0 && !isSearching" description="No matches found" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { searchApi } from '@/api/searchApi'
import type { FileSearchResult, SearchResult } from '@/types'

const emit = defineEmits<{
  (e: 'select', path: string, line?: number): void
}>()

const activeTab = ref('files')
const fileQuery = ref('')
const contentQuery = ref('')
const useRegex = ref(false)
const caseSensitive = ref(false)
const isSearching = ref(false)

const fileResults = ref<FileSearchResult[]>([])
const contentResults = ref<SearchResult[]>([])

let searchTimeout: number | null = null

async function searchFiles() {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  
  if (!fileQuery.value) {
    fileResults.value = []
    return
  }
  
  searchTimeout = window.setTimeout(async () => {
    try {
      fileResults.value = await searchApi.searchFiles(fileQuery.value)
    } catch (e) {
      console.error('Search failed:', e)
    }
  }, 300)
}

async function searchContent() {
  if (!contentQuery.value) {
    contentResults.value = []
    return
  }
  
  isSearching.value = true
  try {
    contentResults.value = await searchApi.searchContent(
      contentQuery.value,
      useRegex.value,
      caseSensitive.value
    )
  } catch (e) {
    console.error('Search failed:', e)
  } finally {
    isSearching.value = false
  }
}

function selectFile(path: string) {
  emit('select', path)
}

function selectMatch(path: string, line: number) {
  emit('select', path, line)
}
</script>

<style scoped>
/* ========================================
   CYBERPUNK SEARCH DIALOG STYLES
   ======================================== */
.search-dialog {
  min-height: 400px;
  background: #0d0d14;
}

.search-dialog :deep(.el-tabs__item) {
  font-weight: 700;
  font-size: 13px;
  color: #666680;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: all 0.3s ease;
}

.search-dialog :deep(.el-tabs__item:hover) {
  color: #00f5ff;
}

.search-dialog :deep(.el-tabs__item.is-active) {
  color: #00f5ff;
  text-shadow: 0 0 10px currentColor;
}

.search-dialog :deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, #00f5ff, #ff00ff);
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.5);
}

.search-dialog :deep(.el-tabs__nav-wrap::after) {
  background: #1a1a2e;
}

.search-options {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.search-options .el-input {
  flex: 1;
  min-width: 200px;
}

.search-options :deep(.el-input__wrapper) {
  border-radius: 10px;
  background: rgba(0, 245, 255, 0.05);
  border: 1px solid rgba(0, 245, 255, 0.2);
  box-shadow: none;
  transition: all 0.3s ease;
}

.search-options :deep(.el-input__wrapper:hover),
.search-options :deep(.el-input__wrapper.is-focus) {
  border-color: #00f5ff;
  box-shadow: 0 0 20px rgba(0, 245, 255, 0.2);
}

.search-options :deep(.el-input__inner) {
  color: #e0e0e8;
}

.search-options :deep(.el-checkbox__label) {
  font-weight: 600;
  font-size: 12px;
  color: #a0a0b8;
}

.search-options :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background: #00f5ff;
  border-color: #00f5ff;
  box-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
}

.search-options :deep(.el-button--primary) {
  background: linear-gradient(45deg, #00f5ff, #00a8ff);
  border: none;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 0 0 20px rgba(0, 245, 255, 0.3);
  transition: all 0.3s ease;
}

.search-options :deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 0 30px rgba(0, 245, 255, 0.5);
}

.search-results {
  max-height: 350px;
  overflow-y: auto;
  margin-top: 18px;
  border: 1px solid rgba(0, 245, 255, 0.2);
  border-radius: 12px;
  background: rgba(10, 10, 15, 0.8);
  backdrop-filter: blur(10px);
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  cursor: pointer;
  border-bottom: 1px solid rgba(0, 245, 255, 0.1);
  transition: all 0.3s ease;
  position: relative;
}

.result-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 0;
  background: linear-gradient(180deg, #00f5ff, #bf00ff);
  transition: width 0.3s ease;
}

.result-item:last-child {
  border-bottom: none;
}

.result-item:hover {
  background: rgba(0, 245, 255, 0.08);
}

.result-item:hover::before {
  width: 3px;
}

.result-item .el-icon {
  color: #666680;
  font-size: 18px;
  transition: all 0.3s ease;
}

.result-item:hover .el-icon {
  color: #00f5ff;
  filter: drop-shadow(0 0 5px currentColor);
}

.result-name {
  font-weight: 700;
  color: #e0e0e8;
}

.result-item:hover .result-name {
  color: #00f5ff;
  text-shadow: 0 0 10px currentColor;
}

.result-path {
  color: #666680;
  font-size: 11px;
  margin-left: auto;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'JetBrains Mono', monospace;
}

.result-group {
  margin-bottom: 0;
  border-bottom: 1px solid rgba(0, 245, 255, 0.15);
}

.result-group:last-child {
  border-bottom: none;
}

.result-file {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 700;
  padding: 14px 18px;
  background: rgba(0, 245, 255, 0.05);
  color: #00f5ff;
  position: sticky;
  top: 0;
  z-index: 1;
  text-shadow: 0 0 10px currentColor;
  border-bottom: 1px solid rgba(0, 245, 255, 0.1);
}

.result-file .el-icon {
  color: #00f5ff;
  filter: drop-shadow(0 0 5px currentColor);
}

.result-match {
  padding: 12px 18px 12px 44px;
  cursor: pointer;
  font-size: 13px;
  border-top: 1px solid rgba(0, 245, 255, 0.05);
  transition: all 0.3s ease;
}

.result-match:hover {
  background: rgba(191, 0, 255, 0.08);
}

.line-number {
  color: #bf00ff;
  font-weight: 700;
  margin-right: 14px;
  font-size: 11px;
  text-shadow: 0 0 8px currentColor;
}

.match-content {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: #a0a0b8;
  font-size: 12px;
}

.result-match:hover .match-content {
  color: #e0e0e8;
}

/* Empty state */
:deep(.el-empty__description) {
  color: #666680;
}
</style>
