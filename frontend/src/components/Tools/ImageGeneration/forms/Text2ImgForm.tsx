/**
 * Text2ImgForm — 对话式文生图
 * 显示 LLM 追问对话 + 用户输入框 + 生成结果
 */
import { useState, useRef, useEffect } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useImageGenerate } from '../../../../hooks/useImageGenerate';
import { useI18n } from '../../../../i18n';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import type { ImageSize, ModelPreference } from '../../../../api/imageGenerationApi';

export default function Text2ImgForm() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const [input, setInput] = useState('');
  const [size, setSize] = useState<ImageSize>('1024x1024');
  const [n, setN] = useState(1);
  const [style] = useState<string>('auto');
  const [modelPreference] = useState<ModelPreference>('auto');

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
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* 对话历史 */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-3 p-2 bg-canvas/50 rounded-lg max-h-96">
        {history.length === 0 && (
          <div className="text-center text-ink-faint py-8">
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
            <div className="bg-surface-2 text-ink px-4 py-2 rounded-lg animate-pulse">
              {igT.chat.thinking}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 生成结果显示 */}
      {chatStatus === 'generated' && currentResult && currentResult.image_urls.length > 0 && (
        <Card className="mb-4 p-4">
          <img
            src={currentResult.image_urls[0]}
            alt="generated"
            className="w-full rounded-lg mb-2"
          />
          <div className="text-xs text-ink-muted">
            {igT.result.model}: {currentResult.model_used}
          </div>
          <div className="flex gap-2 mt-2">
            <Button
              size="sm"
              onClick={() => {
                const imageUrl = currentResult.image_urls[0];
                if (imageUrl && (imageUrl.startsWith('http://') || imageUrl.startsWith('https://'))) {
                  window.open(imageUrl, '_blank');
                }
              }}
              className="px-3 py-1 text-sm"
            >
              {igT.result.download}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={resetConversation}
              className="px-3 py-1 text-sm"
            >
              {igT.chat.newConversation}
            </Button>
          </div>
        </Card>
      )}

      {/* 参数面板（首次对话时显示，可折叠） */}
      {history.length === 0 && (
        <Card className="mb-4 p-3 space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <label className="text-ink-muted w-20">{igT.form.size}</label>
            <Select
              value={size}
              onValueChange={(v) => setSize(v as ImageSize)}
            >
              <SelectTrigger className="flex-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="512x512">512×512</SelectItem>
                <SelectItem value="768x768">768×768</SelectItem>
                <SelectItem value="1024x1024">1024×1024</SelectItem>
                <SelectItem value="1024x1792">1024×1792</SelectItem>
                <SelectItem value="1792x1024">1792×1024</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-ink-muted w-20">{igT.form.count}</label>
            <Select
              value={String(n)}
              onValueChange={(v) => setN(Number(v))}
            >
              <SelectTrigger className="flex-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 张</SelectItem>
                <SelectItem value="2">2 张</SelectItem>
                <SelectItem value="3">3 张</SelectItem>
                <SelectItem value="4">4 张</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </Card>
      )}

      {/* 输入框 */}
      <div className="flex gap-2">
        <Input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={igT.chat.inputPlaceholder}
          disabled={loading}
          className="flex-1"
        />
        <Button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-6"
        >
          {igT.chat.send}
        </Button>
      </div>
    </div>
  );
}
