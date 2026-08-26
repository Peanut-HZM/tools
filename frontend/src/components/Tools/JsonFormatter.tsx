import { AlertCircle, ArrowLeft, Code, Copy, Eraser, FileInput, Minimize2, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from "@/components/ui/Button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/Select";

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
    <div className="flex-1 text-ink flex flex-col overflow-hidden">
      {/* 顶部工具栏 - 紧凑设计 */}
      <div className="bg-surface-1 border-b border-border px-4 py-2 flex items-center justify-between flex-shrink-0">
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
            <div className="w-8 h-8 bg-success rounded flex items-center justify-center">
              <Code className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-lg font-bold">JSON格式化</h1>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center gap-2">
          <Select
            value={String(indentSize)}
            onValueChange={(v) => setIndentSize(Number(v))}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="2">2空格</SelectItem>
              <SelectItem value="4">4空格</SelectItem>
            </SelectContent>
          </Select>
          <Button
            onClick={formatJson}
            size="sm"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1" />
            格式化
          </Button>
          <Button
            onClick={minifyJson}
            size="sm"
            className="bg-warning hover:opacity-90"
          >
            <Minimize2 className="w-3.5 h-3.5 mr-1" />
            压缩
          </Button>
          <Button
            variant="secondary"
            onClick={clearAll}
            size="sm"
          >
            <Eraser className="w-3.5 h-3.5 mr-1" />
            清空
          </Button>
          <Button
            variant="secondary"
            onClick={loadSample}
            size="icon"
            title="加载示例"
          >
            <FileInput className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* 错误提示 - 只在有错误时显示 */}
      {error && (
        <div className="bg-danger/20 border-b border-danger text-danger px-4 py-2 text-sm flex-shrink-0">
          <AlertCircle className="w-4 h-4 mr-2" />
          {error}
        </div>
      )}

      {/* 主内容区域 - 占满剩余空间 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 输入区域 */}
        <div className="flex-1 flex flex-col border-r border-border">
          <div className="bg-surface-1/50 px-4 py-2 flex items-center justify-between border-b border-border flex-shrink-0">
            <span className="text-sm text-ink-muted">输入 JSON</span>
            <button
              onClick={() => copyToClipboard(input)}
              className="text-xs text-ink-faint hover:text-ink-muted"
              title="复制输入"
            >
              <Copy className="w-3.5 h-3.5 mr-1" />
              复制
            </button>
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='粘贴JSON字符串，例如：{"name":"张三","age":30}'
            className="flex-1 w-full bg-canvas text-ink px-4 py-3 font-mono text-sm resize-none focus:outline-none"
            spellCheck={false}
          />
        </div>

        {/* 输出区域 */}
        <div className="flex-1 flex flex-col">
          <div className="bg-surface-1/50 px-4 py-2 flex items-center justify-between border-b border-border flex-shrink-0">
            <span className="text-sm text-ink-muted">格式化结果</span>
            <button
              onClick={() => copyToClipboard(output)}
              className="text-xs text-success hover:text-success/80"
              title="复制结果"
            >
              <Copy className="w-3.5 h-3.5 mr-1" />
              复制
            </button>
          </div>
          <textarea
            value={output}
            readOnly
            placeholder="格式化后的JSON将显示在这里..."
            className="flex-1 w-full bg-canvas text-success px-4 py-3 font-mono text-sm resize-none focus:outline-none"
            spellCheck={false}
          />
        </div>
      </div>

      {/* 底部状态栏 - 紧凑设计 */}
      <div className="bg-surface-1 border-t border-border px-4 py-1.5 flex items-center justify-between text-xs text-ink-faint flex-shrink-0">
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
