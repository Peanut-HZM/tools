/**
 * 章节内容展示组件
 */
import React, { useState } from 'react';
import { ChapterDetail } from '../../../services/openspecCourse';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Button } from '@/components/ui/Button';

interface ChapterContentProps {
  chapter: ChapterDetail;
  onNextChapter: () => void;
  onStartQuiz: () => void;
  onOpenSpecEditor: () => void;
}

const ChapterContent: React.FC<ChapterContentProps> = ({
  chapter,
  onNextChapter,
  onStartQuiz,
  onOpenSpecEditor,
}) => {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Chapter Header */}
      <div className="mb-8">
        <div className="flex items-center space-x-3 mb-4">
          <span className="text-4xl">
            {chapter.chapter_type === 'story' && '📖'}
            {chapter.chapter_type === 'code' && '💻'}
            {chapter.chapter_type === 'quiz' && '📝'}
            {chapter.chapter_type === 'video' && '🎬'}
          </span>
          <h2 className="text-3xl font-bold text-ink">{chapter.title}</h2>
        </div>
      </div>

      {/* Video Section (if available) */}
      {chapter.video_url && (
        <div className="mb-8 glass-card rounded-xl p-6">
          <div className="aspect-video bg-surface-2 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <div className="text-6xl mb-4">🎬</div>
              <div className="text-ink-muted">视频区域</div>
              <div className="text-sm text-ink-faint mt-2">{chapter.video_url}</div>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="glass-card rounded-xl p-8 mb-8">
        <div className="prose dark:prose-invert prose-headings:text-ink prose-p:text-ink-muted prose-a:text-accent prose-lg max-w-none text-ink/80">
          <ReactMarkdown
            components={{
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');
                const code = String(children).replace(/\n$/, '');

                if (!inline && match) {
                  return (
                    <div className="relative group">
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        {...props}
                      >
                        {code}
                      </SyntaxHighlighter>
                      <button
                        onClick={() => handleCopyCode(code)}
                        className="absolute top-2 right-2 px-3 py-1 bg-black/60 hover:bg-black/80 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        {copiedCode === code ? '✅ 已复制' : '📋 复制'}
                      </button>
                    </div>
                  );
                }
                return (
                  // 行内代码 chip：token 化底色（代码块高亮器仍为深色主题，独立于页面主题）
                  <code className="bg-surface-2 px-2 py-1 rounded text-accent" {...props}>
                    {children}
                  </code>
                );
              },
              // 自定义 Markdown 元素样式以确保正确的预览效果（文字统一走 ink 系 token 适配双主题）
              h1: ({node, ...props}: any) => <h1 className="text-3xl font-bold text-ink mb-4" {...props} />,
              h2: ({node, ...props}: any) => <h2 className="text-2xl font-bold text-ink mb-3" {...props} />,
              h3: ({node, ...props}: any) => <h3 className="text-xl font-semibold text-ink mb-2" {...props} />,
              p: ({node, ...props}: any) => <p className="text-ink-muted leading-relaxed mb-4" {...props} />,
              ul: ({node, ...props}: any) => <ul className="list-disc list-inside text-ink-muted mb-4 space-y-1" {...props} />,
              ol: ({node, ...props}: any) => <ol className="list-decimal list-inside text-ink-muted mb-4 space-y-1" {...props} />,
              li: ({node, ...props}: any) => <li className="text-ink-muted" {...props} />,
              blockquote: ({node, ...props}: any) => <blockquote className="border-l-4 border-accent-warning pl-4 text-ink-muted italic my-4" {...props} />,
              a: ({node, ...props}: any) => <a className="text-accent hover:text-accent-hover underline" {...props} />,
              strong: ({node, ...props}: any) => <strong className="font-bold text-ink" {...props} />,
              em: ({node, ...props}: any) => <em className="italic text-ink-muted" {...props} />,
              hr: ({node, ...props}: any) => <hr className="border-border my-6" {...props} />,
              table: ({node, ...props}: any) => <table className="w-full border-collapse border border-border my-4" {...props} />,
              th: ({node, ...props}: any) => <th className="border border-border bg-surface-2 px-3 py-2 text-left text-ink font-semibold" {...props} />,
              td: ({node, ...props}: any) => <td className="border border-border px-3 py-2 text-ink-muted" {...props} />,
            }}
          >
            {chapter.content}
          </ReactMarkdown>
        </div>
      </div>

      {/* Resources Section */}
      {chapter.resources && chapter.resources.length > 0 && (
        <div className="mb-8">
          <h3 className="text-xl font-semibold text-ink mb-4">📎 相关资源</h3>
          <div className="grid gap-4">
            {chapter.resources.map((resource) => (
              <div
                key={resource.id}
                className="glass-card rounded-xl p-6 hover:border-accent transition-colors cursor-pointer"
                onClick={() => {
                  if (resource.resource_type === 'code_sample') {
                    onOpenSpecEditor();
                  }
                }}
              >
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">
                    {resource.resource_type === 'code_sample' && '💻'}
                    {resource.resource_type === 'contrast' && '⚖️'}
                    {resource.resource_type === 'video' && '🎬'}
                    {resource.resource_type === 'template' && '📄'}
                  </span>
                  <div>
                    <h4 className="text-ink font-medium">{resource.title}</h4>
                    <p className="text-ink-muted text-sm">{resource.content.substring(0, 100)}...</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {/* 操作按钮走 ui/Button 语义变体：编辑器次要、测验强调描边、下一章为主操作（品牌渐变） */}
      <div className="flex items-center justify-between">
        <Button
          variant="secondary"
          onClick={onOpenSpecEditor}
        >
          💻 打开 Spec 编辑器
        </Button>

        {chapter.quiz && (
          <Button
            variant="outline"
            onClick={onStartQuiz}
          >
            📝 开始测验
          </Button>
        )}

        <Button
          onClick={onNextChapter}
        >
          继续下一章 →
        </Button>
      </div>
    </div>
  );
};

export default ChapterContent;
