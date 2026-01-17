import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

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
        const response = await fetch('http://localhost:19092/api/tools/key-algorithms');
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
      const response = await fetch('http://localhost:19092/api/tools/generate-key', {
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
    <div className="h-screen bg-slate-900 text-slate-100 flex flex-col overflow-hidden">
      {/* 顶部工具栏 */}
      <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-slate-400 hover:text-white transition-colors flex items-center gap-2"
          >
            <i className="fas fa-arrow-left"></i>
            <span className="hidden sm:inline">返回</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-yellow-500 rounded flex items-center justify-center">
              <i className="fas fa-key text-white text-sm"></i>
            </div>
            <h1 className="text-lg font-bold">密钥生成器</h1>
          </div>
        </div>
      </div>

      {/* 主内容区域 - 左右分栏 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧 - 算法选择 */}
        <div className="w-80 bg-slate-800 border-r border-slate-700 flex flex-col overflow-hidden flex-shrink-0">
          <div className="p-4 border-b border-slate-700 flex-shrink-0">
            <h2 className="font-semibold mb-3">选择算法</h2>
            
            {/* 密钥长度 */}
            {currentAlgorithm && currentAlgorithm.key_sizes.length > 1 && (
              <div className="mb-3">
                <label className="text-xs text-slate-400 mb-1 block">密钥长度</label>
                <select
                  value={selectedKeySize}
                  onChange={(e) => setSelectedKeySize(Number(e.target.value))}
                  className="w-full bg-slate-700 text-white px-3 py-2 rounded border border-slate-600 text-sm"
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
              className="w-full bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white py-2.5 rounded-lg font-medium transition-all disabled:opacity-50"
            >
              {loading ? (
                <><i className="fas fa-spinner fa-spin mr-2"></i>生成中...</>
              ) : (
                <><i className="fas fa-magic mr-2"></i>生成密钥</>
              )}
            </button>
          </div>

          {/* 算法列表 - 可滚动 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* 非对称加密 */}
            <div>
              <h3 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">非对称加密</h3>
              <div className="space-y-1">
                {asymmetricAlgorithms.map(([key, algo]) => (
                  <button
                    key={key}
                    onClick={() => setSelectedAlgorithm(key)}
                    className={`
                      w-full text-left p-2.5 rounded-lg transition-all text-sm
                      ${selectedAlgorithm === key 
                        ? 'bg-blue-500/20 border border-blue-500 text-blue-400' 
                        : 'bg-slate-700/50 border border-transparent hover:bg-slate-700 text-slate-300'}
                    `}
                  >
                    <div className="font-medium">{algo.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{algo.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* 对称加密 */}
            <div>
              <h3 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">对称加密 / 其他</h3>
              <div className="space-y-1">
                {symmetricAlgorithms.map(([key, algo]) => (
                  <button
                    key={key}
                    onClick={() => setSelectedAlgorithm(key)}
                    className={`
                      w-full text-left p-2.5 rounded-lg transition-all text-sm
                      ${selectedAlgorithm === key 
                        ? 'bg-blue-500/20 border border-blue-500 text-blue-400' 
                        : 'bg-slate-700/50 border border-transparent hover:bg-slate-700 text-slate-300'}
                    `}
                  >
                    <div className="font-medium">{algo.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{algo.description}</div>
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
            <div className="bg-red-500/10 border-b border-red-500 text-red-400 px-4 py-2 text-sm flex-shrink-0">
              <i className="fas fa-exclamation-circle mr-2"></i>{error}
            </div>
          )}

          {/* 密钥内容 */}
          <div className="flex-1 overflow-y-auto p-6">
            {!generatedKey ? (
              <div className="h-full flex items-center justify-center text-slate-500">
                <div className="text-center">
                  <i className="fas fa-key text-6xl mb-4 opacity-20"></i>
                  <p>选择算法后点击"生成密钥"</p>
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto space-y-4">
                {/* 标题 */}
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-semibold">{generatedKey.algorithm_name}</h2>
                    <p className="text-sm text-slate-400">
                      {generatedKey.key_size} bits · {generatedKey.type === 'asymmetric' ? '非对称' : '对称'}
                    </p>
                  </div>
                  <button
                    onClick={generateKey}
                    className="text-sm bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded"
                  >
                    <i className="fas fa-redo mr-1"></i>重新生成
                  </button>
                </div>

                {/* 非对称密钥 */}
                {generatedKey.private_key && (
                  <>
                    {/* 私钥 */}
                    <div className="bg-slate-800 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-red-500/10 border-b border-slate-700">
                        <span className="text-sm font-medium text-red-400">
                          <i className="fas fa-lock mr-2"></i>私钥 (Private Key)
                        </span>
                        <div className="flex gap-2">
                          <button
                            onClick={() => copyToClipboard(generatedKey.private_key!, '私钥')}
                            className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
                          >
                            <i className="fas fa-copy mr-1"></i>复制
                          </button>
                          <button
                            onClick={() => downloadKey(generatedKey.private_key!, `${generatedKey.algorithm}_private.pem`)}
                            className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
                          >
                            <i className="fas fa-download mr-1"></i>下载
                          </button>
                        </div>
                      </div>
                      <textarea
                        readOnly
                        value={generatedKey.private_key}
                        className="w-full h-36 bg-slate-900 text-green-400 font-mono text-xs p-3 resize-none focus:outline-none"
                      />
                    </div>

                    {/* 公钥 */}
                    <div className="bg-slate-800 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-blue-500/10 border-b border-slate-700">
                        <span className="text-sm font-medium text-blue-400">
                          <i className="fas fa-unlock mr-2"></i>公钥 (Public Key)
                        </span>
                        <div className="flex gap-2">
                          <button
                            onClick={() => copyToClipboard(generatedKey.public_key!, '公钥')}
                            className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
                          >
                            <i className="fas fa-copy mr-1"></i>复制
                          </button>
                          <button
                            onClick={() => downloadKey(generatedKey.public_key!, `${generatedKey.algorithm}_public.pem`)}
                            className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
                          >
                            <i className="fas fa-download mr-1"></i>下载
                          </button>
                        </div>
                      </div>
                      <textarea
                        readOnly
                        value={generatedKey.public_key}
                        className="w-full h-28 bg-slate-900 text-blue-400 font-mono text-xs p-3 resize-none focus:outline-none"
                      />
                    </div>
                  </>
                )}

                {/* 对称密钥 */}
                {generatedKey.key_hex && (
                  <>
                    <div className="bg-slate-800 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-yellow-500/10 border-b border-slate-700">
                        <span className="text-sm font-medium text-yellow-400">
                          <i className="fas fa-key mr-2"></i>Hex 格式
                        </span>
                        <button
                          onClick={() => copyToClipboard(generatedKey.key_hex!, 'Hex密钥')}
                          className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
                        >
                          <i className="fas fa-copy mr-1"></i>复制
                        </button>
                      </div>
                      <div className="p-3 bg-slate-900">
                        <code className="text-yellow-400 font-mono text-sm break-all">{generatedKey.key_hex}</code>
                      </div>
                    </div>

                    <div className="bg-slate-800 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-cyan-500/10 border-b border-slate-700">
                        <span className="text-sm font-medium text-cyan-400">
                          <i className="fas fa-key mr-2"></i>Base64 格式
                        </span>
                        <button
                          onClick={() => copyToClipboard(generatedKey.key_base64!, 'Base64密钥')}
                          className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
                        >
                          <i className="fas fa-copy mr-1"></i>复制
                        </button>
                      </div>
                      <div className="p-3 bg-slate-900">
                        <code className="text-cyan-400 font-mono text-sm break-all">{generatedKey.key_base64}</code>
                      </div>
                    </div>
                  </>
                )}

                {/* UUID */}
                {generatedKey.uuid && (
                  <div className="bg-slate-800 rounded-lg overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 bg-purple-500/10 border-b border-slate-700">
                      <span className="text-sm font-medium text-purple-400">
                        <i className="fas fa-fingerprint mr-2"></i>UUID
                      </span>
                      <button
                        onClick={() => copyToClipboard(generatedKey.uuid!, 'UUID')}
                        className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
                      >
                        <i className="fas fa-copy mr-1"></i>复制
                      </button>
                    </div>
                    <div className="p-4 bg-slate-900 text-center">
                      <code className="text-purple-400 font-mono text-lg">{generatedKey.uuid}</code>
                    </div>
                  </div>
                )}

                {/* API Key */}
                {generatedKey.api_key && (
                  <div className="bg-slate-800 rounded-lg overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 bg-orange-500/10 border-b border-slate-700">
                      <span className="text-sm font-medium text-orange-400">
                        <i className="fas fa-code mr-2"></i>API Key
                      </span>
                      <button
                        onClick={() => copyToClipboard(generatedKey.api_key!, 'API Key')}
                        className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
                      >
                        <i className="fas fa-copy mr-1"></i>复制
                      </button>
                    </div>
                    <div className="p-3 bg-slate-900">
                      <code className="text-orange-400 font-mono text-sm break-all">{generatedKey.api_key}</code>
                    </div>
                  </div>
                )}

                {/* 安全提示 */}
                <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-xs text-slate-400">
                  <i className="fas fa-exclamation-triangle text-yellow-500 mr-2"></i>
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
