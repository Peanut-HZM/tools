/**
 * ImageViewer 单元测试
 *
 * 验证 ImageViewer 在不同输入下的渲染行为：
 * - 无内容时显示占位提示
 * - 有内容时渲染图片元素
 * - 工具栏显示文件名
 * - 未提供文件名时显示默认标签
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import ImageViewer from '../ImageViewer';

describe('ImageViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('显示空状态当无内容时', () => {
    render(<ImageViewer content={null} />);
    expect(screen.getByText('无图片内容')).toBeTruthy();
  });

  it('无内容时不渲染 img 元素', () => {
    render(<ImageViewer content={null} />);
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('渲染图片元素当有内容时', () => {
    render(<ImageViewer content="base64data" fileName="image.jpg" />);
    const img = screen.getByAltText('image.jpg');
    expect(img).toBeTruthy();
    expect(img.getAttribute('src')).toBe('data:image/jpeg;base64,base64data');
  });

  it('根据文件扩展名正确设置 MIME 类型', () => {
    render(<ImageViewer content="data" fileName="logo.png" />);
    const img = screen.getByAltText('logo.png');
    expect(img.getAttribute('src')).toBe('data:image/png;base64,data');
  });

  it('未知扩展名默认使用 image/png', () => {
    render(<ImageViewer content="data" fileName="file.unknown" />);
    const img = screen.getByAltText('file.unknown');
    expect(img.getAttribute('src')).toBe('data:image/png;base64,data');
  });

  it('显示文件名', () => {
    render(<ImageViewer content="base64data" fileName="photo.png" />);
    expect(screen.getByText('photo.png')).toBeTruthy();
  });

  it('未提供文件名时显示默认标签', () => {
    render(<ImageViewer content="base64data" />);
    expect(screen.getAllByText('图片').length).toBeGreaterThan(0);
  });

  it('初始缩放比例为 100%', () => {
    render(<ImageViewer content="base64data" fileName="image.png" />);
    expect(screen.getByText('100%')).toBeTruthy();
  });

  it('点击放大按钮增加缩放比例', () => {
    render(<ImageViewer content="base64data" fileName="image.png" />);
    fireEvent.click(screen.getByText('放大'));
    expect(screen.getByText('110%')).toBeTruthy();
  });

  it('点击缩小按钮减少缩放比例', () => {
    render(<ImageViewer content="base64data" fileName="image.png" />);
    fireEvent.click(screen.getByText('缩小'));
    expect(screen.getByText('90%')).toBeTruthy();
  });

  it('点击重置按钮恢复缩放比例为 100%', () => {
    render(<ImageViewer content="base64data" fileName="image.png" />);
    fireEvent.click(screen.getByText('放大'));
    fireEvent.click(screen.getByText('放大'));
    expect(screen.getByText('120%')).toBeTruthy();
    fireEvent.click(screen.getByText('重置'));
    expect(screen.getByText('100%')).toBeTruthy();
  });
});
