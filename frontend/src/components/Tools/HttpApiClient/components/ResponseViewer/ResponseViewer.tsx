import { useState } from 'react';
import { SendRequestResponse } from '../../../../../services/httpClientApi';

interface ResponseViewerProps {
  response: SendRequestResponse;
}

export default function ResponseViewer({ response }: ResponseViewerProps) {
  const [activeTab, setActiveTab] = useState<'body' | 'headers'>('body');

  // 格式化 JSON
  const formatJson = (json: string) => {
    try {
      const parsed = JSON.parse(json);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return json;
    }
  };

  // 判断是否是 JSON 响应
  const isJson = response.content_type?.includes('application/json');
  const formattedBody = isJson ? formatJson(response.body) : response.body;

  // 计算状态码颜色
  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-green-400';
    if (status >= 300 && status < 400) return 'text-yellow-400';
    if (status >= 400 && status < 500) return 'text-orange-400';
    if (status >= 500) return 'text-red-400';
    return 'text-slate-400';
  };

  // 计算状态文本
  const getStatusText = (status: number) => {
    const statusTexts: Record<number, string> = {
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
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'body' && (
          <div className="p-4">
            <pre className="font-mono text-sm text-slate-300 whitespace-pre-wrap break-word">
              {formattedBody}
            </pre>
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
      </div>
    </div>
  );
}

// 格式化字节大小
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}
