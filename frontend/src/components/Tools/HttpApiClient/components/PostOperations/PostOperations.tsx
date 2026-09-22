/**
 * PostOperations - 后置操作面板（Apifox 风格）
 *
 * 包含两个子模块：
 * - 提取变量：发送后从响应中提取值写入激活环境（JSONPath / 正则 / Header / 状态码 / 耗时）
 * - 断言：发送后校验响应（可视化配置行，结果展示在响应区）
 */

import { Plus, Variable, CheckCircle2, XCircle } from 'lucide-react';
import {
  AssertionRule,
  ExtractVariableRule,
  ASSERTION_OPERATORS,
} from '../../../../../services/httpClientApi';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';

const EXTRACT_SOURCES: { value: ExtractVariableRule['source']; label: string }[] = [
  { value: 'body_json', label: '响应 JSON（JSONPath）' },
  { value: 'body_text', label: '响应文本（正则）' },
  { value: 'header', label: '响应头（按名称）' },
  { value: 'status', label: '状态码' },
  { value: 'response_time', label: '耗时（毫秒）' },
];

const ASSERTION_SOURCES: { value: AssertionRule['source']; label: string }[] = [
  { value: 'status', label: '状态码' },
  { value: 'header', label: '响应头' },
  { value: 'body_json', label: '响应 JSON（JSONPath）' },
  { value: 'body_text', label: '响应文本' },
  { value: 'response_time', label: '耗时（毫秒）' },
];

interface PostOperationsProps {
  assertions: AssertionRule[];
  extractVariables: ExtractVariableRule[];
  onAssertionsChange: (rules: AssertionRule[]) => void;
  onExtractVariablesChange: (rules: ExtractVariableRule[]) => void;
}

export default function PostOperations({
  assertions,
  extractVariables,
  onAssertionsChange,
  onExtractVariablesChange,
}: PostOperationsProps) {
  // ---- 提取变量 ----
  const addExtract = () => {
    onExtractVariablesChange([
      ...extractVariables,
      { name: '', source: 'body_json', expression: '', index: null, enabled: true },
    ]);
  };

  const updateExtract = (index: number, patch: Partial<ExtractVariableRule>) => {
    onExtractVariablesChange(extractVariables.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  };

  const removeExtract = (index: number) => {
    onExtractVariablesChange(extractVariables.filter((_, i) => i !== index));
  };

  // ---- 断言 ----
  const addAssertion = () => {
    onAssertionsChange([
      ...assertions,
      { name: '', source: 'status', expression: '', operator: 'equal', value: '', enabled: true },
    ]);
  };

  const updateAssertion = (index: number, patch: Partial<AssertionRule>) => {
    onAssertionsChange(assertions.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  };

  const removeAssertion = (index: number) => {
    onAssertionsChange(assertions.filter((_, i) => i !== index));
  };

  const needExpression = (source: string) =>
    source === 'body_json' || source === 'body_text' || source === 'header';

  return (
    <div className="space-y-6">
      {/* 提取变量 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Variable className="w-4 h-4 text-accent-secondary" />
            <span className="text-sm font-medium">提取变量</span>
            <span className="text-xs text-ink-faint">发送后从响应中提取值并写入当前激活的环境变量</span>
          </div>
          <Button variant="ghost" size="sm" onClick={addExtract} className="text-accent-secondary hover:text-accent-secondary text-xs h-7">
            <Plus className="w-3.5 h-3.5 mr-1" />
            添加提取
          </Button>
        </div>

        {extractVariables.length === 0 ? (
          <div className="text-xs text-ink-faint border border-dashed border-border rounded-lg py-4 text-center">
            暂无提取规则（例如从登录响应中提取 token 供后续请求使用）
          </div>
        ) : (
          <div className="space-y-1">
            {extractVariables.map((rule, index) => (
              <div
                key={index}
                className={`flex items-center gap-2 p-2 rounded-lg border border-border bg-surface-2/40 ${rule.enabled ? '' : 'opacity-50'}`}
              >
                <input
                  type="checkbox"
                  checked={rule.enabled}
                  onChange={(e) => updateExtract(index, { enabled: e.target.checked })}
                  className="h-3.5 w-3.5 cursor-pointer accent-accent-secondary"
                  title="启用/禁用"
                />
                <Input
                  type="text"
                  value={rule.name}
                  onChange={(e) => updateExtract(index, { name: e.target.value })}
                  placeholder="变量名"
                  className="w-40 h-8 text-xs font-mono"
                />
                <Select value={rule.source} onValueChange={(v) => updateExtract(index, { source: v as ExtractVariableRule['source'] })}>
                  <SelectTrigger className="w-44 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EXTRACT_SOURCES.map(s => (
                      <SelectItem key={s.value} value={s.value} className="text-xs">{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {needExpression(rule.source) && (
                  <Input
                    type="text"
                    value={rule.expression}
                    onChange={(e) => updateExtract(index, { expression: e.target.value })}
                    placeholder={rule.source === 'body_json' ? '$.data.token' : rule.source === 'body_text' ? '正则表达式' : 'Header 名称'}
                    className="flex-1 h-8 text-xs font-mono"
                  />
                )}
                {rule.source === 'body_json' && (
                  <Input
                    type="number"
                    value={rule.index ?? ''}
                    onChange={(e) => updateExtract(index, { index: e.target.value === '' ? null : Number(e.target.value) })}
                    placeholder="索引"
                    className="w-16 h-8 text-xs"
                    title="多匹配时取第几项（0 开始，留空取第一项）"
                  />
                )}
                <Button variant="ghost" size="icon" onClick={() => removeExtract(index)} className="h-7 w-7 text-ink-faint hover:text-danger">
                  <XCircle className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 断言 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-success" />
            <span className="text-sm font-medium">断言</span>
            <span className="text-xs text-ink-faint">发送后自动校验响应，结果显示在响应区</span>
          </div>
          <Button variant="ghost" size="sm" onClick={addAssertion} className="text-accent-secondary hover:text-accent-secondary text-xs h-7">
            <Plus className="w-3.5 h-3.5 mr-1" />
            添加断言
          </Button>
        </div>

        {assertions.length === 0 ? (
          <div className="text-xs text-ink-faint border border-dashed border-border rounded-lg py-4 text-center">
            暂无断言规则（例如校验状态码等于 200、响应字段包含某值）
          </div>
        ) : (
          <div className="space-y-1">
            {assertions.map((rule, index) => (
              <div
                key={index}
                className={`flex items-center gap-2 p-2 rounded-lg border border-border bg-surface-2/40 ${rule.enabled ? '' : 'opacity-50'}`}
              >
                <input
                  type="checkbox"
                  checked={rule.enabled}
                  onChange={(e) => updateAssertion(index, { enabled: e.target.checked })}
                  className="h-3.5 w-3.5 cursor-pointer accent-accent-secondary"
                  title="启用/禁用"
                />
                <Input
                  type="text"
                  value={rule.name || ''}
                  onChange={(e) => updateAssertion(index, { name: e.target.value })}
                  placeholder="断言名称（可选）"
                  className="w-36 h-8 text-xs"
                />
                <Select value={rule.source} onValueChange={(v) => updateAssertion(index, { source: v as AssertionRule['source'] })}>
                  <SelectTrigger className="w-40 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ASSERTION_SOURCES.map(s => (
                      <SelectItem key={s.value} value={s.value} className="text-xs">{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {needExpression(rule.source) && (
                  <Input
                    type="text"
                    value={rule.expression}
                    onChange={(e) => updateAssertion(index, { expression: e.target.value })}
                    placeholder={rule.source === 'body_json' ? '$.data.status' : rule.source === 'header' ? 'Header 名称' : '匹配文本'}
                    className="flex-1 h-8 text-xs font-mono"
                  />
                )}
                <Select value={rule.operator} onValueChange={(v) => updateAssertion(index, { operator: v })}>
                  <SelectTrigger className="w-32 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ASSERTION_OPERATORS.map(op => (
                      <SelectItem key={op.value} value={op.value} className="text-xs">{op.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {!['is_empty', 'not_empty', 'exists', 'not_exists'].includes(rule.operator) && (
                  <Input
                    type="text"
                    value={rule.value}
                    onChange={(e) => updateAssertion(index, { value: e.target.value })}
                    placeholder="期望值"
                    className="w-36 h-8 text-xs font-mono"
                  />
                )}
                <Button variant="ghost" size="icon" onClick={() => removeAssertion(index)} className="h-7 w-7 text-ink-faint hover:text-danger">
                  <XCircle className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
