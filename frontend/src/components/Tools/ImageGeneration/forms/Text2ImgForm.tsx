/**
 * Text2ImgForm — 对话式文生图
 * 显示 LLM 追问对话 + 用户输入框 + 生成结果
 */
import { useState, useRef, useEffect } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useImageGenerate } from '../../../../hooks/useImageGenerate';
import { useI18n } from '../../../../i18n';
import type { ImageSize, ModelPreference } from '../../../../api/imageGenerationApi';

export default function Text2ImgForm() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const [input, setInput] = useState('');
  const [size, setSize] = useState<ImageSize>('1024x1024');
  const [n, setN] = useState(1);
  const [style] = useState<string>('auto');
  const [modelPreference] = useState<ModelPreference>('auto');
  const [polishPrompt] = useState<boolean>(false);

  const history = useImageGenStore((s) => s.conversationHistory);
  const chatAnswer = useImageGenStore((s) => s.chatAnswer);
  const chatStatus = useImageGenStore((s) => s.chatStatus);
  const currentResult = useImageGenStore((s) => s.currentResult);
  const resetConversation = useImageGenStore((s) => s.resetConversation);

  const { chat, loading } = useImageGenerate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, chatAnswer]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userInput = input;
    setInput('');
    await chat(userInput, {
      size,
      n,
      style,
      model_preference: modelPreference,
      polish_prompt: polishPrompt,
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* 对话历史 */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-3 p-2 bg-slate-900/50 rounded-lg max-h-96">
        {history.length === 0 && (
          <div className="text-center text-slate-500 py-8">
            🤖 {igT.chat.welcome}
          </div>
        )}
        {history.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-100'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg animate-pulse">
              {igT.chat.thinking}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 生成结果显示 */}
      {chatStatus === 'generated' && currentResult && currentResult.image_urls.length > 0 && (
        <div className="mb-4 p-4 bg-slate-800 rounded-lg">
          <img
            src={currentResult.image_urls[0]}
            alt="generated"
            className="w-full rounded-lg mb-2"
          />
          <div className="text-xs text-slate-400">
            {igT.result.model}: {currentResult.model_used}
          </div>
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => {
                const imageUrl = currentResult.image_urls[0];
                if (imageUrl && (imageUrl.startsWith('http://') || imageUrl.startsWith('https://'))) {
                  window.open(imageUrl, '_blank');
                }
              }}
              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
            >
              {igT.result.download}
            </button>
            <button
              onClick={resetConversation}
              className="px-3 py-1 bg-slate-700 text-slate-200 text-sm rounded hover:bg-slate-600"
            >
              {igT.chat.newConversation}
            </button>
          </div>
        </div>
      )}

      {/* 参数面板（首次对话时显示，可折叠） */}
      {history.length === 0 && (
        <div className="mb-4 p-3 bg-slate-800 rounded-lg space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <label className="text-slate-400 w-20">{igT.form.size}</label>
            <select
              value={size}
              onChange={(e) => setSize(e.target.value as ImageSize)}
              className="flex-1 bg-slate-700 text-slate-100 px-2 py-1 rounded"
            >
              <option value="1024x1024">1024×1024</option>
              <option value="1024x1792">1024×1792</option>
              <option value="1792x1024">1792×1024</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-slate-400 w-20">{igT.form.count}</label>
            <select
              value={n}
              onChange={(e) => setN(Number(e.target.value))}
              className="flex-1 bg-slate-700 text-slate-100 px-2 py-1 rounded"
            >
              <option value={1}>1 张</option>
              <option value={2}>2 张</option>
              <option value={3}>3 张</option>
              <option value={4}>4 张</option>
            </select>
          </div>
        </div>
      )}

      {/* 输入框 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={igT.chat.inputPlaceholder}
          disabled={loading}
          className="flex-1 px-4 py-2 bg-slate-700 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {igT.chat.send}
        </button>
      </div>
    </div>
  );
}
