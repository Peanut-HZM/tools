export default function LearningSharePlatform() {
  return (
    <div className="container mx-auto px-6 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-slate-800 rounded-xl p-8 border border-slate-700">
          <div className="flex items-center mb-6">
            <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center mr-4">
              <i className="fas fa-chalkboard-teacher text-white text-2xl"></i>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">学习分享演示平台</h1>
              <p className="text-slate-400">互动式知识分享与技术演示工具</p>
            </div>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-white mb-4">🎯 功能介绍</h2>
            <ul className="space-y-3 text-slate-300">
              <li className="flex items-start">
                <i className="fas fa-check-circle text-purple-400 mr-3 mt-1"></i>
                <span><strong>互动演示</strong>：创建生动的技术演示，支持代码高亮和实时预览</span>
              </li>
              <li className="flex items-start">
                <i className="fas fa-check-circle text-purple-400 mr-3 mt-1"></i>
                <span><strong>知识分享</strong>：支持图文、视频、代码等多种形式的知识内容</span>
              </li>
              <li className="flex items-start">
                <i className="fas fa-check-circle text-purple-400 mr-3 mt-1"></i>
                <span><strong>协作学习</strong>：多人在线协作，实时讨论和反馈</span>
              </li>
              <li className="flex items-start">
                <i className="fas fa-check-circle text-purple-400 mr-3 mt-1"></i>
                <span><strong>资源管理</strong>：系统化管理学习资料和演示文档</span>
              </li>
            </ul>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-white mb-4">💡 适用场景</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-800 rounded-lg p-4">
                <div className="text-purple-400 font-semibold mb-2">技术分享</div>
                <p className="text-sm text-slate-400">团队内部技术分享和培训</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-4">
                <div className="text-purple-400 font-semibold mb-2">在线教学</div>
                <p className="text-sm text-slate-400">远程教学和互动式课程</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-4">
                <div className="text-purple-400 font-semibold mb-2">项目演示</div>
                <p className="text-sm text-slate-400">项目进度汇报和成果展示</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-4">
                <div className="text-purple-400 font-semibold mb-2">文档演示</div>
                <p className="text-sm text-slate-400">产品文档和技术文档演示</p>
              </div>
            </div>
          </div>

          <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-6">
            <div className="flex items-center mb-3">
              <i className="fas fa-info-circle text-purple-400 mr-2"></i>
              <span className="text-purple-400 font-semibold">开发中</span>
            </div>
            <p className="text-slate-300">
              学习分享演示平台正在开发中，即将上线。请关注我们的更新公告！
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
