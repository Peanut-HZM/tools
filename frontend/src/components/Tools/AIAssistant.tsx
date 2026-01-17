import { useNavigate } from 'react-router-dom';

export default function AIAssistant() {
  const navigate = useNavigate();

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
            <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded flex items-center justify-center">
              <i className="fas fa-robot text-white text-sm"></i>
            </div>
            <h1 className="text-lg font-bold">AI助手</h1>
          </div>
        </div>
        
        <a
          href="https://ai-assistant.peanuthzm.com.cn/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-slate-400 hover:text-white transition-colors flex items-center gap-2 text-sm"
        >
          <i className="fas fa-external-link-alt"></i>
          <span className="hidden sm:inline">新窗口打开</span>
        </a>
      </div>

      {/* iframe 嵌入 AI 助手 */}
      <div className="flex-1 overflow-hidden">
        <iframe
          src="https://ai-assistant.peanuthzm.com.cn/"
          className="w-full h-full border-0"
          title="AI助手"
          allow="microphone; camera; clipboard-read; clipboard-write"
        />
      </div>
    </div>
  );
}
