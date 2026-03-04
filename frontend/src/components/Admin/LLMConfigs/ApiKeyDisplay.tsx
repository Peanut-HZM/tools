import { useState } from 'react';
import { useToast } from '../../hooks/useToast';

interface ApiKeyDisplayProps {
  apiKeySuffix?: string;
  fullApiKey?: string;
  onCopy?: () => void;
}

export default function ApiKeyDisplay({ apiKeySuffix, fullApiKey, onCopy }: ApiKeyDisplayProps) {
  const [isVisible, setIsVisible] = useState(false);
  const { success } = useToast();

  // 脱敏显示：如果没有 fullApiKey，只显示后缀
  const maskedKey = apiKeySuffix ? `...${apiKeySuffix}` : '未设置';

  const handleCopy = async () => {
    if (!fullApiKey) return;
    
    try {
      await navigator.clipboard.writeText(fullApiKey);
      success('已复制到剪贴板，请妥善保管，切勿泄露给他人！');
      onCopy?.();
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {/* 脱敏/明文显示 */}
      <div className="font-mono text-sm text-slate-300 bg-slate-800 px-3 py-1.5 rounded border border-slate-600">
        {isVisible && fullApiKey ? fullApiKey : maskedKey}
      </div>
      
      {/* 眼睛图标切换显示 */}
      <button
        type="button"
        onClick={() => setIsVisible(!isVisible)}
        className="p-1.5 text-slate-400 hover:text-slate-200 transition-colors"
        title={isVisible ? '隐藏' : '显示'}
      >
        {isVisible ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        )}
      </button>

      {/* 复制按钮 */}
      {fullApiKey && (
        <button
          type="button"
          onClick={handleCopy}
          className="p-1.5 text-slate-400 hover:text-cyan-400 transition-colors"
          title="复制"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </button>
      )}
    </div>
  );
}
