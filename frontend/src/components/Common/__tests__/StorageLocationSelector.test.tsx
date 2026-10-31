/**
 * StorageLocationSelector 测试
 *
 * 覆盖：默认选中本机、服务器不可用时隐藏上传选项、切换时触发回调
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import StorageLocationSelector from '../StorageLocationSelector';

// 项目未启用 RTL 自动清理（vitest globals 未开启），需手动清理避免用例间 DOM 串扰
afterEach(() => {
  cleanup();
});

describe('StorageLocationSelector', () => {
  it('默认选中「仅保存在本机」', () => {
    render(<StorageLocationSelector value="local" onChange={vi.fn()} serverAvailable />);

    const localOption = screen.getByRole('radio', { name: /仅保存在本机/ });
    expect(localOption).toBeTruthy();
    expect((localOption as HTMLInputElement).checked).toBe(true);
  });

  it('服务器可用时展示两个选项', () => {
    render(<StorageLocationSelector value="local" onChange={vi.fn()} serverAvailable />);

    expect(screen.getByRole('radio', { name: /仅保存在本机/ })).toBeTruthy();
    expect(screen.getByRole('radio', { name: /上传到服务器/ })).toBeTruthy();
  });

  it('服务器不可用时隐藏「上传到服务器」选项', () => {
    render(
      <StorageLocationSelector value="local" onChange={vi.fn()} serverAvailable={false} />,
    );

    expect(screen.getByRole('radio', { name: /仅保存在本机/ })).toBeTruthy();
    expect(screen.queryByRole('radio', { name: /上传到服务器/ })).toBeNull();
  });

  it('选择「上传到服务器」时触发 onChange', () => {
    const onChange = vi.fn();
    render(<StorageLocationSelector value="local" onChange={onChange} serverAvailable />);

    fireEvent.click(screen.getByRole('radio', { name: /上传到服务器/ }));

    expect(onChange).toHaveBeenCalledWith('server');
  });
});
