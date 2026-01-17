<template>
  <div class="app-container" :class="{ 'dark-theme': isDarkTheme }">
    <div class="header">
      <div class="header-left">
        <h1>Markdown Editor</h1>
      </div>
      <div class="header-right">
        <el-button-group>
          <el-button size="small" @click="showFolderSelect = true">
            <el-icon><FolderOpened /></el-icon>
            {{ $t('common.openFolder') }}
          </el-button>
          <el-button size="small" @click="handleNewFile" :disabled="!hasRootPath">
            <el-icon><Plus /></el-icon>
            {{ $t('common.new') }}
          </el-button>
        </el-button-group>
        
        <!-- View/Edit Mode Toggle -->
        <el-button-group v-if="hasCurrentFile" class="mode-toggle">
          <el-button 
            size="small" 
            :type="!isEditMode ? 'primary' : 'default'"
            @click="setViewMode"
          >
            <el-icon><View /></el-icon>
            {{ $t('common.view') }}
          </el-button>
          <el-button 
            size="small" 
            :type="isEditMode ? 'primary' : 'default'"
            @click="setEditMode"
          >
            <el-icon><Edit /></el-icon>
            {{ $t('common.edit') }}
          </el-button>
        </el-button-group>
        
        <el-button size="small" @click="handleSave" :disabled="!canSave" v-if="isEditMode">
          <el-icon><DocumentChecked /></el-icon>
          {{ $t('common.save') }}
        </el-button>
        
        <el-button size="small" circle @click="toggleTheme">
          <el-icon><Sunny v-if="isDarkTheme" /><Moon v-else /></el-icon>
        </el-button>
        
        <!-- Language Switch -->
        <el-dropdown trigger="click" @command="handleLanguageChange">
          <el-button size="small" circle>
            {{ currentLanguage === 'zh-CN' ? '中' : 'En' }}
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="zh-CN" :disabled="currentLanguage === 'zh-CN'">中文</el-dropdown-item>
              <el-dropdown-item command="en-US" :disabled="currentLanguage === 'en-US'">English</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button size="small" circle @click="showSettings = true">
          <el-icon><Setting /></el-icon>
        </el-button>
      </div>
    </div>
    
    <div class="main-content">
      <div class="sidebar" :style="{ width: sidebarWidth + 'px' }">
        <div v-if="!hasRootPath" class="no-folder-state">
          <el-empty :description="$t('editor.selectFolderFirst')">
            <el-button type="primary" @click="showFolderSelect = true">
              <el-icon><FolderOpened /></el-icon>
              {{ $t('common.openFolder') }}
            </el-button>
          </el-empty>
        </div>
        <FileTree v-else @select="handleFileSelect" />
      </div>
      
      <div class="resize-handle" @mousedown="startResize"></div>
      
      <!-- View Mode: TOC sidebar + Full width preview -->
      <template v-if="!isEditMode">
        <div v-if="hasCurrentFile" class="view-mode-container">
          <!-- TOC Sidebar -->
          <div class="toc-sidebar" :style="{ width: tocSidebarWidth + 'px' }">
            <div class="toc-sidebar-header">
              <span>{{ $t('toc.contents') }}</span>
            </div>
            <div class="toc-sidebar-content">
              <ul class="toc-nav-list" v-if="documentToc.length > 0">
                <li
                  v-for="item in documentToc"
                  :key="item.id"
                  :class="['toc-nav-item', 'toc-level-' + item.level, { active: activeTocId === item.id }]"
                  @click="scrollToSection(item.id)"
                >
                  {{ item.text }}
                </li>
              </ul>
              <div v-else class="toc-empty">
                {{ $t('toc.noHeadings') }}
              </div>
            </div>
          </div>
          
          <div class="resize-handle toc-resize" @mousedown="startTocResize"></div>
          
          <!-- Preview Content -->
          <div class="preview-full" ref="previewContainerRef">
            <Preview 
              :content="editorContent" 
              :showHeader="false" 
              @toc-update="handleTocUpdate"
            />
          </div>
        </div>
        <div v-else class="content-area view-mode">
          <div class="empty-state">
            <el-empty :description="hasRootPath ? $t('editor.selectFileToView') : $t('editor.selectFolderFirst')" />
          </div>
        </div>
      </template>
      
      <!-- Edit Mode: Editor + Preview with resizable panels -->
      <template v-else>
        <div class="editor-area" :style="{ flex: editorFlex }">
          <Editor 
            v-if="hasCurrentFile"
            :content="editorContent"
            @update:content="handleContentUpdate"
            @save="handleSave"
          />
          <div v-else class="empty-state">
            <el-empty :description="hasRootPath ? $t('editor.selectFileToEdit') : $t('editor.selectFolderFirst')" />
          </div>
        </div>
        
        <div class="resize-handle preview-resize" @mousedown="startPreviewResize"></div>
        
        <div class="preview-area" :style="{ width: previewWidth + 'px' }">
          <Preview :content="editorContent" />
        </div>
      </template>
    </div>
    
    <div class="status-bar">
      <span class="status-item folder-path" v-if="rootPath">
        <el-icon><Folder /></el-icon>
        {{ rootPath }}
      </span>
      <span class="status-item">{{ currentFilePath || $t('editor.noFileOpen') }}</span>
      <span class="status-item mode-indicator" :class="{ 'edit-mode': isEditMode }">
        {{ isEditMode ? $t('editor.editMode') : $t('editor.viewMode') }}
      </span>
      <span class="status-item" v-if="isEditMode">{{ $t('editor.ln') }} {{ cursorLine }}, {{ $t('editor.col') }} {{ cursorColumn }}</span>
      <span class="status-item" :class="saveStatusClass" v-if="isEditMode">{{ saveStatusText }}</span>
    </div>

    <!-- Settings Dialog -->
    <el-dialog v-model="showSettings" :title="$t('common.settings')" width="500px">
      <SettingsDialog @close="showSettings = false" />
    </el-dialog>

    <!-- New File Dialog -->
    <el-dialog v-model="showNewFile" :title="$t('dialog.newFile')" width="400px">
      <el-form @submit.prevent="createNewFile">
        <el-form-item :label="$t('dialog.fileName')">
          <el-input v-model="newFileName" :placeholder="$t('dialog.fileNamePlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewFile = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="createNewFile">{{ $t('common.create') }}</el-button>
      </template>
    </el-dialog>

    <!-- Folder Select Dialog -->
    <el-dialog v-model="showFolderSelect" :title="$t('dialog.selectFolder')" width="500px">
      <div class="folder-select-content">
        <el-form @submit.prevent="selectFolder">
          <el-form-item :label="$t('dialog.folderPath')">
            <el-input 
              v-model="folderPath" 
              :placeholder="$t('dialog.enterPath')"
            >
              <template #prepend>
                <el-icon><Folder /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item>
            <div class="folder-hint">
              <p>{{ $t('dialog.folderHint') }}</p>
              <p class="hint-examples">
                <strong>Examples:</strong><br>
                Windows: <code>C:\Users\YourName\Documents\notes</code><br>
                macOS/Linux: <code>/home/username/documents/notes</code>
              </p>
            </div>
          </el-form-item>
        </el-form>
        
        <div v-if="recentFolders.length > 0" class="recent-folders">
          <div class="recent-title">{{ $t('dialog.recentFolders') }}</div>
          <div 
            v-for="folder in recentFolders" 
            :key="folder"
            class="recent-folder-item"
            @click="selectRecentFolder(folder)"
          >
            <el-icon><Folder /></el-icon>
            <span>{{ folder }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showFolderSelect = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="selectFolder" :loading="isSelectingFolder">
          {{ $t('common.openFolder') }}
        </el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Plus, DocumentChecked, Setting, Sunny, Moon, FolderOpened, Folder, View, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useFileStore, useEditorStore, useConfigStore } from '@/stores'
import { useI18n } from 'vue-i18n'
import FileTree from '@/components/FileTree.vue'
import Editor from '@/components/Editor.vue'
import Preview from '@/components/Preview.vue'
import SettingsDialog from '@/components/SettingsDialog.vue'

const { t } = useI18n()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const configStore = useConfigStore()

// Layout state
const sidebarWidth = ref(250)
const previewWidth = ref(450)
const tocSidebarWidth = ref(220)
const editorFlex = ref(1)
const showSettings = ref(false)
const showNewFile = ref(false)
const newFileName = ref('')
const showFolderSelect = ref(false)
const folderPath = ref('')
const isSelectingFolder = ref(false)
const recentFolders = ref<string[]>([])
const previewContainerRef = ref<HTMLElement | null>(null)

// View/Edit mode state
const isEditMode = ref(false)

// TOC state for view mode
interface TocItem {
  id: string
  text: string
  level: number
}
const documentToc = ref<TocItem[]>([])
const activeTocId = ref('')

// Load recent folders from localStorage
function loadRecentFolders() {
  try {
    const saved = localStorage.getItem('markdown-editor-recent-folders')
    if (saved) {
      recentFolders.value = JSON.parse(saved)
    }
  } catch (e) {
    console.error('Failed to load recent folders:', e)
  }
}

function saveRecentFolder(path: string) {
  const folders = recentFolders.value.filter(f => f !== path)
  folders.unshift(path)
  recentFolders.value = folders.slice(0, 5) // Keep only 5 recent folders
  localStorage.setItem('markdown-editor-recent-folders', JSON.stringify(recentFolders.value))
}

// Computed
const isDarkTheme = computed(() => configStore.config.theme === 'dark')
const currentLanguage = computed(() => configStore.config.language)
const hasCurrentFile = computed(() => fileStore.hasCurrentFile)
const currentFilePath = computed(() => fileStore.currentFilePath)
const rootPath = computed(() => fileStore.rootPath)
const hasRootPath = computed(() => fileStore.hasRootPath)
const editorContent = computed(() => editorStore.content)
const cursorLine = computed(() => editorStore.cursorLine)
const cursorColumn = computed(() => editorStore.cursorColumn)
const canSave = computed(() => hasCurrentFile.value && editorStore.isDirty && isEditMode.value)

const saveStatusClass = computed(() => {
  const status = editorStore.saveStatus
  return {
    'status-saved': status === 'saved',
    'status-unsaved': status === 'unsaved',
    'status-saving': status === 'saving',
    'status-error': status === 'error'
  }
})

const saveStatusText = computed(() => {
  switch (editorStore.saveStatus) {
    case 'saved': return t('editor.saved')
    case 'unsaved': return t('editor.unsaved')
    case 'saving': return t('editor.saving')
    case 'error': return t('editor.saveError')
    default: return ''
  }
})

// View/Edit mode methods
function setViewMode() {
  isEditMode.value = false
}

function setEditMode() {
  isEditMode.value = true
}

// Language methods
function handleLanguageChange(lang: 'zh-CN' | 'en-US') {
  configStore.setLanguage(lang)
}

// TOC methods for view mode
function handleTocUpdate(toc: TocItem[]) {
  documentToc.value = toc
  if (toc.length > 0 && !activeTocId.value) {
    activeTocId.value = toc[0].id
  }
}

function scrollToSection(id: string) {
  activeTocId.value = id
  const previewContainer = previewContainerRef.value
  if (previewContainer) {
    // 在 preview-full 容器内查找 markdown-body 中的标题元素
    const markdownBody = previewContainer.querySelector('.markdown-body')
    if (markdownBody) {
      const element = markdownBody.querySelector(`#${CSS.escape(id)}`)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }
  }
}

// TOC resize handler
function startTocResize(e: MouseEvent) {
  // isResizing = true
  // resizeType = 'toc'
  // document.addEventListener('mousemove', handleResize)
  // document.addEventListener('mouseup', stopResize)
  // TODO: Fix resize implementation
}

// Methods
async function selectFolder() {
  if (!folderPath.value) {
    ElMessage.warning(t('message.enterFolderPath'))
    return
  }
  
  isSelectingFolder.value = true
  try {
    await fileStore.setRootPath(folderPath.value)
    saveRecentFolder(folderPath.value)
    showFolderSelect.value = false
    ElMessage.success(t('message.folderOpened'))
  } catch (e: any) {
    ElMessage.error(e.message || t('message.openFolderFail'))
  } finally {
    isSelectingFolder.value = false
  }
}

function selectRecentFolder(folder: string) {
  folderPath.value = folder
  selectFolder()
}

async function handleFileSelect(path: string) {
  try {
    await fileStore.openFile(path)
    editorStore.setContent(fileStore.currentFile?.content || '', true)
  } catch (e) {
    ElMessage.error(t('message.openFileFail'))
  }
}

function handleContentUpdate(content: string) {
  editorStore.updateContent(content)
}

async function handleSave() {
  if (!canSave.value) return
  
  editorStore.setSaving(true)
  try {
    await fileStore.saveCurrentFile(editorStore.content)
    editorStore.markAsSaved()
    ElMessage.success(t('message.fileSaved'))
  } catch (e) {
    editorStore.setSaveError(t('message.saveFail'))
    ElMessage.error(t('message.saveFail'))
  } finally {
    editorStore.setSaving(false)
  }
}

function handleNewFile() {
  newFileName.value = ''
  showNewFile.value = true
}

async function createNewFile() {
  if (!newFileName.value) {
    ElMessage.warning('Please enter a file name')
    return
  }
  
  let fileName = newFileName.value
  if (!fileName.endsWith('.md') && !fileName.endsWith('.markdown')) {
    fileName += '.md'
  }
  
  try {
    await fileStore.createFile(fileName)
    showNewFile.value = false
    ElMessage.success('File created')
  } catch (e) {
    ElMessage.error('Failed to create file')
  }
}

function toggleTheme() {
  const newTheme = isDarkTheme.value ? 'light' : 'dark'
  configStore.setTheme(newTheme)
  configStore.saveConfig()
}

// Resize handlers
let isResizing = false
let resizeType = ''

function startResize(e: MouseEvent) {
  isResizing = true
  resizeType = 'sidebar'
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
}

function startPreviewResize(e: MouseEvent) {
  isResizing = true
  resizeType = 'preview'
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
}

function handleResize(e: MouseEvent) {
  if (!isResizing) return
  
  if (resizeType === 'sidebar') {
    sidebarWidth.value = Math.max(150, Math.min(500, e.clientX))
  } else if (resizeType === 'preview') {
    // 允许预览区域完全自由调整宽度，最小100px，最大到窗口宽度-侧边栏-编辑器最小宽度
    const maxPreviewWidth = window.innerWidth - sidebarWidth.value - 200 // 200px 为编辑器最小宽度
    previewWidth.value = Math.max(100, Math.min(maxPreviewWidth, window.innerWidth - e.clientX))
  } else if (resizeType === 'toc') {
    // TOC sidebar resize
    const tocX = e.clientX - sidebarWidth.value - 5 // 5px for resize handle
    tocSidebarWidth.value = Math.max(150, Math.min(400, tocX))
  }
}

function stopResize() {
  isResizing = false
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
}

// Keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 's') {
    e.preventDefault()
    handleSave()
  }
}

// Lifecycle
onMounted(async () => {
  document.addEventListener('keydown', handleKeydown)
  loadRecentFolders()
  
  try {
    await configStore.loadConfig()
    // Load current root path
    const rootInfo = await fileStore.loadRootPath()
    if (rootInfo.exists) {
      folderPath.value = rootInfo.path
      await fileStore.loadDirectoryTree()
    }
  } catch (e) {
    console.error('Failed to initialize:', e)
  }
})
</script>

<style>
/* ========================================
   🌟 CYBERPUNK NEON DARK THEME 🌟
   ======================================== */

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  width: 100%;
}

/* CSS Variables for Neon Colors */
:root {
  --neon-cyan: #00f5ff;
  --neon-pink: #ff2d95;
  --neon-purple: #a855f7;
  --neon-blue: #3b82f6;
  --neon-green: #00ff88;
  --neon-orange: #ff6b35;
  --neon-yellow: #fbbf24;
  
  --bg-dark: #0a0a12;
  --bg-darker: #06060a;
  --bg-card: #0f0f1a;
  --bg-elevated: #141420;
  --bg-hover: #1a1a2e;
  
  --text-primary: #e8e8f0;
  --text-secondary: #a0a0b8;
  --text-muted: #606078;
  
  --border-color: #1e1e32;
  --border-glow: rgba(0, 245, 255, 0.4);
  
  --glow-cyan: 0 0 20px rgba(0, 245, 255, 0.5), 0 0 40px rgba(0, 245, 255, 0.2);
  --glow-pink: 0 0 20px rgba(255, 45, 149, 0.5), 0 0 40px rgba(255, 45, 149, 0.2);
  --glow-purple: 0 0 20px rgba(168, 85, 247, 0.5), 0 0 40px rgba(168, 85, 247, 0.2);
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: var(--bg-dark);
  color: var(--text-primary);
  font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Light theme */
.app-container:not(.dark-theme) {
  --bg-dark: #f8f9fc;
  --bg-darker: #eef0f5;
  --bg-card: #ffffff;
  --bg-elevated: #f0f2f8;
  --bg-hover: #e8eaf2;
  --text-primary: #1a1a2e;
  --text-secondary: #4a4a68;
  --text-muted: #8888a0;
  --border-color: #d8dae5;
  --neon-cyan: #0891b2;
  --neon-pink: #db2777;
  --neon-purple: #7c3aed;
}

/* ========================================
   HEADER - Neon Glow Bar
   ======================================== */
.header {
  height: 56px;
  background: var(--bg-card);
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-color);
  position: relative;
}

.header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    var(--neon-cyan) 25%, 
    var(--neon-pink) 50%, 
    var(--neon-purple) 75%, 
    transparent 100%
  );
  opacity: 0.6;
}

.header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    var(--neon-cyan) 20%, 
    var(--neon-pink) 50%, 
    var(--neon-purple) 80%, 
    transparent 100%
  );
  opacity: 0.8;
}

.dark-theme .header {
  box-shadow: 0 4px 30px rgba(0, 245, 255, 0.08);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h1 {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, var(--neon-cyan) 0%, var(--neon-pink) 50%, var(--neon-purple) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Neon Buttons */
.header-right .el-button-group .el-button,
.header-right .el-button {
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  transition: all 0.25s ease;
  font-weight: 500;
}

.header-right .el-button-group .el-button:hover,
.header-right .el-button:hover {
  background: var(--bg-hover);
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.2);
}

.header-right .el-button.is-circle {
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.header-right .el-button.is-circle:hover {
  border-color: var(--neon-pink);
  color: var(--neon-pink);
  box-shadow: 0 0 15px rgba(255, 45, 149, 0.3);
  transform: scale(1.08);
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  background: var(--bg-dark);
}

/* ========================================
   SIDEBAR - File Tree
   ======================================== */
.sidebar {
  min-width: 180px;
  max-width: 400px;
  border-right: 1px solid var(--border-color);
  overflow: auto;
  background: var(--bg-card);
  flex-shrink: 0;
  position: relative;
}

.sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(180deg, 
    var(--neon-cyan) 0%, 
    var(--neon-purple) 50%, 
    var(--neon-pink) 100%
  );
  opacity: 0.3;
}

.dark-theme .sidebar {
  background: var(--bg-card);
  border-color: var(--border-color);
}

.no-folder-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

/* ========================================
   RESIZE HANDLE - Neon Glow
   ======================================== */
.resize-handle {
  width: 6px;
  cursor: col-resize;
  background: transparent;
  flex-shrink: 0;
  transition: all 0.2s ease;
  position: relative;
}

.resize-handle::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 2px;
  height: 60px;
  background: var(--border-color);
  border-radius: 2px;
  opacity: 0.5;
  transition: all 0.2s ease;
}

.resize-handle:hover {
  background: rgba(0, 245, 255, 0.05);
}

.resize-handle:hover::before {
  opacity: 1;
  background: linear-gradient(180deg, var(--neon-cyan), var(--neon-pink));
  box-shadow: var(--glow-cyan);
  height: 80px;
}

/* ========================================
   EDITOR AREA
   ======================================== */
.editor-area {
  flex: 1;
  overflow: hidden;
  min-width: 200px;
  background: var(--bg-dark);
}

.dark-theme .editor-area {
  background: var(--bg-dark);
}

/* ========================================
   PREVIEW AREA
   ======================================== */
.preview-area {
  min-width: 100px;
  overflow: auto;
  border-left: 1px solid var(--border-color);
  flex-shrink: 0;
  background: var(--bg-card);
  position: relative;
}

.preview-area::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(180deg, 
    var(--neon-purple) 0%, 
    var(--neon-pink) 50%, 
    var(--neon-cyan) 100%
  );
  opacity: 0.3;
}

.dark-theme .preview-area {
  border-color: var(--border-color);
  background: var(--bg-card);
}

/* ========================================
   VIEW MODE
   ======================================== */
.content-area.view-mode {
  flex: 1;
  overflow: hidden;
  display: flex;
  background: var(--bg-dark);
}

.dark-theme .content-area.view-mode {
  background: var(--bg-dark);
}

.view-mode-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ========================================
   TOC SIDEBAR - Neon Navigation
   ======================================== */
.toc-sidebar {
  min-width: 150px;
  max-width: 400px;
  border-right: 1px solid var(--border-color);
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: relative;
}

.toc-sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(180deg, 
    var(--neon-purple) 0%, 
    var(--neon-cyan) 100%
  );
  opacity: 0.3;
}

.dark-theme .toc-sidebar {
  background: var(--bg-card);
  border-color: var(--border-color);
}

.toc-sidebar-header {
  padding: 16px 20px;
  font-size: 11px;
  font-weight: 700;
  color: var(--neon-cyan);
  text-transform: uppercase;
  letter-spacing: 2px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-elevated);
}

.dark-theme .toc-sidebar-header {
  color: var(--neon-cyan);
  border-color: var(--border-color);
  background: var(--bg-elevated);
  text-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
}

.toc-sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0;
}

.toc-nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc-nav-item {
  padding: 10px 20px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
  line-height: 1.5;
  position: relative;
}

.toc-nav-item:hover {
  background: var(--bg-hover);
  color: var(--neon-cyan);
  border-left-color: var(--neon-cyan);
}

.toc-nav-item.active {
  background: rgba(0, 245, 255, 0.1);
  color: var(--neon-cyan);
  border-left-color: var(--neon-cyan);
  font-weight: 600;
}

.dark-theme .toc-nav-item.active {
  text-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
}

/* TOC Level Indentation */
.toc-nav-item.toc-level-1 { 
  padding-left: 20px; 
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}
.toc-nav-item.toc-level-2 { padding-left: 32px; }
.toc-nav-item.toc-level-3 { 
  padding-left: 44px; 
  font-size: 12px;
}
.toc-nav-item.toc-level-4 { 
  padding-left: 56px; 
  font-size: 12px;
  color: var(--text-muted);
}
.toc-nav-item.toc-level-5,
.toc-nav-item.toc-level-6 { 
  padding-left: 68px; 
  font-size: 11px;
  color: var(--text-muted);
}

.toc-empty {
  padding: 24px 20px;
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
  font-style: italic;
}

.toc-resize {
  width: 6px;
}

.preview-full {
  flex: 1;
  overflow: auto;
  background: var(--bg-card);
}

.dark-theme .preview-full {
  background: var(--bg-card);
}

/* ========================================
   MODE TOGGLE - Neon Buttons
   ======================================== */
.mode-toggle {
  margin-left: 8px;
}

.mode-toggle .el-button {
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  transition: all 0.25s ease;
}

.mode-toggle .el-button:hover {
  border-color: var(--neon-purple);
  color: var(--neon-purple);
}

.mode-toggle .el-button.el-button--primary {
  background: linear-gradient(135deg, rgba(0, 245, 255, 0.2), rgba(168, 85, 247, 0.2));
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.dark-theme .mode-toggle .el-button.el-button--primary {
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.3);
}

/* ========================================
   MODE INDICATOR - Status Bar
   ======================================== */
.mode-indicator {
  padding: 3px 10px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: rgba(0, 245, 255, 0.15);
  color: var(--neon-cyan);
  border: 1px solid rgba(0, 245, 255, 0.3);
}

.mode-indicator.edit-mode {
  background: rgba(255, 45, 149, 0.15);
  color: var(--neon-pink);
  border-color: rgba(255, 45, 149, 0.3);
}

.dark-theme .mode-indicator {
  text-shadow: 0 0 8px rgba(0, 245, 255, 0.5);
}

.dark-theme .mode-indicator.edit-mode {
  text-shadow: 0 0 8px rgba(255, 45, 149, 0.5);
}

/* ========================================
   EMPTY STATE
   ======================================== */
.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-dark);
  position: relative;
}

.empty-state::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(0, 245, 255, 0.05) 0%, transparent 70%);
  pointer-events: none;
}

.dark-theme .empty-state {
  background: var(--bg-dark);
}

/* ========================================
   STATUS BAR - Neon Info Bar
   ======================================== */
.status-bar {
  height: 28px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 11px;
  color: var(--text-muted);
  gap: 24px;
  flex-shrink: 0;
  position: relative;
}

.status-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    var(--neon-purple) 25%, 
    var(--neon-pink) 50%, 
    var(--neon-cyan) 75%, 
    transparent 100%
  );
  opacity: 0.4;
}

.dark-theme .status-bar {
  background: var(--bg-card);
  border-color: var(--border-color);
  color: var(--text-muted);
}

.status-item {
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.folder-path {
  color: var(--neon-purple);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.dark-theme .folder-path {
  color: var(--neon-purple);
  text-shadow: 0 0 8px rgba(168, 85, 247, 0.4);
}

.status-saved { 
  color: var(--neon-green);
  font-weight: 600;
}
.status-unsaved { 
  color: var(--neon-orange);
  font-weight: 600;
}
.status-saving { 
  color: var(--neon-cyan);
  font-weight: 600;
}
.status-error { 
  color: var(--neon-pink);
  font-weight: 600;
}

.dark-theme .status-saved { text-shadow: 0 0 8px rgba(0, 255, 136, 0.5); }
.dark-theme .status-unsaved { text-shadow: 0 0 8px rgba(255, 107, 53, 0.5); }
.dark-theme .status-saving { text-shadow: 0 0 8px rgba(0, 245, 255, 0.5); }
.dark-theme .status-error { text-shadow: 0 0 8px rgba(255, 45, 149, 0.5); }

/* Folder Select Dialog */
.folder-select-content {
  padding: 0 10px;
}

.folder-hint {
  background: #f0f9ff;
  padding: 14px 16px;
  border-radius: 8px;
  font-size: 13px;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

.folder-hint p {
  margin: 0 0 8px 0;
  line-height: 1.5;
}

.folder-hint p:last-child {
  margin-bottom: 0;
}

.hint-examples {
  font-size: 12px;
  color: #3b82f6;
}

.hint-examples code {
  background: #dbeafe;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 11px;
}

.recent-folders {
  margin-top: 20px;
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.recent-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.recent-folder-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #4b5563;
  transition: all 0.15s ease;
  margin-bottom: 4px;
}

.recent-folder-item:hover {
  background: #eff6ff;
  color: #2563eb;
}

.recent-folder-item:active {
  background: #dbeafe;
}

/* Dark theme dialogs */
.dark-theme .folder-hint {
  background: #1e3a5f;
  color: #93c5fd;
  border-color: #1e40af;
}

.dark-theme .hint-examples {
  color: #60a5fa;
}

.dark-theme .hint-examples code {
  background: #1e40af;
  color: #bfdbfe;
}

.dark-theme .recent-folders {
  border-color: #374151;
}

.dark-theme .recent-title {
  color: #e5e7eb;
}

.dark-theme .recent-folder-item {
  color: #9ca3af;
}

.dark-theme .recent-folder-item:hover {
  background: #1e3a5f;
  color: #60a5fa;
}

.dark-theme .recent-folder-item:active {
  background: #1e40af;
}

/* Scrollbar Styling - Neon */
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-track {
  background: var(--bg-darker);
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, var(--neon-cyan), var(--neon-purple));
  border-radius: 5px;
  border: 2px solid var(--bg-darker);
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, var(--neon-pink), var(--neon-cyan));
}

/* ========================================
   ELEMENT PLUS OVERRIDES - CYBERPUNK
   ======================================== */
.el-button {
  transition: all 0.3s ease;
}

.el-dialog {
  border-radius: 16px;
  overflow: hidden;
  background: var(--bg-card);
  border: 1px solid rgba(0, 245, 255, 0.2);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(0, 245, 255, 0.1);
}

.dark-theme .el-dialog {
  background: var(--bg-card);
}

.dark-theme .el-dialog__header {
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-color);
  position: relative;
}

.dark-theme .el-dialog__header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 20px;
  right: 20px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--neon-cyan), var(--neon-pink), transparent);
  opacity: 0.5;
}

.dark-theme .el-dialog__title {
  color: var(--neon-cyan);
  font-weight: 700;
  text-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
}

.dark-theme .el-dialog__body {
  background: var(--bg-card);
  color: var(--text-primary);
}

.dark-theme .el-dialog__footer {
  background: var(--bg-elevated);
  border-top: 1px solid var(--border-color);
}

/* Input Overrides */
.dark-theme .el-input__wrapper {
  background: rgba(0, 245, 255, 0.05);
  border: 1px solid rgba(0, 245, 255, 0.2);
  box-shadow: none;
  transition: all 0.3s ease;
}

.dark-theme .el-input__wrapper:hover,
.dark-theme .el-input__wrapper.is-focus {
  border-color: var(--neon-cyan);
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.2);
}

.dark-theme .el-input__inner {
  color: var(--text-primary);
}

.dark-theme .el-input__inner::placeholder {
  color: var(--text-muted);
}

/* Select Dropdown */
.dark-theme .el-select-dropdown {
  background: var(--bg-card);
  border: 1px solid rgba(0, 245, 255, 0.2);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
}

.dark-theme .el-select-dropdown__item {
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.dark-theme .el-select-dropdown__item:hover {
  background: rgba(0, 245, 255, 0.1);
  color: var(--neon-cyan);
}

.dark-theme .el-select-dropdown__item.selected {
  color: var(--neon-cyan);
  font-weight: 600;
}

/* Message Box */
.dark-theme .el-message-box {
  background: var(--bg-card);
  border: 1px solid rgba(0, 245, 255, 0.2);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.dark-theme .el-message-box__title {
  color: var(--neon-cyan);
}

.dark-theme .el-message-box__content {
  color: var(--text-primary);
}

/* Tooltip */
.el-tooltip__trigger {
  outline: none;
}

.dark-theme .el-popper.is-dark {
  background: var(--bg-elevated);
  border: 1px solid rgba(0, 245, 255, 0.2);
  color: var(--text-primary);
}

/* Switch */
.dark-theme .el-switch__core {
  background: rgba(0, 245, 255, 0.1);
  border-color: rgba(0, 245, 255, 0.2);
}

.dark-theme .el-switch.is-checked .el-switch__core {
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-blue));
  border-color: var(--neon-cyan);
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.4);
}

/* Tabs */
.dark-theme .el-tabs__item {
  color: var(--text-muted);
  transition: all 0.3s ease;
}

.dark-theme .el-tabs__item:hover {
  color: var(--neon-cyan);
}

.dark-theme .el-tabs__item.is-active {
  color: var(--neon-cyan);
  text-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
}

.dark-theme .el-tabs__active-bar {
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-pink));
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.5);
}

.dark-theme .el-tabs__nav-wrap::after {
  background: var(--border-color);
}

/* Empty State */
.dark-theme .el-empty__description {
  color: var(--text-muted);
}
</style>
