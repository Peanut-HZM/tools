/**
 * K8s 工具 - 连接配置模态框
 *
 * 三种创建方式 Tab 切换：
 * 1. 上传 kubeconfig 文件（react-dropzone）
 * 2. 粘贴 kubeconfig 文本
 * 3. 手动填写连接信息
 *
 * 编辑模式下展示只读连接信息 + 可编辑名称/命名空间 + 敏感字段重新输入
 */
import { useQueryClient } from '@tanstack/react-query';
import React, { useEffect, useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import type { K8sConnection, CreateK8sManualRequest } from './types';
import * as api from '../../../api/k8sToolApi';
import { useI18n } from '../../../i18n';
import { useToast } from '../../../hooks/useToast';
import { useK8sStore } from '../../../stores/k8sStore';

type TabKey = 'upload' | 'paste' | 'manual';
type AuthType = CreateK8sManualRequest['auth_type'];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  /** 编辑时传入已有配置，为 undefined 表示新建 */
  initialData?: K8sConnection;
}

/** kubeconfig 文件上传大小限制（1MB） */
const MAX_FILE_SIZE = 1_048_576;

export const ConnectionModal: React.FC<Props> = ({ isOpen, onClose, initialData }) => {
  const { t } = useI18n();
  const { addToast } = useToast();
  const queryClient = useQueryClient();
  const k8sT = t.tools['k8s-tool'];

  // 当前激活的 Tab
  const [activeTab, setActiveTab] = useState<TabKey>('upload');

  // 上传 Tab 状态
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadNamespaceFilter, setUploadNamespaceFilter] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  // 粘贴 Tab 状态
  const [pasteText, setPasteText] = useState('');
  const [pasteNamespaceFilter, setPasteNamespaceFilter] = useState('');
  const [isPasting, setIsPasting] = useState(false);

  // 手动 Tab 状态
  const [manualName, setManualName] = useState('');
  const [manualServer, setManualServer] = useState('');
  const [manualAuthType, setManualAuthType] = useState<AuthType>('bearer_token');
  const [manualToken, setManualToken] = useState('');
  const [manualClientCert, setManualClientCert] = useState('');
  const [manualClientKey, setManualClientKey] = useState('');
  const [manualUsername, setManualUsername] = useState('');
  const [manualPassword, setManualPassword] = useState('');
  const [manualCaCert, setManualCaCert] = useState('');
  const [manualNamespaceFilter, setManualNamespaceFilter] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // 编辑模式状态
  const [editName, setEditName] = useState('');
  const [editNamespaceFilter, setEditNamespaceFilter] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // 编辑模式敏感字段状态
  const [editToken, setEditToken] = useState('');
  const [editClientCert, setEditClientCert] = useState('');
  const [editClientKey, setEditClientKey] = useState('');
  const [editUsername, setEditUsername] = useState('');
  const [editPassword, setEditPassword] = useState('');
  const [editCaCert, setEditCaCert] = useState('');

  // 测试连接状态
  const [testConfigId, setTestConfigId] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [testMessage, setTestMessage] = useState('');
  const [testStatus, setTestStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const isEditing = !!initialData;

  /** 将逗号分隔的命名空间字符串转为数组 */
  const parseNamespaceFilter = (raw: string): string[] =>
    raw.split(',').map(s => s.trim()).filter(Boolean);

  // 模态框打开时根据 initialData 初始化编辑字段
  useEffect(() => {
    if (!isOpen) return;
    if (initialData) {
      setEditName(initialData.name);
      setEditNamespaceFilter(initialData.namespace_filter.join(', '));
      // 重置敏感字段
      setEditToken('');
      setEditClientCert('');
      setEditClientKey('');
      setEditUsername('');
      setEditPassword('');
      setEditCaCert('');
    }
    // 重置所有创建表单状态
    setActiveTab('upload');
    setUploadFile(null);
    setUploadNamespaceFilter('');
    setPasteText('');
    setPasteNamespaceFilter('');
    setManualName('');
    setManualServer('');
    setManualAuthType('bearer_token');
    setManualToken('');
    setManualClientCert('');
    setManualClientKey('');
    setManualUsername('');
    setManualPassword('');
    setManualCaCert('');
    setManualNamespaceFilter('');
    setTestConfigId(null);
    setIsTesting(false);
    setTestMessage('');
    setTestStatus('idle');
  }, [isOpen, initialData]);

  /** react-dropzone 回调 */
  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length > 0) {
      setUploadFile(accepted[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    // 不限制 accept，允许选择任何文件（包括无后缀和 .kubeconfig）
    // 后端会验证文件内容是否为有效的 kubeconfig YAML
    maxSize: MAX_FILE_SIZE,
    multiple: false,
  });

  /** 上传 kubeconfig 文件 */
  const handleUpload = async () => {
    if (!uploadFile) {
      addToast(k8sT.modal.upload.hint, 'error');
      return;
    }
    setIsUploading(true);
    try {
      await api.uploadKubeconfig(uploadFile, parseNamespaceFilter(uploadNamespaceFilter));
      addToast(k8sT.modal.upload.uploadSuccess, 'success');
      // 立即刷新连接列表
      queryClient.invalidateQueries({ queryKey: ['k8s', 'connections'] });
      onClose();
    } catch (err) {
      addToast(err instanceof Error ? err.message : k8sT.modal.upload.uploadFailed, 'error');
    } finally {
      setIsUploading(false);
    }
  };

  /** 粘贴 kubeconfig 文本 */
  const handlePaste = async () => {
    if (!pasteText.trim()) {
      addToast(k8sT.modal.kubeconfigRequired, 'error');
      return;
    }
    setIsPasting(true);
    try {
      await api.pasteKubeconfig({
        kubeconfig_text: pasteText,
        namespace_filter: parseNamespaceFilter(pasteNamespaceFilter),
      });
      addToast(k8sT.saveSuccess, 'success');
      // 立即刷新连接列表
      queryClient.invalidateQueries({ queryKey: ['k8s', 'connections'] });
      onClose();
    } catch (err) {
      addToast(err instanceof Error ? err.message : k8sT.modal.paste.parseFailed, 'error');
    } finally {
      setIsPasting(false);
    }
  };

  /** 手动创建连接 */
  const handleManualCreate = async () => {
    if (!manualName.trim()) {
      addToast(k8sT.modal.nameRequired, 'error');
      return;
    }
    if (!manualServer.trim()) {
      addToast(k8sT.modal.serverRequired, 'error');
      return;
    }

    const payload: CreateK8sManualRequest = {
      name: manualName.trim(),
      server: manualServer.trim(),
      auth_type: manualAuthType,
      namespace_filter: parseNamespaceFilter(manualNamespaceFilter),
    };

    // 按认证类型填充字段
    if (manualAuthType === 'bearer_token') {
      payload.token = manualToken || undefined;
    } else if (manualAuthType === 'client_cert') {
      payload.client_cert = manualClientCert || undefined;
      payload.client_key = manualClientKey || undefined;
    } else if (manualAuthType === 'basic_auth') {
      payload.username = manualUsername || undefined;
      payload.password = manualPassword || undefined;
    }

    if (manualCaCert.trim()) {
      payload.ca_cert = manualCaCert.trim();
    }

    setIsCreating(true);
    try {
      const result = await api.createK8sManual(payload);
      // 记录新连接 ID 用于测试
      setTestConfigId(result.id);
      addToast(k8sT.saveSuccess, 'success');
      // 立即刷新连接列表
      queryClient.invalidateQueries({ queryKey: ['k8s', 'connections'] });
      onClose();
    } catch (err) {
      addToast(err instanceof Error ? err.message : t.common.error, 'error');
    } finally {
      setIsCreating(false);
    }
  };

  /** 编辑模式下保存 */
  const handleEditSave = async () => {
    if (!initialData || !editName.trim()) return;
    setIsSaving(true);
    try {
      // 先更新基本信息
      const updatedConfig = await api.updateK8sConfig({
        id: initialData.id,
        name: editName.trim(),
        namespace_filter: parseNamespaceFilter(editNamespaceFilter),
      });

      // 如果有敏感字段更新，调用 update-auth API
      const hasAuthUpdates =
        (initialData.auth_type === 'bearer_token' && editToken) ||
        (initialData.auth_type === 'client_cert' && (editClientCert || editClientKey)) ||
        (initialData.auth_type === 'basic_auth' && (editUsername || editPassword)) ||
        editCaCert;

      if (hasAuthUpdates) {
        await api.updateK8sConfigAuth({
          id: initialData.id,
          token: editToken || undefined,
          client_cert: editClientCert || undefined,
          client_key: editClientKey || undefined,
          username: editUsername || undefined,
          password: editPassword || undefined,
          ca_cert: editCaCert || undefined,
        });
      }

      addToast(k8sT.saveSuccess, 'success');

      // 立即刷新连接列表
      queryClient.invalidateQueries({ queryKey: ['k8s', 'connections'] });

      // 如果编辑的是当前活跃连接，更新 store 中的 namespace_filter
      if (updatedConfig.namespace_filter) {
        const { setNamespaces } = useK8sStore.getState();
        setNamespaces(updatedConfig.namespace_filter);
      }

      onClose();
    } catch (err) {
      addToast(err instanceof Error ? err.message : t.common.error, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  /** 测试连接 */
  const handleTestConnection = async (configId: string) => {
    setIsTesting(true);
    setTestMessage('');
    setTestStatus('idle');
    try {
      const result = await api.testK8sConnection(configId);
      setTestStatus(result.reachable ? 'success' : 'error');
      setTestMessage(
        result.reachable
          ? k8sT.connection.testSuccess + (result.server_version ? ` (v${result.server_version})` : '')
          : k8sT.connection.testFailed.replace('{reason}', 'Unreachable')
      );
    } catch (err) {
      setTestStatus('error');
      setTestMessage(err instanceof Error ? err.message : k8sT.connection.testFailed.replace('{reason}', 'Unknown'));
    } finally {
      setIsTesting(false);
    }
  };

  if (!isOpen) return null;

  /** Tab 配置 */
  const tabs: { key: TabKey; label: string }[] = [
    { key: 'upload', label: k8sT.modal.tabs.upload },
    { key: 'paste', label: k8sT.modal.tabs.paste },
    { key: 'manual', label: k8sT.modal.tabs.manual },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-800 rounded-lg shadow-xl w-full max-w-lg border border-slate-700 overflow-hidden">
        {/* 标题栏 */}
        <div className="px-6 pt-5 pb-3 border-b border-slate-700">
          <h2 className="text-xl font-bold text-white">
            {isEditing ? k8sT.editConnection : k8sT.addConnection}
          </h2>
        </div>

        <div className="px-6 py-4 max-h-[70vh] overflow-y-auto">
          {/* 编辑模式：连接信息 + 可编辑字段 + 敏感字段重新输入 */}
          {isEditing ? (
            <div className="space-y-4">
              {/* 只读展示的连接信息 */}
              <div className="bg-slate-900 rounded-md p-3 border border-slate-700">
                <div className="text-xs text-slate-500 mb-2">连接信息</div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <i className="fas fa-server text-xs text-slate-400"></i>
                    <span className="text-sm text-slate-300">{initialData.server}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <i className="fas fa-key text-xs text-slate-400"></i>
                    <span className="text-sm text-slate-300">
                      {k8sT.modal.authTypes[initialData.auth_type]}
                      {initialData.has_auth_data && <i className="fas fa-check-circle ml-1 text-green-400"></i>}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <i className="fas fa-shield-alt text-xs text-slate-400"></i>
                    <span className="text-sm text-slate-300">
                      {initialData.has_ca_cert ? '已配置 CA 证书' : '使用系统 CA'}
                    </span>
                  </div>
                </div>
              </div>

              {/* 可编辑的字段 */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  {k8sT.modal.fields.name}
                </label>
                <input
                  type="text"
                  required
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                  value={editName}
                  onChange={e => setEditName(e.target.value)}
                />
              </div>

              {/* 敏感字段重新输入 */}
              {initialData.auth_type === 'bearer_token' && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    {k8sT.modal.fields.token}
                    <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
                  </label>
                  <input
                    type="password"
                    className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                    placeholder="输入新的 token，留空则保持原值"
                    value={editToken}
                    onChange={e => setEditToken(e.target.value)}
                  />
                </div>
              )}

              {initialData.auth_type === 'client_cert' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.clientCert}
                      <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
                    </label>
                    <textarea
                      rows={3}
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
                      placeholder="输入新的证书，留空则保持原值"
                      value={editClientCert}
                      onChange={e => setEditClientCert(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.clientKey}
                      <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
                    </label>
                    <textarea
                      rows={3}
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
                      placeholder="输入新的私钥，留空则保持原值"
                      value={editClientKey}
                      onChange={e => setEditClientKey(e.target.value)}
                    />
                  </div>
                </>
              )}

              {initialData.auth_type === 'basic_auth' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.username}
                      <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
                    </label>
                    <input
                      type="text"
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                      placeholder="输入新的用户名"
                      value={editUsername}
                      onChange={e => setEditUsername(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.password}
                      <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
                    </label>
                    <input
                      type="password"
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                      placeholder="输入新的密码"
                      value={editPassword}
                      onChange={e => setEditPassword(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {/* CA 证书 */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  {k8sT.modal.fields.caCert}
                  <span className="text-xs text-slate-500 ml-2">（留空表示不修改）</span>
                </label>
                <textarea
                  rows={2}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
                  placeholder="输入新的 CA 证书，留空则保持原值"
                  value={editCaCert}
                  onChange={e => setEditCaCert(e.target.value)}
                />
              </div>

              {/* 命名空间过滤 */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  {k8sT.modal.fields.namespaceFilter}
                </label>
                <input
                  type="text"
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                  placeholder={k8sT.modal.fields.namespaceHint}
                  value={editNamespaceFilter}
                  onChange={e => setEditNamespaceFilter(e.target.value)}
                />
              </div>

              {/* 测试连接 + 保存按钮 */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  disabled={isTesting}
                  onClick={() => handleTestConnection(initialData!.id)}
                  className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-md text-sm font-medium text-slate-200 hover:bg-slate-600 transition-colors disabled:opacity-60"
                >
                  {isTesting ? k8sT.testing : k8sT.testConnection}
                </button>
                {testMessage && (
                  <span className={`text-sm ${testStatus === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                    {testMessage}
                  </span>
                )}
              </div>
            </div>
          ) : (
            /* 新建模式：三 Tab 切换 */
            <>
              {/* Tab 栏 */}
              <div className="flex border-b border-slate-700 mb-4">
                {tabs.map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={[
                      'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
                      activeTab === tab.key
                        ? 'text-blue-400 border-blue-400'
                        : 'text-slate-400 border-transparent hover:text-slate-200',
                    ].join(' ')}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab 内容 */}
              {activeTab === 'upload' && (
                <div className="space-y-4">
                  {/* react-dropzone 拖拽区域 */}
                  <div
                    {...getRootProps()}
                    className={[
                      'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
                      isDragActive
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-slate-600 hover:border-slate-500',
                    ].join(' ')}
                  >
                    <input {...getInputProps()} />
                    <i className="fas fa-cloud-upload-alt text-3xl text-slate-500 mb-3"></i>
                    <p className="text-sm text-slate-400 mb-1">
                      {isDragActive ? '松开以上传' : k8sT.modal.upload.hint}
                    </p>
                    <p className="text-xs text-slate-600">{k8sT.modal.upload.maxSize}</p>
                    {uploadFile && (
                      <p className="mt-2 text-sm text-green-400">
                        <i className="fas fa-check-circle mr-1"></i>
                        {uploadFile.name}
                      </p>
                    )}
                  </div>

                  {/* 命名空间过滤 */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.namespaceFilter}
                    </label>
                    <input
                      type="text"
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                      placeholder={k8sT.modal.fields.namespaceHint}
                      value={uploadNamespaceFilter}
                      onChange={e => setUploadNamespaceFilter(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {activeTab === 'paste' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      kubeconfig YAML
                    </label>
                    <textarea
                      rows={8}
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
                      placeholder={k8sT.modal.paste.placeholder}
                      value={pasteText}
                      onChange={e => setPasteText(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.namespaceFilter}
                    </label>
                    <input
                      type="text"
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                      placeholder={k8sT.modal.fields.namespaceHint}
                      value={pasteNamespaceFilter}
                      onChange={e => setPasteNamespaceFilter(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {activeTab === 'manual' && (
                <div className="space-y-4">
                  {/* 连接名称 */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.name}
                    </label>
                    <input
                      type="text"
                      required
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                      value={manualName}
                      onChange={e => setManualName(e.target.value)}
                    />
                  </div>

                  {/* 服务器地址 */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.server}
                    </label>
                    <input
                      type="url"
                      required
                      placeholder="https://k8s.example.com:6443"
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                      value={manualServer}
                      onChange={e => setManualServer(e.target.value)}
                    />
                  </div>

                  {/* 认证方式 */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.authType}
                    </label>
                    <select
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                      value={manualAuthType}
                      onChange={e => setManualAuthType(e.target.value as AuthType)}
                    >
                      <option value="bearer_token">{k8sT.modal.authTypes.bearer_token}</option>
                      <option value="client_cert">{k8sT.modal.authTypes.client_cert}</option>
                      <option value="basic_auth">{k8sT.modal.authTypes.basic_auth}</option>
                    </select>
                  </div>

                  {/* 按认证类型显示对应字段 */}
                  {manualAuthType === 'bearer_token' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1">
                        {k8sT.modal.fields.token}
                      </label>
                      <input
                        type="password"
                        className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                        value={manualToken}
                        onChange={e => setManualToken(e.target.value)}
                      />
                    </div>
                  )}

                  {manualAuthType === 'client_cert' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                          {k8sT.modal.fields.clientCert}
                        </label>
                        <textarea
                          rows={3}
                          className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
                          placeholder="-----BEGIN CERTIFICATE-----"
                          value={manualClientCert}
                          onChange={e => setManualClientCert(e.target.value)}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                          {k8sT.modal.fields.clientKey}
                        </label>
                        <textarea
                          rows={3}
                          className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
                          placeholder="-----BEGIN RSA PRIVATE KEY-----"
                          value={manualClientKey}
                          onChange={e => setManualClientKey(e.target.value)}
                        />
                      </div>
                    </>
                  )}

                  {manualAuthType === 'basic_auth' && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                          {k8sT.modal.fields.username}
                        </label>
                        <input
                          type="text"
                          className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                          value={manualUsername}
                          onChange={e => setManualUsername(e.target.value)}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                          {k8sT.modal.fields.password}
                        </label>
                        <input
                          type="password"
                          className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                          value={manualPassword}
                          onChange={e => setManualPassword(e.target.value)}
                        />
                      </div>
                    </div>
                  )}

                  {/* CA 证书（可选，所有认证类型共用） */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.caCert}
                    </label>
                    <textarea
                      rows={2}
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
                      placeholder="-----BEGIN CERTIFICATE-----"
                      value={manualCaCert}
                      onChange={e => setManualCaCert(e.target.value)}
                    />
                  </div>

                  {/* 命名空间过滤 */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      {k8sT.modal.fields.namespaceFilter}
                    </label>
                    <input
                      type="text"
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                      placeholder={k8sT.modal.fields.namespaceHint}
                      value={manualNamespaceFilter}
                      onChange={e => setManualNamespaceFilter(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* 底部按钮区 */}
        <div className="px-6 py-4 border-t border-slate-700 flex justify-between items-center">
          {/* 左侧：测试结果显示（编辑模式下） */}
          <div className="text-sm flex-1">
            {!isEditing && testMessage && (
              <span className={testStatus === 'success' ? 'text-green-400' : 'text-red-400'}>
                {testMessage}
              </span>
            )}
          </div>

          {/* 右侧：操作按钮 */}
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-md text-sm font-medium text-slate-300 hover:bg-slate-600 transition-colors"
            >
              {t.common.cancel}
            </button>

            {isEditing ? (
              <button
                type="button"
                onClick={handleEditSave}
                disabled={isSaving}
                className="px-4 py-2 bg-blue-600 border border-transparent rounded-md text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-60"
              >
                {isSaving ? t.common.loading : t.common.save}
              </button>
            ) : (
              <button
                type="button"
                disabled={isUploading || isPasting || isCreating}
                onClick={() => {
                  if (activeTab === 'upload') handleUpload();
                  else if (activeTab === 'paste') handlePaste();
                  else handleManualCreate();
                }}
                className="px-4 py-2 bg-blue-600 border border-transparent rounded-md text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-60"
              >
                {(isUploading || isPasting || isCreating) ? t.common.loading : t.common.save}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
