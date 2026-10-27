import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SESSION_KEEP_ALIVE_TOOLS, TabPanels } from './TabPanels';
import { useWorkspaceStore } from '../../stores/workspaceStore';

vi.mock('./toolComponents', () => ({
  toolComponentMap: {
    'tool-a': () => <div>工具 A 内容</div>,
    'tool-b': () => <div>工具 B 内容</div>,
    'database-tool': () => <div>数据库会话内容</div>,
    'ssh-tool': () => <div>SSH 会话内容</div>,
    'markdown-editor': () => <div>文件编辑草稿</div>,
    'json-formatter': () => <div>JSON 草稿</div>,
    'openclaw': () => <div>流式对话任务</div>,
  },
}));

vi.mock('../../i18n', () => ({
  useI18n: () => ({
    t: { workspace: { unknownTool: '未知工具' } },
  }),
}));

describe('TabPanels', () => {
  beforeEach(() => {
    useWorkspaceStore.setState({
      tabs: [
        { id: 'tab-a', toolId: 'tool-a', toolName: '工具 A', toolIcon: '', openedAt: 1 },
        { id: 'tab-b', toolId: 'tool-b', toolName: '工具 B', toolIcon: '', openedAt: 2 },
      ],
      activeTabId: 'tab-a',
    });
  });

  afterEach(cleanup);

  it('保活清单覆盖所有仍使用组件内存保存用户上下文的工具', () => {
    expect(SESSION_KEEP_ALIVE_TOOLS).toEqual(new Set([
      'database-tool', 'ssh-tool', 'markdown-editor', 'redis-tool', 'token-usage',
      'json-formatter', 'calendar', 'ai-assistant', 'key-generator', 'ocr-tool', 'ocr',
      'asr-tool', 'asr', 'markitdown-converter', 'learning-share', 'course-platform',
      'cross-share', 'openclaw', 'product-manager', 'image-downloader',
      'video-downloader', 'image-generation', 'video-generation', 'system-monitor',
    ]));
  });

  it('切换普通工具时卸载非活跃实例，避免后台实例无限累积', () => {
    const { rerender } = render(<TabPanels />);

    expect(screen.getByText('工具 A 内容')).toBeTruthy();
    expect(screen.queryByText('工具 B 内容')).toBeNull();

    useWorkspaceStore.setState({ activeTabId: 'tab-b' });
    rerender(<TabPanels />);

    expect(screen.queryByText('工具 A 内容')).toBeNull();
    expect(screen.getByText('工具 B 内容')).toBeTruthy();
  });

  it('数据库工具在非活跃时仍保留内存会话实例', () => {
    useWorkspaceStore.setState({
      tabs: [
        { id: 'tab-db', toolId: 'database-tool', toolName: '数据库', toolIcon: '', openedAt: 1 },
        { id: 'tab-a', toolId: 'tool-a', toolName: '工具 A', toolIcon: '', openedAt: 2 },
      ],
      activeTabId: 'tab-a',
    });

    render(<TabPanels />);

    expect(screen.getByText('数据库会话内容')).toBeTruthy();
    expect(screen.getByText('工具 A 内容')).toBeTruthy();
  });

  it.each([
    ['ssh-tool', 'SSH 会话内容'],
    ['markdown-editor', '文件编辑草稿'],
    ['json-formatter', 'JSON 草稿'],
    ['openclaw', '流式对话任务'],
  ])('%s 非活跃时保留用户上下文', (toolId, content) => {
    useWorkspaceStore.setState({
      tabs: [
        { id: 'tab-stateful', toolId, toolName: toolId, toolIcon: '', openedAt: 1 },
        { id: 'tab-a', toolId: 'tool-a', toolName: '工具 A', toolIcon: '', openedAt: 2 },
      ],
      activeTabId: 'tab-a',
    });

    render(<TabPanels />);

    expect(screen.getByText(content)).toBeTruthy();
  });

  it('关闭标签后卸载保活工具实例', () => {
    useWorkspaceStore.setState({
      tabs: [
        { id: 'tab-db', toolId: 'database-tool', toolName: '数据库', toolIcon: '', openedAt: 1 },
        { id: 'tab-a', toolId: 'tool-a', toolName: '工具 A', toolIcon: '', openedAt: 2 },
      ],
      activeTabId: 'tab-a',
    });
    const { rerender } = render(<TabPanels />);
    expect(screen.getByText('数据库会话内容')).toBeTruthy();

    useWorkspaceStore.getState().removeTab('tab-db');
    rerender(<TabPanels />);

    expect(screen.queryByText('数据库会话内容')).toBeNull();
  });
});
