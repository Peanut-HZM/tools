import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import RequestEditor from './RequestEditor';
import type { HttpRequest } from '../../../../../services/httpClientApi';

// Mock Monaco ScriptEditor（测试环境无法渲染 Monaco）
vi.mock('../ScriptEditor/ScriptEditor', () => ({
  default: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <input data-testid="mock-script-editor" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

const mockRequest: HttpRequest = {
  id: 'req-1',
  collection_id: 'col-1',
  name: '测试请求',
  method: 'GET',
  url: 'https://example.com/api',
  headers: {},
  params: {},
  body_type: 'none',
  auth_type: 'none',
  auth_config: {},
  sort_order: 0,
  created_at: '',
  updated_at: '',
};

afterEach(() => {
  cleanup();
});

describe('RequestEditor 保存/删除按钮', () => {
  it('isModified 为 false 时保存按钮禁用', () => {
    render(
      <RequestEditor
        request={mockRequest}
        isModified={false}
        onUpdate={vi.fn()}
        onSend={vi.fn()}
        sending={false}
        onSave={vi.fn()}
      />
    );
    const saveButton = screen.getByTitle('保存') as HTMLButtonElement;
    expect(saveButton.disabled).toBe(true);
  });

  it('isModified 为 true 时保存按钮可点击且触发 onSave', () => {
    const onSave = vi.fn();
    render(
      <RequestEditor
        request={mockRequest}
        isModified={true}
        onUpdate={vi.fn()}
        onSend={vi.fn()}
        sending={false}
        onSave={onSave}
      />
    );
    const saveButton = screen.getByTitle('保存') as HTMLButtonElement;
    expect(saveButton.disabled).toBe(false);
    fireEvent.click(saveButton);
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('点击删除按钮应触发 onDelete', () => {
    const onDelete = vi.fn();
    render(
      <RequestEditor
        request={mockRequest}
        isModified={false}
        onUpdate={vi.fn()}
        onSend={vi.fn()}
        sending={false}
        onDelete={onDelete}
      />
    );
    fireEvent.click(screen.getByTitle('删除'));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it('未传 onSave 时不渲染保存按钮，未传 onDelete 时不渲染删除按钮', () => {
    render(
      <RequestEditor
        request={mockRequest}
        isModified={true}
        onUpdate={vi.fn()}
        onSend={vi.fn()}
        sending={false}
      />
    );
    expect(screen.queryByTitle('保存')).toBeNull();
    expect(screen.queryByTitle('删除')).toBeNull();
  });
});
