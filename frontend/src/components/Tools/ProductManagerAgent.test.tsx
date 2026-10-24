import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProductManagerAgent from './ProductManagerAgent';
import { conversationApi, type Conversation, type Message } from '../../services/conversationApi';

vi.mock('../../services/conversationApi', () => ({
  conversationApi: {
    getConversations: vi.fn(() => Promise.resolve([])),
    getConversation: vi.fn(),
    getMessages: vi.fn(),
    createConversation: vi.fn(),
    sendMessageStream: vi.fn(),
  },
}));

vi.mock('../../services/llmConfigApi', () => ({
  llmConfigApi: { getConfigs: vi.fn(() => Promise.resolve([])) },
}));

vi.mock('../../services/agentApi', () => ({
  agentApi: { getAgents: vi.fn(() => Promise.resolve([])) },
}));

vi.mock('../ProductManagerAgent/Sidebar', () => ({
  default: ({ onSelectConversation }: { onSelectConversation: (id: string) => void }) => (
    <button onClick={() => onSelectConversation('conversation-b')}>切换到会话 B</button>
  ),
}));

vi.mock('../ProductManagerAgent/ChatInterface', () => ({
  default: ({
    messages,
    onSendMessage,
  }: {
    messages: Message[];
    onSendMessage: (content: string) => void;
  }) => (
    <div>
      <span>{messages.map((message) => message.content).join('|')}</span>
      <button onClick={() => onSendMessage('测试消息')}>发送测试消息</button>
    </div>
  ),
}));

vi.mock('../ProductManagerAgent/PRDPreview', () => ({ default: () => null }));
vi.mock('../ProductManagerAgent/ExportDialog', () => ({ default: () => null }));
vi.mock('../Harness/MemoryViewer', () => ({ MemoryViewer: () => null }));
vi.mock('../Harness/SkillsViewer', () => ({ SkillsViewer: () => null }));
vi.mock('../Harness/TraceViewer', () => ({ TraceViewer: () => null }));
vi.mock('../Harness/TimeTravel/TimelinePanel', () => ({ TimelinePanel: () => null }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

function conversation(id: string, title: string): Conversation {
  return {
    id,
    user_id: 'user-1',
    title,
    current_stage: 'requirement_clarification',
    version: 1,
    created_at: '2026-10-20T00:00:00Z',
    updated_at: '2026-10-20T00:00:00Z',
  };
}

function message(conversationId: string, content: string): Message {
  return {
    id: `message-${conversationId}`,
    conversation_id: conversationId,
    sender_type: 'agent',
    content,
    message_type: 'text',
    sent_at: '2026-10-20T00:00:00Z',
  };
}

function HistoryNavigation() {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate('/workspace?pmConversation=conversation-b')}>
      历史切换到会话 B
    </button>
  );
}

describe('ProductManagerAgent 会话请求隔离', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(cleanup);

  it('切换会话后忽略旧会话迟到的详情和消息', async () => {
    const oldConversation = deferred<Conversation>();
    const oldMessages = deferred<Message[]>();
    vi.mocked(conversationApi.getConversation).mockImplementation((id) => (
      id === 'conversation-a'
        ? oldConversation.promise
        : Promise.resolve(conversation(id, '会话 B'))
    ));
    vi.mocked(conversationApi.getMessages).mockImplementation((id) => (
      id === 'conversation-a'
        ? oldMessages.promise
        : Promise.resolve([message(id, 'B 的消息')])
    ));

    render(
      <MemoryRouter initialEntries={['/workspace?pmConversation=conversation-a']}>
        <Routes>
          <Route path="/workspace" element={<ProductManagerAgent />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole('button', { name: '切换到会话 B' }));
    await screen.findByRole('heading', { name: '会话 B' });
    expect(screen.getByText('B 的消息')).toBeTruthy();

    await act(async () => {
      oldConversation.resolve(conversation('conversation-a', '会话 A'));
      oldMessages.resolve([message('conversation-a', 'A 的迟到消息')]);
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '会话 B' })).toBeTruthy();
      expect(screen.queryByText('A 的迟到消息')).toBeNull();
    });
  });

  it('路由切换时取消旧流并在新会话加载期间清空旧内容', async () => {
    const nextConversation = deferred<Conversation>();
    const nextMessages = deferred<Message[]>();
    const cancelStream = vi.fn();
    vi.mocked(conversationApi.sendMessageStream).mockReturnValue(cancelStream);
    vi.mocked(conversationApi.getConversation).mockImplementation((id) => (
      id === 'conversation-a'
        ? Promise.resolve(conversation(id, '会话 A'))
        : nextConversation.promise
    ));
    vi.mocked(conversationApi.getMessages).mockImplementation((id) => (
      id === 'conversation-a'
        ? Promise.resolve([message(id, 'A 的消息')])
        : nextMessages.promise
    ));

    render(
      <MemoryRouter initialEntries={['/workspace?pmConversation=conversation-a']}>
        <HistoryNavigation />
        <Routes>
          <Route path="/workspace" element={<ProductManagerAgent />} />
        </Routes>
      </MemoryRouter>,
    );

    await screen.findByRole('heading', { name: '会话 A' });
    expect(screen.getByText('A 的消息')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '发送测试消息' }));
    fireEvent.click(screen.getByRole('button', { name: '历史切换到会话 B' }));

    expect(cancelStream).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('heading', { name: '会话 A' })).toBeNull();
    expect(screen.queryByText('A 的消息')).toBeNull();

    await act(async () => {
      nextConversation.resolve(conversation('conversation-b', '会话 B'));
      await nextConversation.promise;
    });
    expect(screen.getByText('正在加载会话...')).toBeTruthy();
    expect(screen.queryByRole('button', { name: '发送测试消息' })).toBeNull();

    await act(async () => {
      nextMessages.resolve([message('conversation-b', 'B 的消息')]);
      await nextMessages.promise;
    });

    await screen.findByRole('heading', { name: '会话 B' });
    expect(screen.getByText('B 的消息')).toBeTruthy();
  });

  it('会话加载失败时显示错误并可重试', async () => {
    vi.mocked(conversationApi.getConversation)
      .mockRejectedValueOnce(new Error('网络错误'))
      .mockResolvedValueOnce(conversation('conversation-a', '会话 A'));
    vi.mocked(conversationApi.getMessages)
      .mockResolvedValue([message('conversation-a', '恢复后的消息')]);

    render(
      <MemoryRouter initialEntries={['/workspace?pmConversation=conversation-a']}>
        <Routes>
          <Route path="/workspace" element={<ProductManagerAgent />} />
        </Routes>
      </MemoryRouter>,
    );

    expect((await screen.findByRole('alert')).textContent).toContain('会话加载失败');
    fireEvent.click(screen.getByRole('button', { name: '重试' }));

    await screen.findByRole('heading', { name: '会话 A' });
    expect(screen.getByText('恢复后的消息')).toBeTruthy();
  });
});
