import { useState } from 'react';
import { SendRequestResponse, HttpRequest } from '../../../../../services/httpClientApi';
import { generateSnippet } from '../../../../../utils/codeSnippetGenerator';
import JsonView from 'react18-json-view';
import 'react18-json-view/src/style.css';

interface ResponseViewerProps {
  response: SendRequestResponse;
  request?: HttpRequest;
  envVariables?: Record<string, string>;
}

export default function ResponseViewer({ response, request, envVariables = {} }: ResponseViewerProps) {
  const [activeTab, setActiveTab] = useState<'body' | 'headers' | 'code'>('body');
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
    if (response.body.startsWith('{') || response.body.startsWith('[')) return 'json';
    return 'text';
  };

  const contentType = detectContentType();
  const isJson = contentType === 'json';
  const formattedBody = isJson ? formatJson(response.body) : contentType === 'xml' ? formatXml(response.body) : response.body;

  // 计算状态码颜色
  const getStatusColor = (status: number) => {
    if (status === 0) return 'text-red-400';
    if (status >= 200 && status < 300) return 'text-green-400';
    if (status >= 300 && status < 400) return 'text-yellow-400';
    if (status >= 400 && status < 500) return 'text-orange-400';
    if (status >= 500) return 'text-red-400';
    return 'text-slate-400';
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
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">Status:</span>
            <span className={`font-mono font-bold ${getStatusColor(response.status_code)}`}>
              {response.status_code} {getStatusText(response.status_code)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">Time:</span>
            <span className="font-mono text-cyan-400">{response.response_time}ms</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">Size:</span>
            <span className="font-mono text-purple-400">
              {formatBytes(response.body.length)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigator.clipboard.writeText(response.body)}
            className="text-slate-400 hover:text-white transition-colors text-xs"
            title="复制响应体"
          >
            <i className="fas fa-copy mr-1"></i>
            复制
          </button>
        </div>
      </div>

      {/* 标签页 */}
      <div className="flex items-center gap-1 px-4 border-b border-slate-700 bg-slate-800/30 flex-shrink-0">
        <button
          onClick={() => setActiveTab('body')}
          className={`
            px-4 py-2 text-sm transition-colors border-b-2
            ${activeTab === 'body'
              ? 'text-purple-400 border-purple-500'
              : 'text-slate-400 border-transparent hover:text-slate-300'
            }
          `}
        >
          <i className="fas fa-code mr-2"></i>
          Body
        </button>
        <button
          onClick={() => setActiveTab('headers')}
          className={`
            px-4 py-2 text-sm transition-colors border-b-2
            ${activeTab === 'headers'
              ? 'text-purple-400 border-purple-500'
              : 'text-slate-400 border-transparent hover:text-slate-300'
            }
          `}
        >
          <i className="fas fa-heading mr-2"></i>
          Headers
        </button>
        {request && (
          <button
            onClick={() => setActiveTab('code')}
            className={`
              px-4 py-2 text-sm transition-colors border-b-2
              ${activeTab === 'code'
                ? 'text-purple-400 border-purple-500'
                : 'text-slate-400 border-transparent hover:text-slate-300'
              }
            `}
          >
            <i className="fas fa-file-code mr-2"></i>
            Code
          </button>
        )}
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'body' && (
          <div>
            {/* Body 子标签 */}
            {isJson && (
              <div className="flex items-center gap-1 px-4 py-1 border-b border-slate-700/50 bg-slate-800/20">
                {(['raw', 'formatted', 'tree'] as const).map(view => (
                  <button
                    key={view}
                    onClick={() => setBodyView(view)}
                    className={`
                      px-2 py-1 text-xs rounded transition-colors
                      ${bodyView === view
                        ? 'bg-purple-500/20 text-purple-400'
                        : 'text-slate-500 hover:text-slate-300'
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
                <pre className="font-mono text-sm text-slate-300 whitespace-pre-wrap break-word">
                  {formattedBody}
                </pre>
              )}
            </div>
          </div>
        )}

        {activeTab === 'headers' && (
          <div className="p-4">
            <div className="space-y-1">
              {Object.entries(response.headers).map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-start gap-4 py-1.5 border-b border-slate-700/50 last:border-0"
                >
                  <span className="font-mono text-xs text-purple-400 min-w-[200px]">
                    {key}
                  </span>
                  <span className="font-mono text-xs text-slate-300 flex-1 break-all">
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'code' && request && (
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
                      ? 'bg-purple-500/20 text-purple-400 border border-purple-500'
                      : 'bg-slate-700 text-slate-400 border border-transparent hover:bg-slate-600'
                    }
                  `}
                >
                  {lang === 'curl' ? 'cURL' : lang === 'python' ? 'Python' : lang === 'javascript' ? 'JavaScript' : 'Go'}
                </button>
              ))}
              <button
                onClick={() => navigator.clipboard.writeText(codeSnippet)}
                className="ml-auto text-slate-400 hover:text-white transition-colors text-xs"
                title="复制代码"
              >
                <i className="fas fa-copy mr-1"></i>
                复制
              </button>
            </div>

            <pre className="font-mono text-sm text-slate-300 bg-slate-900/50 p-4 rounded-lg overflow-x-auto whitespace-pre">
              {codeSnippet}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
