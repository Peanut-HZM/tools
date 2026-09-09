/**
 * Preview Component - Markdown preview with syntax highlighting
 */
import { useMemo, useEffect, useRef } from 'react';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import DOMPurify from 'dompurify';
import './Preview.css';

interface PreviewProps {
  content: string;
  theme?: 'light' | 'dark';
  /** 内容搜索关键词，用于在渲染的 HTML 中高亮匹配文本 */
  searchQuery?: string;
  /** 当前匹配的索引，用于高亮当前选中匹配项并滚动到可视区域 */
  currentMatchIndex?: number;
  /** 实际 DOM 高亮数量变化回调（由 DOM 计算，避免 markdown/HTML 计数不一致） */
  onMatchCountChange?: (count: number) => void;
}

export default function Preview({ content, theme = 'dark', searchQuery = '', currentMatchIndex = 0, onMatchCountChange }: PreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // 将回调存入 ref，避免加入高亮 effect 的依赖导致反复触发
  const onMatchCountChangeRef = useRef(onMatchCountChange);
  onMatchCountChangeRef.current = onMatchCountChange;
  const md = useMemo(() => {
    const markdownIt: any = new MarkdownIt({
      html: true,
      linkify: true,
      typographer: true,
      highlight: function (str: string, lang?: string): string {
        if (lang && hljs.getLanguage(lang)) {
          try {
            return '<pre class="hljs"><code>' +
              hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
              '</code></pre>';
          } catch (__) {}
        }
        return '<pre class="hljs"><code>' + markdownIt.utils.escapeHtml(str) + '</code></pre>';
      }
    });

    // Custom renderer for headings to add IDs for TOC
    const defaultRender = markdownIt.renderer.rules.heading_open || function(tokens: any, idx: number, options: any, _env: any, self: any) {
      return self.renderToken(tokens, idx, options);
    };

    // Shared state for ID generation to handle duplicates within a single render

    markdownIt.renderer.rules.heading_open = function (tokens: any, idx: number, options: any, env: any, self: any) {
      // If this is the first token (idx 0), reset the map.
      // Note: This is a bit of a hack. A better way would be to wrap render() but we are inside the instance setup.
      // Since we use useMemo to recreate md only when necessary, we might need a way to reset.
      // Actually, we can't easily detect start of render here.
      // BUT, MarkdownEditor.tsx handles TOC generation separately.
      // We just need to ensure we generate DETERMINISTIC IDs.
      // If we assume the content is rendered top-to-bottom, we can try to reset.
      
      // However, for React, we should create a fresh renderer or use env.
      // Markdown-it `render` takes an `env` object.
      
      const token = tokens[idx];
      const nextToken = tokens[idx + 1];
      
      if (nextToken && nextToken.type === 'inline') {
        const text = nextToken.content;
        // Match logic in MarkdownEditor.tsx
        let id = text.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-');
        
        // We need to handle duplicates to match MarkdownEditor.
        // But we don't have access to global state easily here without env.
        // Let's use the env object passed to render.
        const usedIds = env.usedIds || new Map<string, number>();
        
        if (usedIds.has(id)) {
            const count = usedIds.get(id);
            usedIds.set(id, count + 1);
            id = `${id}-${count}`;
        } else {
            usedIds.set(id, 1);
        }
        
        // Update env if we created it (though env is usually passed by caller)
        if (!env.usedIds) {
            env.usedIds = usedIds;
        }

        token.attrSet('id', id);
      }
      return defaultRender(tokens, idx, options, env, self);
    };

    return markdownIt;
  }, []);

  const html = useMemo(() => {
    // Pass an empty env object to track used IDs for this render
    const env = { usedIds: new Map<string, number>() };
    const rawHtml = md.render(content, env);
    
    return DOMPurify.sanitize(rawHtml, {
      ADD_TAGS: ['input'], // Allow input for task lists
      ADD_ATTR: ['checked', 'disabled', 'type'] // Allow attributes for task lists
    });
  }, [content, md]);

  // Handle task list checkbox clicks (prevent mutation)
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleCheckboxClick = (e: Event) => {
      const target = e.target as HTMLInputElement;
      if (target.type === 'checkbox') {
        e.preventDefault();
      }
    };

    container.querySelectorAll('input[type="checkbox"]').forEach(el => {
        el.addEventListener('click', handleCheckboxClick);
    });

    return () => {
        container.querySelectorAll('input[type="checkbox"]').forEach(el => {
            el.removeEventListener('click', handleCheckboxClick);
        });
    };
  }, [html]);

  // 内容搜索高亮：在渲染的 HTML 中查找并高亮匹配文本
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 清除之前的高亮标记
    const existingMarks = container.querySelectorAll('mark.search-highlight');
    existingMarks.forEach((mark) => {
      const parent = mark.parentNode;
      if (parent) {
        parent.replaceChild(document.createTextNode(mark.textContent || ''), mark);
        parent.normalize();
      }
    });

    if (!searchQuery.trim()) return;

    const escapedQuery = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(escapedQuery, 'gi');

    // 收集所有文本节点
    const textNodes: Text[] = [];
    const walker = document.createTreeWalker(
      container,
      NodeFilter.SHOW_TEXT,
      null
    );
    let node: Node | null;
    while ((node = walker.nextNode())) {
      textNodes.push(node as Text);
    }

    // 在每个文本节点中查找匹配并创建高亮标记
    const allMarks: HTMLElement[] = [];
    textNodes.forEach((textNode) => {
      const text = textNode.textContent || '';
      if (!regex.test(text)) return;
      regex.lastIndex = 0;

      const frag = document.createDocumentFragment();
      let lastIdx = 0;
      let match: RegExpExecArray | null;

      while ((match = regex.exec(text)) !== null) {
        // 匹配前的普通文本
        if (match.index > lastIdx) {
          frag.appendChild(document.createTextNode(text.slice(lastIdx, match.index)));
        }
        // 高亮匹配文本
        const mark = document.createElement('mark');
        mark.className = 'search-highlight';
        mark.textContent = match[0];
        frag.appendChild(mark);
        allMarks.push(mark);
        lastIdx = regex.lastIndex;
      }

      // 剩余文本
      if (lastIdx < text.length) {
        frag.appendChild(document.createTextNode(text.slice(lastIdx)));
      }

      textNode.parentNode?.replaceChild(frag, textNode);
    });

    // 高亮当前选中匹配项（如果有）并滚动到可视区域
    if (allMarks.length > 0 && currentMatchIndex >= 0) {
      const idx = currentMatchIndex % allMarks.length;
      allMarks.forEach((m, i) => {
        if (i === idx) {
          m.classList.add('active-search-match');
          m.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          m.classList.remove('active-search-match');
        }
      });
    }

    // 将实际 DOM 高亮数量回传给父组件（确保与渲染后的 HTML 一致）
    onMatchCountChangeRef.current?.(allMarks.length);
  }, [html, searchQuery, currentMatchIndex]);

  return (
    <div className={`h-full overflow-auto bg-transparent text-inherit ${theme === 'dark' ? 'dark-theme' : ''}`}>
      <div
        ref={containerRef}
        className="markdown-body"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
