/**
 * Dify 配置 Tab — Task 12.1
 * URL + 4 个 workflow ID + 超时 + 测试连通性按钮
 */
import { useEffect, useState } from 'react';
import {
  getDifyConfig,
  updateDifyConfig,
  testDifyConnection,
  DifyConfig,
  UpdateDifyConfigRequest,
} from '../../../../api/adminImageGenerationApi';
import { useI18n } from '../../../../i18n';

export default function DifyConfigPanel() {
  const { t } = useI18n();
  const igT = t.imageGeneration.admin;
  const [config, setConfig] = useState<DifyConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 表单状态
  const [apiUrl, setApiUrl] = useState('');
  const [appApiKey, setAppApiKey] = useState('');
  const [text2imgWorkflowId, setText2imgWorkflowId] = useState('');
  const [img2imgWorkflowId, setImg2imgWorkflowId] = useState('');
  const [inpaintWorkflowId, setInpaintWorkflowId] = useState('');
  const [uploadEditWorkflowId, setUploadEditWorkflowId] = useState('');
  const [timeoutSeconds, setTimeoutSeconds] = useState(30);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDifyConfig();
      setConfig(data);
      // 填充表单
      setApiUrl(data.api_url || '');
      setText2imgWorkflowId(data.workflow_text2img || '');
      setImg2imgWorkflowId(data.workflow_img2img || '');
      setInpaintWorkflowId(data.workflow_inpaint || '');
      setUploadEditWorkflowId(data.workflow_upload_edit || '');
      setTimeoutSeconds(data.default_timeout || 30);
    } catch (e) {
      setError(e instanceof Error ? e.message : igT.loadConfigFailed);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const updates: UpdateDifyConfigRequest = {
        api_url: apiUrl,
        text2img_workflow_id: text2imgWorkflowId,
        img2img_workflow_id: img2imgWorkflowId,
        inpaint_workflow_id: inpaintWorkflowId,
        upload_edit_workflow_id: uploadEditWorkflowId,
        timeout_seconds: timeoutSeconds,
      };
      // 仅在用户输入了 API key 时才发送
      if (appApiKey.trim()) {
        updates.app_api_key = appApiKey;
      }
      const updated = await updateDifyConfig(updates);
      setConfig(updated);
      setAppApiKey(''); // 清空输入框
      setMessage({ type: 'success', text: igT.saveSuccess });
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : igT.saveFailed });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      setMessage(null);
      const result = await testDifyConnection();
      setMessage({
        type: result.success ? 'success' : 'error',
        text: result.success
          ? igT.connectionResultSuccess.replace('{message}', result.message)
          : igT.connectionResultFailed.replace('{message}', result.message),
      });
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : igT.testFailed });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-accent"></div>
        <p className="mt-4 text-ink-muted">{igT.loadConfigLoading}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-danger/10 border border-danger text-danger px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {message && (
        <div
          className={`px-4 py-3 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-500/10 border border-green-500 text-green-400'
              : 'bg-danger/10 border border-danger text-danger'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="bg-surface-1 border border-border rounded-lg p-6 space-y-4">
        <div>
          <label className="block text-sm text-ink-muted mb-2">
            {igT.apiUrl}
            <span className="text-danger ml-1">*</span>
          </label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder={igT.apiUrlPlaceholder}
            className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
          />
        </div>

        <div>
          <label className="block text-sm text-ink-muted mb-2">
            {igT.apiKey}
            <span className="text-ink-faint ml-2 text-xs">
              {config?.is_api_key_set ? igT.apiKeySet : igT.apiKeyUnset}
            </span>
          </label>
          <input
            type="password"
            value={appApiKey}
            onChange={(e) => setAppApiKey(e.target.value)}
            placeholder={igT.apiKeyPlaceholder}
            className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-ink-muted mb-2">{igT.text2imgWorkflowId}</label>
            <input
              type="text"
              value={text2imgWorkflowId}
              onChange={(e) => setText2imgWorkflowId(e.target.value)}
              className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-sm text-ink-muted mb-2">{igT.img2imgWorkflowId}</label>
            <input
              type="text"
              value={img2imgWorkflowId}
              onChange={(e) => setImg2imgWorkflowId(e.target.value)}
              className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-sm text-ink-muted mb-2">{igT.inpaintWorkflowId}</label>
            <input
              type="text"
              value={inpaintWorkflowId}
              onChange={(e) => setInpaintWorkflowId(e.target.value)}
              className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-sm text-ink-muted mb-2">{igT.uploadEditWorkflowId}</label>
            <input
              type="text"
              value={uploadEditWorkflowId}
              onChange={(e) => setUploadEditWorkflowId(e.target.value)}
              className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm text-ink-muted mb-2">{igT.timeoutSeconds}</label>
          <input
            type="number"
            min="5"
            max="300"
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
            className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
          />
          <p className="text-xs text-ink-faint mt-1">{igT.timeoutRange}</p>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-accent hover:bg-accent-hover disabled:bg-surface-3 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg transition-colors"
          >
            {saving ? igT.saving : igT.saveConfig}
          </button>
          <button
            onClick={handleTest}
            disabled={testing}
            className="bg-surface-2 hover:bg-surface-3 disabled:bg-surface-1 disabled:cursor-not-allowed text-ink-inverse px-6 py-2 rounded-lg transition-colors border border-border"
          >
            {testing ? igT.testing : igT.testConnection}
          </button>
        </div>
      </div>
    </div>
  );
}