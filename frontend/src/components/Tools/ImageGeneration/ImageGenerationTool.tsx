/**
 * ImageGenerationTool — 图像生成页面（多轮对话式图生）v2
 *
 * 交互流程（spec: docs/superpowers/specs/2026-08-30-image-generation-page-fix-design.md）：
 * 1. 进入页面 → 获取（幂等创建）图像生成助手 Agent
 * 2. 多轮对话探究意图：信息不足时助手追问（主体/风格/比例/数量），不生成
 * 3. 信息足够 → 助手复述意图并调用 image_gen 工具 → 页面实时渲染生成中的图片卡片
 * 4. 生成成功显示真实图片；会话持久化，刷新后图片仍在
 *
 * v2（用户反馈迭代）：
 * - 全宽布局（消除窄栏空间浪费）
 * - 助手文本中的原始签名 URL 折叠为"🔗 图片链接"徽章
 * - 图片点击 → 弹框预览（大图 + 下载到本地 + 关闭）
 * - 生成图片持久化到自有 OSS（后端转存，本页只消费稳定 URL）
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Download, ImagePlus, RefreshCw, Send, X } from 'lucide-react';
import axios from 'axios';
import {
  conversationApi,
  type Message,
} from '../../../services/conversationApi';
import { getAuthHeaders } from '../../../api/authApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const CONV_STORAGE_KEY = 'image-gen-conversation-id';

/** 安全 URL：仅允许 http/https（防 javascript:/data: scheme） */
function isSafeUrl(url: string): boolean {
  try {
    const u = new URL(url);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

/** 页面内部消息模型（含实时生成的图片） */
interface ChatItem {
  role: 'user' | 'agent';
  content: string;
  images: string[];
  generating?: boolean;
  failed?: boolean;
}

/** 弹框预览状态 */
interface LightboxState {
  url: string;
}

/** 从消息 attachments 提取图片 URL 列表 */
function imagesOf(attachments: unknown): string[] {
  if (!Array.isArray(attachments)) return [];
  return attachments
    .map((a) => (a as { type?: string; url?: string }))
    .filter((a) => a?.type === 'image' && typeof a.url === 'string' && isSafeUrl(a.url))
    .map((a) => a.url as string);
}

/**
 * 折叠文本中的长/签名 URL，避免裸露刷屏。
 * - markdown 链接 [text](url) → "text 🔗"（text 存在时）或 "🔗 图片链接"
 * - 裸长 URL（≥48 字符，一般是签名地址）→ "🔗 图片链接"
 */
function foldUrls(text: string): string {
  if (!text) return '';
  let out = text.replace(
    /\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g,
    (_m, label: string, url: string) =>
      isSafeUrl(url) ? (label.trim() ? `${label} 🔗` : '🔗 图片链接') : _m,
  );
  out = out.replace(/(https?:\/\/[^\s<>"')\]]{48,})/g, () => '🔗 图片链接');
  return out;
}

/** 后端 Message → 页面 ChatItem（跳过工具消息：原始 JSON 输出无需展示） */
function toChatItem(m: Message): ChatItem | null {
  if ((m as unknown as { tool_name?: string }).tool_name) {
    // 工具输出消息：其图片已随 agent 文本消息的附件展示
    return null;
  }
  return {
    role: m.sender_type === 'user' ? 'user' : 'agent',
    content: m.content || '',
    images: imagesOf((m as unknown as { attachments?: unknown }).attachments),
  };
}

/** 下载图片到本地（blob 方式保证落盘；跨域失败回退新标签打开） */
async function downloadImage(url: string): Promise<void> {
  try {
    const resp = await fetch(url, { mode: 'cors' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const blob = await resp.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = `image-gen-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  } catch {
    // 跨域等场景回退：新标签打开（用户可手动保存）
    window.open(url, '_blank', 'noopener');
  }
}

const ImageGenerationTool: React.FC = () => {
  const [agentId, setAgentId] = useState<string>('');
  const [conversationId, setConversationId] = useState<string>('');
  const [items, setItems] = useState<ChatItem[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [lightbox, setLightbox] = useState<LightboxState | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [items]);

  /** 初始化：取 agent → 恢复/等待会话 → 回填历史 */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await axios.get(`${API_BASE_URL}/tools/image-generation/agent`, {
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
            setItems(history.map(toChatItem).filter((x): x is ChatItem => x !== null));
          } catch {
            // 会话已失效：清掉，等首条消息时新建
            localStorage.removeItem(CONV_STORAGE_KEY);
          }
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : '初始化失败，请确认已登录');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  /** 开始新对话：清空本地会话（下次发送时创建新会话） */
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
      setItems((prev) => [...prev, { role: 'user', content: text, images: [] }]);

      // 首条消息：创建会话
      if (!convId) {
        const conv = await conversationApi.createConversation({
          title: `图像生成-${new Date().toLocaleString()}`,
        });
        convId = conv.id;
        setConversationId(convId);
        localStorage.setItem(CONV_STORAGE_KEY, convId);
      }

      // 助手占位（流式填充）
      setItems((prev) => [
        ...prev,
        { role: 'agent', content: '', images: [], generating: false },
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
            if (event.type === 'tool_call_start' && event.name === 'image_gen') {
              patchLast({ generating: true });
            } else if (event.type === 'tool_result' && event.name === 'image_gen') {
              const data = event as {
                success?: boolean;
                content?: { image_urls?: string[] };
              };
              const urls = (data.content?.image_urls || []).filter(isSafeUrl);
              if (data.success && urls.length > 0) {
                patchLast({ images: urls, generating: false });
              } else {
                patchLast({ generating: false, failed: true });
              }
            }
          },
          onDone: (message) => {
            // done 消息可能带 attachments（持久化来源）；内容以流式文本为准，取二者较长者
            const doneImages = imagesOf(
              (message as unknown as { attachments?: unknown }).attachments,
            );
            setItems((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last && last.role === 'agent') {
                next[next.length - 1] = {
                  ...last,
                  content: last.content || message.content || '',
                  images: last.images.length > 0 ? last.images : doneImages,
                  generating: false,
                };
              }
              return next;
            });
          },
          onError: (error) => {
            patchLast({
              content:
                (error || '') + '\n（生成未完成，可调整需求后重试，或点击"开始新对话"）',
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
          <ImagePlus className="w-5 h-5" />
          <span className="font-semibold">图像生成</span>
          <span className="text-xs text-ink-muted">
            先聊清楚需求，再生成图片 · 图片自动保存到文件服务器
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

      {/* 消息区（全宽，气泡按角色靠边） */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-5 pr-1">
        {items.length === 0 && (
          <div className="text-ink-muted text-sm mt-10 text-center">
            描述你想生成的图片（例如"给公众号画一张关于秋天咖啡的配图"），
            <br />
            我会先和你确认风格、比例等细节，再开始生成。生成结果自动保存到文件服务器。
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
                  正在生成图像，请稍候…
                </div>
              )}
              {item.role === 'agent' ? foldUrls(item.content) : item.content}
              {item.images.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                  {item.images.map((url) => (
                    <button
                      key={url}
                      type="button"
                      onClick={() => setLightbox({ url })}
                      className="group relative block w-full text-left rounded-xl overflow-hidden border border-border hover:border-accent transition-colors"
                      title="点击查看大图"
                    >
                      <img
                        src={url}
                        alt="生成结果"
                        className="w-full max-h-[420px] object-contain bg-canvas"
                      />
                      <span className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity px-2 py-1 rounded bg-black/60 text-white text-xs">
                        点击预览
                      </span>
                    </button>
                  ))}
                </div>
              )}
              {item.failed && item.images.length === 0 && !item.generating && (
                <div className="text-danger text-xs mt-1">本次未能生成图片</div>
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
          placeholder="描述你的图像需求…（可先简单说，我会追问细节）"
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

      {/* 弹框预览（点击遮罩关闭） */}
      {lightbox && (
        <div
          className="fixed inset-0 bg-black/80 z-[60] flex items-center justify-center p-6"
          onClick={() => setLightbox(null)}
        >
          <div
            className="relative max-w-[92vw] max-h-[92vh] flex flex-col items-center gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={lightbox.url}
              alt="预览"
              className="max-w-[92vw] max-h-[80vh] object-contain rounded-lg shadow-2xl"
            />
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => downloadImage(lightbox.url)}
                className="flex items-center gap-1 px-4 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg text-sm transition-colors"
              >
                <Download className="w-4 h-4" />
                下载图片
              </button>
              <button
                type="button"
                onClick={() => setLightbox(null)}
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

export default ImageGenerationTool;
