import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { convertDocument, getHistory, deleteHistory as deleteHistoryApi } from '../../api/converterApi';
import { getAuthToken } from '../../api/authApi';
import { useFileStore } from '../../stores/fileStore';
import Preview from '../MarkdownEditor/Preview/Preview';
import { useI18n } from '../../i18n';

interface HistoryItem {
  id: string;
  fileName: string;
  fileSize: number;
  content: string;
  timestamp: number;
}

export default function MarkItDownConverter() {
  const navigate = useNavigate();
  const { t } = useI18n();
  const [file, setFile] = useState<File | null>(null);
  const [markdownContent, setMarkdownContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      // Load from backend if logged in
      getHistory()
        .then(items => {
          const mappedItems: HistoryItem[] = items.map(item => ({
            id: item.id,
            fileName: item.file_name,
            fileSize: item.file_size,
            content: item.content,
            timestamp: item.created_at
          }));
          setHistory(mappedItems);
        })
        .catch(e => {
          console.error('Failed to load history from backend', e);
          // Fallback to local storage if backend fails? 
          // Maybe better to show error or empty. 
          // For now, let's keep it simple and just log error.
        });
    } else {
      // Load from local storage if not logged in
      const saved = localStorage.getItem('markdown_converter_history');
      if (saved) {
        try {
          setHistory(JSON.parse(saved));
        } catch (e) {
          console.error('Failed to parse history', e);
        }
      }
    }
  }, []);

  const addToHistory = (fileName: string, fileSize: number, content: string) => {
    const newItem: HistoryItem = {
      id: Date.now().toString(),
      fileName,
      fileSize,
      content,
      timestamp: Date.now(),
    };
    const newHistory = [newItem, ...history].slice(0, 50);
    setHistory(newHistory);
    localStorage.setItem('markdown_converter_history', JSON.stringify(newHistory));
  };

  const loadHistoryItem = (item: HistoryItem) => {
    setMarkdownContent(item.content);
    setFile(null); // Clear current file input as we are viewing history
    setError(null);
  };

  const handleDeleteHistory = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    
    if (getAuthToken()) {
      try {
        await deleteHistoryApi(id);
        setHistory(prev => prev.filter(item => item.id !== id));
      } catch (e) {
        console.error('Failed to delete history item', e);
        alert('Failed to delete history item');
      }
    } else {
      const newHistory = history.filter(item => item.id !== id);
      setHistory(newHistory);
      localStorage.setItem('markdown_converter_history', JSON.stringify(newHistory));
    }
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
      setMarkdownContent('');
    }
  }, []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setMarkdownContent('');
    }
  }, []);

  const handleConvert = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      const response = await convertDocument(file);
      setMarkdownContent(response.content);
      
      if (getAuthToken() && response.history_item) {
        const h = response.history_item;
        const newItem: HistoryItem = {
             id: h.id,
             fileName: h.file_name,
             fileSize: h.file_size,
             content: h.content,
             timestamp: h.created_at
        };
        setHistory(prev => [newItem, ...prev]);
      } else {
        addToHistory(file.name, file.size, response.content);
      }
    } catch (e) {
      console.error('Conversion error:', e);
      let errorMessage = t.converter.conversionFailed;
      if (e instanceof Error) {
        errorMessage = e.message;
      } else if (typeof e === 'string') {
        errorMessage = e;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(markdownContent);
    alert(t.converter.copySuccess);
  };

  const handleOpenInEditor = async () => {
    // Ideally we should save this to a temp file or pass it via state
    // For now, let's try to pass it via state location
    // Note: The MarkdownEditorTool component needs to handle location state
    // But since MarkdownEditorTool uses complex state management, maybe we can just copy it
    // and guide user to paste.
    // Better yet, let's create a new file via API if we can, but that requires a filename.
    
    // Simple approach: Copy to clipboard and navigate
    await navigator.clipboard.writeText(markdownContent);
    const confirm = window.confirm(t.converter.openEditorConfirm);
    if (confirm) {
      navigate('/tools/markdown-editor');
    }
  };

  return (
    <div className="w-full flex-1 flex flex-col p-4 text-slate-300">
      <div className="flex items-center justify-between mb-4 px-2">
        <button 
          onClick={() => navigate('/')}
          className="flex items-center text-slate-400 hover:text-white transition-colors"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          {t.converter.back}
        </button>
        <h1 className="text-2xl font-bold text-white">{t.converter.title}</h1>
        <div className="w-24"></div> {/* Spacer */}
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">
        {/* Left Column: Upload & History */}
        <div className="lg:col-span-3 flex flex-col gap-4 h-full min-h-0">
          <div 
            className={`shrink-0 h-64 border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-6 transition-all duration-300 ${
              dragActive 
                ? 'border-cyan-500 bg-cyan-500/10 scale-[1.02]' 
                : 'border-slate-700 bg-slate-800/50 hover:border-cyan-500/50 hover:bg-slate-800'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input 
              type="file" 
              className="hidden" 
              id="file-upload"
              onChange={handleChange}
              accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.html,.txt"
            />
            
            {file ? (
              <div className="text-center w-full">
                <div className="w-12 h-12 bg-cyan-500/20 rounded-full flex items-center justify-center mx-auto mb-3 text-cyan-500">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <p className="text-base font-medium text-white mb-1 truncate px-2">{file.name}</p>
                <p className="text-xs text-slate-400 mb-4">{(file.size / 1024).toFixed(2)} KB</p>
                <button 
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="text-red-400 hover:text-red-300 text-xs underline"
                >
                  {t.converter.remove}
                </button>
              </div>
            ) : (
              <div className="text-center">
                <div className="w-12 h-12 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-3 text-slate-400">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="text-base font-medium text-white mb-1">{t.converter.dragDrop}</p>
                <p className="text-xs text-slate-400 mb-4 px-4">{t.converter.supports}</p>
                <label 
                  htmlFor="file-upload"
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg cursor-pointer transition-colors inline-block text-sm"
                >
                  {t.converter.browse}
                </label>
              </div>
            )}
          </div>

          <button 
            onClick={handleConvert}
            disabled={!file || loading}
            className={`shrink-0 w-full py-3 rounded-xl font-bold text-base transition-all ${
              !file || loading
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg hover:shadow-cyan-500/25'
            }`}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                {t.converter.converting}
              </span>
            ) : (
              t.converter.convert
            )}
          </button>

          {error && (
            <div className="shrink-0 p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-xs break-all">
              {error}
            </div>
          )}

          <div className="flex-1 bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden flex flex-col min-h-0">
            <div className="p-3 border-b border-slate-700/50 bg-slate-800/80 backdrop-blur-sm">
              <h4 className="text-slate-300 font-medium text-sm flex items-center gap-2">
                <svg className="w-4 h-4 text-cyan-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                转换历史
              </h4>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
              {history.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs p-4 text-center">
                  <p>暂无转换记录</p>
                </div>
              ) : (
                history.map(item => (
                  <div 
                    key={item.id}
                    onClick={() => loadHistoryItem(item)}
                    className="group p-3 rounded-lg bg-slate-800/30 hover:bg-slate-700/50 border border-transparent hover:border-slate-600 transition-all cursor-pointer relative"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-200 font-medium truncate mb-1">{item.fileName}</p>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <span>{(item.fileSize / 1024).toFixed(1)} KB</span>
                          <span>•</span>
                          <span>{formatTime(item.timestamp)}</span>
                        </div>
                      </div>
                      <button
                        onClick={(e) => handleDeleteHistory(e, item.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 text-slate-500 hover:text-red-400 rounded transition-all"
                        title="删除记录"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Result & Preview */}
        <div className="lg:col-span-9 bg-slate-800/50 border border-slate-700 rounded-xl flex flex-col overflow-hidden h-full">
          <div className="p-3 border-b border-slate-700 flex items-center justify-between bg-slate-800">
            <h3 className="font-semibold text-slate-200 text-sm">{t.converter.result}</h3>
            <div className="flex gap-2">
              <button 
                onClick={handleCopyToClipboard}
                disabled={!markdownContent}
                className="px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-white rounded-md disabled:opacity-50 transition-colors"
              >
                {t.converter.copy}
              </button>
              <button 
                onClick={handleOpenInEditor}
                disabled={!markdownContent}
                className="px-3 py-1.5 text-xs bg-cyan-600 hover:bg-cyan-500 text-white rounded-md disabled:opacity-50 transition-colors"
              >
                {t.converter.openInEditor}
              </button>
            </div>
          </div>
          
          <div className="flex-1 overflow-auto bg-[#0d0d14] relative">
            {markdownContent ? (
              <div className="h-full">
                 <Preview content={markdownContent} theme="dark" />
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 p-8">
                <svg className="w-16 h-16 mb-4 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>Converted content will appear here</p>
                <p className="text-sm mt-2 opacity-50">Select a history item or upload a new file</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
