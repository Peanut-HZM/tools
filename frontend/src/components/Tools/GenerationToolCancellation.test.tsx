import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ImageGenerationTool from './ImageGeneration/ImageGenerationTool';
import VideoGenerationTool from './VideoGeneration/VideoGenerationTool';
import { conversationApi, type Conversation } from '../../services/conversationApi';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { agent_id: 'agent-1' } })),
  },
}));

vi.mock('../../api/authApi', () => ({
  getAuthHeaders: vi.fn(() => ({})),
}));

vi.mock('../../services/conversationApi', () => ({
  conversationApi: {
    getMessages: vi.fn(() => Promise.resolve([])),
    createConversation: vi.fn(),
    sendMessageStream: vi.fn(() => vi.fn()),
  },
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

const conversation: Conversation = {
  id: 'new-conversation',
  user_id: 'user-1',
  title: '新会话',
  current_stage: 'requirement_clarification',
  version: 1,
  created_at: '2026-10-20T00:00:00Z',
  updated_at: '2026-10-20T00:00:00Z',
};

const tools = [
  {
    name: '图像生成',
    Component: ImageGenerationTool,
    placeholder: '描述你的图像需求…（可先简单说，我会追问细节）',
    storageKey: 'image-gen-conversation-id',
  },
  {
    name: '视频生成',
    Component: VideoGenerationTool,
    placeholder: '描述你的视频需求…（如"高燃动漫战斗场景"）',
    storageKey: 'video-gen-conversation-id',
  },
];

describe.each(tools)('$name 首次发送取消', ({ Component, placeholder, storageKey }) => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(cleanup);

  it('创建会话完成前卸载时不启动流', async () => {
    const pendingConversation = deferred<Conversation>();
    vi.mocked(conversationApi.createConversation).mockReturnValue(pendingConversation.promise);
    const { unmount } = render(<Component />);
    const input = await screen.findByPlaceholderText(placeholder);
    await waitFor(() => expect((input as HTMLInputElement).disabled).toBe(false));

    fireEvent.change(input, { target: { value: '生成需求' } });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));
    unmount();

    await act(async () => {
      pendingConversation.resolve(conversation);
      await pendingConversation.promise;
    });

    expect(conversationApi.sendMessageStream).not.toHaveBeenCalled();
    expect(localStorage.getItem(storageKey)).toBeNull();
  });

  it('创建会话完成前开始新对话时不启动旧流并解除 busy', async () => {
    const pendingConversation = deferred<Conversation>();
    vi.mocked(conversationApi.createConversation).mockReturnValue(pendingConversation.promise);
    render(<Component />);
    const input = await screen.findByPlaceholderText(placeholder);
    await waitFor(() => expect((input as HTMLInputElement).disabled).toBe(false));

    fireEvent.change(input, { target: { value: '生成需求' } });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));
    fireEvent.click(screen.getByRole('button', { name: '开始新对话' }));

    await act(async () => {
      pendingConversation.resolve(conversation);
      await pendingConversation.promise;
    });

    expect((input as HTMLInputElement).disabled).toBe(false);
    expect(conversationApi.sendMessageStream).not.toHaveBeenCalled();
    expect(localStorage.getItem(storageKey)).toBeNull();
  });
});
