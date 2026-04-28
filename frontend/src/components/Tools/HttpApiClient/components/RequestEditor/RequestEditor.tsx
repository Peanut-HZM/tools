import { useState } from 'react';
import { HttpRequest } from '../../../../../services/httpClientApi';

interface RequestEditorProps {
  request: HttpRequest;
  isModified: boolean;
  onUpdate: (updatedRequest: Partial<HttpRequest>) => void;
  onSend: () => void;
  sending: boolean;
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'];

export default function RequestEditor({
  request,
  isModified,
  onUpdate,
  onSend,
  sending,
}: RequestEditorProps) {
  const [activeTab, setActiveTab] = useState<'params' | 'headers' | 'body' | 'auth' | 'docs'>('params');

  const handleMethodChange = (method: string) => {
    onUpdate({ method });
  };

  const handleUrlChange = (url: string) => {
    onUpdate({ url });
  };

  const handleHeaderChange = (key: string, value: string, index: number) => {
    const newHeaders = { ...request.headers };
    if (key) {
      newHeaders[key] = value;
    }
    onUpdate({ headers: newHeaders });
  };

  const handleParamChange = (key: string, value: string, index: number) => {
    const newParams = { ...request.params };
    if (key) {
      newParams[key] = value;
    }
    onUpdate({ params: newParams });
  };

  const handleBodyChange = (body: string) => {
    onUpdate({ body });
  };

  const handleAddParam = () => {
    const key = `param_${Date.now()}`;
    const newParams = { ...request.params, [key]: '' };
    onUpdate({ params: newParams });
  };

  const handleRemoveParam = (key: string) => {
    const newParams = { ...request.params };
    delete newParams[key];
    onUpdate({ params: newParams });
  };

  const handleAddHeader = () => {
    const key = `header_${Date.now()}`;
    const newHeaders = { ...request.headers, [key]: '' };
    onUpdate({ headers: newHeaders });
  };

  const handleRemoveHeader = (key: string) => {
    const newHeaders = { ...request.headers };
    delete newHeaders[key];
    onUpdate({ headers: newHeaders });
  };

  const getMethodColor = (method: string) => {
    const colors: Record<string, string> = {
      GET: 'text-green-400',
      POST: 'text-blue-400',
      PUT: 'text-yellow-400',
      DELETE: 'text-red-400',
      PATCH: 'text-purple-400',
      HEAD: 'text-slate-400',
      OPTIONS: 'text-slate-400',
    };
    return colors[method] || 'text-slate-400';
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* URL 栏 */}
      <div className="p-4 border-b border-slate-700 flex-shrink-0">
        <div className="flex items-center gap-2">
          {/* 方法选择器 */}
          <select
            value={request.method}
            onChange={(e) => handleMethodChange(e.target.value)}
            className={`
              bg-slate-700 text-white px-3 py-2 rounded-lg font-mono text-sm
              border border-slate-600 focus:border-purple-500 focus:outline-none
              ${getMethodColor(request.method)}
            `}
          >
            {HTTP_METHODS.map(method => (
              <option key={method} value={method}>{method}</option>
            ))}
          </select>

          {/* URL 输入框 */}
          <input
            type="text"
            value={request.url}
            onChange={(e) => handleUrlChange(e.target.value)}
            placeholder="输入请求 URL"
            className="flex-1 bg-slate-700 text-white px-4 py-2 rounded-lg text-sm
                       border border-slate-600 focus:border-purple-500 focus:outline-none"
          />

          {/* 发送按钮 */}
          <button
            onClick={onSend}
            disabled={sending}
            className={`
              px-6 py-2 rounded-lg font-medium text-sm transition-colors
              ${sending
                ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white'
              }
            `}
          >
            {sending ? (
              <>
                <i className="fas fa-spinner fa-spin mr-2"></i>
                发送中...
              </>
            ) : (
              <>
                <i className="fas fa-paper-plane mr-2"></i>
                发送
              </>
            )}
          </button>
        </div>
      </div>

      {/* 标签页 */}
      <div className="flex items-center gap-1 px-4 border-b border-slate-700 bg-slate-800/50 flex-shrink-0">
        <button
          onClick={() => setActiveTab('params')}
          className={`
            px-4 py-2 text-sm transition-colors border-b-2
            ${activeTab === 'params'
              ? 'text-purple-400 border-purple-500'
              : 'text-slate-400 border-transparent hover:text-slate-300'
            }
          `}
        >
          <i className="fas fa-table mr-2"></i>
          Params
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
          onClick={() => setActiveTab('auth')}
          className={`
            px-4 py-2 text-sm transition-colors border-b-2
            ${activeTab === 'auth'
              ? 'text-purple-400 border-purple-500'
              : 'text-slate-400 border-transparent hover:text-slate-300'
            }
          `}
        >
          <i className="fas fa-lock mr-2"></i>
          Auth
        </button>
        <button
          onClick={() => setActiveTab('docs')}
          className={`
            px-4 py-2 text-sm transition-colors border-b-2
            ${activeTab === 'docs'
              ? 'text-purple-400 border-purple-500'
              : 'text-slate-400 border-transparent hover:text-slate-300'
            }
          `}
        >
          <i className="fas fa-book mr-2"></i>
          Docs
        </button>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'params' && (
          <ParamsPanel
            params={request.params}
            onChange={handleParamChange}
            onAdd={handleAddParam}
            onRemove={handleRemoveParam}
          />
        )}
        {activeTab === 'headers' && (
          <HeadersPanel
            headers={request.headers}
            onChange={handleHeaderChange}
            onAdd={handleAddHeader}
            onRemove={handleRemoveHeader}
          />
        )}
        {activeTab === 'body' && (
          <BodyPanel
            bodyType={request.body_type}
            body={request.body}
            onBodyTypeChange={(bodyType) => onUpdate({ body_type: bodyType as any })}
            onBodyChange={handleBodyChange}
          />
        )}
        {activeTab === 'auth' && (
          <AuthPanel
            authType={request.auth_type}
            authConfig={request.auth_config}
            onAuthTypeChange={(authType) => onUpdate({ auth_type: authType as any })}
            onAuthConfigChange={(authConfig) => onUpdate({ auth_config: authConfig })}
          />
        )}
        {activeTab === 'docs' && (
          <DocsPanel
            description={request.description || ''}
            onChange={(description) => onUpdate({ description })}
          />
        )}
      </div>
    </div>
  );
}

// ============= Sub-components =============

interface ParamsPanelProps {
  params: Record<string, string>;
  onChange: (key: string, value: string, index: number) => void;
  onAdd: () => void;
  onRemove: (key: string) => void;
}

function ParamsPanel({ params, onChange, onAdd, onRemove }: ParamsPanelProps) {
  const entries = Object.entries(params);

  return (
    <div className="space-y-2">
      {entries.length === 0 ? (
        <div className="text-slate-500 text-sm text-center py-8">
          暂无参数，点击下方按钮添加
        </div>
      ) : (
        entries.map(([key, value], index) => (
          <div key={index} className="flex items-center gap-2">
            <input
              type="text"
              value={key}
              onChange={(e) => onChange(e.target.value, value, index)}
              placeholder="参数名"
              className="flex-1 bg-slate-700 text-white px-3 py-2 rounded border border-slate-600 text-sm"
            />
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(key, e.target.value, index)}
              placeholder="参数值"
              className="flex-1 bg-slate-700 text-white px-3 py-2 rounded border border-slate-600 text-sm"
            />
            <button
              onClick={() => onRemove(key)}
              className="text-slate-500 hover:text-red-400 transition-colors"
            >
              <i className="fas fa-times"></i>
            </button>
          </div>
        ))
      )}
      <button
        onClick={onAdd}
        className="text-purple-400 hover:text-purple-300 transition-colors text-sm"
      >
        <i className="fas fa-plus mr-2"></i>
        添加参数
      </button>
    </div>
  );
}

interface HeadersPanelProps {
  headers: Record<string, string>;
  onChange: (key: string, value: string, index: number) => void;
  onAdd: () => void;
  onRemove: (key: string) => void;
}

function HeadersPanel({ headers, onChange, onAdd, onRemove }: HeadersPanelProps) {
  const entries = Object.entries(headers);

  return (
    <div className="space-y-2">
      {entries.length === 0 ? (
        <div className="text-slate-500 text-sm text-center py-8">
          暂无 Header，点击下方按钮添加
        </div>
      ) : (
        entries.map(([key, value], index) => (
          <div key={index} className="flex items-center gap-2">
            <input
              type="text"
              value={key}
              onChange={(e) => onChange(e.target.value, value, index)}
              placeholder="Header 名"
              className="flex-1 bg-slate-700 text-white px-3 py-2 rounded border border-slate-600 text-sm"
            />
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(key, e.target.value, index)}
              placeholder="Header 值"
              className="flex-1 bg-slate-700 text-white px-3 py-2 rounded border border-slate-600 text-sm"
            />
            <button
              onClick={() => onRemove(key)}
              className="text-slate-500 hover:text-red-400 transition-colors"
            >
              <i className="fas fa-times"></i>
            </button>
          </div>
        ))
      )}
      <button
        onClick={onAdd}
        className="text-purple-400 hover:text-purple-300 transition-colors text-sm"
      >
        <i className="fas fa-plus mr-2"></i>
        添加 Header
      </button>
    </div>
  );
}

interface BodyPanelProps {
  bodyType: string;
  body?: string;
  onBodyTypeChange: (type: string) => void;
  onBodyChange: (body: string) => void;
}

const BODY_TYPES = [
  { value: 'none', label: 'none' },
  { value: 'json', label: 'JSON' },
  { value: 'form', label: 'Form' },
  { value: 'raw', label: 'Raw' },
];

function BodyPanel({ bodyType, body, onBodyTypeChange, onBodyChange }: BodyPanelProps) {
  return (
    <div className="space-y-3">
      {/* Body 类型选择 */}
      <div className="flex items-center gap-2">
        {BODY_TYPES.map(type => (
          <button
            key={type.value}
            onClick={() => onBodyTypeChange(type.value)}
            className={`
              px-3 py-1.5 rounded text-xs font-medium transition-colors
              ${bodyType === type.value
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500'
                : 'bg-slate-700 text-slate-400 border border-transparent hover:bg-slate-600'
              }
            `}
          >
            {type.label}
          </button>
        ))}
      </div>

      {/* Body 编辑器 */}
      {bodyType !== 'none' && (
        <textarea
          value={body || ''}
          onChange={(e) => onBodyChange(e.target.value)}
          placeholder={
            bodyType === 'json'
              ? '{\n  "key": "value"\n}'
              : bodyType === 'form'
              ? 'key1=value1&key2=value2'
              : '输入请求体...'
          }
          className="w-full h-64 bg-slate-900 text-white px-4 py-3 rounded-lg
                     border border-slate-600 font-mono text-sm resize-none
                     focus:border-purple-500 focus:outline-none"
        />
      )}
    </div>
  );
}

interface AuthPanelProps {
  authType: string;
  authConfig: Record<string, any>;
  onAuthTypeChange: (type: string) => void;
  onAuthConfigChange: (config: Record<string, any>) => void;
}

const AUTH_TYPES = [
  { value: 'none', label: 'None' },
  { value: 'bearer', label: 'Bearer Token' },
  { value: 'basic', label: 'Basic Auth' },
  { value: 'apikey', label: 'API Key' },
];

function AuthPanel({ authType, authConfig, onAuthTypeChange, onAuthConfigChange }: AuthPanelProps) {
  const handleBearerChange = (token: string) => {
    onAuthConfigChange({ ...authConfig, token });
  };

  const handleBasicChange = (username: string, password: string) => {
    onAuthConfigChange({ ...authConfig, username, password });
  };

  const handleApiKeyChange = (key: string, value: string, inHeader: boolean) => {
    onAuthConfigChange({ ...authConfig, key, value, in: inHeader ? 'header' : 'query' });
  };

  return (
    <div className="space-y-4">
      {/* Auth 类型选择 */}
      <div className="flex items-center gap-2 flex-wrap">
        {AUTH_TYPES.map(type => (
          <button
            key={type.value}
            onClick={() => onAuthTypeChange(type.value)}
            className={`
              px-3 py-1.5 rounded text-xs font-medium transition-colors
              ${authType === type.value
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500'
                : 'bg-slate-700 text-slate-400 border border-transparent hover:bg-slate-600'
              }
            `}
          >
            {type.label}
          </button>
        ))}
      </div>

      {/* Bearer Token */}
      {authType === 'bearer' && (
        <div className="space-y-2">
          <label className="text-sm text-slate-400">Token</label>
          <input
            type="text"
            value={authConfig.token || ''}
            onChange={(e) => handleBearerChange(e.target.value)}
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            className="w-full bg-slate-700 text-white px-4 py-2 rounded border border-slate-600 text-sm"
          />
        </div>
      )}

      {/* Basic Auth */}
      {authType === 'basic' && (
        <div className="space-y-3">
          <div className="space-y-2">
            <label className="text-sm text-slate-400">Username</label>
            <input
              type="text"
              value={authConfig.username || ''}
              onChange={(e) => handleBasicChange(e.target.value, authConfig.password || '')}
              placeholder="username"
              className="w-full bg-slate-700 text-white px-4 py-2 rounded border border-slate-600 text-sm"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-slate-400">Password</label>
            <input
              type="password"
              value={authConfig.password || ''}
              onChange={(e) => handleBasicChange(authConfig.username || '', e.target.value)}
              placeholder="password"
              className="w-full bg-slate-700 text-white px-4 py-2 rounded border border-slate-600 text-sm"
            />
          </div>
        </div>
      )}

      {/* API Key */}
      {authType === 'apikey' && (
        <div className="space-y-3">
          <div className="space-y-2">
            <label className="text-sm text-slate-400">Key Name</label>
            <input
              type="text"
              value={authConfig.key || ''}
              onChange={(e) => handleApiKeyChange(e.target.value, authConfig.value || '', authConfig.in === 'header')}
              placeholder="X-API-Key"
              className="w-full bg-slate-700 text-white px-4 py-2 rounded border border-slate-600 text-sm"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-slate-400">Key Value</label>
            <input
              type="text"
              value={authConfig.value || ''}
              onChange={(e) => handleApiKeyChange(authConfig.key || '', e.target.value, authConfig.in === 'header')}
              placeholder="your-api-key-value"
              className="w-full bg-slate-700 text-white px-4 py-2 rounded border border-slate-600 text-sm"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="inHeader"
              checked={authConfig.in !== 'query'}
              onChange={(e) => handleApiKeyChange(authConfig.key || '', authConfig.value || '', e.target.checked)}
              className="rounded border-slate-600 bg-slate-700"
            />
            <label htmlFor="inHeader" className="text-sm text-slate-400">放在 Header 中</label>
          </div>
        </div>
      )}

      {authType === 'none' && (
        <div className="text-slate-500 text-sm text-center py-8">
          <i className="fas fa-unlock text-4xl mb-3 opacity-30"></i>
          <p>此请求不需要认证</p>
        </div>
      )}
    </div>
  );
}

// ============= Docs Panel =============

interface DocsPanelProps {
  description: string;
  onChange: (description: string) => void;
}

function DocsPanel({ description, onChange }: DocsPanelProps) {
  const [preview, setPreview] = useState(false);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-400">请求描述（支持 Markdown）</span>
        <button
          onClick={() => setPreview(!preview)}
          className="px-3 py-1 rounded text-xs font-medium transition-colors
                     bg-slate-700 text-slate-300 hover:bg-slate-600"
        >
          {preview ? '编辑' : '预览'}
        </button>
      </div>
      {preview ? (
        <div className="bg-slate-900 border border-slate-600 rounded-lg p-4 text-sm text-slate-300 min-h-[256px]">
          {description ? (
            <div className="prose prose-invert max-w-none">
              {description.split('\n').map((line, i) => {
                // 简易 Markdown 渲染
                if (line.startsWith('### ')) {
                  return <h3 key={i} className="text-lg font-bold text-white mt-4 mb-2">{line.slice(4)}</h3>;
                }
                if (line.startsWith('## ')) {
                  return <h2 key={i} className="text-xl font-bold text-white mt-4 mb-2">{line.slice(3)}</h2>;
                }
                if (line.startsWith('# ')) {
                  return <h1 key={i} className="text-2xl font-bold text-white mt-4 mb-2">{line.slice(2)}</h1>;
                }
                if (line.startsWith('- ') || line.startsWith('* ')) {
                  return <li key={i} className="ml-4">{line.slice(2)}</li>;
                }
                if (line.startsWith('```')) {
                  return <hr key={i} className="my-2 border-slate-600" />;
                }
                if (line.trim() === '') {
                  return <br key={i} />;
                }
                return <p key={i} className="mb-1">{line}</p>;
              })}
            </div>
          ) : (
            <span className="text-slate-600 italic">暂无描述</span>
          )}
        </div>
      ) : (
        <textarea
          value={description}
          onChange={(e) => onChange(e.target.value)}
          placeholder="输入请求描述，支持 Markdown 语法..."
          className="w-full h-64 bg-slate-900 text-white px-4 py-3 rounded-lg
                     border border-slate-600 text-sm resize-none focus:border-purple-500 focus:outline-none"
        />
      )}
    </div>
  );
}
