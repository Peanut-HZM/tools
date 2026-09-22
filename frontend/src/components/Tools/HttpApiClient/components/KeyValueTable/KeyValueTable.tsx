/**
 * KeyValueTable - Apifox 风格的键值对编辑表格
 *
 * 特性：
 * - 每行 checkbox 启用/禁用（禁用后不发送，但保留在表格中）
 * - Key 常用值自动补全（Headers 场景）
 * - Value 支持 {{变量}} 与内置动态变量（$timestamp 等）补全
 * - 批量编辑（Bulk Edit）：每行 `key: value` 文本模式
 * - 可选的类型列（form-data 场景由调用方扩展）
 */

import { useMemo, useRef, useState } from 'react';
import { Plus, Trash2, AlignLeft, AlignJustify } from 'lucide-react';
import { KeyValueItem } from '../../../../../services/httpClientApi';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

/** 内置动态变量（与后端 _dyn_value 保持一致） */
export const DYNAMIC_VARIABLES: string[] = [
  '$timestamp', '$timestampMs', '$isoTimestamp', '$dateNow', '$dateToday',
  '$uuid', '$guid', '$randomInt', '$randomBoolean',
  '$randomFirstName', '$randomLastName', '$randomName', '$randomEmail', '$randomPhone',
  '$randomCity', '$randomCountry', '$randomLatitude', '$randomLongitude',
  '$randomUrl', '$randomIPv4', '$randomUserAgent',
  '$randomColor', '$randomHexColor', '$randomPrice', '$randomCompanyName',
  '$randomWord', '$randomWords', '$randomSentence', '$randomParagraph',
];

/** 常用请求头 */
export const COMMON_HEADERS: string[] = [
  'Accept', 'Accept-Language', 'Authorization', 'Cache-Control', 'Content-Type',
  'Content-Length', 'Cookie', 'Origin', 'Referer', 'User-Agent',
  'X-Requested-With', 'X-API-Key', 'X-CSRF-Token', 'If-None-Match', 'Range',
];

/** Content-Type 快捷值 */
export const CONTENT_TYPE_SUGGESTIONS: string[] = [
  'application/json', 'application/xml', 'application/x-www-form-urlencoded',
  'multipart/form-data', 'text/plain', 'text/html', 'application/octet-stream',
];

interface KeyValueTableProps {
  items: KeyValueItem[];
  onChange: (items: KeyValueItem[]) => void;
  keyPlaceholder?: string;
  valuePlaceholder?: string;
  /** Key 输入建议（如常用请求头） */
  keySuggestions?: string[];
  /** Value 输入建议（如 Content-Type 常见值） */
  valueSuggestions?: Record<string, string[]>;
  /** 环境变量名（用于 {{变量}} 补全） */
  envVariableNames?: string[];
  /** 空态提示 */
  emptyHint?: string;
}

export default function KeyValueTable({
  items,
  onChange,
  keyPlaceholder = 'Key',
  valuePlaceholder = 'Value',
  keySuggestions,
  valueSuggestions,
  envVariableNames = [],
  emptyHint = '暂无条目，点击下方按钮添加',
}: KeyValueTableProps) {
  const [bulkMode, setBulkMode] = useState(false);
  const [bulkText, setBulkText] = useState('');
  const tableRef = useRef<HTMLDivElement>(null);

  const valueDatalistId = useMemo(() => `kv-values-${Math.random().toString(36).slice(2, 9)}`, []);
  const keyDatalistId = useMemo(() => `kv-keys-${Math.random().toString(36).slice(2, 9)}`, []);

  // 变量补全列表：环境变量 + 动态变量
  const variableSuggestions = useMemo(
    () => [
      ...envVariableNames.map(name => `{{${name}}}`),
      ...DYNAMIC_VARIABLES.map(name => `{{${name}}}`),
    ],
    [envVariableNames]
  );

  const updateRow = (index: number, patch: Partial<KeyValueItem>) => {
    const newItems = items.map((item, i) => (i === index ? { ...item, ...patch } : item));
    onChange(newItems);
  };

  const removeRow = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  const addRow = () => {
    onChange([...items, { key: '', value: '', enabled: true, description: '' }]);
    // 滚动到底部，聚焦新增行
    requestAnimationFrame(() => {
      tableRef.current?.scrollTo({ top: tableRef.current.scrollHeight, behavior: 'smooth' });
    });
  };

  // ---- 批量编辑 ----
  const enterBulkMode = () => {
    setBulkText(items.map(item => `${item.key}: ${item.value}`).join('\n'));
    setBulkMode(true);
  };

  const applyBulkEdit = () => {
    const newItems: KeyValueItem[] = [];
    for (const line of bulkText.split('\n')) {
      if (!line.trim()) continue;
      const idx = line.indexOf(':');
      if (idx > 0) {
        const key = line.slice(0, idx).trim();
        const value = line.slice(idx + 1).trim();
        if (key) newItems.push({ key, value, enabled: true, description: '' });
      }
    }
    onChange(newItems);
    setBulkMode(false);
  };

  const currentKeySuggestions = keySuggestions || [];
  const valueSuggestionFor = (key: string): string[] => {
    if (!valueSuggestions) return variableSuggestions;
    const specific = valueSuggestions[key.toLowerCase()] || [];
    return [...specific, ...variableSuggestions];
  };

  if (bulkMode) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-ink-faint">
            每行一条，格式：<code className="text-accent-secondary">Key: Value</code>（支持 {'{{变量}}'}）
          </span>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setBulkMode(false)} className="text-xs h-7">
              <AlignJustify className="w-3.5 h-3.5 mr-1" />
              取消
            </Button>
            <Button variant="default" size="sm" onClick={applyBulkEdit} className="text-xs h-7">
              <AlignLeft className="w-3.5 h-3.5 mr-1" />
              应用
            </Button>
          </div>
        </div>
        <textarea
          value={bulkText}
          onChange={(e) => setBulkText(e.target.value)}
          className="w-full h-48 bg-canvas text-ink px-3 py-2 rounded-lg border border-border
                     font-mono text-sm resize-none focus:border-accent-secondary focus:outline-none"
          autoFocus
        />
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <datalist id={keyDatalistId}>
        {currentKeySuggestions.map(s => <option key={s} value={s} />)}
      </datalist>
      <datalist id={valueDatalistId}>
        {variableSuggestions.map(s => <option key={s} value={s} />)}
      </datalist>

      <div ref={tableRef} className="overflow-y-auto max-h-72 rounded-lg border border-border">
        {items.length === 0 ? (
          <div className="text-ink-faint text-xs text-center py-6">{emptyHint}</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-2/60 text-ink-faint text-xs">
                <th className="w-9 py-1.5 font-normal"></th>
                <th className="py-1.5 px-1 font-normal text-left w-[35%]">Key</th>
                <th className="py-1.5 px-1 font-normal text-left">Value</th>
                <th className="py-1.5 px-1 font-normal text-left w-[18%]">描述</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                const valueSuggestionsFor = valueSuggestionFor(item.key);
                return (
                  <tr
                    key={index}
                    className={`border-t border-border/60 ${item.enabled ? '' : 'opacity-50'}`}
                  >
                    <td className="pl-2">
                      <input
                        type="checkbox"
                        checked={item.enabled}
                        onChange={(e) => updateRow(index, { enabled: e.target.checked })}
                        className="h-3.5 w-3.5 cursor-pointer accent-accent-secondary"
                        title={item.enabled ? '已启用（点击禁用）' : '已禁用（点击启用）'}
                      />
                    </td>
                    <td className="py-0.5 px-1">
                      <input
                        type="text"
                        value={item.key}
                        list={keyDatalistId}
                        onChange={(e) => updateRow(index, { key: e.target.value })}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            addRow();
                          }
                        }}
                        placeholder={keyPlaceholder}
                        className="w-full bg-transparent px-1.5 py-1 font-mono text-xs text-ink
                                   rounded focus:bg-canvas focus:outline-none focus:ring-1 focus:ring-accent-secondary/50"
                      />
                    </td>
                    <td className="py-0.5 px-1">
                      <input
                        type="text"
                        value={item.value}
                        list={valueDatalistId}
                        onChange={(e) => updateRow(index, { value: e.target.value })}
                        placeholder={valuePlaceholder}
                        className="w-full bg-transparent px-1.5 py-1 font-mono text-xs text-ink
                                   rounded focus:bg-canvas focus:outline-none focus:ring-1 focus:ring-accent-secondary/50"
                      />
                      {/* 为当前行的 key 定制 value 建议 */}
                      {valueSuggestionsFor.length > 0 && item.key && (
                        <datalist id={`${valueDatalistId}-${index}`}>
                          {valueSuggestionsFor.map(s => <option key={s} value={s} />)}
                        </datalist>
                      )}
                    </td>
                    <td className="py-0.5 px-1">
                      <input
                        type="text"
                        value={item.description || ''}
                        onChange={(e) => updateRow(index, { description: e.target.value })}
                        placeholder="备注"
                        className="w-full bg-transparent px-1.5 py-1 text-xs text-ink-muted
                                   rounded focus:bg-canvas focus:outline-none focus:ring-1 focus:ring-accent-secondary/50"
                      />
                    </td>
                    <td>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeRow(index)}
                        className="h-6 w-6 text-ink-faint hover:text-danger"
                        title="删除"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={addRow}
          className="text-accent-secondary hover:text-accent-secondary text-xs h-7"
        >
          <Plus className="w-3.5 h-3.5 mr-1" />
          添加
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={enterBulkMode}
          className="text-ink-muted hover:text-ink text-xs h-7"
          title="以文本模式批量编辑（Key: Value 每行一条）"
        >
          <AlignLeft className="w-3.5 h-3.5 mr-1" />
          批量编辑
        </Button>
        {items.length > 0 && (
          <span className="text-xs text-ink-faint ml-auto">
            {items.filter(i => i.enabled).length}/{items.length} 已启用
          </span>
        )}
      </div>
    </div>
  );
}
