/**
 * ChatPanel — 左侧对话面板（1/4 宽度）
 * 包含：顶部操作栏 + Tab 栏 + 聊天历史 + 输入框
 * 注意：参数控制暂时使用 store 默认值，后续版本添加参数编辑器
 */
import { useState, useRef, useEffect } from 'react';
import { useImageGenStore } from '../../../stores/imageGenerationStore';
import { useAuth } from '../../../stores/authStore';
import { useImageGenerate } from '../../../hooks/useImageGenerate';
import { useI18n } from '../../../i18n';
import RequireAuthNotice from '../../Common/RequireAuthNotice';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

// 公共组件
import QuotaBadge from './components/QuotaBadge';
import BackendSwitch from './BackendSwitch';

import type { Operation, ChatParams } from '../../../api/imageGenerationApi';

const TABS: { key: Operation; icon: string; labelKey: keyof typeof TAB_LABELS }[] = [
  { key: 'text2img', icon: '✍️', labelKey: 'text2img' },
  { key: 'img2img', icon: '🖼️', labelKey: 'img2img' },
  { key: 'inpaint', icon: '🎯', labelKey: 'inpaint' },
  { key: 'upload_edit', icon: '🔧', labelKey: 'uploadEdit' },
];

const TAB_LABELS = {
  text2img: '文生图',
  img2img: '图生图',
  inpaint: '局部重绘',
  uploadEdit: '上传编辑',
};

export default function ChatPanel() {
  const { isAuthenticated } = useAuth();
  const operation = useImageGenStore((s) => s.operation);
  const setOperation = useImageGenStore((s) => s.setOperation);
  const reset = useImageGenStore((s) => s.reset);
  const conversationHistory = useImageGenStore((s) => s.conversationHistory);
  const chatAnswer = useImageGenStore((s) => s.chatAnswer);
  const chatStatus = useImageGenStore((s) => s.chatStatus);
  const resetConversation = useImageGenStore((s) => s.resetConversation);

  const { chat, loading } = useImageGenerate();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationHistory, chatAnswer]);

  if (!isAuthenticated) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <RequireAuthNotice />
      </div>
    );
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userInput = input;
    setInput('');

    // 使用 store 默认 params（后续版本添加参数编辑器）
    const params = useImageGenStore.getState().params;
    const referenceImage = useImageGenStore.getState().referenceImage;
    const maskImage = useImageGenStore.getState().maskImage;

    let chatParams: ChatParams = {};

    if (operation === 'text2img') {
      chatParams = {
        size: params.size,
        n: params.n,
        model_preference: params.model_preference,
      };
    } else if (operation === 'img2img') {
      if (!referenceImage) {
        setInput(userInput);
        return;
      }
      chatParams = {
        strength: params.strength,
        model_preference: params.model_preference,
        referenceImage,
      };
    } else if (operation === 'inpaint') {
      if (!referenceImage || !maskImage) {
        setInput(userInput);
        return;
      }
      chatParams = {
        referenceImage,
        maskImage,
      };
    } else if (operation === 'upload_edit') {
      if (!referenceImage) {
        setInput(userInput);
        return;
      }
      chatParams = {
        edit_type: params.edit_type,
        referenceImage,
      };
    }

    await chat(userInput, chatParams);
  };

  return (
    <div className="w-1/4 flex flex-col min-h-0 border-r border-border bg-canvas">
      {/* 顶部操作栏 */}
      <div className="flex items-center justify-between p-3 border-b border-border flex-shrink-0">
        <BackendSwitch />
        <div className="flex items-center gap-2">
          <QuotaBadge />
          <Button
            variant="secondary"
            size="sm"
            onClick={reset}
            className="flex items-center gap-1.5 px-2.5"
            title="重置"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </Button>
        </div>
      </div>

      {/* Tab 栏 */}
      <div className="flex gap-1 p-2 border-b border-border bg-surface-1/50 flex-shrink-0">
        {TABS.map((tab) => (
          <Button
            key={tab.key}
            variant={operation === tab.key ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setOperation(tab.key)}
            className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs font-medium"
            title={TAB_LABELS[tab.labelKey]}
          >
            <span className="text-sm">{tab.icon}</span>
          </Button>
        ))}
      </div>

      {/* 聊天历史 */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {conversationHistory.length === 0 && chatStatus === 'idle' && (
          <div className="text-center text-ink-faint py-8">
            🤖 你想画什么？告诉我主题、风格、场景等
          </div>
        )}
        {conversationHistory.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[90%] px-3 py-2 rounded-lg text-sm ${
                msg.role === 'user'
                  ? 'bg-accent text-white'
                  : 'bg-surface-2 text-ink'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-2 text-ink px-3 py-2 rounded-lg text-sm animate-pulse">
              思考中...
            </div>
          </div>
        )}
        {chatAnswer && chatStatus === 'asking' && (
          <div className="flex justify-start">
            <div className="bg-surface-2 text-ink px-3 py-2 rounded-lg text-sm">
              {chatAnswer}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div className="p-3 border-t border-border bg-surface-1/50 flex-shrink-0">
        <div className="flex gap-2">
          <Input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入你的回复..."
            disabled={loading}
            className="flex-1"
          />
          <Button
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >
            发送
          </Button>
        </div>
        {chatStatus === 'generated' && (
          <Button
            variant="secondary"
            size="sm"
            onClick={resetConversation}
            className="mt-2 w-full"
          >
            新对话
          </Button>
        )}
      </div>
    </div>
  );
}
