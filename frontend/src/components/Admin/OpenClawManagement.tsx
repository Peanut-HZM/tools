import { useState, useEffect } from 'react';
import {
  getOpenClawConfig,
  updateOpenClawConfig,
  getOpenClawStatus,
  reconnectOpenClaw,
  disconnectOpenClaw,
  testOpenClawConnection,
  type OpenClawConfig,
} from '../../api/openclawApi';

export default function OpenClawManagement() {
  const [config, setConfig] = useState<OpenClawConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 表单状态
  const [gatewayUrl, setGatewayUrl] = useState('');
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [enabled, setEnabled] = useState('true');
  const [authMode, setAuthMode] = useState('token');
  const [showPassword, setShowPassword] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getOpenClawConfig();
      setConfig(data);
      setGatewayUrl(data.gateway_url || '');
      setToken(data.token || ''); // Token 回显
      setUsername(data.username || '');
      setPassword(''); // 密码不回显密文
      setEnabled(data.enabled || 'true');
      setAuthMode(data.auth_mode || 'token');
    } catch (err: any) {
      setError(err.message || '加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaveSuccess(null);
    try {
      const data: any = { enabled, auth_mode: authMode };
      if (gatewayUrl) data.gateway_url = gatewayUrl;
      if (username) data.username = username;
      if (password) data.password = password;
      if (token) data.token = token;

      const result = await updateOpenClawConfig(data);
      if (result.ok === false) {
        setError(result.message || '配置已保存，但重连失败');
      } else {
        setSaveSuccess('配置已保存，连接成功');
      }
      await loadData();
    } catch (err: any) {
      setError(err.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleReconnect = async () => {
    setActionLoading('reconnect');
    setError(null);
    try {
      await reconnectOpenClaw();
      await loadData();
    } catch (err: any) {
      setError(err.message || '重连失败');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDisconnect = async () => {
    setActionLoading('disconnect');
    setError(null);
    try {
      await disconnectOpenClaw();
      await loadData();
    } catch (err: any) {
      setError(err.message || '断开失败');
    } finally {
      setActionLoading(null);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    setError(null);
    try {
      const result = await testOpenClawConnection({
        gateway_url: gatewayUrl || 'ws://127.0.0.1:18081',
        auth_mode: authMode,
        username: authMode === 'token_with_password' ? username : undefined,
        password: authMode === 'token_with_password' ? password : undefined,
        token: token || undefined,
      });
      setTestResult({ ok: result.ok, message: result.message });
    } catch (err: any) {
      setTestResult({ ok: false, message: err.message || '测试失败' });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">OpenClaw 管理</h1>
        <p className="text-slate-400 mt-1">管理 OpenClaw Gateway 连接配置和状态</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {saveSuccess && (
        <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg">
          {saveSuccess}
        </div>
      )}

      {/* 状态卡片 */}
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
        <h2 className="text-lg font-semibold text-white mb-4">连接状态</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-slate-400 text-sm">状态</p>
            <div className="flex items-center gap-2 mt-1">
              <span className={`w-2.5 h-2.5 rounded-full ${config?.connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
              <span className="text-white font-medium">{config?.connected ? '已连接' : '未连接'}</span>
            </div>
          </div>
          <div>
            <p className="text-slate-400 text-sm">启用状态</p>
            <p className="text-white font-medium mt-1">{enabled === 'true' ? '已启用' : '已禁用'}</p>
          </div>
          <div>
            <p className="text-slate-400 text-sm">认证方式</p>
            <p className="text-white font-medium mt-1">{config?.auth_mode === 'token_with_password' ? '双重认证' : 'Token 认证'}</p>
          </div>
          <div>
            <p className="text-slate-400 text-sm">Gateway 地址</p>
            <p className="text-white font-mono text-sm mt-1">{config?.gateway_url || '-'}</p>
          </div>
          <div>
            <p className="text-slate-400 text-sm">用户名</p>
            <p className="text-white font-mono text-sm mt-1">{config?.username || '-'}</p>
          </div>
          <div>
            <p className="text-slate-400 text-sm">Token</p>
            <p className="text-white font-mono text-sm mt-1">{config?.token || '(未设置)'}</p>
          </div>
        </div>
        <div className="flex gap-3 mt-6">
          <button
            onClick={handleReconnect}
            disabled={actionLoading !== null}
            className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors disabled:opacity-50"
          >
            <i className="fas fa-rotate mr-1"></i>
            重新连接
          </button>
          <button
            onClick={handleDisconnect}
            disabled={actionLoading !== null || !config?.connected}
            className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors disabled:opacity-50"
          >
            <i className="fas fa-plug-circle-xmark mr-1"></i>
            断开连接
          </button>
        </div>
      </div>

      {/* 配置表单 */}
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
        <h2 className="text-lg font-semibold text-white mb-4">连接配置</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-slate-300 text-sm mb-1">Gateway URL</label>
            <input
              type="text"
              value={gatewayUrl}
              onChange={(e) => setGatewayUrl(e.target.value)}
              placeholder="ws://127.0.0.1:18081"
              className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>
          <div>
            <label className="block text-slate-300 text-sm mb-1">认证方式</label>
            <select
              value={authMode}
              onChange={(e) => setAuthMode(e.target.value)}
              className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 focus:outline-none focus:border-cyan-500"
            >
              <option value="token">仅 Token 鉴权</option>
              <option value="token_with_password">Token + 用户名密码双重认证</option>
            </select>
          </div>
          {authMode === 'token_with_password' && (
            <>
              {/* 用户名 */}
              <div>
                <label className="block text-slate-300 text-sm mb-1">用户名</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="留空表示不修改"
                  className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>
              {/* 密码 */}
              <div>
                <label className="block text-slate-300 text-sm mb-1">密码</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="留空表示不修改"
                    className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 pr-12 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                  >
                    <i className={`fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                  </button>
                </div>
                <p className="text-slate-500 text-xs mt-1">输入新密码将覆盖当前密码，留空不修改</p>
              </div>
            </>
          )}
          <div>
            <label className="block text-slate-300 text-sm mb-1">Token</label>
            <div className="relative">
              <input
                type={showToken ? 'text' : 'password'}
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="留空表示不修改"
                className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 pr-12 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
              >
                <i className={`fas ${showToken ? 'fa-eye-slash' : 'fa-eye'}`}></i>
              </button>
            </div>
            <p className="text-amber-400/70 text-xs mt-1">💡 保存配置后将自动尝试连接，如果连接失败会在页面顶部显示错误信息。建议先点击"测试连接"验证配置</p>
          </div>
          <div>
            <label className="block text-slate-300 text-sm mb-1">功能开关</label>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setEnabled(enabled === 'true' ? 'false' : 'true')}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  enabled === 'true' ? 'bg-green-500' : 'bg-slate-600'
                }`}
              >
                <span
                  className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                    enabled === 'true' ? 'left-6' : 'left-0.5'
                  }`}
                />
              </button>
              <span className="text-white">{enabled === 'true' ? '已启用' : '已禁用'}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-3 items-start mt-6">
          <button
            onClick={handleSave}
            disabled={saving || testing}
            className="px-6 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-50"
          >
            <i className="fas fa-save mr-1"></i>
            {saving ? '保存中...' : '保存配置'}
          </button>
          <button
            onClick={handleTestConnection}
            disabled={testing || saving}
            className="px-6 py-2.5 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition-all disabled:opacity-50"
          >
            {testing ? (
              <>
                <span className="inline-block animate-spin mr-1">⟳</span>
                测试中...
              </>
            ) : (
              <>
                <i className="fas fa-plug mr-1"></i>
                测试连接
              </>
            )}
          </button>
        </div>
        {testResult && (
          <div className={`mt-3 text-sm ${testResult.ok ? 'text-green-400' : 'text-red-400'}`}>
            <i className={`fas ${testResult.ok ? 'fa-check-circle' : 'fa-times-circle'} mr-1`}></i>
            {testResult.message}
          </div>
        )}
      </div>
    </div>
  );
}
