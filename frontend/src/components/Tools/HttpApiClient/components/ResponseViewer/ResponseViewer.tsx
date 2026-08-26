import { useState } from 'react';
import { SendRequestResponse, HttpRequest } from '../../../../../services/httpClientApi';
import { generateSnippet } from '../../../../../utils/codeSnippetGenerator';
import { Button } from '@/components/ui/Button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import HtmlPreview from '../ResponsePreview/HtmlPreview';
import ImagePreview from '../ResponsePreview/ImagePreview';
import JsonView from 'react18-json-view';
import 'react18-json-view/src/style.css';

interface ResponseViewerProps {
  response: SendRequestResponse;
  request?: HttpRequest;
  envVariables?: Record<string, string>;
}

export default function ResponseViewer({ response, request, envVariables = {} }: ResponseViewerProps) {
  const [activeTab, setActiveTab] = useState<'body' | 'headers' | 'code' | 'preview'>('body');
  const [bodyView, setBodyView] = useState<'raw' | 'formatted' | 'tree'>('formatted');
  const [snippetLang, setSnippetLang] = useState<'curl' | 'python' | 'javascript' | 'go'>('curl');

  // 格式化 JSON
  const formatJson = (json: string) => {
    try {
      const parsed = JSON.parse(json);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return json;
    }
  };

  // 格式化 XML
  const formatXml = (xml: string) => {
    let formatted = '';
    let indent = 0;
    const lines = xml.replace(/>\s*</g, '><').split(/(<[^>]+>)/g).filter(Boolean);
    for (const line of lines) {
      if (line.startsWith('</')) indent--;
      formatted += '  '.repeat(Math.max(0, indent)) + line + '\n';
      if (line.startsWith('<') && !line.startsWith('</') && !line.endsWith('/>')) indent++;
    }
    return formatted.trim();
  };

  // 检测响应类型
  const detectContentType = (): 'json' | 'xml' | 'html' | 'image' | 'text' | 'binary' => {
    const ct = response.content_type || '';
    if (ct.includes('application/json')) return 'json';
    if (ct.includes('xml')) return 'xml';
    if (ct.includes('html')) return 'html';
    if (ct.startsWith('image/')) return 'image';
    if (ct.startsWith('text/')) return 'text';
    // 显式二进制类型（如 application/octet-stream、application/pdf）走 binary 分支
    if (ct.includes('octet-stream') || ct.includes('application/pdf') || ct.includes('application/zip')) return 'binary';
    if (response.body.startsWith('{') || response.body.startsWith('[')) return 'json';
    return 'text';
  };

  const contentType = detectContentType();
  const isJson = contentType === 'json';
  const formattedBody = isJson ? formatJson(response.body) : contentType === 'xml' ? formatXml(response.body) : response.body;

  // 安全地将字符串编码为 base64。
  // - btoa() 本身仅接受码点 < 256 的 latin-1 字符串，传入中文/UTF-8 字符会抛出 InvalidCharacterError，
  //   在没有 ErrorBoundary 的情况下会直接导致 HTTP API Client 工具页面白屏。
  // - 这里先通过 TextEncoder 转成 UTF-8 字节再逐字节生成 binary string，绕过 btoa 的限制。
  // - 仍用 try/catch 兜底（例如 body 含代理对等极端情况），失败时返回 null，由调用方降级。
  const encodeBase64Safe = (input: string): string | null => {
    try {
      const bytes = new TextEncoder().encode(input);
      let binary = '';
      for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      return btoa(binary);
    } catch {
      return null;
    }
  };

  // 图片响应转 base64。
  // 协议假设：后端将图片字节以原始二进制形式序列化进 response.body（字符串），
  // 这里再做一次 base64 编码以组装 data URL。若后续 Task 9/10 明确后端已返回 base64 字符串，
  // 需要去掉这次编码直接透传，避免出现"双重 base64"。
  const imageBase64 = contentType === 'image' ? encodeBase64Safe(response.body) : null;

  // 计算状态码颜色
  const getStatusColor = (status: number) => {
    if (status === 0) return 'text-danger';
    if (status >= 200 && status < 300) return 'text-green-400';
    if (status >= 300 && status < 400) return 'text-accent-warning';
    if (status >= 400 && status < 500) return 'text-orange-400';
    if (status >= 500) return 'text-danger';
    return 'text-ink-muted';
  };

  const getStatusText = (status: number) => {
    const statusTexts: Record<number, string> = {
      0: '请求失败',
      200: 'OK',
      201: 'Created',
      204: 'No Content',
      301: 'Moved Permanently',
      302: 'Found',
      304: 'Not Modified',
      400: 'Bad Request',
      401: 'Unauthorized',
      403: 'Forbidden',
      404: 'Not Found',
      405: 'Method Not Allowed',
      408: 'Request Timeout',
      429: 'Too Many Requests',
      500: 'Internal Server Error',
      502: 'Bad Gateway',
      503: 'Service Unavailable',
      504: 'Gateway Timeout',
    };
    return statusTexts[status] || 'Unknown';
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  // 生成代码片段
  const codeSnippet = request ? generateSnippet(request, snippetLang, envVariables) : '';

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 响应状态栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-surface-1 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-ink-muted">Status:</span>
            <span className={`font-mono font-bold ${getStatusColor(response.status_code)}`}>
              {response.status_code} {getStatusText(response.status_code)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-ink-muted">Time:</span>
            <span className="font-mono text-accent">{response.response_time}ms</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-ink-muted">Size:</span>
            <span className="font-mono text-accent-secondary">
              {formatBytes(response.body.length)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigator.clipboard.writeText(response.body)}
            className="text-xs text-ink-muted hover:text-ink-inverse"
            title="复制响应体"
          >
            <i className="fas fa-copy mr-1"></i>
            复制
          </Button>
        </div>
      </div>

      {/* 标签页 */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as 'body' | 'headers' | 'code' | 'preview')}
        className="flex flex-col flex-1 overflow-hidden"
      >
        <TabsList className="px-4 bg-surface-1/30 flex-shrink-0 w-full justify-start rounded-none border-b border-border">
          <TabsTrigger value="body" className="gap-2">
            <i className="fas fa-code"></i>
            Body
          </TabsTrigger>
          <TabsTrigger value="headers" className="gap-2">
            <i className="fas fa-heading"></i>
            Headers
          </TabsTrigger>
          {request && (
            <TabsTrigger value="code" className="gap-2">
              <i className="fas fa-file-code"></i>
              Code
            </TabsTrigger>
          )}
          <TabsTrigger value="preview" className="gap-2">
            <i className="fas fa-eye"></i>
            Preview
          </TabsTrigger>
        </TabsList>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto">
          <TabsContent value="body">
            <div>
              {/* Body 子标签 */}
              {isJson && (
                <div className="flex items-center gap-1 px-4 py-1 border-b border-border/50 bg-surface-1/20">
                  {(['raw', 'formatted', 'tree'] as const).map(view => (
                    <button
                      key={view}
                      onClick={() => setBodyView(view)}
                      className={`
                        px-2 py-1 text-xs rounded transition-colors
                        ${bodyView === view
                          ? 'bg-accent-secondary/20 text-accent-secondary'
                          : 'text-ink-faint hover:text-ink-muted'
                        }
                      `}
                    >
                      {view === 'raw' ? 'Raw' : view === 'formatted' ? 'Formatted' : 'Tree'}
                    </button>
                  ))}
                </div>
              )}

              <div className="p-4">
                {isJson && bodyView === 'tree' ? (
                  <JsonView src={JSON.parse(response.body)} theme="dark" collapsed={1} />
                ) : (
                  <pre className="font-mono text-sm text-ink-muted whitespace-pre-wrap break-word">
                    {formattedBody}
                  </pre>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="headers">
            <div className="p-4">
              <div className="space-y-1">
                {Object.entries(response.headers).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-start gap-4 py-1.5 border-b border-border/50 last:border-0"
                  >
                    <span className="font-mono text-xs text-accent-secondary min-w-[200px]">
                      {key}
                    </span>
                    <span className="font-mono text-xs text-ink-muted flex-1 break-all">
                      {value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          {request && (
            <TabsContent value="code">
              <div className="p-4">
                {/* 语言选择 */}
                <div className="flex items-center gap-2 mb-3">
                  {(['curl', 'python', 'javascript', 'go'] as const).map(lang => (
                    <button
                      key={lang}
                      onClick={() => setSnippetLang(lang)}
                      className={`
                        px-3 py-1 rounded text-xs font-medium transition-colors
                        ${snippetLang === lang
                          ? 'bg-accent-secondary/20 text-accent-secondary border border-accent-secondary'
                          : 'bg-surface-2 text-ink-muted border border-transparent hover:bg-surface-3'
                        }
                      `}
                    >
                      {lang === 'curl' ? 'cURL' : lang === 'python' ? 'Python' : lang === 'javascript' ? 'JavaScript' : 'Go'}
                    </button>
                  ))}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigator.clipboard.writeText(codeSnippet)}
                    className="ml-auto text-xs text-ink-muted hover:text-ink-inverse"
                    title="复制代码"
                  >
                    <i className="fas fa-copy mr-1"></i>
                    复制
                  </Button>
                </div>

                <pre className="font-mono text-sm text-ink-muted bg-canvas/50 p-4 rounded-lg overflow-x-auto whitespace-pre">
                  {codeSnippet}
                </pre>
              </div>
            </TabsContent>
          )}

          <TabsContent value="preview">
            <div className="p-4 h-full">
              {contentType === 'html' && <HtmlPreview html={response.body} />}
              {contentType === 'image' && imageBase64 !== null && (
                <ImagePreview
                  base64Data={imageBase64}
                  contentType={response.content_type || 'image/png'}
                />
              )}
              {contentType === 'image' && imageBase64 === null && (
                <div className="text-ink-faint text-sm text-center py-8">
                  <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
                  <p>图片数据编码失败，无法预览，请切换到 Body 标签查看</p>
                </div>
              )}
              {(contentType === 'json' || contentType === 'xml' || contentType === 'text' || contentType === 'binary') && (
                <div className="text-ink-faint text-sm text-center py-8">
                  <i className="fas fa-info-circle text-2xl mb-2"></i>
                  <p>此响应类型不支持预览，请切换到 Body 标签查看</p>
                </div>
              )}
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
