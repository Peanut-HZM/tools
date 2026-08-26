import { AlertCircle, AlertTriangle, ArrowLeft, Code, Copy, Download, Fingerprint, Key, Loader2, Lock, RefreshCw, Sparkles, Type, Unlock } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../../config/api';
import { Button } from "@/components/ui/Button";

interface Algorithm {
  name: string;
  description: string;
  key_sizes: number[];
  default_size: number;
  type: 'symmetric' | 'asymmetric';
}

interface GeneratedKey {
  algorithm: string;
  algorithm_name: string;
  key_size: number;
  type: string;
  private_key?: string;
  public_key?: string;
  key_hex?: string;
  key_base64?: string;
  uuid?: string;
  uuid_hex?: string;
  api_key?: string;
  api_key_hex?: string;
  base64_string?: string;
}

export default function KeyGenerator() {
  const navigate = useNavigate();
  const [algorithms, setAlgorithms] = useState<Record<string, Algorithm>>({});
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<string>('rsa');
  const [selectedKeySize, setSelectedKeySize] = useState<number>(2048);
  const [generatedKey, setGeneratedKey] = useState<GeneratedKey | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAlgorithms = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/tools/key-algorithms`);
        if (response.ok) {
          const data = await response.json();
          setAlgorithms(data.algorithms);
        }
      } catch (err) {
        console.error('获取算法列表失败:', err);
      }
    };
    fetchAlgorithms();
  }, []);

  useEffect(() => {
    if (algorithms[selectedAlgorithm]) {
      setSelectedKeySize(algorithms[selectedAlgorithm].default_size);
    }
  }, [selectedAlgorithm, algorithms]);

  const generateKey = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/tools/generate-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          algorithm: selectedAlgorithm,
          key_size: selectedKeySize,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '生成密钥失败');
      }

      const data = await response.json();
      setGeneratedKey(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成密钥失败');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text).then(() => {
      alert(`✅ ${label} 已复制！`);
    }).catch(() => {
      alert('❌ 复制失败');
    });
  };

  const downloadKey = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const currentAlgorithm = algorithms[selectedAlgorithm];
  const asymmetricAlgorithms = Object.entries(algorithms).filter(([_, algo]) => algo.type === 'asymmetric');
  const symmetricAlgorithms = Object.entries(algorithms).filter(([_, algo]) => algo.type === 'symmetric');

  return (
    <div className="flex-1 text-ink flex flex-col overflow-hidden">
      {/* 顶部工具栏 */}
      <div className="bg-surface-1 border-b border-border px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">返回</span>
          </Button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-yellow-500 rounded flex items-center justify-center">
              <Key className="w-4 h-4 text-ink-inverse" />
            </div>
            <h1 className="text-lg font-bold">密钥生成器</h1>
          </div>
        </div>
      </div>

      {/* 主内容区域 - 左右分栏 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧 - 算法选择 */}
        <div className="w-80 bg-surface-1 border-r border-border flex flex-col overflow-hidden flex-shrink-0">
          <div className="p-4 border-b border-border flex-shrink-0">
            <h2 className="font-semibold mb-3">选择算法</h2>

            {/* 密钥长度 */}
            {currentAlgorithm && currentAlgorithm.key_sizes.length > 1 && (
              <div className="mb-3">
                <label className="text-xs text-ink-muted mb-1 block">密钥长度</label>
                <select
                  value={selectedKeySize}
                  onChange={(e) => setSelectedKeySize(Number(e.target.value))}
                  className="w-full bg-surface-2 text-ink-inverse px-3 py-2 rounded border border-border text-sm"
                >
                  {currentAlgorithm.key_sizes.map((size) => (
                    <option key={size} value={size}>{size} bits</option>
                  ))}
                </select>
              </div>
            )}

            {/* 生成按钮 */}
            <button
              onClick={generateKey}
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-ink-inverse py-2.5 rounded-lg font-medium transition-all disabled:opacity-50"
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />生成中...</>
              ) : (
                <><Sparkles className="w-4 h-4 mr-2" />生成密钥</>
              )}
            </button>
          </div>

          {/* 算法列表 - 可滚动 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* 非对称加密 */}
            <div>
              <h3 className="text-xs font-medium text-ink-muted mb-2 uppercase tracking-wider">非对称加密</h3>
              <div className="space-y-1">
                {asymmetricAlgorithms.map(([key, algo]) => (
                  <button
                    key={key}
                    onClick={() => setSelectedAlgorithm(key)}
                    className={`
                      w-full text-left p-2.5 rounded-lg transition-all text-sm
                      ${selectedAlgorithm === key
                        ? 'bg-accent-info/20 border border-accent-info text-accent-info'
                        : 'bg-surface-2/50 border border-transparent hover:bg-surface-2 text-ink-muted'}
                    `}
                  >
                    <div className="font-medium">{algo.name}</div>
                    <div className="text-xs text-ink-faint mt-0.5">{algo.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* 对称加密 */}
            <div>
              <h3 className="text-xs font-medium text-ink-muted mb-2 uppercase tracking-wider">对称加密 / 其他</h3>
              <div className="space-y-1">
                {symmetricAlgorithms.map(([key, algo]) => (
                  <button
                    key={key}
                    onClick={() => setSelectedAlgorithm(key)}
                    className={`
                      w-full text-left p-2.5 rounded-lg transition-all text-sm
                      ${selectedAlgorithm === key
                        ? 'bg-accent-info/20 border border-accent-info text-accent-info'
                        : 'bg-surface-2/50 border border-transparent hover:bg-surface-2 text-ink-muted'}
                    `}
                  >
                    <div className="font-medium">{algo.name}</div>
                    <div className="text-xs text-ink-faint mt-0.5">{algo.description}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 右侧 - 密钥展示 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* 错误提示 */}
          {error && (
            <div className="bg-danger/10 border-b border-danger text-danger px-4 py-2 text-sm flex-shrink-0">
              <AlertCircle className="w-4 h-4 mr-2" />{error}
            </div>
          )}

          {/* 密钥内容 */}
          <div className="flex-1 overflow-y-auto p-6">
            {!generatedKey ? (
              <div className="h-full flex items-center justify-center text-ink-faint">
                <div className="text-center">
                  <Key className="w-16 h-16 mb-4 opacity-20" />
                  <p>选择算法后点击"生成密钥"</p>
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto space-y-4">
                {/* 标题 */}
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-semibold">{generatedKey.algorithm_name}</h2>
                    <p className="text-sm text-ink-muted">
                      {generatedKey.key_size} bits · {generatedKey.type === 'asymmetric' ? '非对称' : '对称'}
                    </p>
                  </div>
                  <Button
                    variant="secondary"
                    onClick={generateKey}
                    size="sm"
                  >
                    <RefreshCw className="w-3.5 h-3.5 mr-1" />重新生成
                  </Button>
                </div>

                {/* 非对称密钥 */}
                {generatedKey.private_key && (
                  <>
                    {/* 私钥 */}
                    <div className="bg-surface-1 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-danger/10 border-b border-border">
                        <span className="text-sm font-medium text-danger">
                          <Lock className="w-4 h-4 mr-2" />私钥 (Private Key)
                        </span>
                        <div className="flex gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => copyToClipboard(generatedKey.private_key!, '私钥')}
                          >
                            <Copy className="w-3.5 h-3.5 mr-1" />复制
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => downloadKey(generatedKey.private_key!, `${generatedKey.algorithm}_private.pem`)}
                          >
                            <Download className="w-3.5 h-3.5 mr-1" />下载
                          </Button>
                        </div>
                      </div>
                      <textarea
                        readOnly
                        value={generatedKey.private_key}
                        className="w-full h-36 bg-canvas text-success font-mono text-xs p-3 resize-none focus:outline-none"
                      />
                    </div>

                    {/* 公钥 */}
                    <div className="bg-surface-1 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-accent-info/10 border-b border-border">
                        <span className="text-sm font-medium text-accent-info">
                          <Unlock className="w-4 h-4 mr-2" />公钥 (Public Key)
                        </span>
                        <div className="flex gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => copyToClipboard(generatedKey.public_key!, '公钥')}
                          >
                            <Copy className="w-3.5 h-3.5 mr-1" />复制
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => downloadKey(generatedKey.public_key!, `${generatedKey.algorithm}_public.pem`)}
                          >
                            <Download className="w-3.5 h-3.5 mr-1" />下载
                          </Button>
                        </div>
                      </div>
                      <textarea
                        readOnly
                        value={generatedKey.public_key}
                        className="w-full h-28 bg-canvas text-accent-info font-mono text-xs p-3 resize-none focus:outline-none"
                      />
                    </div>
                  </>
                )}

                {/* 对称密钥 */}
                {generatedKey.key_hex && (
                  <>
                    <div className="bg-surface-1 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-accent-warning/10 border-b border-border">
                        <span className="text-sm font-medium text-accent-warning">
                          <Key className="w-4 h-4 mr-2" />Hex 格式
                        </span>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => copyToClipboard(generatedKey.key_hex!, 'Hex密钥')}
                        >
                          <Copy className="w-3.5 h-3.5 mr-1" />复制
                        </Button>
                      </div>
                      <div className="p-3 bg-canvas">
                        <code className="text-accent-warning font-mono text-sm break-all">{generatedKey.key_hex}</code>
                      </div>
                    </div>

                    <div className="bg-surface-1 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-accent/10 border-b border-border">
                        <span className="text-sm font-medium text-accent">
                          <Key className="w-4 h-4 mr-2" />Base64 格式
                        </span>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => copyToClipboard(generatedKey.key_base64!, 'Base64密钥')}
                        >
                          <Copy className="w-3.5 h-3.5 mr-1" />复制
                        </Button>
                      </div>
                      <div className="p-3 bg-canvas">
                        <code className="text-accent font-mono text-sm break-all">{generatedKey.key_base64}</code>
                      </div>
                    </div>
                  </>
                )}

                {/* UUID */}
                {generatedKey.uuid && (
                  <div className="bg-surface-1 rounded-lg overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 bg-accent-secondary/10 border-b border-border">
                      <span className="text-sm font-medium text-accent-secondary">
                        <Fingerprint className="w-4 h-4 mr-2" />UUID
                      </span>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => copyToClipboard(generatedKey.uuid!, 'UUID')}
                      >
                        <Copy className="w-3.5 h-3.5 mr-1" />复制
                      </Button>
                    </div>
                    <div className="p-4 bg-canvas text-center">
                      <code className="text-accent-secondary font-mono text-lg">{generatedKey.uuid}</code>
                    </div>
                  </div>
                )}

                {/* API Key */}
                {generatedKey.api_key && (
                  <div className="bg-surface-1 rounded-lg overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 bg-orange-500/10 border-b border-border">
                      <span className="text-sm font-medium text-orange-400">
                        <Code className="w-4 h-4 mr-2" />API Key
                      </span>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => copyToClipboard(generatedKey.api_key!, 'API Key')}
                      >
                        <Copy className="w-3.5 h-3.5 mr-1" />复制
                      </Button>
                    </div>
                    <div className="p-3 bg-canvas">
                      <code className="text-orange-400 font-mono text-sm break-all">{generatedKey.api_key}</code>
                    </div>
                  </div>
                )}

                {/* Base64 字符串 */}
                {generatedKey.base64_string && (
                  <div className="bg-surface-1 rounded-lg overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 bg-pink-500/10 border-b border-border">
                      <span className="text-sm font-medium text-pink-400">
                        <Type className="w-4 h-4 mr-2" />Base64 字符串
                      </span>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => copyToClipboard(generatedKey.base64_string!, 'Base64 字符串')}
                      >
                        <Copy className="w-3.5 h-3.5 mr-1" />复制
                      </Button>
                    </div>
                    <div className="p-3 bg-canvas">
                      <code className="text-pink-400 font-mono text-sm break-all">{generatedKey.base64_string}</code>
                    </div>
                  </div>
                )}

                {/* 安全提示 */}
                <div className="p-3 bg-accent-warning/10 border border-accent-warning/30 rounded-lg text-xs text-ink-muted">
                  <AlertTriangle className="w-4 h-4 text-yellow-500 mr-2" />
                  私钥请妥善保管，切勿泄露。密钥仅在本地生成，不会上传到服务器。
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}