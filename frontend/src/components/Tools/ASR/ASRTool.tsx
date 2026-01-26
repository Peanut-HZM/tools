import React, { useState, useRef } from 'react';
import { asrApi, ASRResult } from '../../../api/asrApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';

export default function ASRTool() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ASRResult | null>(null);
  const { success, error } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { t } = useI18n();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      setResult(null);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handlePredict = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const res = await asrApi.predict(file);
      setResult(res);
      success('识别成功');
    } catch (err: any) {
      error(err.message || '识别失败');
    } finally {
      setLoading(false);
    }
  };

  const clearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setFile(null);
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="flex items-center space-x-3 mb-8">
        <div className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center">
          <i className="fas fa-microphone text-white text-xl"></i>
        </div>
        <h1 className="text-2xl font-bold text-slate-100">{t.tools['asr-tool'].title}</h1>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-[calc(100vh-200px)] min-h-[600px]">
        {/* Input Section */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-xl flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-slate-200">音频上传</h2>
            {file && (
              <button 
                onClick={clearFile}
                className="text-slate-400 hover:text-red-400 text-sm transition-colors flex items-center"
              >
                <i className="fas fa-trash-alt mr-1"></i> 清除
              </button>
            )}
          </div>
          
          <div 
            onClick={() => !file && fileInputRef.current?.click()}
            onDrop={onDrop}
            onDragOver={onDragOver}
            className={`flex-1 border-2 border-dashed rounded-xl transition-all relative flex flex-col items-center justify-center overflow-hidden
              ${file ? 'border-slate-700 bg-slate-900' : 'border-slate-600 hover:border-emerald-500 hover:bg-slate-700/50 cursor-pointer'}
            `}
          >
             <input 
                type="file" 
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".mp3,.wav,.m4a,.flac,.ogg"
                className="hidden" 
            />
            {file ? (
              <div className="text-center p-6">
                <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4 border border-slate-700 animate-pulse">
                  <i className="fas fa-music text-3xl text-emerald-500"></i>
                </div>
                <p className="text-lg text-slate-200 font-medium break-all">{file.name}</p>
                <p className="text-sm text-slate-400 mt-2">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div className="text-center p-6">
                <div className="w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                  <i className="fas fa-cloud-upload-alt text-3xl text-emerald-400"></i>
                </div>
                <p className="text-lg text-slate-200 mb-2">点击或拖拽音频文件到这里</p>
                <p className="text-sm text-slate-400">支持 mp3, wav, m4a, flac, ogg 等格式</p>
              </div>
            )}
          </div>
          
          <div className="mt-6">
            <button
              onClick={handlePredict}
              disabled={!file || loading}
              className={`w-full py-3 rounded-lg font-medium transition-all flex items-center justify-center space-x-2
                ${!file || loading 
                  ? 'bg-slate-700 text-slate-400 cursor-not-allowed' 
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                }
              `}
            >
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin"></i>
                  <span>识别中...</span>
                </>
              ) : (
                <>
                  <i className="fas fa-microphone-alt"></i>
                  <span>开始识别</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Result Section */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-xl flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-slate-200">识别结果</h2>
            {result && (
              <div className="flex items-center space-x-4 text-sm text-slate-400">
                <span><i className="fas fa-clock mr-1"></i> {result.processing_time.toFixed(2)}s</span>
                <button 
                  onClick={() => {
                    navigator.clipboard.writeText(result.text);
                    success('已复制到剪贴板');
                  }}
                  className="text-emerald-400 hover:text-emerald-300 transition-colors flex items-center"
                >
                  <i className="fas fa-copy mr-1"></i> 复制
                </button>
              </div>
            )}
          </div>
          
          <div className="flex-1 bg-slate-900 rounded-xl border border-slate-700 p-4 overflow-hidden relative">
            {result ? (
              <textarea 
                className="w-full h-full bg-transparent border-none resize-none focus:ring-0 text-slate-200 font-mono text-sm leading-relaxed outline-none"
                value={result.text}
                readOnly
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-slate-500 flex-col">
                <i className="fas fa-align-left text-4xl mb-4 opacity-30"></i>
                <p>等待识别结果...</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
