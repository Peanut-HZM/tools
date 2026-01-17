<template>
  <div class="file-tree">
    <div class="tree-header">
      <el-input
        v-model="searchQuery"
        placeholder="Search files..."
        size="small"
        clearable
        :prefix-icon="Search"
      />
    </div>
    
    <div class="tree-content">
      <el-tree
        ref="treeRef"
        :data="filteredTreeData"
        :props="treeProps"
        node-key="path"
        :default-expanded-keys="expandedKeys"
        :filter-node-method="filterNode"
        highlight-current
        @node-click="handleNodeClick"
        @node-contextmenu="handleContextMenu"
      >
        <template #default="{ node, data }">
          <div class="tree-node" @mouseenter="hoveredNode = data" @mouseleave="hoveredNode = null">
            <el-icon class="node-icon">
              <Folder v-if="data.type === 'directory'" />
              <Document v-else />
            </el-icon>
            <span class="node-label" :class="{ 'highlight': isHighlighted(data.name) }">
              {{ data.name }}
            </span>
            <el-tooltip
              v-if="data.type === 'file' && hoveredNode === data"
              :content="getFileInfo(data)"
              placement="right"
            >
              <el-icon class="info-icon"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
        </template>
      </el-tree>
    </div>

    <!-- Context Menu -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
    >
      <div class="menu-item" @click="handleNewFile">
        <el-icon><Plus /></el-icon>
        New File
      </div>
      <div class="menu-item" @click="handleNewFolder">
        <el-icon><FolderAdd /></el-icon>
        New Folder
      </div>
      <div class="menu-item" @click="handleRename" v-if="contextMenu.node">
        <el-icon><Edit /></el-icon>
        Rename
      </div>
      <div class="menu-item danger" @click="handleDelete" v-if="contextMenu.node">
        <el-icon><Delete /></el-icon>
        Delete
      </div>
    </div>

    <!-- Rename Dialog -->
    <el-dialog v-model="renameDialog.visible" title="Rename" width="400px">
      <el-input v-model="renameDialog.newName" placeholder="New name" />
      <template #footer>
        <el-button @click="renameDialog.visible = false">Cancel</el-button>
        <el-button type="primary" @click="confirmRename">Rename</el-button>
      </template>
    </el-dialog>

    <!-- New File/Folder Dialog -->
    <el-dialog v-model="createDialog.visible" :title="createDialog.isFolder ? 'New Folder' : 'New File'" width="400px">
      <el-input v-model="createDialog.name" :placeholder="createDialog.isFolder ? 'Folder name' : 'File name'" />
      <template #footer>
        <el-button @click="createDialog.visible = false">Cancel</el-button>
        <el-button type="primary" @click="confirmCreate">Create</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Search, Folder, Document, InfoFilled, Plus, FolderAdd, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FileNode } from '@/types'
import { useFileStore } from '@/stores'

const emit = defineEmits<{
  (e: 'select', path: string): void
}>()

const fileStore = useFileStore()
const treeRef = ref()

// State
const searchQuery = ref('')
const hoveredNode = ref<FileNode | null>(null)
const expandedKeys = ref<string[]>([])

// Context menu state
const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  node: null as FileNode | null
})

// Rename dialog state
const renameDialog = ref({
  visible: false,
  node: null as FileNode | null,
  newName: ''
})

// Create dialog state
const createDialog = ref({
  visible: false,
  isFolder: false,
  parentPath: '',
  name: ''
})

// Tree props
const treeProps = {
  children: 'children',
  label: 'name'
}

// Computed
const filteredTreeData = computed(() => {
  if (!fileStore.directoryTree) return []
  return fileStore.directoryTree.children || []
})

// Methods
function filterNode(value: string, data: FileNode) {
  if (!value) return true
  return data.name.toLowerCase().includes(value.toLowerCase())
}

function isHighlighted(name: string) {
  if (!searchQuery.value) return false
  return name.toLowerCase().includes(searchQuery.value.toLowerCase())
}

function handleNodeClick(data: FileNode) {
  if (data.type === 'file') {
    emit('select', data.path)
  }
}

function getFileInfo(data: FileNode) {
  const size = data.size ? formatFileSize(data.size) : 'Unknown'
  const modified = data.modified ? new Date(data.modified).toLocaleString() : 'Unknown'
  return `Size: ${size}\nModified: ${modified}`
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function handleContextMenu(event: MouseEvent, data: FileNode) {
  event.preventDefault()
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    node: data
  }
}

function closeContextMenu() {
  contextMenu.value.visible = false
}

function handleNewFile() {
  const parentPath = contextMenu.value.node?.type === 'directory' 
    ? contextMenu.value.node.path 
    : ''
  createDialog.value = {
    visible: true,
    isFolder: false,
    parentPath,
    name: ''
  }
  closeContextMenu()
}

function handleNewFolder() {
  const parentPath = contextMenu.value.node?.type === 'directory'
    ? contextMenu.value.node.path
    : ''
  createDialog.value = {
    visible: true,
    isFolder: true,
    parentPath,
    name: ''
  }
  closeContextMenu()
}

function handleRename() {
  if (!contextMenu.value.node) return
  renameDialog.value = {
    visible: true,
    node: contextMenu.value.node,
    newName: contextMenu.value.node.name
  }
  closeContextMenu()
}

async function handleDelete() {
  if (!contextMenu.value.node) return
  const node = contextMenu.value.node
  closeContextMenu()

  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete "${node.name}"?`,
      'Confirm Delete',
      { type: 'warning' }
    )

    if (node.type === 'file') {
      await fileStore.deleteFile(node.path)
    } else {
      // For directories, we need to handle recursive delete
      await fileStore.deleteFile(node.path)
    }
    ElMessage.success('Deleted successfully')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('Failed to delete')
    }
  }
}

async function confirmRename() {
  if (!renameDialog.value.node || !renameDialog.value.newName) return

  const oldPath = renameDialog.value.node.path
  const pathParts = oldPath.split('/')
  pathParts[pathParts.length - 1] = renameDialog.value.newName
  const newPath = pathParts.join('/')

  try {
    await fileStore.renameFile(oldPath, newPath)
    renameDialog.value.visible = false
    ElMessage.success('Renamed successfully')
  } catch (e) {
    ElMessage.error('Failed to rename')
  }
}

async function confirmCreate() {
  if (!createDialog.value.name) {
    ElMessage.warning('Please enter a name')
    return
  }

  let name = createDialog.value.name
  const parentPath = createDialog.value.parentPath

  if (!createDialog.value.isFolder && !name.endsWith('.md') && !name.endsWith('.markdown')) {
    name += '.md'
  }

  const fullPath = parentPath ? `${parentPath}/${name}` : name

  try {
    if (createDialog.value.isFolder) {
      // Create directory via API
      const { fileApi } = await import('@/api/fileApi')
      await fileApi.createDirectory(fullPath)
      await fileStore.loadDirectoryTree()
    } else {
      await fileStore.createFile(fullPath)
    }
    createDialog.value.visible = false
    ElMessage.success('Created successfully')
  } catch (e) {
    ElMessage.error('Failed to create')
  }
}

// Watch for search query changes
watch(searchQuery, (val) => {
  treeRef.value?.filter(val)
})

// Close context menu on click outside
function handleClickOutside(e: MouseEvent) {
  if (contextMenu.value.visible) {
    closeContextMenu()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
/* ========================================
   CYBERPUNK FILE TREE STYLES
   ======================================== */
.file-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0d0d14;
}

.tree-header {
  padding: 14px;
  border-bottom: 1px solid #1a1a2e;
  background: #12121a;
  position: relative;
}

.tree-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 14px;
  right: 14px;
  height: 1px;
  background: linear-gradient(90deg, transparent, #00f5ff, transparent);
  opacity: 0.4;
}

.tree-header :deep(.el-input__wrapper) {
  border-radius: 8px;
  background: rgba(0, 245, 255, 0.05);
  border: 1px solid rgba(0, 245, 255, 0.2);
  box-shadow: none;
  transition: all 0.3s ease;
}

.tree-header :deep(.el-input__wrapper:hover),
.tree-header :deep(.el-input__wrapper.is-focus) {
  border-color: #00f5ff;
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.2);
}

.tree-header :deep(.el-input__inner) {
  color: #e0e0e8;
}

.tree-header :deep(.el-input__inner::placeholder) {
  color: #666680;
}

.tree-header :deep(.el-input__prefix) {
  color: #00f5ff;
}

.tree-content {
  flex: 1;
  overflow: auto;
  padding: 10px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.tree-node::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 0;
  background: linear-gradient(180deg, #00f5ff, #bf00ff);
  border-radius: 6px 0 0 6px;
  transition: width 0.3s ease;
}

.tree-node:hover {
  background: rgba(0, 245, 255, 0.08);
}

.tree-node:hover::before {
  width: 3px;
}

.node-icon {
  flex-shrink: 0;
  color: #666680;
  font-size: 15px;
  transition: all 0.3s ease;
}

.tree-node:hover .node-icon {
  color: #00f5ff;
  filter: drop-shadow(0 0 5px currentColor);
}

.node-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #a0a0b8;
  font-weight: 500;
  transition: all 0.3s ease;
}

.tree-node:hover .node-label {
  color: #e0e0e8;
}

.node-label.highlight {
  background: linear-gradient(120deg, rgba(255, 0, 255, 0.2), rgba(0, 245, 255, 0.2));
  padding: 2px 6px;
  border-radius: 4px;
  color: #00f5ff;
  text-shadow: 0 0 8px currentColor;
}

.info-icon {
  color: #666680;
  font-size: 12px;
  opacity: 0;
  transition: all 0.3s ease;
}

.tree-node:hover .info-icon {
  opacity: 1;
  color: #bf00ff;
}

/* ========================================
   CYBERPUNK CONTEXT MENU
   ======================================== */
.context-menu {
  position: fixed;
  background: #12121a;
  border: 1px solid rgba(0, 245, 255, 0.3);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), 0 0 30px rgba(0, 245, 255, 0.1);
  z-index: 1000;
  min-width: 180px;
  padding: 8px;
  animation: contextMenuFadeIn 0.2s ease;
  backdrop-filter: blur(20px);
}

@keyframes contextMenuFadeIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.menu-item {
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  font-size: 13px;
  border-radius: 8px;
  color: #a0a0b8;
  transition: all 0.3s ease;
  font-weight: 500;
  position: relative;
}

.menu-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 60%;
  background: #00f5ff;
  border-radius: 0 2px 2px 0;
  transition: width 0.3s ease;
}

.menu-item:hover {
  background: rgba(0, 245, 255, 0.1);
  color: #00f5ff;
  text-shadow: 0 0 10px currentColor;
}

.menu-item:hover::before {
  width: 3px;
}

.menu-item:hover .el-icon {
  filter: drop-shadow(0 0 5px currentColor);
}

.menu-item.danger {
  color: #ff4466;
}

.menu-item.danger:hover {
  background: rgba(255, 68, 102, 0.1);
  color: #ff4466;
}

.menu-item.danger::before {
  background: #ff4466;
}

/* ========================================
   ELEMENT PLUS TREE OVERRIDES - CYBERPUNK
   ======================================== */
:deep(.el-tree) {
  background: transparent;
  --el-tree-node-hover-bg-color: transparent;
}

:deep(.el-tree-node__content) {
  height: 36px;
  border-radius: 8px;
  transition: all 0.3s ease;
  background: transparent;
}

:deep(.el-tree-node__content:hover) {
  background: rgba(0, 245, 255, 0.05);
}

:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: rgba(0, 245, 255, 0.1);
  border: 1px solid rgba(0, 245, 255, 0.2);
}

:deep(.el-tree-node.is-current > .el-tree-node__content .node-label) {
  color: #00f5ff;
  text-shadow: 0 0 10px currentColor;
}

:deep(.el-tree-node.is-current > .el-tree-node__content .node-icon) {
  color: #00f5ff;
  filter: drop-shadow(0 0 5px currentColor);
}

:deep(.el-tree-node__expand-icon) {
  color: #666680;
  transition: all 0.3s ease;
}

:deep(.el-tree-node__expand-icon:hover) {
  color: #00f5ff;
}

:deep(.el-tree-node__expand-icon.expanded) {
  color: #bf00ff;
}

/* Dialog Overrides */
:deep(.el-dialog) {
  background: #12121a;
  border: 1px solid rgba(0, 245, 255, 0.2);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(0, 245, 255, 0.1);
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid #1a1a2e;
}

:deep(.el-dialog__title) {
  color: #00f5ff;
  text-shadow: 0 0 10px currentColor;
}

:deep(.el-dialog__body) {
  color: #e0e0e8;
}
</style>
