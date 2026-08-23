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

export default function DifyConfigPanel() {
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
      setError(e instanceof Error ? e.message : '加载配置失败');
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
      setMessage({ type: 'success', text: '配置已保存' });
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : '保存失败' });
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
        text: result.success ? `连接成功：${result.message}` : `连接失败：${result.message}`,
      });
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : '测试失败' });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500"></div>
        <p className="mt-4 text-slate-400">加载配置中...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {message && (
        <div
          className={`px-4 py-3 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-500/10 border border-green-500 text-green-400'
              : 'bg-red-500/10 border border-red-500 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 space-y-4">
        <div>
          <label className="block text-sm text-slate-300 mb-2">
            Dify API URL
            <span className="text-red-400 ml-1">*</span>
          </label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="https://api.dify.ai/v1"
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div>
          <label className="block text-sm text-slate-300 mb-2">
            App API Key
            <span className="text-slate-500 ml-2 text-xs">
              {config?.is_api_key_set ? '（已设置，留空保持不变）' : '（未设置）'}
            </span>
          </label>
          <input
            type="password"
            value={appApiKey}
            onChange={(e) => setAppApiKey(e.target.value)}
            placeholder="app-xxxxxxxxxxxxxxxx"
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-300 mb-2">文生图 Workflow ID</label>
            <input
              type="text"
              value={text2imgWorkflowId}
              onChange={(e) => setText2imgWorkflowId(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-300 mb-2">图生图 Workflow ID</label>
            <input
              type="text"
              value={img2imgWorkflowId}
              onChange={(e) => setImg2imgWorkflowId(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-300 mb-2">局部重绘 Workflow ID</label>
            <input
              type="text"
              value={inpaintWorkflowId}
              onChange={(e) => setInpaintWorkflowId(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-300 mb-2">上传编辑 Workflow ID</label>
            <input
              type="text"
              value={uploadEditWorkflowId}
              onChange={(e) => setUploadEditWorkflowId(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm text-slate-300 mb-2">超时时间（秒）</label>
          <input
            type="number"
            min="5"
            max="300"
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
          />
          <p className="text-xs text-slate-500 mt-1">范围：5 ~ 300 秒</p>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg transition-colors"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
          <button
            onClick={handleTest}
            disabled={testing}
            className="bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg transition-colors border border-slate-600"
          >
            {testing ? '测试中...' : '测试连通性'}
          </button>
        </div>
      </div>
    </div>
  );
}