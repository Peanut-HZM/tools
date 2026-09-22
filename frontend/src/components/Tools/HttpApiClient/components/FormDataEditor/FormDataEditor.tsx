/**
 * FormDataEditor 组件
 * 用于编辑 form-data 类型的请求体（支持 text/file 条目、启用/禁用、变量补全）
 */
import { FormDataEntry } from '../../../../../services/httpClientApi';
import { X, Plus, FileText } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

interface FormDataEditorProps {
  formData: FormDataEntry[];
  onChange: (formData: FormDataEntry[]) => void;
  /** 环境变量名（text 值的 {{变量}} 补全） */
  envVariableNames?: string[];
}

export default function FormDataEditor({ formData, onChange, envVariableNames = [] }: FormDataEditorProps) {
  const entries = formData || [];
  const varDatalistId = `fd-vars-${Math.random().toString(36).slice(2, 9)}`;

  /** 添加新的 form-data 条目 */
  const handleAdd = () => {
    onChange([...entries, { key: '', value: '', type: 'text', enabled: true, description: '' }]);
  };

  /** 删除指定索引的条目 */
  const handleRemove = (index: number) => {
    onChange(entries.filter((_, i) => i !== index));
  };

  /** 更新指定条目的字段值 */
  const handleChange = (index: number, field: keyof FormDataEntry, value: any) => {
    const newEntries = entries.map((entry, i) =>
      i === index ? { ...entry, [field]: value } : entry
    );
    onChange(newEntries);
  };

  /** 处理文件选择 */
  const handleFileChange = (index: number, file: File) => {
    const newEntries = entries.map((entry, i) =>
      i === index ? { ...entry, file, value: file.name } : entry
    );
    onChange(newEntries);
  };

  return (
    <div className="space-y-2">
      <datalist id={varDatalistId}>
        {envVariableNames.map(name => <option key={name} value={`{{${name}}}`} />)}
      </datalist>

      {entries.length === 0 ? (
        <div className="text-ink-faint text-xs text-center py-6 border border-dashed border-border rounded-lg">
          暂无 Form-data 条目，点击下方按钮添加（Text 为普通字段，File 为文件上传）
        </div>
      ) : (
        <div className="rounded-lg border border-border overflow-y-auto max-h-72">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-2/60 text-ink-faint text-xs">
                <th className="w-9 py-1.5 font-normal"></th>
                <th className="py-1.5 px-1 font-normal text-left w-24">类型</th>
                <th className="py-1.5 px-1 font-normal text-left w-[30%]">Key</th>
                <th className="py-1.5 px-1 font-normal text-left">Value</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, index) => (
                <tr key={index} className={`border-t border-border/60 ${entry.enabled === false ? 'opacity-50' : ''}`}>
                  <td className="pl-2">
                    <input
                      type="checkbox"
                      checked={entry.enabled !== false}
                      onChange={(e) => handleChange(index, 'enabled', e.target.checked)}
                      className="h-3.5 w-3.5 cursor-pointer accent-accent-secondary"
                      title="启用/禁用"
                    />
                  </td>
                  <td className="py-0.5 px-1">
                    <Select value={entry.type} onValueChange={(v) => handleChange(index, 'type', v)}>
                      <SelectTrigger className="h-7 text-xs border-0 bg-transparent px-2 focus:ring-0">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="text" className="text-xs">Text</SelectItem>
                        <SelectItem value="file" className="text-xs">File</SelectItem>
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="py-0.5 px-1">
                    <Input
                      type="text"
                      value={entry.key}
                      onChange={(e) => handleChange(index, 'key', e.target.value)}
                      placeholder="字段名"
                      className="h-7 bg-transparent border-0 px-1.5 font-mono text-xs rounded focus:bg-canvas focus:ring-1 focus:ring-accent-secondary/50"
                    />
                  </td>
                  <td className="py-0.5 px-1">
                    {entry.type === 'text' ? (
                      <Input
                        type="text"
                        value={entry.value}
                        list={varDatalistId}
                        onChange={(e) => handleChange(index, 'value', e.target.value)}
                        placeholder="字段值（支持 {{变量}}）"
                        className="h-7 bg-transparent border-0 px-1.5 font-mono text-xs rounded focus:bg-canvas focus:ring-1 focus:ring-accent-secondary/50"
                      />
                    ) : (
                      <div className="flex items-center gap-2 py-0.5">
                        <Input
                          type="file"
                          onChange={(e) => e.target.files?.[0] && handleFileChange(index, e.target.files[0])}
                          className="hidden"
                          id={`fd-file-${index}`}
                        />
                        <label
                          htmlFor={`fd-file-${index}`}
                          className="flex-1 flex items-center gap-2 bg-surface-2 text-ink-muted px-3 py-1 rounded border border-border text-xs cursor-pointer hover:bg-surface-3"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          {entry.file ? `${entry.file.name}（${(entry.file.size / 1024).toFixed(1)} KB）` : entry.value || '选择文件...'}
                        </label>
                      </div>
                    )}
                  </td>
                  <td>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemove(index)}
                      className="h-6 w-6 text-ink-faint hover:text-danger"
                      title="删除"
                    >
                      <X className="w-3.5 h-3.5" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleAdd}
          className="text-accent-secondary hover:text-accent-secondary text-xs h-7"
        >
          <Plus className="w-3.5 h-3.5 mr-1" />
          添加字段
        </Button>
        {entries.length > 0 && (
          <span className="text-xs text-ink-faint">
            {entries.filter(e => e.enabled !== false).length}/{entries.length} 已启用
          </span>
        )}
      </div>
    </div>
  );
}
