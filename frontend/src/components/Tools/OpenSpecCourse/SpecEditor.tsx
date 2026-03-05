/**
 * Spec 编辑器组件 - 供用户尝试编写简单的 spec 文件
 */
import React, { useState } from 'react';

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
          <h2 className="text-2xl font-bold text-white">💻 Spec 编辑器</h2>
          <p className="text-white/60 text-sm">尝试编写你的第一个 spec 文件</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setPreviewMode('edit')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              previewMode === 'edit'
                ? 'bg-yellow-500 text-black'
                : 'bg-gray-700 text-white hover:bg-gray-600'
            }`}
          >
            编辑
          </button>
          <button
            onClick={() => setPreviewMode('split')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              previewMode === 'split'
                ? 'bg-yellow-500 text-black'
                : 'bg-gray-700 text-white hover:bg-gray-600'
            }`}
          >
            分屏
          </button>
          <button
            onClick={() => setPreviewMode('preview')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              previewMode === 'preview'
                ? 'bg-yellow-500 text-black'
                : 'bg-gray-700 text-white hover:bg-gray-600'
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
          <div className="flex-1 bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
              <span className="text-sm text-gray-400">spec.md</span>
              <div className="flex items-center space-x-2">
                {saved && (
                  <span className="text-xs text-green-400">✅ 已保存</span>
                )}
                <button
                  onClick={handleReset}
                  className="text-xs text-gray-400 hover:text-white"
                >
                  重置
                </button>
                <button
                  onClick={handleSave}
                  className="text-xs px-3 py-1 bg-yellow-500 hover:bg-yellow-600 text-black rounded transition-colors"
                >
                  保存
                </button>
              </div>
            </div>
            <textarea
              value={specContent}
              onChange={(e) => setSpecContent(e.target.value)}
              className="w-full h-full bg-gray-900 text-gray-100 p-4 font-mono text-sm resize-none focus:outline-none"
              spellCheck={false}
            />
          </div>
        )}

        {/* Preview */}
        {(previewMode === 'preview' || previewMode === 'split') && (
          <div className={`bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 overflow-y-auto ${
            previewMode === 'split' ? 'flex-1' : 'flex-1'
          }`}>
            <div className="p-6">
              <div className="prose prose-invert prose-lg max-w-none">
                <h3>📄 预览效果</h3>
                <div className="text-gray-300 whitespace-pre-wrap font-sans">
                  {specContent}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Tips */}
      <div className="mt-4 p-4 bg-purple-500/20 border border-purple-500 rounded-xl">
        <div className="flex items-start space-x-3">
          <span className="text-xl">💡</span>
          <div className="text-white/80 text-sm">
            <strong>提示：</strong>
            Spec 文件是 OpenSpec 的核心，它描述了需求的详细规范。好的 spec 应该清晰、具体、可测试。
            尝试修改上面的模板，添加或删除一些需求条目。
          </div>
        </div>
      </div>

      {/* Close Button */}
      <div className="mt-4 flex justify-end">
        <button
          onClick={onClose}
          className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-xl transition-colors"
        >
          关闭
        </button>
      </div>
    </div>
  );
};

export default SpecEditor;
