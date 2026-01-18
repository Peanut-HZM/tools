import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function JsonFormatter() {
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [output, setOutput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [indentSize, setIndentSize] = useState(2);

  const formatJson = () => {
    if (!input.trim()) {
      setError('请输入JSON字符串');
      setOutput('');
      return;
    }

    try {
      const parsed = JSON.parse(input);
      const formatted = JSON.stringify(parsed, null, indentSize);
      setOutput(formatted);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '未知错误';
      setError(`JSON格式错误: ${errorMessage}`);
      setOutput('');
      alert(`❌ JSON格式错误\n\n${errorMessage}\n\n请检查您的JSON字符串是否正确。`);
    }
  };

  const minifyJson = () => {
    if (!input.trim()) {
      setError('请输入JSON字符串');
      setOutput('');
      return;
    }

    try {
      const parsed = JSON.parse(input);
      const minified = JSON.stringify(parsed);
      setOutput(minified);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '未知错误';
      setError(`JSON格式错误: ${errorMessage}`);
      setOutput('');
      alert(`❌ JSON格式错误\n\n${errorMessage}\n\n请检查您的JSON字符串是否正确。`);
    }
  };

  const copyToClipboard = (text: string) => {
    if (!text) {
      alert('没有可复制的内容');
      return;
    }
    navigator.clipboard.writeText(text).then(() => {
      alert('✅ 已复制到剪贴板！');
    }).catch(() => {
      alert('❌ 复制失败，请手动复制');
    });
  };

  const clearAll = () => {
    setInput('');
    setOutput('');
    setError(null);
  };

  const loadSample = () => {
    const sample = {
      "name": "张三",
      "age": 30,
      "email": "zhangsan@example.com",
      "address": {
        "city": "北京",
        "district": "朝阳区",
        "street": "建国路1号"
      },
      "hobbies": ["阅读", "旅游", "摄影"],
      "isActive": true,
      "balance": 1234.56
    };
    setInput(JSON.stringify(sample));
  };

  return (
    <div className="flex-1 text-slate-100 flex flex-col overflow-hidden">
      {/* 顶部工具栏 - 紧凑设计 */}
      <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-slate-400 hover:text-white transition-colors flex items-center gap-2"
          >
            <i className="fas fa-arrow-left"></i>
            <span className="hidden sm:inline">返回</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-green-500 rounded flex items-center justify-center">
              <i className="fas fa-code text-white text-sm"></i>
            </div>
            <h1 className="text-lg font-bold">JSON格式化</h1>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center gap-2">
          <select
            value={indentSize}
            onChange={(e) => setIndentSize(Number(e.target.value))}
            className="bg-slate-700 text-white px-2 py-1.5 rounded border border-slate-600 text-sm"
          >
            <option value={2}>2空格</option>
            <option value={4}>4空格</option>
          </select>
          <button
            onClick={formatJson}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium"
          >
            <i className="fas fa-magic mr-1"></i>
            格式化
          </button>
          <button
            onClick={minifyJson}
            className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-1.5 rounded text-sm font-medium"
          >
            <i className="fas fa-compress mr-1"></i>
            压缩
          </button>
          <button
            onClick={clearAll}
            className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm"
          >
            <i className="fas fa-eraser mr-1"></i>
            清空
          </button>
          <button
            onClick={loadSample}
            className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm"
            title="加载示例"
          >
            <i className="fas fa-file-import"></i>
          </button>
        </div>
      </div>

      {/* 错误提示 - 只在有错误时显示 */}
      {error && (
        <div className="bg-red-500/20 border-b border-red-500 text-red-400 px-4 py-2 text-sm flex-shrink-0">
          <i className="fas fa-exclamation-circle mr-2"></i>
          {error}
        </div>
      )}

      {/* 主内容区域 - 占满剩余空间 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 输入区域 */}
        <div className="flex-1 flex flex-col border-r border-slate-700">
          <div className="bg-slate-800/50 px-4 py-2 flex items-center justify-between border-b border-slate-700 flex-shrink-0">
            <span className="text-sm text-slate-400">输入 JSON</span>
            <button
              onClick={() => copyToClipboard(input)}
              className="text-xs text-slate-500 hover:text-slate-300"
              title="复制输入"
            >
              <i className="fas fa-copy mr-1"></i>
              复制
            </button>
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='粘贴JSON字符串，例如：{"name":"张三","age":30}'
            className="flex-1 w-full bg-slate-900 text-white px-4 py-3 font-mono text-sm resize-none focus:outline-none"
            spellCheck={false}
          />
        </div>

        {/* 输出区域 */}
        <div className="flex-1 flex flex-col">
          <div className="bg-slate-800/50 px-4 py-2 flex items-center justify-between border-b border-slate-700 flex-shrink-0">
            <span className="text-sm text-slate-400">格式化结果</span>
            <button
              onClick={() => copyToClipboard(output)}
              className="text-xs text-green-500 hover:text-green-400"
              title="复制结果"
            >
              <i className="fas fa-copy mr-1"></i>
              复制
            </button>
          </div>
          <textarea
            value={output}
            readOnly
            placeholder="格式化后的JSON将显示在这里..."
            className="flex-1 w-full bg-slate-900 text-green-400 px-4 py-3 font-mono text-sm resize-none focus:outline-none"
            spellCheck={false}
          />
        </div>
      </div>

      {/* 底部状态栏 - 紧凑设计 */}
      <div className="bg-slate-800 border-t border-slate-700 px-4 py-1.5 flex items-center justify-between text-xs text-slate-500 flex-shrink-0">
        <div className="flex items-center gap-4">
          <span>输入: {input.length} 字符</span>
          <span>输出: {output.length} 字符</span>
        </div>
        <div className="flex items-center gap-4">
          <span>💡 Ctrl+V 粘贴 | 点击格式化</span>
        </div>
      </div>
    </div>
  );
}
