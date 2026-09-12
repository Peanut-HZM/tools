/**
 * Spec 编辑器组件 - 供用户尝试编写简单的 spec 文件
 */
import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';

interface SpecEditorProps {
  onClose: () => void;
}

const DEFAULT_SPEC_TEMPLATE = `# OpenSpec 示例文件
# 这是一个简单的规范文件示例

## 功能需求

### 用户登录
- 用户可以通过邮箱和密码登录
- 登录成功后返回 JWT token
- token 有效期为 24 小时

### 用户注册
- 用户可以通过邮箱注册账号
- 需要验证邮箱格式
- 密码长度至少 8 位

## 技术约束
- 使用 Node.js 18+
- 使用 TypeScript
- 数据库使用 PostgreSQL

## 验收标准
- [ ] 用户可以成功登录
- [ ] 登录失败时显示错误信息
- [ ] token 可以正常刷新
`;

const SpecEditor: React.FC<SpecEditorProps> = ({ onClose }) => {
  const [specContent, setSpecContent] = useState(DEFAULT_SPEC_TEMPLATE);
  const [previewMode, setPreviewMode] = useState<'edit' | 'preview' | 'split'>('edit');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // 模拟保存
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    setSpecContent(DEFAULT_SPEC_TEMPLATE);
  };

  return (
    <div className="h-[calc(100vh-200px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-ink">💻 Spec 编辑器</h2>
          <p className="text-ink-muted text-sm">尝试编写你的第一个 spec 文件</p>
        </div>
        <div className="flex items-center space-x-2">
          {/* 模式切换胶囊：激活态走品牌渐变底（同 TechContentsPage 筛选 Tab 范式） */}
          <button
            onClick={() => setPreviewMode('edit')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              previewMode === 'edit'
                ? 'text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)]'
                : 'text-ink-muted hover:text-ink hover:bg-glass-bg'
            }`}
          >
            编辑
          </button>
          <button
            onClick={() => setPreviewMode('split')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              previewMode === 'split'
                ? 'text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)]'
                : 'text-ink-muted hover:text-ink hover:bg-glass-bg'
            }`}
          >
            分屏
          </button>
          <button
            onClick={() => setPreviewMode('preview')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              previewMode === 'preview'
                ? 'text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)]'
                : 'text-ink-muted hover:text-ink hover:bg-glass-bg'
            }`}
          >
            预览
          </button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 flex gap-4 overflow-hidden">
        {/* Editor */}
        {(previewMode === 'edit' || previewMode === 'split') && (
          <div className="flex-1 glass-card rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-surface-1/60 border-b border-border">
              <span className="text-sm text-ink-muted">spec.md</span>
              <div className="flex items-center space-x-2">
                {saved && (
                  <span className="text-xs text-success">✅ 已保存</span>
                )}
                <button
                  onClick={handleReset}
                  className="text-xs text-ink-faint hover:text-ink transition-colors"
                >
                  重置
                </button>
                <Button
                  variant="secondary"
                  onClick={handleSave}
                  size="sm"
                >
                  保存
                </Button>
              </div>
            </div>
            <textarea
              value={specContent}
              onChange={(e) => setSpecContent(e.target.value)}
              className="w-full h-full bg-canvas text-ink p-4 font-mono text-sm resize-none focus:outline-none"
              spellCheck={false}
            />
          </div>
        )}

        {/* Preview */}
        {(previewMode === 'preview' || previewMode === 'split') && (
          <div className={`glass-card rounded-xl overflow-y-auto ${
            previewMode === 'split' ? 'flex-1' : 'flex-1'
          }`}>
            <div className="p-6">
              <div className="prose dark:prose-invert prose-headings:text-ink prose-p:text-ink-muted prose-lg max-w-none">
                <h3>📄 预览效果</h3>
                <div className="text-ink whitespace-pre-wrap font-sans">
                  {specContent}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Tips */}
      <div className="mt-4 p-4 rounded-xl bg-[rgba(101,116,255,0.14)] border border-[rgba(101,116,255,0.28)]">
        <div className="flex items-start space-x-3">
          <span className="text-xl">💡</span>
          <div className="text-ink-muted text-sm">
            <strong>提示：</strong>
            Spec 文件是 OpenSpec 的核心，它描述了需求的详细规范。好的 spec 应该清晰、具体、可测试。
            尝试修改上面的模板，添加或删除一些需求条目。
          </div>
        </div>
      </div>

      {/* Close Button */}
      <div className="mt-4 flex justify-end">
        <Button
          variant="secondary"
          onClick={onClose}
        >
          关闭
        </Button>
      </div>
    </div>
  );
};

export default SpecEditor;
