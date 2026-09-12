import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Bot, ExternalLink, Info } from 'lucide-react';
import { Button } from "@/components/ui/Button";

// AI 助手外部地址，从构建时环境变量注入（见 .env.example）
// 未在 .env 中配置时不展示"新窗口打开"入口，iframe 也改为空白占位提示。
const AI_ASSISTANT_URL = (import.meta.env.VITE_AI_ASSISTANT_URL as string | undefined) || '';

export default function AIAssistant() {
  const navigate = useNavigate();

  return (
    <div className="flex-1 text-ink flex flex-col overflow-hidden">
      {/* 顶部工具栏（玻璃面板范式：贴边去左右/顶部描边，底部描边由玻璃边框承担） */}
      <div className="glass-panel border-x-0 border-t-0 rounded-none px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">返回</span>
          </Button>
          <div className="flex items-center gap-2">
            {/* tint chip：低饱和紫底 + 同色描边（替换紫粉渐变色块） */}
            <div className="w-10 h-10 tint tint-purple rounded-xl">
              <Bot className="w-4 h-4" />
            </div>
            <h1 className="text-lg font-bold">
              {/* gradient-text 会置 color: transparent，故只包文字词组 */}
              <span className="gradient-text">AI</span>助手
            </h1>
          </div>
        </div>

        {AI_ASSISTANT_URL && (
          <a
            href={AI_ASSISTANT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink-muted hover:text-ink transition-colors flex items-center gap-2 text-sm"
          >
            <ExternalLink className="w-4 h-4" />
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
              <Info className="w-8 h-8 mb-3" />
              <p>AI 助手未配置</p>
              <p className="text-xs mt-2 text-ink-faint">
                请在 <code className="text-warning">.env</code> 中设置{' '}
                <code className="text-warning">VITE_AI_ASSISTANT_URL</code>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
