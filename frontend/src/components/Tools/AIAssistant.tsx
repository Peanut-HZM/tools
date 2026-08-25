import { useNavigate } from 'react-router-dom';

// AI 助手外部地址，从构建时环境变量注入（见 .env.example）
// 未在 .env 中配置时不展示"新窗口打开"入口，iframe 也改为空白占位提示。
const AI_ASSISTANT_URL = (import.meta.env.VITE_AI_ASSISTANT_URL as string | undefined) || '';

export default function AIAssistant() {
  const navigate = useNavigate();

  return (
    <div className="flex-1 text-ink flex flex-col overflow-hidden">
      {/* 顶部工具栏 */}
      <div className="bg-surface-1 border-b border-border px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-ink-muted hover:text-ink-inverse transition-colors flex items-center gap-2"
          >
            <i className="fas fa-arrow-left"></i>
            <span className="hidden sm:inline">返回</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded flex items-center justify-center">
              <i className="fas fa-robot text-white text-sm"></i>
            </div>
            <h1 className="text-lg font-bold">AI助手</h1>
          </div>
        </div>

        {AI_ASSISTANT_URL && (
          <a
            href={AI_ASSISTANT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink-muted hover:text-ink-inverse transition-colors flex items-center gap-2 text-sm"
          >
            <i className="fas fa-external-link-alt"></i>
            <span className="hidden sm:inline">新窗口打开</span>
          </a>
        )}
      </div>

      {/* iframe 嵌入 AI 助手 */}
      <div className="flex-1 overflow-hidden">
        {AI_ASSISTANT_URL ? (
          <iframe
            src={AI_ASSISTANT_URL}
            className="w-full h-full border-0"
            title="AI助手"
            allow="microphone; camera; clipboard-read; clipboard-write"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-ink-muted">
            <div className="text-center">
              <i className="fas fa-info-circle text-3xl mb-3"></i>
              <p>AI 助手未配置</p>
              <p className="text-xs mt-2 text-ink-faint">
                请在 <code className="text-pink-400">.env</code> 中设置{' '}
                <code className="text-pink-400">VITE_AI_ASSISTANT_URL</code>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
