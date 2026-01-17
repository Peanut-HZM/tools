/**
 * useMarkdownPreview Hook - Handles Markdown rendering and TOC generation
 */
import { useMemo } from 'react';

interface TocItem {
  level: number;
  text: string;
  id: string;
}

interface UseMarkdownPreviewResult {
  html: string;
  toc: TocItem[];
}

// Simple markdown to HTML converter
function markdownToHtml(markdown: string): string {
  let html = markdown;
  
  // Escape HTML
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  
  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mt-6 mb-3">$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>');
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold">$1</strong>');
  
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>');
  
  // Code blocks
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre class="bg-slate-800 rounded-lg p-4 my-4 overflow-x-auto"><code class="text-sm text-slate-300">${code.trim()}</code></pre>`;
  });
  
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="bg-slate-700 px-1 py-0.5 rounded text-sm text-cyan-400">$1</code>');
  
  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-cyan-400 hover:underline" target="_blank" rel="noopener noreferrer">$1</a>');
  
  // Images
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="max-w-full h-auto rounded-lg my-4" />');
  
  // Unordered lists
  html = html.replace(/^\s*[-*+] (.*$)/gim, '<li class="ml-4">$1</li>');
  html = html.replace(/(<li.*<\/li>\n?)+/g, '<ul class="list-disc list-inside my-2">$&</ul>');
  
  // Ordered lists
  html = html.replace(/^\s*\d+\. (.*$)/gim, '<li class="ml-4">$1</li>');
  
  // Blockquotes
  html = html.replace(/^&gt; (.*$)/gim, '<blockquote class="border-l-4 border-cyan-500 pl-4 my-4 text-slate-400 italic">$1</blockquote>');
  
  // Horizontal rules
  html = html.replace(/^---$/gim, '<hr class="border-slate-600 my-6" />');
  
  // Paragraphs
  html = html.replace(/^(?!<[a-z])(.*$)/gim, (match) => {
    if (match.trim() === '') return '';
    if (match.startsWith('<')) return match;
    return `<p class="my-2">${match}</p>`;
  });
  
  // Clean up empty paragraphs
  html = html.replace(/<p class="my-2"><\/p>/g, '');
  
  return html;
}

// Extract TOC from markdown
function extractToc(markdown: string): TocItem[] {
  const toc: TocItem[] = [];
  const headerRegex = /^(#{1,6})\s+(.+)$/gm;
  let match;
  let counter = 0;

  while ((match = headerRegex.exec(markdown)) !== null) {
    const level = match[1].length;
    const text = match[2].trim();
    const id = `heading-${counter++}`;
    toc.push({ level, text, id });
  }

  return toc;
}

export function useMarkdownPreview(content: string): UseMarkdownPreviewResult {
  const html = useMemo(() => markdownToHtml(content), [content]);
  const toc = useMemo(() => extractToc(content), [content]);

  return { html, toc };
}

export default useMarkdownPreview;
