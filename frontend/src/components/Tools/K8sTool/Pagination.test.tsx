/**
 * Pagination 分页器组件单元测试
 */
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { Pagination } from './Pagination';

afterEach(() => cleanup());

describe('Pagination - 渲染', () => {
  it('显示总数和当前页码', () => {
    render(
      <Pagination
        total={100}
        currentPage={1}
        pageSize={20}
        onPageChange={vi.fn()}
        onPageSizeChange={vi.fn()}
      />
    );
    expect(screen.getByText(/共 100 条/)).toBeTruthy();
    expect(screen.getByText(/第 1 页/)).toBeTruthy();
    expect(screen.getByText(/共 5 页/)).toBeTruthy();
  });

  it('总数为 0 时显示无数据', () => {
    render(
      <Pagination
        total={0}
        currentPage={1}
        pageSize={20}
        onPageChange={vi.fn()}
        onPageSizeChange={vi.fn()}
      />
    );
    expect(screen.getByText(/共 0 条/)).toBeTruthy();
  });
});

describe('Pagination - 翻页按钮', () => {
  it('首页时上一页按钮禁用', () => {
    const onPageChange = vi.fn();
    render(
      <Pagination
        total={100}
        currentPage={1}
        pageSize={20}
        onPageChange={onPageChange}
        onPageSizeChange={vi.fn()}
      />
    );
    const prevBtn = screen.getByText('上一页').closest('button');
    expect(prevBtn?.disabled).toBe(true);
  });

  it('末页时下一页按钮禁用', () => {
    const onPageChange = vi.fn();
    render(
      <Pagination
        total={100}
        currentPage={5}
        pageSize={20}
        onPageChange={onPageChange}
        onPageSizeChange={vi.fn()}
      />
    );
    const nextBtn = screen.getByText('下一页').closest('button');
    expect(nextBtn?.disabled).toBe(true);
  });

  it('点击下一页调用 onPageChange(currentPage + 1)', () => {
    const onPageChange = vi.fn();
    render(
      <Pagination
        total={100}
        currentPage={2}
        pageSize={20}
        onPageChange={onPageChange}
        onPageSizeChange={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('下一页'));
    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it('点击上一页调用 onPageChange(currentPage - 1)', () => {
    const onPageChange = vi.fn();
    render(
      <Pagination
        total={100}
        currentPage={3}
        pageSize={20}
        onPageChange={onPageChange}
        onPageSizeChange={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('上一页'));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });
});

describe('Pagination - 每页条数切换', () => {
  it('提供 10/20/50 三个选项', () => {
    render(
      <Pagination
        total={100}
        currentPage={1}
        pageSize={20}
        onPageChange={vi.fn()}
        onPageSizeChange={vi.fn()}
      />
    );
    // 当前选中 20
    expect(screen.getByText('20条/页')).toBeTruthy();
  });

  it('切换条数调用 onPageSizeChange 并重置到第 1 页', () => {
    const onPageChange = vi.fn();
    const onPageSizeChange = vi.fn();
    render(
      <Pagination
        total={100}
        currentPage={3}
        pageSize={20}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
      />
    );
    // 点击 50 条/页选项（通过角色查找）
    const trigger = screen.getByText('20条/页');
    fireEvent.click(trigger);
    // Radix Select 会打开下拉菜单
    const option50 = screen.getByText('50条/页');
    fireEvent.click(option50);
    expect(onPageSizeChange).toHaveBeenCalledWith(50);
    expect(onPageChange).toHaveBeenCalledWith(1);
  });
});
