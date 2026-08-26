import { Clock, CloudUpload, Copy, FileMusic, Loader2, Mic, Mic2, Trash2, AlignLeft } from 'lucide-react';
import React, { useState, useRef } from 'react';
import { asrApi, ASRResult } from '../../../api/asrApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";

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
        <div className="w-10 h-10 bg-success rounded-lg flex items-center justify-center">
          <Mic className="w-5 h-5 text-ink-inverse" />
        </div>
        <h1 className="text-2xl font-bold text-ink">{t.tools['asr-tool'].title}</h1>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-[calc(100vh-200px)] min-h-[600px]">
        {/* Input Section */}
        <Card className="p-6 shadow-md flex flex-col">
          <CardHeader className="flex-row justify-between items-center mb-4 p-0 space-y-0">
            <CardTitle className="text-lg">音频上传</CardTitle>
            {file && (
              <button 
                onClick={clearFile}
                className="text-ink-muted hover:text-danger text-sm transition-colors flex items-center"
              >
                <Trash2 className="w-3.5 h-3.5 mr-1" /> 清除
              </button>
            )}
          </CardHeader>

          <CardContent className="flex-1 flex flex-col p-0">
          <div
            onClick={() => !file && fileInputRef.current?.click()}
            onDrop={onDrop}
            onDragOver={onDragOver}
            className={`flex-1 border-2 border-dashed rounded-xl transition-all relative flex flex-col items-center justify-center overflow-hidden
              ${file ? 'border-border bg-canvas' : 'border-border hover:border-success hover:bg-surface-2/50 cursor-pointer'}
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
                <div className="w-16 h-16 bg-surface-1 rounded-full flex items-center justify-center mx-auto mb-4 border border-border animate-pulse">
                  <FileMusic className="w-8 h-8 text-success" />
                </div>
                <p className="text-lg text-ink font-medium break-all">{file.name}</p>
                <p className="text-sm text-ink-muted mt-2">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div className="text-center p-6">
                <div className="w-16 h-16 bg-surface-2 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CloudUpload className="w-8 h-8 text-success" />
                </div>
                <p className="text-lg text-ink mb-2">点击或拖拽音频文件到这里</p>
                <p className="text-sm text-ink-muted">支持 mp3, wav, m4a, flac, ogg 等格式</p>
              </div>
            )}
          </div>
          
          <div className="mt-6">
            <button
              onClick={handlePredict}
              disabled={!file || loading}
              className={`w-full py-3 rounded-lg font-medium transition-all flex items-center justify-center space-x-2
                ${!file || loading 
                  ? 'bg-surface-2 text-ink-muted cursor-not-allowed' 
                  : 'bg-success hover:opacity-90 text-ink-inverse shadow-lg shadow-success/30'
                }
              `}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>识别中...</span>
                </>
              ) : (
                <>
                  <Mic2 className="w-4 h-4" />
                  <span>开始识别</span>
                </>
              )}
            </button>
          </div>
          </CardContent>
        </Card>

        {/* Result Section */}
        <Card className="p-6 shadow-md flex flex-col">
          <CardHeader className="flex-row justify-between items-center mb-4 p-0 space-y-0">
            <CardTitle className="text-lg">识别结果</CardTitle>
            {result && (
              <div className="flex items-center space-x-4 text-sm text-ink-muted">
                <span><Clock className="w-3.5 h-3.5 mr-1" /> {result.processing_time.toFixed(2)}s</span>
                <button 
                  onClick={() => {
                    navigator.clipboard.writeText(result.text);
                    success('已复制到剪贴板');
                  }}
                  className="text-success hover:text-success/80 transition-colors flex items-center"
                >
                  <Copy className="w-3.5 h-3.5 mr-1" /> 复制
                </button>
              </div>
            )}
          </CardHeader>

          <CardContent className="flex-1 p-0">
          <div className="flex-1 bg-canvas rounded-xl border border-border p-4 overflow-hidden relative">
            {result ? (
              <textarea 
                className="w-full h-full bg-transparent border-none resize-none focus:ring-0 text-ink font-mono text-sm leading-relaxed outline-none"
                value={result.text}
                readOnly
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-ink-faint flex-col">
                <AlignLeft className="w-10 h-10 mb-4 opacity-30" />
                <p>等待识别结果...</p>
              </div>
            )}
          </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
