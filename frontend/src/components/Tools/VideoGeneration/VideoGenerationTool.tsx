/**
 * VideoGenerationTool — 视频生成页面（多轮对话式）
 *
 * 镜像 ImageGenerationTool 的设计：
 * 1. 进入页面 → 获取（幂等创建）视频生成助手 Agent
 * 2. 多轮对话探究意图 → 调用 video_gen 工具 → 实时显示生成状态
 * 3. 生成成功显示视频播放器（内嵌 <video>）；会话持久化
 * 4. 视频自动保存到 OSS 文件服务器，可在 /admin/oss 查看下载
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Download, Film, RefreshCw, Send, X } from 'lucide-react';
import axios from 'axios';
import {
  conversationApi,
  type Message,
} from '../../../services/conversationApi';
import { getAuthHeaders } from '../../../api/authApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const CONV_STORAGE_KEY = 'video-gen-conversation-id';

function isSafeUrl(url: string): boolean {
  try {
    const u = new URL(url);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

interface ChatItem {
  role: 'user' | 'agent';
  content: string;
  videoUrl: string;
  generating?: boolean;
  failed?: boolean;
  refinedPrompt?: string;
}

/** 从附件中提取视频 URL（type=file + video MIME） */
function videoOf(attachments: unknown): string {
  if (!Array.isArray(attachments)) return '';
  const found = attachments
    .map((a) => a as { type?: string; url?: string; mime_type?: string })
    .find((a) => {
      if (a?.type === 'file' && typeof a.url === 'string' && isSafeUrl(a.url)) return true;
      if (typeof a?.url === 'string' && a.url.includes('video-gen/') && isSafeUrl(a.url)) return true;
      return false;
    });
  return found?.url || '';
}

function foldUrls(text: string): string {
  if (!text) return '';
  let out = text.replace(
    /\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g,
    (_m, label: string, url: string) =>
      isSafeUrl(url) ? (label.trim() ? `${label} 🔗` : '🔗 视频链接') : _m,
  );
  out = out.replace(/(https?:\/\/[^\s<>"')\]]{48,})/g, () => '🔗 视频链接');
  return out;
}

function toChatItem(m: Message): ChatItem | null {
  if ((m as unknown as { tool_name?: string }).tool_name) return null;
  return {
    role: m.sender_type === 'user' ? 'user' : 'agent',
    content: m.content || '',
    videoUrl: videoOf((m as unknown as { attachments?: unknown }).attachments),
  };
}

async function downloadVideo(url: string): Promise<void> {
  try {
    const resp = await fetch(url, { mode: 'cors' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const blob = await resp.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = `video-gen-${Date.now()}.mp4`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  } catch {
    window.open(url, '_blank', 'noopener');
  }
}

const VideoGenerationTool: React.FC = () => {
  const [agentId, setAgentId] = useState<string>('');
  const [conversationId, setConversationId] = useState<string>('');
  const [items, setItems] = useState<ChatItem[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [fullscreen, setFullscreen] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [items]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await axios.get(`${API_BASE_URL}/tools/video-generation/agent`, {
          headers: getAuthHeaders() as Record<string, string>,
        });
        if (cancelled) return;
        setAgentId(resp.data.agent_id);

        const saved = localStorage.getItem(CONV_STORAGE_KEY);
        if (saved) {
          try {
            const history = await conversationApi.getMessages(saved, 50);
            if (cancelled) return;
            setConversationId(saved);
            const chronological = [...history].reverse();
            setItems(chronological.map(toChatItem).filter((x): x is ChatItem => x !== null));
          } catch {
            localStorage.removeItem(CONV_STORAGE_KEY);
          }
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : '初始化失败，请确认已登录');
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleNewConversation = useCallback(() => {
    localStorage.removeItem(CONV_STORAGE_KEY);
    setConversationId('');
    setItems([]);
  }, []);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || busy || !agentId) return;

    let convId = conversationId;
    try {
      setBusy(true);
      setInput('');
      setItems((prev) => [...prev, { role: 'user', content: text, videoUrl: '' }]);

      if (!convId) {
        const conv = await conversationApi.createConversation({
          title: `视频生成-${new Date().toLocaleString()}`,
        });
        convId = conv.id;
        setConversationId(convId);
        localStorage.setItem(CONV_STORAGE_KEY, convId);
      }

      setItems((prev) => [
        ...prev,
        { role: 'agent', content: '', videoUrl: '', generating: false },
      ]);

      const patchLast = (patch: Partial<ChatItem>) => {
        setItems((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last && last.role === 'agent') {
            next[next.length - 1] = { ...last, ...patch };
          }
          return next;
        });
      };

      await conversationApi.sendMessageStream(
        convId,
        { content: text, agent_id: agentId },
        {
          onChunk: (chunk) => {
            setItems((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last && last.role === 'agent') {
                next[next.length - 1] = { ...last, content: last.content + chunk };
              }
              return next;
            });
          },
          onEvent: (event) => {
            if (event.type === 'tool_call_start' && event.name === 'video_gen') {
              patchLast({ generating: true });
            } else if (event.type === 'tool_result' && event.name === 'video_gen') {
              const data = event as {
                success?: boolean;
                content?: { video_url?: string; revised_prompt?: string };
              };
              const url = data.content?.video_url || '';
              const refined = (data.content?.revised_prompt || '').trim();
              if (data.success && url && isSafeUrl(url)) {
                patchLast({ videoUrl: url, generating: false, refinedPrompt: refined || undefined });
              } else {
                patchLast({ generating: false, failed: true });
              }
            }
          },
          onDone: (message) => {
            const doneVideo = videoOf(
              (message as unknown as { attachments?: unknown }).attachments,
            );
            setItems((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last && last.role === 'agent') {
                next[next.length - 1] = {
                  ...last,
                  content: last.content || message.content || '',
                  videoUrl: last.videoUrl || doneVideo,
                  generating: false,
                };
              }
              return next;
            });
          },
          onError: (error) => {
            patchLast({
              content: (error || '') + '\n（生成未完成，可调整需求后重试）',
              generating: false,
              failed: true,
            });
          },
        },
      );
    } catch (e: unknown) {
      setLoadError(e instanceof Error ? e.message : '发送失败');
    } finally {
      setBusy(false);
    }
  }, [input, busy, agentId, conversationId]);

  return (
    <div className="h-full flex flex-col w-full px-6 lg:px-10">
      {/* 头部 */}
      <div className="flex items-center justify-between pb-3 border-b border-border mb-3 shrink-0">
        <div className="flex items-center gap-2 text-ink">
          <Film className="w-5 h-5" />
          <span className="font-semibold">视频生成</span>
          <span className="text-xs text-ink-muted">
            先聊清楚需求，再生成视频 · 视频自动保存到文件服务器
          </span>
        </div>
        <button
          type="button"
          onClick={handleNewConversation}
          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-surface-2 hover:bg-surface-3 text-ink rounded-lg transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          开始新对话
        </button>
      </div>

      {loadError && (
        <div className="text-danger text-sm mb-3 shrink-0">{loadError}</div>
      )}

      {/* 消息区 */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-5 pr-1">
        {items.length === 0 && (
          <div className="text-ink-muted text-sm mt-10 text-center">
            描述你想生成的视频（例如"一段高燃的动漫战斗场景"），
            <br />
            我会先和你确认风格、比例、时长等细节，再开始生成。生成结果自动保存到文件服务器。
          </div>
        )}
        {items.map((item, idx) => (
          <div
            key={idx}
            className={`flex w-full ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[78%] rounded-xl px-5 py-3.5 text-sm whitespace-pre-wrap break-words ${
                item.role === 'user'
                  ? 'bg-accent text-ink-inverse'
                  : 'bg-surface-1 border border-border text-ink'
              }`}
            >
              {item.generating && (
                <div className="flex items-center gap-2 text-ink-muted mb-2">
                  <span className="animate-spin">◌</span>
                  正在生成视频，请耐心等待（可能需要 1-3 分钟）…
                </div>
              )}
              {item.role === 'agent' ? foldUrls(item.content) : item.content}
              {item.videoUrl && (
                <div className="mt-3">
                  <div className="relative rounded-xl overflow-hidden border border-border bg-black">
                    <video
                      src={item.videoUrl}
                      controls
                      className="w-full max-h-[480px]"
                      preload="metadata"
                    />
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <button
                      type="button"
                      onClick={() => setFullscreen(item.videoUrl)}
                      className="text-xs text-accent-info hover:underline"
                    >
                      全屏预览
                    </button>
                    <button
                      type="button"
                      onClick={() => downloadVideo(item.videoUrl)}
                      className="flex items-center gap-1 text-xs text-accent-info hover:underline"
                    >
                      <Download className="w-3 h-3" />
                      下载视频
                    </button>
                  </div>
                </div>
              )}
              {item.refinedPrompt && (
                <details className="mt-3 group">
                  <summary className="text-xs text-ink-muted cursor-pointer hover:text-ink select-none">
                    ✨ 优化后的视频描述
                  </summary>
                  <div className="mt-1 px-3 py-2 bg-canvas border border-border/60 rounded text-xs text-ink-muted whitespace-pre-wrap">
                    {item.refinedPrompt}
                  </div>
                </details>
              )}
              {item.failed && !item.videoUrl && !item.generating && (
                <div className="text-danger text-xs mt-1">本次未能生成视频</div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* 输入区 */}
      <div className="flex gap-2 pt-3 border-t border-border mt-3 shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={'描述你的视频需求…（如"高燃动漫战斗场景"）'}
          disabled={busy || !agentId}
          className="flex-1 px-4 py-2.5 bg-surface-1 border border-border rounded-lg text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={busy || !input.trim() || !agentId}
          className="flex items-center gap-1 px-4 py-2.5 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" />
          {busy ? '处理中' : '发送'}
        </button>
      </div>

      {/* 全屏视频预览 */}
      {fullscreen && (
        <div
          className="fixed inset-0 bg-black/90 z-[60] flex items-center justify-center p-6"
          onClick={() => setFullscreen(null)}
        >
          <div
            className="relative max-w-[95vw] max-h-[95vh] flex flex-col items-center gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <video
              src={fullscreen}
              controls
              autoPlay
              className="max-w-[95vw] max-h-[85vh] rounded-lg shadow-2xl"
            />
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => downloadVideo(fullscreen)}
                className="flex items-center gap-1 px-4 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg text-sm transition-colors"
              >
                <Download className="w-4 h-4" />
                下载视频
              </button>
              <button
                type="button"
                onClick={() => setFullscreen(null)}
                className="flex items-center gap-1 px-4 py-2 bg-surface-2 hover:bg-surface-3 text-ink rounded-lg text-sm transition-colors"
              >
                <X className="w-4 h-4" />
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoGenerationTool;
