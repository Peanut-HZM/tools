/**
 * ResponseViewer - 响应查看器（Apifox 风格）
 *
 * 状态栏：状态码（着色）/ 耗时 / 大小 / 网络错误
 * 标签页：Body（Pretty/Raw/Preview + JSONPath 过滤）/ Headers / 断言结果 / 实际请求 / 代码
 */

import { useMemo, useState } from 'react';
import { SendRequestResponse, HttpRequest } from '../../../../../services/httpClientApi';
import { generateSnippet, Language } from '../../../../../utils/codeSnippetGenerator';
import { Copy, Code, Heading, FileCode, Eye, AlertTriangle, Info, Download, CheckCircle2, XCircle, Radio } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import HtmlPreview from '../ResponsePreview/HtmlPreview';
import ImagePreview from '../ResponsePreview/ImagePreview';
import JsonTree from './JsonTree';

interface ResponseViewerProps {
  response: SendRequestResponse;
  request?: HttpRequest;
  envVariables?: Record<string, string>;
}

export default function ResponseViewer({ response, request, envVariables = {} }: ResponseViewerProps) {
  const [activeTab, setActiveTab] = useState<'body' | 'headers' | 'assertions' | 'actual' | 'code'>('body');
  const [bodyView, setBodyView] = useState<'pretty' | 'raw' | 'preview'>('pretty');
  const [jsonPathFilter, setJsonPathFilter] = useState('');
  const [snippetLang, setSnippetLang] = useState<Language>('curl');
  const [copiedBody, setCopiedBody] = useState(false);

  // 格式化 JSON
  const parsedJson = useMemo(() => {
    try {
      return JSON.parse(response.body);
    } catch {
      return null;
    }
  }, [response.body]);

  // JSONPath 过滤结果（用最简单的多层取值：$.a.b[0]）
  const filteredJson = useMemo(() => {
    if (!jsonPathFilter.trim() || !parsedJson) return null;
    try {
      const tokens = jsonPathFilter.trim().replace(/^\$\.?/, '').split(/[.[\]]+/).filter(Boolean);
      let current: any = parsedJson;
      for (const token of tokens) {
        if (current === null || current === undefined) return undefined;
        if (/^\d+$/.test(token) && Array.isArray(current)) {
          current = current[Number(token)];
        } else if (token === '*') {
          return Array.isArray(current) ? current : Object.values(current);
        } else {
          current = current[token];
        }
      }
      return current;
    } catch {
      return undefined;
    }
  }, [jsonPathFilter, parsedJson]);

  // 检测响应类型
  const detectContentType = (): 'json' | 'xml' | 'html' | 'image' | 'text' | 'binary' | 'event-stream' => {
    const ct = response.content_type || '';
    if (ct.includes('event-stream')) return 'event-stream';
    if (ct.includes('application/json')) return 'json';
    if (ct.includes('xml')) return 'xml';
    if (ct.includes('html')) return 'html';
    if (ct.startsWith('image/')) return 'image';
    if (ct.startsWith('text/')) return 'text';
    if (ct.includes('octet-stream') || ct.includes('application/pdf') || ct.includes('application/zip')) return 'binary';
    if (response.body.startsWith('{') || response.body.startsWith('[')) return 'json';
    return 'text';
  };

  const contentType = detectContentType();
  const isJson = contentType === 'json';
  const isEventStream = contentType === 'event-stream';

  // 安全地将字符串编码为 base64（btoa 不支持非 latin-1 字符，先转 UTF-8 字节）
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

  const imageBase64 = contentType === 'image' ? encodeBase64Safe(response.body) : null;

  // 状态码颜色与描述
  const getStatusColor = (status: number) => {
    if (status === 0) return 'text-danger';
    if (status >= 200 && status < 300) return 'text-success';
    if (status >= 300 && status < 400) return 'text-accent-warning';
    if (status >= 400 && status < 500) return 'text-warning';
    if (status >= 500) return 'text-danger';
    return 'text-ink-muted';
  };

  const getStatusText = (status: number) => {
    if (response.status_text) return response.status_text;
    const statusTexts: Record<number, string> = {
      0: '请求失败', 200: 'OK', 201: 'Created', 204: 'No Content',
      301: 'Moved Permanently', 302: 'Found', 304: 'Not Modified',
      400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
      405: 'Method Not Allowed', 408: 'Request Timeout', 429: 'Too Many Requests',
      500: 'Internal Server Error', 502: 'Bad Gateway', 503: 'Service Unavailable', 504: 'Gateway Timeout',
    };
    return statusTexts[status] || 'Unknown';
  };

  const formatBytes = (bytes: number): string => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 2)} ${sizes[i]}`;
  };

  // 断言统计
  const assertionResults = response.assertion_results || [];
  const passedCount = assertionResults.filter(a => a.passed).length;
  const failedCount = assertionResults.length - passedCount;

  // 下载响应体
  const handleDownload = () => {
    const blob = new Blob([response.body], { type: response.content_type || 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const ext = isJson ? 'json' : contentType === 'xml' ? 'xml' : contentType === 'html' ? 'html' : contentType === 'image' ? 'png' : 'txt';
    link.href = url;
    link.download = `response_${Date.now()}.${ext}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyBody = () => {
    navigator.clipboard.writeText(response.body).then(() => {
      setCopiedBody(true);
      setTimeout(() => setCopiedBody(false), 1500);
    });
  };

  const codeSnippet = request ? generateSnippet(request, snippetLang, envVariables) : '';

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 响应状态栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-surface-1 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-4 flex-wrap">
          {response.error ? (
            <span className="flex items-center gap-2 text-danger text-sm font-medium">
              <AlertTriangle className="w-4 h-4" />
              {response.error}
            </span>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <span className={`font-mono font-bold text-sm ${getStatusColor(response.status_code)}`}>
                  {response.status_code} {getStatusText(response.status_code)}
                </span>
              </div>
              <span className="text-ink-faint">·</span>
              <div className="flex items-center gap-1" title="响应耗时">
                <span className="font-mono text-accent text-sm">{response.response_time}ms</span>
              </div>
              <span className="text-ink-faint">·</span>
              <div className="flex items-center gap-1" title="响应体大小">
                <span className="font-mono text-accent-secondary text-sm">{formatBytes(response.size)}</span>
              </div>
            </>
          )}

          {/* 提取变量提示 */}
          {Object.keys(response.extracted_variables || {}).length > 0 && (
            <>
              <span className="text-ink-faint">·</span>
              <div className="flex items-center gap-1.5 flex-wrap" title="已提取并写入激活环境">
                {Object.entries(response.extracted_variables).map(([k, v]) => (
                  <span key={k} className="text-xs bg-success/10 text-success px-2 py-0.5 rounded font-mono">
                    {k}={v.length > 20 ? `${v.slice(0, 20)}…` : v}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDownload}
            className="text-xs text-ink-muted hover:text-ink"
            title="下载响应体"
          >
            <Download className="w-3.5 h-3.5 mr-1" />
            下载
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopyBody}
            className="text-xs text-ink-muted hover:text-ink"
            title="复制响应体"
          >
            <Copy className="w-3.5 h-3.5 mr-1" />
            {copiedBody ? '已复制' : '复制'}
          </Button>
        </div>
      </div>

      {/* 标签页 */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as typeof activeTab)}
        className="flex flex-col flex-1 overflow-hidden"
      >
        <TabsList className="px-4 bg-surface-1/30 flex-shrink-0 w-full justify-start rounded-none border-b border-border">
          <TabsTrigger value="body" className="gap-2">
            <Code className="w-4 h-4" />
            Body
          </TabsTrigger>
          <TabsTrigger value="headers" className="gap-2">
            <Heading className="w-4 h-4" />
            Headers
          </TabsTrigger>
          {(assertionResults.length > 0 || (request?.assertions?.length || 0) > 0) && (
            <TabsTrigger value="assertions" className="gap-2">
              {failedCount > 0 ? <XCircle className="w-4 h-4 text-danger" /> : <CheckCircle2 className="w-4 h-4 text-success" />}
              断言
              {assertionResults.length > 0 && (
                <span className={`ml-1 px-1.5 py-0.5 rounded-full text-[10px] ${failedCount > 0 ? 'bg-danger/20 text-danger' : 'bg-success/20 text-success'}`}>
                  {passedCount}/{assertionResults.length}
                </span>
              )}
            </TabsTrigger>
          )}
          {request && (
            <TabsTrigger value="actual" className="gap-2">
              <Radio className="w-4 h-4" />
              实际请求
            </TabsTrigger>
          )}
          {request && (
            <TabsTrigger value="code" className="gap-2">
              <FileCode className="w-4 h-4" />
              代码
            </TabsTrigger>
          )}
        </TabsList>

        {/* 内容区域 */}
        <div className="flex-1 overflow-hidden">
          <TabsContent value="body" className="h-full flex flex-col">
            <div className="flex-1 overflow-y-auto">
              {/* Body 视图切换 */}
              <div className="flex items-center gap-1 px-4 py-1.5 border-b border-border/50 bg-surface-1/20 sticky top-0">
                {(['pretty', 'raw', ...(contentType === 'html' || contentType === 'image' ? ['preview' as const] : [])] as const).map(view => (
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
                    {view === 'pretty' ? '美化' : view === 'raw' ? 'Raw' : '预览'}
                  </button>
                ))}
                {isJson && bodyView === 'pretty' && (
                  <div className="ml-auto flex items-center gap-1.5">
                    <Input
                      type="text"
                      value={jsonPathFilter}
                      onChange={(e) => setJsonPathFilter(e.target.value)}
                      placeholder="JSONPath 过滤，如 $.data.items[0]"
                      className="h-6 w-56 text-xs font-mono"
                    />
                    {jsonPathFilter && (
                      <button onClick={() => setJsonPathFilter('')} className="text-xs text-ink-faint hover:text-ink">
                        清除
                      </button>
                    )}
                  </div>
                )}
              </div>

              <div className="p-4">
                {isEventStream && (
                  <div className="mb-3 flex items-center gap-2 text-xs text-accent-info">
                    <Radio className="w-3.5 h-3.5" />
                    SSE 响应流（text/event-stream），以下为原始事件文本
                  </div>
                )}

                {bodyView === 'preview' && contentType === 'html' && <HtmlPreview html={response.body} />}
                {bodyView === 'preview' && contentType === 'image' && imageBase64 !== null && (
                  <ImagePreview base64Data={imageBase64} contentType={response.content_type || 'image/png'} />
                )}
                {bodyView === 'preview' && contentType === 'image' && imageBase64 === null && (
                  <div className="text-ink-faint text-sm text-center py-8">
                    <AlertTriangle className="w-8 h-8 mb-2" />
                    <p>图片数据编码失败，无法预览，请切换到 Raw 查看</p>
                  </div>
                )}

                {bodyView === 'pretty' && (
                  isJson && parsedJson !== null ? (
                    jsonPathFilter.trim() ? (
                      filteredJson === undefined ? (
                        <div className="text-ink-faint text-sm text-center py-8">
                          <Info className="w-6 h-6 mb-2 opacity-50" />
                          <p>JSONPath 未匹配到值</p>
                        </div>
                      ) : (
                        <JsonTree data={filteredJson} />
                      )
                    ) : (
                      <JsonTree data={parsedJson} />
                    )
                  ) : (
                    <pre className="font-mono text-sm text-ink-muted whitespace-pre-wrap break-word">{response.body}</pre>
                  )
                )}

                {bodyView === 'raw' && (
                  <pre className="font-mono text-sm text-ink-muted whitespace-pre-wrap break-word">{response.body}</pre>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="headers" className="h-full overflow-y-auto">
            <div className="p-4">
              <div className="space-y-1">
                {Object.entries(response.headers).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-start gap-4 py-1.5 border-b border-border/50 last:border-0"
                  >
                    <span className="font-mono text-xs text-accent-secondary min-w-[220px] break-all">{key}</span>
                    <span className="font-mono text-xs text-ink-muted flex-1 break-all">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="assertions" className="h-full overflow-y-auto">
            <div className="p-4 space-y-2">
              {assertionResults.length === 0 ? (
                <div className="text-ink-faint text-sm text-center py-8">
                  尚未执行断言（在此请求的「后置操作」中配置断言后重新发送）
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-3 text-xs mb-3">
                    <span className="text-success">{passedCount} 项通过</span>
                    {failedCount > 0 && <span className="text-danger">{failedCount} 项失败</span>}
                  </div>
                  {assertionResults.map((result, i) => (
                    <div
                      key={i}
                      className={`flex items-start gap-3 p-3 rounded-lg border ${
                        result.passed ? 'border-success/30 bg-success/5' : 'border-danger/30 bg-danger/5'
                      }`}
                    >
                      {result.passed ? (
                        <CheckCircle2 className="w-4 h-4 text-success flex-shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-4 h-4 text-danger flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-ink">
                          {result.name || result.expression || result.source}
                        </p>
                        <p className="text-xs text-ink-faint mt-1 font-mono break-all">
                          {result.source}{result.expression ? ` · ${result.expression}` : ''} · {operatorLabel(result.operator)}
                        </p>
                        {!result.passed && (
                          <p className="text-xs text-ink-muted mt-1.5 break-all">
                            {result.message || `期望 ${result.expected || '(空)'}，实际 ${truncateActual(result.actual)}`}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </TabsContent>

          <TabsContent value="actual" className="h-full overflow-y-auto">
            <div className="p-4 space-y-4">
              <div>
                <h4 className="text-xs text-ink-faint mb-1.5 font-medium">实际发送的 URL（变量已替换）</h4>
                <div className="bg-canvas border border-border rounded-lg p-3 font-mono text-xs text-ink break-all">
                  {response.request_url || response.error || '-'}
                </div>
              </div>
              <div>
                <h4 className="text-xs text-ink-faint mb-1.5 font-medium">实际发送的请求头（含认证注入）</h4>
                <div className="bg-canvas border border-border rounded-lg divide-y divide-border/50">
                  {Object.entries(response.request_headers || {}).map(([key, value]) => (
                    <div key={key} className="flex items-start gap-3 px-3 py-1.5">
                      <span className="font-mono text-xs text-accent-secondary min-w-[200px] break-all">{key}</span>
                      <span className="font-mono text-xs text-ink-muted flex-1 break-all">{value}</span>
                    </div>
                  ))}
                  {Object.keys(response.request_headers || {}).length === 0 && (
                    <div className="px-3 py-3 text-xs text-ink-faint">无自定义请求头</div>
                  )}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="code" className="h-full overflow-y-auto">
            <div className="p-4">
              {/* 语言选择 */}
              <div className="flex items-center gap-2 mb-3">
                {(['curl', 'javascript', 'python', 'go', 'http'] as const).map(lang => (
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
                    {lang === 'curl' ? 'cURL' : lang === 'javascript' ? 'Fetch' : lang === 'python' ? 'Python' : lang === 'go' ? 'Go' : 'HTTP'}
                  </button>
                ))}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigator.clipboard.writeText(codeSnippet)}
                  className="ml-auto text-xs text-ink-muted hover:text-ink"
                  title="复制代码"
                >
                  <Copy className="w-3 h-3 mr-1" />
                  复制
                </Button>
              </div>

              <pre className="font-mono text-sm text-ink-muted bg-canvas/50 p-4 rounded-lg overflow-x-auto whitespace-pre">
                {codeSnippet}
              </pre>
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

function operatorLabel(op: string): string {
  const labels: Record<string, string> = {
    equal: '等于', not_equal: '不等于', contains: '包含', not_contains: '不包含',
    greater_than: '大于', less_than: '小于', greater_or_equal: '大于等于', less_or_equal: '小于等于',
    is_empty: '为空', not_empty: '不为空', exists: '存在', not_exists: '不存在',
    regex_match: '正则匹配', starts_with: '以...开始', ends_with: '以...结束',
  };
  return labels[op] || op;
}

function truncateActual(actual: string): string {
  if (!actual) return '(空)';
  return actual.length > 60 ? `${actual.slice(0, 60)}…` : actual;
}
