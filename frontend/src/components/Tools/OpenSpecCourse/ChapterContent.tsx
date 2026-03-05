/**
 * 章节内容展示组件
 */
import React, { useState } from 'react';
import { ChapterDetail } from '../../../services/openspecCourse';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ChapterContentProps {
  chapter: ChapterDetail;
  onNextChapter: () => void;
  onStartQuiz: () => void;
  onOpenSpecEditor: () => void;
  isCompleted: boolean;
}

const ChapterContent: React.FC<ChapterContentProps> = ({
  chapter,
  onNextChapter,
  onStartQuiz,
  onOpenSpecEditor,
  isCompleted,
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
          <h2 className="text-3xl font-bold text-white">{chapter.title}</h2>
        </div>
        {isCompleted && (
          <div className="inline-flex items-center px-3 py-1 bg-green-500/20 border border-green-500 text-green-400 rounded-full text-sm">
            ✅ 已完成
          </div>
        )}
      </div>

      {/* Video Section (if available) */}
      {chapter.video_url && (
        <div className="mb-8 bg-black/30 rounded-xl p-6 border border-white/10">
          <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <div className="text-6xl mb-4">🎬</div>
              <div className="text-white/60">视频区域</div>
              <div className="text-sm text-white/40 mt-2">{chapter.video_url}</div>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="bg-white/5 backdrop-blur-sm rounded-xl p-8 border border-white/10 mb-8">
        <ReactMarkdown
          className="prose prose-invert prose-lg max-w-none"
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
                      className="absolute top-2 right-2 px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      {copiedCode === code ? '✅ 已复制' : '📋 复制'}
                    </button>
                  </div>
                );
              }
              return (
                <code className="bg-gray-800 px-2 py-1 rounded text-pink-400" {...props}>
                  {children}
                </code>
              );
            },
          }}
        >
          {chapter.content}
        </ReactMarkdown>
      </div>

      {/* Resources Section */}
      {chapter.resources && chapter.resources.length > 0 && (
        <div className="mb-8">
          <h3 className="text-xl font-semibold text-white mb-4">📎 相关资源</h3>
          <div className="grid gap-4">
            {chapter.resources.map((resource) => (
              <div
                key={resource.id}
                className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10 hover:border-yellow-500/50 transition-colors cursor-pointer"
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
                    <h4 className="text-white font-medium">{resource.title}</h4>
                    <p className="text-white/60 text-sm">{resource.content.substring(0, 100)}...</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={onOpenSpecEditor}
          className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition-colors font-medium"
        >
          💻 打开 Spec 编辑器
        </button>

        {chapter.quiz && !isCompleted && (
          <button
            onClick={onStartQuiz}
            className="px-6 py-3 bg-yellow-500 hover:bg-yellow-600 text-black rounded-xl transition-colors font-medium"
          >
            📝 开始测验
          </button>
        )}

        {isCompleted && (
          <button
            onClick={onNextChapter}
            className="px-6 py-3 bg-green-500 hover:bg-green-600 text-white rounded-xl transition-colors font-medium"
          >
            继续下一章 →
          </button>
        )}
      </div>
    </div>
  );
};

export default ChapterContent;
