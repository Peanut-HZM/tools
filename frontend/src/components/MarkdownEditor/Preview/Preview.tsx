/**
 * Preview Component - Markdown preview with syntax highlighting
 */
import { useMemo, useEffect } from 'react';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import DOMPurify from 'dompurify';
import './Preview.css';

interface PreviewProps {
  content: string;
  theme?: 'light' | 'dark';
}

export default function Preview({ content, theme = 'dark' }: PreviewProps) {
  const md = useMemo(() => {
    const markdownIt = new MarkdownIt({
      html: true,
      linkify: true,
      typographer: true,
      highlight: function (str, lang) {
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
    const defaultRender = markdownIt.renderer.rules.heading_open || function(tokens, idx, options, env, self) {
      return self.renderToken(tokens, idx, options);
    };

    // Shared state for ID generation to handle duplicates within a single render
    let idMap = new Map<string, number>();

    markdownIt.renderer.rules.heading_open = function (tokens, idx, options, env, self) {
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
    const handleCheckboxClick = (e: Event) => {
      const target = e.target as HTMLInputElement;
      if (target.type === 'checkbox') {
        e.preventDefault();
      }
    };
    
    // Attach event listener to a container if possible, or we rely on the fact 
    // that React re-renders. But native events on dangerouslySetInnerHTML content 
    // need manual handling if we want to intercept them, though preventDefault on click works.
    // We'll attach to the document or specific container if we had a ref.
    // Since we don't have a ref in this simple component, we can skip or add one.
    // Let's add a class to the container and delegate.
    document.querySelectorAll('.markdown-body input[type="checkbox"]').forEach(el => {
        el.addEventListener('click', handleCheckboxClick);
    });
    
    return () => {
        document.querySelectorAll('.markdown-body input[type="checkbox"]').forEach(el => {
            el.removeEventListener('click', handleCheckboxClick);
        });
    };
  }, [html]);

  return (
    <div className={`h-full overflow-auto bg-transparent text-inherit ${theme === 'dark' ? 'dark-theme' : ''}`}>
      <div
        className="markdown-body"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
