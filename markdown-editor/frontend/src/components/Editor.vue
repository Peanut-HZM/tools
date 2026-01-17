<template>
  <div class="editor-container">
    <div class="editor-toolbar">
      <el-button-group class="toolbar-group">
        <el-tooltip content="Bold (Ctrl+B)" :show-after="500">
          <el-button size="small" @click="insertMarkdown('bold')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/><path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/>
            </svg>
          </el-button>
        </el-tooltip>
        <el-tooltip content="Italic (Ctrl+I)" :show-after="500">
          <el-button size="small" @click="insertMarkdown('italic')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="4" x2="10" y2="4"/><line x1="14" y1="20" x2="5" y2="20"/><line x1="15" y1="4" x2="9" y2="20"/>
            </svg>
          </el-button>
        </el-tooltip>
        <el-tooltip content="Heading" :show-after="500">
          <el-button size="small" @click="insertMarkdown('heading')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 12h8"/><path d="M4 18V6"/><path d="M12 18V6"/><path d="m17 12 3-2v8"/>
            </svg>
          </el-button>
        </el-tooltip>
      </el-button-group>
      
      <div class="toolbar-divider"></div>
      
      <el-button-group class="toolbar-group">
        <el-tooltip content="Link" :show-after="500">
          <el-button size="small" @click="insertMarkdown('link')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
          </el-button>
        </el-tooltip>
        <el-tooltip content="Image" :show-after="500">
          <el-button size="small" @click="insertMarkdown('image')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
            </svg>
          </el-button>
        </el-tooltip>
      </el-button-group>
      
      <div class="toolbar-divider"></div>
      
      <el-button-group class="toolbar-group">
        <el-tooltip content="Code Block" :show-after="500">
          <el-button size="small" @click="insertMarkdown('code')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
          </el-button>
        </el-tooltip>
        <el-tooltip content="Bullet List" :show-after="500">
          <el-button size="small" @click="insertMarkdown('list')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
              <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
            </svg>
          </el-button>
        </el-tooltip>
        <el-tooltip content="Numbered List" :show-after="500">
          <el-button size="small" @click="insertMarkdown('orderedList')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="10" y1="6" x2="21" y2="6"/><line x1="10" y1="12" x2="21" y2="12"/><line x1="10" y1="18" x2="21" y2="18"/>
              <path d="M4 6h1v4"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/>
            </svg>
          </el-button>
        </el-tooltip>
      </el-button-group>
      
      <div class="toolbar-divider"></div>
      
      <el-button-group class="toolbar-group">
        <el-tooltip content="Quote" :show-after="500">
          <el-button size="small" @click="insertMarkdown('quote')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V21z"/>
              <path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3z"/>
            </svg>
          </el-button>
        </el-tooltip>
        <el-tooltip content="Table" :show-after="500">
          <el-button size="small" @click="insertMarkdown('table')" class="toolbar-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/>
            </svg>
          </el-button>
        </el-tooltip>
      </el-button-group>
    </div>
    <div ref="editorContainer" class="monaco-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { useConfigStore, useEditorStore } from '@/stores'

const props = defineProps<{
  content: string
}>()

const emit = defineEmits<{
  (e: 'update:content', content: string): void
  (e: 'save'): void
}>()

const configStore = useConfigStore()
const editorStore = useEditorStore()

const editorContainer = ref<HTMLElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null

// Markdown syntax templates
const markdownTemplates: Record<string, { prefix: string; suffix: string; placeholder?: string }> = {
  bold: { prefix: '**', suffix: '**', placeholder: 'bold text' },
  italic: { prefix: '_', suffix: '_', placeholder: 'italic text' },
  heading: { prefix: '## ', suffix: '', placeholder: 'Heading' },
  link: { prefix: '[', suffix: '](url)', placeholder: 'link text' },
  image: { prefix: '![', suffix: '](image-url)', placeholder: 'alt text' },
  code: { prefix: '```\n', suffix: '\n```', placeholder: 'code' },
  list: { prefix: '- ', suffix: '', placeholder: 'list item' },
  orderedList: { prefix: '1. ', suffix: '', placeholder: 'list item' },
  quote: { prefix: '> ', suffix: '', placeholder: 'quote' },
  table: { 
    prefix: '| Header 1 | Header 2 |\n| --- | --- |\n| ', 
    suffix: ' | Cell 2 |', 
    placeholder: 'Cell 1' 
  }
}

function insertMarkdown(type: string) {
  if (!editor) return
  
  const template = markdownTemplates[type]
  if (!template) return
  
  const selection = editor.getSelection()
  if (!selection) return
  
  const selectedText = editor.getModel()?.getValueInRange(selection) || ''
  const textToInsert = selectedText || template.placeholder || ''
  const newText = template.prefix + textToInsert + template.suffix
  
  editor.executeEdits('insert-markdown', [{
    range: selection,
    text: newText,
    forceMoveMarkers: true
  }])
  
  // Select the placeholder if no text was selected
  if (!selectedText && template.placeholder) {
    const startPos = selection.getStartPosition()
    const prefixLines = template.prefix.split('\n')
    const lastPrefixLine = prefixLines[prefixLines.length - 1]
    
    const newStartLine = startPos.lineNumber + prefixLines.length - 1
    const newStartCol = prefixLines.length > 1 
      ? lastPrefixLine.length + 1 
      : startPos.column + template.prefix.length
    
    editor.setSelection({
      startLineNumber: newStartLine,
      startColumn: newStartCol,
      endLineNumber: newStartLine,
      endColumn: newStartCol + template.placeholder.length
    })
  }
  
  editor.focus()
}

function initEditor() {
  if (!editorContainer.value) return
  
  // Configure Monaco for Markdown
  monaco.languages.register({ id: 'markdown' })
  
  editor = monaco.editor.create(editorContainer.value, {
    value: props.content,
    language: 'markdown',
    theme: configStore.config.theme === 'dark' ? 'vs-dark' : 'vs',
    fontSize: configStore.config.fontSize,
    lineNumbers: configStore.config.showLineNumbers ? 'on' : 'off',
    tabSize: configStore.config.tabSize,
    insertSpaces: configStore.config.useSpaces,
    wordWrap: 'on',
    minimap: { enabled: false },
    automaticLayout: true,
    scrollBeyondLastLine: false,
    renderWhitespace: 'selection',
    quickSuggestions: true,
    suggestOnTriggerCharacters: true
  })
  
  // Listen for content changes
  editor.onDidChangeModelContent(() => {
    const value = editor?.getValue() || ''
    emit('update:content', value)
  })
  
  // Listen for cursor position changes
  editor.onDidChangeCursorPosition((e) => {
    editorStore.setCursorPosition(e.position.lineNumber, e.position.column)
  })
  
  // Add keyboard shortcuts
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    emit('save')
  })
  
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyB, () => {
    insertMarkdown('bold')
  })
  
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyI, () => {
    insertMarkdown('italic')
  })
}

// Watch for content prop changes
watch(() => props.content, (newContent) => {
  if (editor && editor.getValue() !== newContent) {
    editor.setValue(newContent)
  }
})

// Watch for theme changes
watch(() => configStore.config.theme, (theme) => {
  if (editor) {
    monaco.editor.setTheme(theme === 'dark' ? 'vs-dark' : 'vs')
  }
})

// Watch for font size changes
watch(() => configStore.config.fontSize, (fontSize) => {
  if (editor) {
    editor.updateOptions({ fontSize })
  }
})

onMounted(() => {
  initEditor()
})

onUnmounted(() => {
  editor?.dispose()
})
</script>

<style scoped>
/* ========================================
   CYBERPUNK EDITOR STYLES
   ======================================== */
.editor-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0d0d14;
  position: relative;
}

.editor-toolbar {
  padding: 10px 16px;
  border-bottom: 1px solid #1a1a2e;
  background: #12121a;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
}

.editor-toolbar::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    #00f5ff 30%, 
    #ff00ff 70%, 
    transparent 100%
  );
  opacity: 0.5;
}

.toolbar-group {
  display: flex;
  gap: 4px;
}

.toolbar-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0, 245, 255, 0.2);
  background: rgba(0, 245, 255, 0.05);
  color: #00f5ff;
  transition: all 0.3s ease;
  border-radius: 8px;
  position: relative;
  backdrop-filter: blur(10px);
}

.toolbar-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 8px;
  background: linear-gradient(45deg, #00f5ff, #ff00ff);
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: -1;
}

.toolbar-btn:hover {
  background: rgba(0, 245, 255, 0.15);
  border-color: #00f5ff;
  color: #00f5ff;
  box-shadow: 0 0 20px rgba(0, 245, 255, 0.3);
  transform: translateY(-2px);
}

.toolbar-btn:hover::before {
  opacity: 0.1;
}

.toolbar-btn:active {
  transform: translateY(0);
  box-shadow: 0 0 25px rgba(0, 245, 255, 0.4);
}

.toolbar-btn svg {
  width: 18px;
  height: 18px;
  filter: drop-shadow(0 0 5px currentColor);
}

.toolbar-divider {
  width: 2px;
  height: 28px;
  background: linear-gradient(180deg, 
    transparent 0%, 
    #ff00ff 50%, 
    transparent 100%
  );
  margin: 0 12px;
  border-radius: 1px;
  opacity: 0.6;
}

.monaco-container {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.monaco-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 80% 20%, rgba(0, 245, 255, 0.02) 0%, transparent 50%);
  pointer-events: none;
  z-index: 1;
}
</style>
