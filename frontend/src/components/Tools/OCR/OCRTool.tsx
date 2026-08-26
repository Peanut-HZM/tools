import { Clock, Copy, FileImage, FileText, Image as ImageIcon, Loader2, QrCode, Sparkles, Trash2, AlignLeft } from 'lucide-react';
import React, { useState, useEffect, useRef } from 'react';
import { ocrApi, OCRResult, QRCodeResult } from '../../../api/ocrApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/Tabs";

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
          <div className="w-10 h-10 bg-accent-hover rounded-lg flex items-center justify-center">
            <FileImage className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-ink">{t.tools['ocr-tool'].title}</h1>
        </div>

        <div className="flex items-center gap-2">
          <Tabs value={mode} onValueChange={(v) => switchMode(v as Mode)}>
            <TabsList>
              <TabsTrigger value="image">
                <ImageIcon className="w-4 h-4 mr-2" />图片识别
              </TabsTrigger>
              <TabsTrigger value="pdf">
                <FileText className="w-4 h-4 mr-2" />PDF识别
              </TabsTrigger>
              <TabsTrigger value="qrcode">
                <QrCode className="w-4 h-4 mr-2" />二维码
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-[calc(100vh-200px)] min-h-[600px]">
        {/* Input Section */}
        <Card className="p-6 shadow-md flex flex-col">
          <CardHeader className="flex-row justify-between items-center mb-4 p-0 space-y-0">
            <CardTitle className="text-lg">
              {mode === 'image' ? '图片上传' : mode === 'pdf' ? 'PDF上传' : '二维码上传'}
            </CardTitle>
            {(file || preview) && (
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
              ${(file || preview) ? 'border-border bg-canvas' : 'border-border hover:border-indigo-500 hover:bg-surface-2/50 cursor-pointer'}
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
                 <div className="w-16 h-16 bg-surface-1 rounded-full flex items-center justify-center mx-auto mb-4 border border-border">
                   <FileText className="w-8 h-8 text-danger" />
                 </div>
                 <p className="text-lg text-ink font-medium">{file.name}</p>
                 <p className="text-sm text-ink-muted mt-2">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div className="text-center p-6">
                <div className="w-16 h-16 bg-surface-2 rounded-full flex items-center justify-center mx-auto mb-4">
                  <i className={`fas ${mode === 'pdf' ? 'fa-file-pdf' : mode === 'qrcode' ? 'fa-qrcode' : 'fa-cloud-upload-alt'} text-3xl text-accent`}></i>
                </div>
                <p className="text-lg text-ink mb-2">点击或拖拽{mode === 'pdf' ? 'PDF' : '图片'}到这里</p>
                {mode !== 'pdf' && <p className="text-sm text-ink-muted">支持 Ctrl+V 粘贴图片</p>}
              </div>
            )}
          </div>
          
          <div className="mt-6">
            <button
              onClick={handlePredict}
              disabled={(!file && !preview) || loading}
              className={`w-full py-3 rounded-lg font-medium transition-all flex items-center justify-center space-x-2
                ${(!file && !preview) || loading 
                  ? 'bg-surface-2 text-ink-muted cursor-not-allowed' 
                  : 'bg-accent hover:bg-accent-hover text-white shadow-lg shadow-accent/30'
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
                  <Sparkles className="w-4 h-4" />
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
                  className="text-accent hover:text-indigo-300 transition-colors flex items-center"
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
                value={result.text || (result as QRCodeResult).type ? `[类型: ${(result as QRCodeResult).type}]\n${result.text}` : ''}
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
