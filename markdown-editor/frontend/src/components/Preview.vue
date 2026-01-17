<template>
  <div class="preview-container" :class="{ 'full-mode': !showHeader }">
    <div class="preview-header" v-if="showHeader">
      <span>Preview</span>
      <el-switch
        v-model="showToc"
        size="small"
        active-text="TOC"
      />
    </div>
    
    <div class="preview-content" :class="{ 'no-header': !showHeader }">
      <!-- 只在编辑模式（有header）时显示内嵌TOC -->
      <div v-if="showHeader && showToc && toc.length > 0" class="toc-container">
        <div class="toc-title">Table of Contents</div>
        <ul class="toc-list">
          <li
            v-for="item in toc"
            :key="item.id"
            :class="'toc-level-' + item.level"
          >
            <a :href="'#' + item.id" @click.prevent="scrollToHeading(item.id)">
              {{ item.text }}
            </a>
          </li>
        </ul>
      </div>
      
      <div
        ref="previewRef"
        class="markdown-body"
        v-html="renderedContent"
      ></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import DOMPurify from 'dompurify'

const props = withDefaults(defineProps<{
  content: string
  showHeader?: boolean
}>(), {
  showHeader: true
})

const emit = defineEmits<{
  (e: 'toc-update', toc: TocItem[]): void
}>()

const previewRef = ref<HTMLElement | null>(null)
const showToc = ref(true)

interface TocItem {
  id: string
  text: string
  level: number
}

const toc = ref<TocItem[]>([])

// Initialize markdown-it with plugins
const md = new MarkdownIt({
  html: false, // Disable HTML for security
  linkify: true,
  typographer: true,
  highlight: function (str: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
          hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
          '</code></pre>'
      } catch (__) {}
    }
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>'
  }
})

// Add heading IDs for TOC
const defaultRender = md.renderer.rules.heading_open || function(tokens: any, idx: any, options: any, env: any, self: any) {
  return self.renderToken(tokens, idx, options)
}

md.renderer.rules.heading_open = function (tokens: any, idx: any, options: any, env: any, self: any) {
  const token = tokens[idx]
  const nextToken = tokens[idx + 1]
  if (nextToken && nextToken.type === 'inline') {
    const text = nextToken.content
    const id = text.toLowerCase().replace(/[^\w]+/g, '-')
    token.attrSet('id', id)
  }
  return defaultRender(tokens, idx, options, env, self)
}

// Extract TOC from content
function extractToc(content: string): TocItem[] {
  const items: TocItem[] = []
  const headingRegex = /^(#{1,6})\s+(.+)$/gm
  let match
  
  while ((match = headingRegex.exec(content)) !== null) {
    const level = match[1].length
    const text = match[2].trim()
    const id = text.toLowerCase().replace(/[^\w]+/g, '-')
    items.push({ id, text, level })
  }
  
  return items
}

// Render markdown with sanitization
const renderedContent = computed(() => {
  if (!props.content) return ''
  
  // Extract TOC
  const extractedToc = extractToc(props.content)
  toc.value = extractedToc
  
  // Emit TOC update for parent component
  emit('toc-update', extractedToc)
  
  // Render markdown
  const html = md.render(props.content)
  
  // Sanitize HTML to prevent XSS
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'ul', 'ol', 'li',
      'blockquote', 'pre', 'code',
      'a', 'img',
      'strong', 'em', 'del', 's',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'div', 'span',
      'input' // For task lists
    ],
    ALLOWED_ATTR: [
      'href', 'src', 'alt', 'title', 'class', 'id',
      'type', 'checked', 'disabled'
    ]
  })
})

function scrollToHeading(id: string) {
  const element = previewRef.value?.querySelector(`#${id}`)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}

// Handle checkbox clicks for task lists
function handleCheckboxClick(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.type === 'checkbox') {
    // Prevent default to keep it read-only in preview
    e.preventDefault()
  }
}

onMounted(() => {
  previewRef.value?.addEventListener('click', handleCheckboxClick)
})
</script>

<style scoped>
/* ========================================
   CYBERPUNK PREVIEW CONTAINER
   ======================================== */
.preview-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0d0d14;
  position: relative;
}

.preview-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 70% 30%, rgba(191, 0, 255, 0.03) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}

.preview-header {
  padding: 12px 20px;
  border-bottom: 1px solid #1a1a2e;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  color: #bf00ff;
  flex-shrink: 0;
  background: #12121a;
  text-transform: uppercase;
  letter-spacing: 2px;
  position: relative;
  z-index: 2;
  text-shadow: 0 0 10px currentColor;
}

.preview-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 20px;
  right: 20px;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    #bf00ff 50%, 
    transparent 100%
  );
  opacity: 0.6;
}

.preview-content {
  flex: 1;
  overflow: auto;
  padding: 24px 28px;
  position: relative;
  z-index: 1;
}

/* 查看模式下的内容区域 */
.preview-content.no-header {
  padding: 32px 40px;
  width: 100%;
  max-width: none;
  margin: 0;
}

.preview-container.full-mode {
  background: #0a0a0f;
}

.preview-container.full-mode .preview-content {
  padding: 32px 48px;
  width: 100%;
  max-width: none;
}

/* ========================================
   CYBERPUNK TOC CONTAINER
   ======================================== */
.toc-container {
  background: rgba(0, 245, 255, 0.05);
  border: 1px solid rgba(0, 245, 255, 0.2);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 28px;
  position: relative;
  backdrop-filter: blur(10px);
}

.toc-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 12px;
  background: linear-gradient(135deg, 
    rgba(0, 245, 255, 0.1) 0%, 
    transparent 50%, 
    rgba(255, 0, 255, 0.1) 100%
  );
  pointer-events: none;
}

.toc-title {
  font-weight: 800;
  margin-bottom: 16px;
  color: #00f5ff;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 0 0 10px currentColor;
  position: relative;
  padding-bottom: 10px;
}

.toc-title::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 60px;
  height: 2px;
  background: linear-gradient(90deg, #00f5ff, transparent);
}

.toc-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc-list li {
  margin: 8px 0;
}

.toc-list a {
  color: #8888a0;
  text-decoration: none;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: inline-block;
  padding: 4px 0;
  position: relative;
}

.toc-list a:hover {
  color: #00f5ff;
  transform: translateX(8px);
  text-shadow: 0 0 10px currentColor;
}

.toc-level-1 { padding-left: 0; font-weight: 700; }
.toc-level-1 a { color: #00f5ff; }
.toc-level-2 { padding-left: 16px; }
.toc-level-2 a { color: #00a8ff; }
.toc-level-3 { padding-left: 32px; font-size: 13px; }
.toc-level-3 a { color: #bf00ff; }
.toc-level-4 { padding-left: 48px; font-size: 13px; }
.toc-level-4 a { color: #ff00ff; }
.toc-level-5 { padding-left: 64px; font-size: 12px; }
.toc-level-5 a { color: #39ff14; }
.toc-level-6 { padding-left: 80px; font-size: 12px; }
.toc-level-6 a { color: #ff6600; }
</style>

<!-- Unscoped styles for v-html rendered content - CYBERPUNK NEON THEME -->
<style>
/* ========================================
   CYBERPUNK MARKDOWN BODY STYLES
   ======================================== */
.markdown-body {
  font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 16px;
  line-height: 1.8;
  color: #e0e0e8;
  word-wrap: break-word;
}

.markdown-body > *:first-child {
  margin-top: 0 !important;
}

.markdown-body > *:last-child {
  margin-bottom: 0 !important;
}

/* ========================================
   NEON HEADINGS
   ======================================== */
.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4,
.markdown-body h5,
.markdown-body h6 {
  margin-top: 32px;
  margin-bottom: 20px;
  font-weight: 800;
  line-height: 1.2;
  color: #f3f4f6;
  position: relative;
}

.markdown-body h1 { 
  font-size: 2.2em; 
  background: linear-gradient(45deg, #00f5ff, #ff00ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  border-bottom: 2px solid transparent;
  border-image: linear-gradient(90deg, #00f5ff, #ff00ff, transparent) 1;
  padding-bottom: 0.5em;
}

.markdown-body h2 { 
  font-size: 1.7em; 
  color: #00f5ff;
  border-bottom: 1px solid rgba(0, 245, 255, 0.3);
  padding-bottom: 0.4em;
  text-shadow: 0 0 20px currentColor;
}

.markdown-body h3 { 
  font-size: 1.4em; 
  color: #bf00ff;
  text-shadow: 0 0 15px currentColor;
}

.markdown-body h4 { 
  font-size: 1.15em; 
  color: #ff00ff;
  text-shadow: 0 0 10px currentColor;
}

.markdown-body h5 { 
  font-size: 1em; 
  color: #00a8ff;
  text-shadow: 0 0 8px currentColor;
}

.markdown-body h6 { 
  font-size: 0.9em; 
  color: #8888a0;
}

.markdown-body p {
  margin-top: 0;
  margin-bottom: 18px;
  color: #c0c0d0;
}

/* ========================================
   NEON LINKS
   ======================================== */
.markdown-body a {
  color: #00f5ff;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s ease;
  position: relative;
  text-shadow: 0 0 10px currentColor;
}

.markdown-body a::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 1px;
  background: currentColor;
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.markdown-body a:hover {
  color: #ff00ff;
  text-shadow: 0 0 15px currentColor;
}

.markdown-body a:hover::after {
  transform: scaleX(1);
}

/* ========================================
   NEON CODE BLOCKS
   ======================================== */
.markdown-body code {
  padding: 0.3em 0.6em;
  margin: 0;
  font-size: 85%;
  background: rgba(0, 245, 255, 0.1);
  border: 1px solid rgba(0, 245, 255, 0.2);
  border-radius: 6px;
  font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
  color: #00f5ff;
  text-shadow: 0 0 8px currentColor;
  font-weight: 600;
}

.markdown-body pre {
  padding: 20px 24px;
  overflow: auto;
  font-size: 14px;
  line-height: 1.6;
  background: rgba(10, 10, 15, 0.9);
  border-radius: 12px;
  margin-bottom: 20px;
  border: 1px solid rgba(0, 245, 255, 0.2);
  position: relative;
  backdrop-filter: blur(10px);
}

.markdown-body pre::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #00f5ff, #ff00ff, #bf00ff);
  border-radius: 12px 12px 0 0;
}

.markdown-body pre code {
  padding: 0;
  margin: 0;
  font-size: 100%;
  background: transparent;
  border: 0;
  display: block;
  overflow-x: auto;
  color: #e0e0e8;
  text-shadow: none;
  font-weight: 400;
}

/* ========================================
   NEON BLOCKQUOTES
   ======================================== */
.markdown-body blockquote {
  padding: 16px 24px;
  color: #a0a0b8;
  border-left: 4px solid #bf00ff;
  margin: 0 0 20px 0;
  background: linear-gradient(to right, rgba(191, 0, 255, 0.1), transparent);
  border-radius: 0 12px 12px 0;
  position: relative;
}

.markdown-body blockquote::before {
  content: '"';
  position: absolute;
  top: -10px;
  left: 10px;
  font-size: 48px;
  color: rgba(191, 0, 255, 0.3);
  font-family: Georgia, serif;
}

.markdown-body blockquote > :first-child {
  margin-top: 0;
}

.markdown-body blockquote > :last-child {
  margin-bottom: 0;
}

/* ========================================
   NEON LISTS
   ======================================== */
.markdown-body ul,
.markdown-body ol {
  padding-left: 2em;
  margin-top: 0;
  margin-bottom: 18px;
}

.markdown-body li {
  margin-top: 0.3em;
  color: #c0c0d0;
}

.markdown-body li + li {
  margin-top: 0.6em;
}

.markdown-body li::marker {
  color: #00f5ff;
}

/* ========================================
   NEON TABLES
   ======================================== */
.markdown-body table {
  display: block;
  width: 100%;
  max-width: 100%;
  overflow: auto;
  border-spacing: 0;
  border-collapse: collapse;
  margin-top: 0;
  margin-bottom: 20px;
  border-radius: 12px;
  border: 1px solid rgba(0, 245, 255, 0.2);
}

.markdown-body table th {
  font-weight: 700;
  padding: 12px 18px;
  border: 1px solid rgba(0, 245, 255, 0.2);
  background: rgba(0, 245, 255, 0.1);
  color: #00f5ff;
  text-align: left;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 12px;
  text-shadow: 0 0 10px currentColor;
}

.markdown-body table td {
  padding: 12px 18px;
  border: 1px solid rgba(0, 245, 255, 0.1);
  color: #c0c0d0;
}

.markdown-body table tr {
  background-color: rgba(10, 10, 15, 0.5);
  transition: all 0.3s ease;
}

.markdown-body table tr:nth-child(2n) {
  background-color: rgba(0, 245, 255, 0.02);
}

.markdown-body table tr:hover {
  background-color: rgba(0, 245, 255, 0.08);
  box-shadow: inset 0 0 20px rgba(0, 245, 255, 0.1);
}

/* ========================================
   NEON HORIZONTAL RULE
   ======================================== */
.markdown-body hr {
  height: 2px;
  padding: 0;
  margin: 32px 0;
  background: linear-gradient(90deg, transparent, #00f5ff, #ff00ff, #bf00ff, transparent);
  border: 0;
  box-shadow: 0 0 20px rgba(0, 245, 255, 0.5);
}

/* ========================================
   NEON IMAGES
   ======================================== */
.markdown-body img {
  max-width: 100%;
  box-sizing: content-box;
  background-color: #0a0a0f;
  border-style: none;
  border-radius: 12px;
  border: 1px solid rgba(0, 245, 255, 0.2);
  box-shadow: 0 0 30px rgba(0, 245, 255, 0.2);
  transition: all 0.3s ease;
}

.markdown-body img:hover {
  box-shadow: 0 0 40px rgba(0, 245, 255, 0.4);
  transform: scale(1.01);
}

/* ========================================
   NEON TASK LIST
   ======================================== */
.markdown-body input[type="checkbox"] {
  margin: 0 0.5em 0.25em -1.4em;
  vertical-align: middle;
  width: 18px;
  height: 18px;
  accent-color: #00f5ff;
  cursor: pointer;
}

/* ========================================
   NEON CODE HIGHLIGHTING
   ======================================== */
.markdown-body .hljs {
  background: rgba(10, 10, 15, 0.9);
  padding: 20px 24px;
  border-radius: 12px;
  overflow-x: auto;
}

/* ========================================
   NEON TEXT STYLES
   ======================================== */
.markdown-body strong {
  font-weight: 800;
  color: #ff00ff;
  text-shadow: 0 0 8px currentColor;
}

.markdown-body em {
  font-style: italic;
  color: #bf00ff;
}

.markdown-body del {
  text-decoration: line-through;
  color: #666680;
}
</style>
