import { useEffect, useMemo, useRef, useState } from 'react';
import { HttpRequest, FormDataEntry, KeyValueItem, BodyType, AssertionRule, ExtractVariableRule, kvFromDict } from '../../../../../services/httpClientApi';
import FormDataEditor from '../FormDataEditor/FormDataEditor';
import KeyValueTable, { COMMON_HEADERS, CONTENT_TYPE_SUGGESTIONS, DYNAMIC_VARIABLES } from '../KeyValueTable/KeyValueTable';
import PostOperations from '../PostOperations/PostOperations';
import ScriptEditor from '../ScriptEditor/ScriptEditor';
import { buildUrlWithQuery, rebuildParamsFromUrl, splitUrlQuery } from '../../utils/urlParamsSync';
import { Loader2, Send, Save, Trash2, Table, Heading, Code, Lock, BookOpen, Zap, FileUp, Braces, Loader } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

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

const MAX_BINARY_FILE_BYTES = 25 * 1024 * 1024;

/** 兼容旧数据：headers/params 可能是 dict 格式 */
function ensureKvList(v: unknown): KeyValueItem[] {
  if (Array.isArray(v)) return v as KeyValueItem[];
  return kvFromDict(v as Record<string, string>);
}

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
  const [activeTab, setActiveTab] = useState<'params' | 'body' | 'auth' | 'headers' | 'post' | 'docs'>('params');
  const binaryInputRef = useRef<HTMLInputElement>(null);
  const [binaryLoading, setBinaryLoading] = useState(false);

  const headers = useMemo(() => ensureKvList(request.headers), [request.headers]);
  const params = useMemo(() => ensureKvList(request.params), [request.params]);

  const envVariableNames = useMemo(() => Object.keys(envVariables), [envVariables]);

  const handleMethodChange = (method: string) => {
    onUpdate({ method });
  };

  // URL 编辑：解析 query 同步到 Params 表（保留已禁用参数）
  const handleUrlChange = (url: string) => {
    const newParams = rebuildParamsFromUrl(params, url);
    const path = splitUrlQuery(url).path;
    onUpdate({ url: path, params: newParams });
  };

  // Params 表编辑：启用的参数同步回 URL
  const handleParamsChange = (newParams: KeyValueItem[]) => {
    onUpdate({ params: newParams, url: buildUrlWithQuery(request.url, newParams) });
  };

  const handleBodyChange = (body: string) => {
    onUpdate({ body });
  };

  const getMethodColor = (method: string) => {
    const colors: Record<string, string> = {
      GET: 'text-success',
      POST: 'text-accent-info',
      PUT: 'text-accent-warning',
      DELETE: 'text-danger',
      PATCH: 'text-accent-secondary',
      HEAD: 'text-ink-muted',
      OPTIONS: 'text-ink-muted',
    };
    return colors[method] || 'text-ink-muted';
  };

  // binary 文件选择 → base64 data URL 存入 body
  const handleBinaryFile = async (file: File) => {
    if (file.size > MAX_BINARY_FILE_BYTES) {
      alert(`文件过大（${(file.size / 1024 / 1024).toFixed(1)}MB），binary 请求体上限 25MB`);
      return;
    }
    setBinaryLoading(true);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ''));
        reader.onerror = () => reject(reader.error || new Error('FileReader error'));
        reader.readAsDataURL(file);
      });
      onUpdate({ body: dataUrl });
    } finally {
      setBinaryLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* URL 栏 */}
      <div className="p-4 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2">
          {/* 方法选择器（固定宽度，避免 w-full 基础类挤压缩 URL 输入框） */}
          <Select value={request.method} onValueChange={handleMethodChange}>
            <SelectTrigger
              className={`w-32 shrink-0 bg-surface-2 px-3 py-2 font-mono text-sm focus:border-accent-secondary ${getMethodColor(request.method)}`}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {HTTP_METHODS.map(method => (
                <SelectItem key={method} value={method}>{method}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* URL 输入框（支持 {{变量}} 高亮） */}
          <div className="flex-1">
            <ScriptEditor
              value={request.url}
              onChange={handleUrlChange}
              language="plaintext"
              variables={envVariables}
              height="40px"
              placeholder="输入请求 URL（支持 {{变量}}，路径以 / 开头时自动拼接环境前置 URL）"
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
            title="Ctrl+Enter"
          >
            {sending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                发送中...
              </>
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                发送
              </>
            )}
          </button>

          {/* 保存按钮（有修改时高亮可点） */}
          {onSave && (
            <Button
              variant="default"
              size="sm"
              onClick={onSave}
              disabled={!isModified}
              title="Ctrl+S"
            >
              <Save className="w-4 h-4 mr-1" />
              保存
            </Button>
          )}

          {/* 删除按钮 */}
          {onDelete && (
            <button
              onClick={onDelete}
              title="删除"
              className="px-4 py-2 rounded-lg font-medium text-sm transition-colors
                         bg-danger/20 text-danger border border-danger hover:bg-danger/30"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              删除
            </button>
          )}
        </div>
      </div>

      {/* 标签页 */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as typeof activeTab)}
        className="flex flex-col flex-1 overflow-hidden"
      >
        <TabsList className="px-4 bg-surface-1/50 flex-shrink-0 w-full justify-start rounded-none border-b border-border">
          <TabsTrigger value="params" className="gap-2">
            <Table className="w-4 h-4" />
            Params
            {params.filter(p => p.enabled).length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-accent-secondary/20 text-accent-secondary text-[10px]">
                {params.filter(p => p.enabled).length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="body" className="gap-2">
            <Code className="w-4 h-4" />
            Body
            {request.body_type !== 'none' && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-accent-secondary/20 text-accent-secondary text-[10px]">
                {request.body_type === 'form-data' ? 'form' : request.body_type}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="auth" className="gap-2">
            <Lock className="w-4 h-4" />
            Auth
            {request.auth_type !== 'none' && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-accent-secondary/20 text-accent-secondary text-[10px]">
                {request.auth_type}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="headers" className="gap-2">
            <Heading className="w-4 h-4" />
            Headers
            {headers.filter(h => h.enabled).length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-accent-secondary/20 text-accent-secondary text-[10px]">
                {headers.filter(h => h.enabled).length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="post" className="gap-2">
            <Zap className="w-4 h-4" />
            后置操作
            {(request.assertions?.length || 0) + (request.extract_variables?.length || 0) > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-accent-secondary/20 text-accent-secondary text-[10px]">
                {(request.assertions?.length || 0) + (request.extract_variables?.length || 0)}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="docs" className="gap-2">
            <BookOpen className="w-4 h-4" />
            Docs
          </TabsTrigger>
        </TabsList>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-4">
          <TabsContent value="params">
            <ParamsPanel
              params={params}
              onChange={handleParamsChange}
              envVariableNames={envVariableNames}
            />
          </TabsContent>

          <TabsContent value="headers">
            <HeadersPanel
              headers={headers}
              onChange={(newHeaders) => onUpdate({ headers: newHeaders })}
              envVariableNames={envVariableNames}
            />
          </TabsContent>

          <TabsContent value="body">
            <BodyPanel
              bodyType={request.body_type}
              body={request.body}
              formData={request.form_data}
              envVariables={envVariables}
              envVariableNames={envVariableNames}
              binaryInputRef={binaryInputRef}
              binaryLoading={binaryLoading}
              onBodyTypeChange={(bodyType) => onUpdate({ body_type: bodyType as BodyType })}
              onBodyChange={handleBodyChange}
              onFormDataChange={(entries) => onUpdate({ form_data: entries })}
              onBinaryFile={handleBinaryFile}
            />
          </TabsContent>

          <TabsContent value="auth">
            <AuthPanel
              authType={request.auth_type}
              authConfig={request.auth_config}
              onAuthTypeChange={(authType) => onUpdate({ auth_type: authType as HttpRequest['auth_type'] })}
              onAuthConfigChange={(authConfig) => onUpdate({ auth_config: authConfig })}
              envVariables={envVariables}
            />
          </TabsContent>

          <TabsContent value="post">
            <PostOperations
              assertions={(request.assertions || []) as AssertionRule[]}
              extractVariables={(request.extract_variables || []) as ExtractVariableRule[]}
              onAssertionsChange={(rules) => onUpdate({ assertions: rules })}
              onExtractVariablesChange={(rules) => onUpdate({ extract_variables: rules })}
            />
          </TabsContent>

          <TabsContent value="docs">
            <DocsPanel
              description={request.description || ''}
              onChange={(description) => onUpdate({ description })}
            />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

// ============= Sub-components =============

interface ParamsPanelProps {
  params: KeyValueItem[];
  onChange: (params: KeyValueItem[]) => void;
  envVariableNames: string[];
}

/** Params 面板：与 URL query 双向同步的表格 */
function ParamsPanel({ params, onChange, envVariableNames }: ParamsPanelProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-ink-faint">
        启用的参数自动同步到上方 URL 的查询字符串，直接编辑 URL 也会同步到这里
      </p>
      <KeyValueTable
        items={params}
        onChange={onChange}
        keyPlaceholder="参数名"
        valuePlaceholder="参数值（支持 {{变量}}）"
        envVariableNames={envVariableNames}
        emptyHint="暂无查询参数，点击下方按钮添加，或直接在 URL 中输入 ?key=value"
      />
    </div>
  );
}

interface HeadersPanelProps {
  headers: KeyValueItem[];
  onChange: (headers: KeyValueItem[]) => void;
  envVariableNames: string[];
}

/** Headers 面板：常用头自动补全 + 启用/禁用 */
function HeadersPanel({ headers, onChange, envVariableNames }: HeadersPanelProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-ink-faint">
        Content-Type 会按 Body 类型自动设置（可在此手动覆盖）；取消勾选的 Header 不会发送
      </p>
      <KeyValueTable
        items={headers}
        onChange={onChange}
        keyPlaceholder="Header 名称"
        valuePlaceholder="Header 值（支持 {{变量}}）"
        keySuggestions={COMMON_HEADERS}
        valueSuggestions={{ 'content-type': CONTENT_TYPE_SUGGESTIONS }}
        envVariableNames={envVariableNames}
        emptyHint="暂无自定义 Header，点击下方按钮添加"
      />
    </div>
  );
}

interface BodyPanelProps {
  bodyType: string;
  body?: string;
  formData?: FormDataEntry[];
  envVariables: Record<string, string>;
  envVariableNames: string[];
  binaryInputRef: React.RefObject<HTMLInputElement | null>;
  binaryLoading: boolean;
  onBodyTypeChange: (type: string) => void;
  onBodyChange: (body: string) => void;
  onFormDataChange?: (entries: FormDataEntry[]) => void;
  onBinaryFile: (file: File) => void;
}

const BODY_TYPES: { value: BodyType; label: string; hint: string }[] = [
  { value: 'none', label: 'none', hint: '不发送请求体' },
  { value: 'json', label: 'JSON', hint: 'application/json' },
  { value: 'xml', label: 'XML', hint: 'application/xml' },
  { value: 'form', label: 'Form', hint: 'x-www-form-urlencoded' },
  { value: 'form-data', label: 'Form-data', hint: 'multipart/form-data，支持文件上传' },
  { value: 'raw', label: 'Raw', hint: '任意文本' },
  { value: 'binary', label: 'Binary', hint: '二进制文件' },
  { value: 'graphql', label: 'GraphQL', hint: 'GraphQL Query + Variables' },
];

function BodyPanel({
  bodyType,
  body,
  formData,
  envVariables,
  envVariableNames,
  binaryInputRef,
  binaryLoading,
  onBodyTypeChange,
  onBodyChange,
  onFormDataChange,
  onBinaryFile,
}: BodyPanelProps) {
  const [gqlQuery, setGqlQuery] = useState('');
  const [gqlVars, setGqlVars] = useState('');
  const gqlInitializedFor = useRef<string | null>(null);

  // 切换到 GraphQL 类型时，从已保存的 body 中拆出 query / variables（每类型切换只初始化一次）
  useEffect(() => {
    if (bodyType === 'graphql' && gqlInitializedFor.current !== 'graphql') {
      gqlInitializedFor.current = 'graphql';
      if (body) {
        try {
          const parsed = JSON.parse(body);
          setGqlQuery(parsed.query || '');
          setGqlVars(typeof parsed.variables === 'string' ? parsed.variables : JSON.stringify(parsed.variables || {}, null, 2));
        } catch {
          setGqlQuery(body);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bodyType]);

  // GraphQL 编辑：合并 query + variables 存回 body
  const handleGqlChange = (query: string, vars: string) => {
    setGqlQuery(query);
    setGqlVars(vars);
    let variablesObj: any = {};
    try {
      variablesObj = vars.trim() ? JSON.parse(vars) : {};
    } catch {
      variablesObj = { __invalid: vars };
    }
    onBodyChange(JSON.stringify({ query, variables: variablesObj }));
  };

  return (
    <div className="space-y-3">
      {/* Body 类型选择 */}
      <div className="flex items-center gap-2 flex-wrap">
        {BODY_TYPES.map(type => (
          <button
            key={type.value}
            onClick={() => onBodyTypeChange(type.value)}
            title={type.hint}
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
          onChange={onFormDataChange || (() => {})}
          envVariableNames={envVariableNames}
        />
      )}

      {/* binary 文件选择 */}
      {bodyType === 'binary' && (
        <div className="space-y-2">
          <input
            ref={binaryInputRef}
            type="file"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onBinaryFile(e.target.files[0])}
          />
          <div
            onClick={() => binaryInputRef.current?.click()}
            className="flex flex-col items-center justify-center gap-2 border border-dashed border-border
                       rounded-lg py-10 cursor-pointer hover:border-accent-secondary/60 hover:bg-surface-2/40 transition-colors"
          >
            {binaryLoading ? (
              <Loader className="w-6 h-6 text-accent-secondary animate-spin" />
            ) : (
              <FileUp className="w-6 h-6 text-ink-faint" />
            )}
            {body ? (
              <>
                <p className="text-sm text-ink">已选择文件</p>
                <p className="text-xs text-ink-faint">点击可重新选择；大小 {(body.length * 0.75 / 1024).toFixed(1)} KB</p>
              </>
            ) : (
              <>
                <p className="text-sm text-ink-muted">点击选择二进制文件</p>
                <p className="text-xs text-ink-faint">单文件上限 25MB，发送时以原始字节流传输</p>
              </>
            )}
          </div>
        </div>
      )}

      {/* GraphQL 编辑器 */}
      {bodyType === 'graphql' && (
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-ink-muted font-medium">Query</label>
            <ScriptEditor
              value={gqlQuery}
              onChange={(v) => handleGqlChange(v, gqlVars)}
              language="plaintext"
              variables={envVariables}
              height="220px"
              placeholder={'query {\\n  user(id: "1") {\\n    name\\n  }\\n}'}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-ink-muted font-medium">Variables（JSON）</label>
            <ScriptEditor
              value={gqlVars}
              onChange={(v) => handleGqlChange(gqlQuery, v)}
              language="json"
              variables={envVariables}
              height="220px"
              placeholder={'{\\n  "id": "1"\\n}'}
            />
          </div>
        </div>
      )}

      {/* JSON / XML / Raw / Form 编辑器 */}
      {(bodyType === 'json' || bodyType === 'xml' || bodyType === 'raw' || bodyType === 'form') && (
        <div className="space-y-1">
          {bodyType === 'json' && (
            <div className="flex items-center justify-between">
              <p className="text-xs text-ink-faint">支持 {'{{变量}}'} 替换；格式非法时以原文发送</p>
              <Button
                variant="ghost"
                size="sm"
                className="text-xs h-6 text-ink-muted"
                onClick={() => {
                  if (!body) return;
                  try {
                    onBodyChange(JSON.stringify(JSON.parse(body), null, 2));
                  } catch { /* 非法 JSON 不处理 */ }
                }}
                title="格式化 JSON"
              >
                <Braces className="w-3.5 h-3.5 mr-1" />
                格式化
              </Button>
            </div>
          )}
          <ScriptEditor
            value={body || ''}
            onChange={onBodyChange}
            language={bodyType === 'json' ? 'json' : 'plaintext'}
            variables={envVariables}
            height="240px"
            placeholder={
              bodyType === 'json'
                ? '{\n  "key": "{{变量}}"\n}'
                : bodyType === 'xml'
                ? '<?xml version="1.0"?>\n<request>\n  <key>value</key>\n</request>'
                : bodyType === 'form'
                ? 'key1=value1&key2=value2'
                : '输入请求体...'
            }
          />
        </div>
      )}

      {bodyType === 'none' && (
        <div className="text-ink-faint text-sm text-center py-10">
          此请求不携带请求体
        </div>
      )}
    </div>
  );
}

interface AuthPanelProps {
  authType: string;
  authConfig: Record<string, any>;
  onAuthTypeChange: (type: string) => void;
  onAuthConfigChange: (config: Record<string, any>) => void;
  envVariables: Record<string, string>;
}

const AUTH_TYPES = [
  { value: 'none', label: 'None' },
  { value: 'bearer', label: 'Bearer Token' },
  { value: 'basic', label: 'Basic Auth' },
  { value: 'apikey', label: 'API Key' },
];

function AuthPanel({ authType, authConfig, onAuthTypeChange, onAuthConfigChange, envVariables }: AuthPanelProps) {
  const handleBearerChange = (token: string) => {
    onAuthConfigChange({ ...authConfig, token });
  };

  const handleBasicChange = (username: string, password: string) => {
    onAuthConfigChange({ ...authConfig, username, password });
  };

  const handleApiKeyChange = (key: string, value: string, inHeader: boolean) => {
    onAuthConfigChange({ ...authConfig, key, value, in: inHeader ? 'header' : 'query' });
  };

  const VarHint = () => (
    <p className="text-xs text-ink-faint mt-1">
      支持环境变量 {'{{变量}}'} 与动态值（{DYNAMIC_VARIABLES.slice(0, 3).join('、')} 等）
    </p>
  );

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
        <div className="space-y-2 max-w-2xl">
          <label className="text-sm text-ink-muted">Token</label>
          <Input
            type="text"
            value={authConfig.token || ''}
            onChange={(e) => handleBearerChange(e.target.value)}
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... 或 {{token}}"
            className="w-full text-sm font-mono"
          />
          <VarHint />
          <p className="text-xs text-ink-faint">发送时自动附加 Header：<code className="text-accent-secondary">Authorization: Bearer &lt;token&gt;</code></p>
        </div>
      )}

      {/* Basic Auth */}
      {authType === 'basic' && (
        <div className="space-y-3 max-w-2xl">
          <div className="space-y-2">
            <label className="text-sm text-ink-muted">Username</label>
            <Input
              type="text"
              value={authConfig.username || ''}
              onChange={(e) => handleBasicChange(e.target.value, authConfig.password || '')}
              placeholder="username"
              className="w-full text-sm font-mono"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-ink-muted">Password</label>
            <Input
              type="password"
              value={authConfig.password || ''}
              onChange={(e) => handleBasicChange(authConfig.username || '', e.target.value)}
              placeholder="password"
              className="w-full text-sm font-mono"
            />
          </div>
          <p className="text-xs text-ink-faint">发送时自动 Base64 编码并附加 Authorization Header</p>
        </div>
      )}

      {/* API Key */}
      {authType === 'apikey' && (
        <div className="space-y-3 max-w-2xl">
          <div className="space-y-2">
            <label className="text-sm text-ink-muted">Key Name</label>
            <Input
              type="text"
              value={authConfig.key || ''}
              onChange={(e) => handleApiKeyChange(e.target.value, authConfig.value || '', authConfig.in === 'header')}
              placeholder="X-API-Key"
              className="w-full text-sm font-mono"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-ink-muted">Key Value</label>
            <Input
              type="text"
              value={authConfig.value || ''}
              onChange={(e) => handleApiKeyChange(authConfig.key || '', e.target.value, authConfig.in === 'header')}
              placeholder="your-api-key-value 或 {{apiKey}}"
              className="w-full text-sm font-mono"
            />
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="checkbox"
              id="inHeader"
              checked={authConfig.in !== 'query'}
              onChange={(e) => handleApiKeyChange(authConfig.key || '', authConfig.value || '', e.target.checked)}
              className="h-4 w-4 p-0 cursor-pointer"
            />
            <label htmlFor="inHeader" className="text-sm text-ink-muted">放在 Header 中（取消勾选则追加到 Query 参数）</label>
          </div>
        </div>
      )}

      {authType === 'none' && (
        <div className="text-ink-faint text-sm text-center py-8">
          <Lock className="w-10 h-10 mb-3 opacity-30" />
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
                  return <h3 key={i} className="text-lg font-bold text-ink mt-4 mb-2">{line.slice(4)}</h3>;
                }
                if (line.startsWith('## ')) {
                  return <h2 key={i} className="text-xl font-bold text-ink mt-4 mb-2">{line.slice(3)}</h2>;
                }
                if (line.startsWith('# ')) {
                  return <h1 key={i} className="text-2xl font-bold text-ink mt-4 mb-2">{line.slice(2)}</h1>;
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
          className="w-full h-64 bg-canvas text-ink px-4 py-3 rounded-lg
                     border border-border text-sm resize-none focus:border-accent-secondary focus:outline-none"
        />
      )}
    </div>
  );
}
