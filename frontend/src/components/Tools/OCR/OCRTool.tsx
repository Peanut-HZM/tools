import React, { useState, useEffect, useRef } from 'react';
import { ocrApi, OCRResult, QRCodeResult } from '../../../api/ocrApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';

type Mode = 'image' | 'pdf' | 'qrcode';

export default function OCRTool() {
  const [mode, setMode] = useState<Mode>('image');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OCRResult | QRCodeResult | null>(null);
  const { success, error } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { t } = useI18n();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  const processFile = (selectedFile: File) => {
    if (mode === 'pdf' && selectedFile.type !== 'application/pdf') {
      error('请上传 PDF 文件');
      return;
    }
    if ((mode === 'image' || mode === 'qrcode') && !selectedFile.type.startsWith('image/')) {
      error('请上传图片文件');
      return;
    }

    setFile(selectedFile);
    
    if (selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview(null); // PDF暂不支持预览
    }
    
    setResult(null);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      processFile(droppedFile);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handlePaste = (e: ClipboardEvent) => {
    if (mode === 'pdf') return; // PDF模式不支持粘贴
    
    const items = e.clipboardData?.items;
    if (items) {
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
          const blob = items[i].getAsFile();
          if (blob) {
            processFile(blob);
          }
        }
      }
    }
  };

  useEffect(() => {
    document.addEventListener('paste', handlePaste as any);
    return () => {
      document.removeEventListener('paste', handlePaste as any);
    };
  }, [mode]);

  const handlePredict = async () => {
    if (!file && !preview) return;
    setLoading(true);
    try {
      let res;
      if (mode === 'image' && preview) {
        res = await ocrApi.predict(preview);
      } else if (mode === 'pdf' && file) {
        res = await ocrApi.predictPdf(file);
      } else if (mode === 'qrcode' && preview) {
        res = await ocrApi.scanQrcode(preview);
      }
      
      if (res) {
        setResult(res);
        success('识别成功');
      }
    } catch (err: any) {
      error(err.message || '识别失败');
    } finally {
      setLoading(false);
    }
  };

  const clearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setFile(null);
    setPreview(null);
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const switchMode = (newMode: Mode) => {
    setMode(newMode);
    clearFile({ stopPropagation: () => {} } as React.MouseEvent);
  };

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-indigo-500 rounded-lg flex items-center justify-center">
            <i className="fas fa-file-image text-white text-xl"></i>
          </div>
          <h1 className="text-2xl font-bold text-slate-100">{t.tools['ocr-tool'].title}</h1>
        </div>

        <div className="flex bg-slate-800 rounded-lg p-1 border border-slate-700">
          <button
            onClick={() => switchMode('image')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              mode === 'image' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <i className="fas fa-image mr-2"></i>图片识别
          </button>
          <button
            onClick={() => switchMode('pdf')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              mode === 'pdf' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <i className="fas fa-file-pdf mr-2"></i>PDF识别
          </button>
          <button
            onClick={() => switchMode('qrcode')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              mode === 'qrcode' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <i className="fas fa-qrcode mr-2"></i>二维码
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-[calc(100vh-200px)] min-h-[600px]">
        {/* Input Section */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-xl flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-slate-200">
              {mode === 'image' ? '图片上传' : mode === 'pdf' ? 'PDF上传' : '二维码上传'}
            </h2>
            {(file || preview) && (
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
              ${(file || preview) ? 'border-slate-700 bg-slate-900' : 'border-slate-600 hover:border-indigo-500 hover:bg-slate-700/50 cursor-pointer'}
            `}
          >
            <input 
                type="file" 
                ref={fileInputRef}
                onChange={handleFileChange}
                accept={mode === 'pdf' ? '.pdf' : 'image/*'}
                className="hidden" 
            />
            {preview ? (
              <div className="relative w-full h-full flex items-center justify-center p-4">
                <img src={preview} alt="Preview" className="max-h-full max-w-full object-contain rounded-lg shadow-lg" />
              </div>
            ) : file && mode === 'pdf' ? (
              <div className="text-center p-6">
                 <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4 border border-slate-700">
                   <i className="fas fa-file-pdf text-3xl text-red-500"></i>
                 </div>
                 <p className="text-lg text-slate-200 font-medium">{file.name}</p>
                 <p className="text-sm text-slate-400 mt-2">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div className="text-center p-6">
                <div className="w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                  <i className={`fas ${mode === 'pdf' ? 'fa-file-pdf' : mode === 'qrcode' ? 'fa-qrcode' : 'fa-cloud-upload-alt'} text-3xl text-indigo-400`}></i>
                </div>
                <p className="text-lg text-slate-200 mb-2">点击或拖拽{mode === 'pdf' ? 'PDF' : '图片'}到这里</p>
                {mode !== 'pdf' && <p className="text-sm text-slate-400">支持 Ctrl+V 粘贴图片</p>}
              </div>
            )}
          </div>
          
          <div className="mt-6">
            <button
              onClick={handlePredict}
              disabled={(!file && !preview) || loading}
              className={`w-full py-3 rounded-lg font-medium transition-all flex items-center justify-center space-x-2
                ${(!file && !preview) || loading 
                  ? 'bg-slate-700 text-slate-400 cursor-not-allowed' 
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/30'
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
                  <i className="fas fa-magic"></i>
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
                  className="text-indigo-400 hover:text-indigo-300 transition-colors flex items-center"
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
                value={result.text || (result as QRCodeResult).type ? `[类型: ${(result as QRCodeResult).type}]\n${result.text}` : ''}
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
