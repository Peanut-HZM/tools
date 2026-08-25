import { useState } from 'react';
import { HttpRequest, FormDataEntry } from '../../../../../services/httpClientApi';
import FormDataEditor from '../FormDataEditor/FormDataEditor';
import ScriptEditor from '../ScriptEditor/ScriptEditor';

interface RequestEditorProps {
  request: HttpRequest;
  isModified: boolean;
  onUpdate: (updatedRequest: Partial<HttpRequest>) => void;
  onSend: () => void;
  sending: boolean;
  /** 环境变量，用于 URL/Headers/Params 中的 {{变量}} 高亮与补全 */
  envVariables?: Record<string, string>;
  /** 保存回调（历史回放标签页不传，隐藏保存按钮） */
  onSave?: () => void;
  /** 删除回调（历史回放标签页不传，隐藏删除按钮） */
  onDelete?: () => void;
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'];

export default function RequestEditor({
  request,
  isModified,
  onUpdate,
  onSend,
  sending,
  envVariables = {},
  onSave,
  onDelete,
}: RequestEditorProps) {
  const [activeTab, setActiveTab] = useState<'params' | 'headers' | 'body' | 'auth' | 'docs'>('params');

  const handleMethodChange = (method: string) => {
    onUpdate({ method });
  };

  const handleUrlChange = (url: string) => {
    onUpdate({ url });
  };

  const handleBodyChange = (body: string) => {
    onUpdate({ body });
  };

  const getMethodColor = (method: string) => {
    const colors: Record<string, string> = {
      GET: 'text-green-400',
      POST: 'text-accent-info',
      PUT: 'text-accent-warning',
      DELETE: 'text-danger',
      PATCH: 'text-accent-secondary',
      HEAD: 'text-ink-muted',
      OPTIONS: 'text-ink-muted',
    };
    return colors[method] || 'text-ink-muted';
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* URL 栏 */}
      <div className="p-4 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2">
          {/* 方法选择器 */}
          <select
            value={request.method}
            onChange={(e) => handleMethodChange(e.target.value)}
            className={`
              bg-surface-2 text-ink-inverse px-3 py-2 rounded-lg font-mono text-sm
              border border-border focus:border-accent-secondary focus:outline-none
              ${getMethodColor(request.method)}
            `}
          >
            {HTTP_METHODS.map(method => (
              <option key={method} value={method}>{method}</option>
            ))}
          </select>

          {/* URL 输入框（支持 {{变量}} 高亮） */}
          <div className="flex-1">
            <ScriptEditor
              value={request.url}
              onChange={handleUrlChange}
              language="plaintext"
              variables={envVariables}
              height="40px"
              placeholder="输入请求 URL，支持 {{变量}} 语法"
            />
          </div>

          {/* 发送按钮 */}
          <button
            onClick={onSend}
            disabled={sending}
            className={`
              px-6 py-2 rounded-lg font-medium text-sm transition-colors
              ${sending
                ? 'bg-surface-3 text-ink-muted cursor-not-allowed'
                : 'bg-gradient-to-r from-accent-secondary to-accent-info hover:from-accent-secondary hover:to-accent-hover text-ink-inverse'
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

          {/* 保存按钮（有修改时高亮可点） */}
          {onSave && (
            <button
              onClick={onSave}
              disabled={!isModified}
              title="保存"
              className={`
                px-4 py-2 rounded-lg font-medium text-sm transition-colors
                ${isModified
                  ? 'bg-accent-secondary hover:bg-accent-secondary text-ink-inverse'
                  : 'bg-surface-2 text-ink-faint cursor-not-allowed'
                }
              `}
            >
              <i className="fas fa-save mr-1"></i>
              保存
            </button>
          )}

          {/* 删除按钮 */}
          {onDelete && (
            <button
              onClick={onDelete}
              title="删除"
              className="px-4 py-2 rounded-lg font-medium text-sm transition-colors
                         bg-danger/20 text-danger border border-red-500 hover:bg-red-500/30"
            >
              <i className="fas fa-trash mr-1"></i>
              删除
            </button>
          )}
        </div>
      </div>

      {/* 标签页 */}
      <div className="flex items-center gap-1 px-4 border-b border-border bg-surface-1/50 flex-shrink-0">
        <button
          onClick={() => setActiveTab('params')}
          className={`
            px-4 py-2 text-sm transition-colors border-b-2
            ${activeTab === 'params'
              ? 'text-accent-secondary border-accent-secondary'
              : 'text-ink-muted border-transparent hover:text-ink-muted'
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
              ? 'text-accent-secondary border-accent-secondary'
              : 'text-ink-muted border-transparent hover:text-ink-muted'
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
              ? 'text-accent-secondary border-accent-secondary'
              : 'text-ink-muted border-transparent hover:text-ink-muted'
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
              ? 'text-accent-secondary border-accent-secondary'
              : 'text-ink-muted border-transparent hover:text-ink-muted'
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
              ? 'text-accent-secondary border-accent-secondary'
              : 'text-ink-muted border-transparent hover:text-ink-muted'
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
            onChange={(params) => onUpdate({ params })}
            envVariables={envVariables}
          />
        )}
        {activeTab === 'headers' && (
          <HeadersPanel
            headers={request.headers}
            onChange={(headers) => onUpdate({ headers })}
            envVariables={envVariables}
          />
        )}
        {activeTab === 'body' && (
          <BodyPanel
            bodyType={request.body_type}
            body={request.body}
            formData={request.form_data}
            onBodyTypeChange={(bodyType) => onUpdate({ body_type: bodyType as any })}
            onBodyChange={handleBodyChange}
            onFormDataChange={(entries) => onUpdate({ form_data: entries })}
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
  onChange: (params: Record<string, string>) => void;
  envVariables: Record<string, string>;
}

/**
 * 参数面板：使用 ScriptEditor 支持 {{变量}} 高亮
 * 每行一个参数，格式：key=value
 */
function ParamsPanel({ params, onChange, envVariables }: ParamsPanelProps) {
  const text = Object.entries(params).map(([k, v]) => `${k}=${v}`).join('\n');

  return (
    <div className="space-y-2">
      <ScriptEditor
        value={text}
        onChange={(newText) => {
          const newParams = newText.split('\n').reduce((acc, line) => {
            const eqIndex = line.indexOf('=');
            if (eqIndex > 0) {
              const key = line.slice(0, eqIndex).trim();
              const value = line.slice(eqIndex + 1).trim();
              if (key) {
                acc[key] = value;
              }
            }
            return acc;
          }, {} as Record<string, string>);
          onChange(newParams);
        }}
        language="plaintext"
        variables={envVariables}
        height="150px"
        placeholder="每行一个参数，格式：key=value（支持 {{变量}}）"
      />
    </div>
  );
}

interface HeadersPanelProps {
  headers: Record<string, string>;
  onChange: (headers: Record<string, string>) => void;
  envVariables: Record<string, string>;
}

/**
 * Headers 面板：使用 ScriptEditor 支持 {{变量}} 高亮
 * 每行一个 header，格式：key: value
 */
function HeadersPanel({ headers, onChange, envVariables }: HeadersPanelProps) {
  const text = Object.entries(headers).map(([k, v]) => `${k}: ${v}`).join('\n');

  return (
    <div className="space-y-2">
      <ScriptEditor
        value={text}
        onChange={(newText) => {
          const newHeaders = newText.split('\n').reduce((acc, line) => {
            const colonIndex = line.indexOf(':');
            if (colonIndex > 0) {
              const key = line.slice(0, colonIndex).trim();
              const value = line.slice(colonIndex + 1).trim();
              if (key) {
                acc[key] = value;
              }
            }
            return acc;
          }, {} as Record<string, string>);
          onChange(newHeaders);
        }}
        language="plaintext"
        variables={envVariables}
        height="150px"
        placeholder="每行一个 Header，格式：key: value（支持 {{变量}}）"
      />
    </div>
  );
}

interface BodyPanelProps {
  bodyType: string;
  body?: string;
  formData?: FormDataEntry[];
  onBodyTypeChange: (type: string) => void;
  onBodyChange: (body: string) => void;
  onFormDataChange?: (entries: FormDataEntry[]) => void;
}

const BODY_TYPES = [
  { value: 'none', label: 'none' },
  { value: 'json', label: 'JSON' },
  { value: 'form', label: 'Form' },
  { value: 'form-data', label: 'Form-data' },
  { value: 'raw', label: 'Raw' },
];

function BodyPanel({
  bodyType,
  body,
  formData,
  onBodyTypeChange,
  onBodyChange,
  onFormDataChange,
}: BodyPanelProps) {
  // form-data 类型：将 FormDataEntry[] 转换为 JSON 字符串存到 body
  const handleFormDataChange = (entries: FormDataEntry[]) => {
    // 通知父组件更新 form_data 字段
    if (onFormDataChange) {
      onFormDataChange(entries);
    }
    // 将 FormDataEntry[] 转换为后端格式
    const formDataObj = entries.reduce((acc, entry) => {
      acc[entry.key] = entry.type === 'file' ? entry.file?.name || '' : entry.value;
      return acc;
    }, {} as Record<string, any>);
    onBodyChange(JSON.stringify(formDataObj));
  };

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
                ? 'bg-accent-secondary/20 text-accent-secondary border border-accent-secondary'
                : 'bg-surface-2 text-ink-muted border border-transparent hover:bg-surface-3'
              }
            `}
          >
            {type.label}
          </button>
        ))}
      </div>

      {/* form-data 编辑器 */}
      {bodyType === 'form-data' && (
        <FormDataEditor
          formData={formData || []}
          onChange={handleFormDataChange}
        />
      )}

      {/* 其他类型 Body 编辑器 */}
      {bodyType !== 'none' && bodyType !== 'form-data' && (
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
          className="w-full h-64 bg-canvas text-ink-inverse px-4 py-3 rounded-lg
                     border border-border font-mono text-sm resize-none
                     focus:border-accent-secondary focus:outline-none"
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
                ? 'bg-accent-secondary/20 text-accent-secondary border border-accent-secondary'
                : 'bg-surface-2 text-ink-muted border border-transparent hover:bg-surface-3'
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
          <label className="text-sm text-ink-muted">Token</label>
          <input
            type="text"
            value={authConfig.token || ''}
            onChange={(e) => handleBearerChange(e.target.value)}
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            className="w-full bg-surface-2 text-ink-inverse px-4 py-2 rounded border border-border text-sm"
          />
        </div>
      )}

      {/* Basic Auth */}
      {authType === 'basic' && (
        <div className="space-y-3">
          <div className="space-y-2">
            <label className="text-sm text-ink-muted">Username</label>
            <input
              type="text"
              value={authConfig.username || ''}
              onChange={(e) => handleBasicChange(e.target.value, authConfig.password || '')}
              placeholder="username"
              className="w-full bg-surface-2 text-ink-inverse px-4 py-2 rounded border border-border text-sm"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-ink-muted">Password</label>
            <input
              type="password"
              value={authConfig.password || ''}
              onChange={(e) => handleBasicChange(authConfig.username || '', e.target.value)}
              placeholder="password"
              className="w-full bg-surface-2 text-ink-inverse px-4 py-2 rounded border border-border text-sm"
            />
          </div>
        </div>
      )}

      {/* API Key */}
      {authType === 'apikey' && (
        <div className="space-y-3">
          <div className="space-y-2">
            <label className="text-sm text-ink-muted">Key Name</label>
            <input
              type="text"
              value={authConfig.key || ''}
              onChange={(e) => handleApiKeyChange(e.target.value, authConfig.value || '', authConfig.in === 'header')}
              placeholder="X-API-Key"
              className="w-full bg-surface-2 text-ink-inverse px-4 py-2 rounded border border-border text-sm"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-ink-muted">Key Value</label>
            <input
              type="text"
              value={authConfig.value || ''}
              onChange={(e) => handleApiKeyChange(authConfig.key || '', e.target.value, authConfig.in === 'header')}
              placeholder="your-api-key-value"
              className="w-full bg-surface-2 text-ink-inverse px-4 py-2 rounded border border-border text-sm"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="inHeader"
              checked={authConfig.in !== 'query'}
              onChange={(e) => handleApiKeyChange(authConfig.key || '', authConfig.value || '', e.target.checked)}
              className="rounded border-border bg-surface-2"
            />
            <label htmlFor="inHeader" className="text-sm text-ink-muted">放在 Header 中</label>
          </div>
        </div>
      )}

      {authType === 'none' && (
        <div className="text-ink-faint text-sm text-center py-8">
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
        <span className="text-sm text-ink-muted">请求描述（支持 Markdown）</span>
        <button
          onClick={() => setPreview(!preview)}
          className="px-3 py-1 rounded text-xs font-medium transition-colors
                     bg-surface-2 text-ink-muted hover:bg-surface-3"
        >
          {preview ? '编辑' : '预览'}
        </button>
      </div>
      {preview ? (
        <div className="bg-canvas border border-border rounded-lg p-4 text-sm text-ink-muted min-h-[256px]">
          {description ? (
            <div className="prose prose-invert max-w-none">
              {description.split('\n').map((line, i) => {
                // 简易 Markdown 渲染
                if (line.startsWith('### ')) {
                  return <h3 key={i} className="text-lg font-bold text-ink-inverse mt-4 mb-2">{line.slice(4)}</h3>;
                }
                if (line.startsWith('## ')) {
                  return <h2 key={i} className="text-xl font-bold text-ink-inverse mt-4 mb-2">{line.slice(3)}</h2>;
                }
                if (line.startsWith('# ')) {
                  return <h1 key={i} className="text-2xl font-bold text-ink-inverse mt-4 mb-2">{line.slice(2)}</h1>;
                }
                if (line.startsWith('- ') || line.startsWith('* ')) {
                  return <li key={i} className="ml-4">{line.slice(2)}</li>;
                }
                if (line.startsWith('```')) {
                  return <hr key={i} className="my-2 border-border" />;
                }
                if (line.trim() === '') {
                  return <br key={i} />;
                }
                return <p key={i} className="mb-1">{line}</p>;
              })}
            </div>
          ) : (
            <span className="text-ink-faint italic">暂无描述</span>
          )}
        </div>
      ) : (
        <textarea
          value={description}
          onChange={(e) => onChange(e.target.value)}
          placeholder="输入请求描述，支持 Markdown 语法..."
          className="w-full h-64 bg-canvas text-ink-inverse px-4 py-3 rounded-lg
                     border border-border text-sm resize-none focus:border-accent-secondary focus:outline-none"
        />
      )}
    </div>
  );
}
