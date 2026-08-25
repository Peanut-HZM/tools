/**
 * FormDataEditor 组件
 * 用于编辑 form-data 类型的请求体
 */
import { useState } from 'react';
import { FormDataEntry } from '../../../../../services/httpClientApi';

interface FormDataEditorProps {
  formData: FormDataEntry[];
  onChange: (formData: FormDataEntry[]) => void;
}

export default function FormDataEditor({ formData, onChange }: FormDataEditorProps) {
  const [entries, setEntries] = useState<FormDataEntry[]>(formData || []);

  /** 添加新的 form-data 条目 */
  const handleAdd = () => {
    const newEntry: FormDataEntry = {
      key: `key_${Date.now()}`,
      value: '',
      type: 'text',
    };
    const newEntries = [...entries, newEntry];
    setEntries(newEntries);
    onChange(newEntries);
  };

  /** 删除指定索引的条目 */
  const handleRemove = (index: number) => {
    const newEntries = entries.filter((_, i) => i !== index);
    setEntries(newEntries);
    onChange(newEntries);
  };

  /** 更新指定条目的字段值 */
  const handleChange = (index: number, field: keyof FormDataEntry, value: any) => {
    const newEntries = [...entries];
    newEntries[index] = { ...newEntries[index], [field]: value };
    setEntries(newEntries);
    onChange(newEntries);
  };

  /** 处理文件选择 */
  const handleFileChange = (index: number, file: File) => {
    const newEntries = [...entries];
    newEntries[index] = { ...newEntries[index], file, value: file.name };
    setEntries(newEntries);
    onChange(newEntries);
  };

  return (
    <div className="space-y-3">
      {entries.length === 0 ? (
        <div className="text-ink-faint text-sm text-center py-8">
          暂无 Form-data，点击下方按钮添加
        </div>
      ) : (
        entries.map((entry, index) => (
          <div key={index} className="flex items-center gap-2">
            {/* 类型选择 */}
            <select
              value={entry.type}
              onChange={(e) => handleChange(index, 'type', e.target.value)}
              className="bg-surface-2 text-ink-inverse px-2 py-2 rounded border border-border text-sm"
            >
              <option value="text">Text</option>
              <option value="file">File</option>
            </select>

            {/* Key 输入 */}
            <input
              type="text"
              value={entry.key}
              onChange={(e) => handleChange(index, 'key', e.target.value)}
              placeholder="Key"
              className="flex-1 bg-surface-2 text-ink-inverse px-3 py-2 rounded border border-border text-sm"
            />

            {/* Value 输入（text 类型）或文件选择（file 类型） */}
            {entry.type === 'text' ? (
              <input
                type="text"
                value={entry.value}
                onChange={(e) => handleChange(index, 'value', e.target.value)}
                placeholder="Value"
                className="flex-1 bg-surface-2 text-ink-inverse px-3 py-2 rounded border border-border text-sm"
              />
            ) : (
              <div className="flex-1 flex items-center gap-2">
                <input
                  type="file"
                  onChange={(e) => e.target.files?.[0] && handleFileChange(index, e.target.files[0])}
                  className="hidden"
                  id={`file-${index}`}
                />
                <label
                  htmlFor={`file-${index}`}
                  className="flex-1 bg-surface-2 text-ink-inverse px-3 py-2 rounded border border-border text-sm cursor-pointer hover:bg-surface-3"
                >
                  {entry.file ? entry.file.name : '选择文件...'}
                </label>
              </div>
            )}

            {/* 删除按钮 */}
            <button
              onClick={() => handleRemove(index)}
              className="text-ink-faint hover:text-danger transition-colors"
            >
              <i className="fas fa-times"></i>
            </button>
          </div>
        ))
      )}

      <button
        onClick={handleAdd}
        className="text-accent-secondary hover:text-accent-secondary transition-colors text-sm"
      >
        <i className="fas fa-plus mr-2"></i>
        添加 Form-data
      </button>
    </div>
  );
}
