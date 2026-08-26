import { CheckCircle, Info, Presentation } from 'lucide-react';
import { Card } from "@/components/ui/Card";

export default function LearningSharePlatform() {
  return (
    <div className="container mx-auto px-6 py-8">
      <div className="max-w-4xl mx-auto">
        <Card className="p-8">
          <div className="flex items-center mb-6">
            <div className="w-14 h-14 bg-gradient-to-br from-accent to-accent-secondary rounded-xl flex items-center justify-center mr-4">
              <Presentation className="w-6 h-6 text-ink-inverse" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-ink">学习分享演示平台</h1>
              <p className="text-ink-muted">互动式知识分享与技术演示工具</p>
            </div>
          </div>

          <Card className="p-6 mb-6">
            <h2 className="text-lg font-semibold text-ink mb-4">🎯 功能介绍</h2>
            <ul className="space-y-3 text-ink-muted">
              <li className="flex items-start">
                <CheckCircle className="w-4 h-4 text-accent-secondary mr-3 mt-1" />
                <span><strong>互动演示</strong>：创建生动的技术演示，支持代码高亮和实时预览</span>
              </li>
              <li className="flex items-start">
                <CheckCircle className="w-4 h-4 text-accent-secondary mr-3 mt-1" />
                <span><strong>知识分享</strong>：支持图文、视频、代码等多种形式的知识内容</span>
              </li>
              <li className="flex items-start">
                <CheckCircle className="w-4 h-4 text-accent-secondary mr-3 mt-1" />
                <span><strong>协作学习</strong>：多人在线协作，实时讨论和反馈</span>
              </li>
              <li className="flex items-start">
                <CheckCircle className="w-4 h-4 text-accent-secondary mr-3 mt-1" />
                <span><strong>资源管理</strong>：系统化管理学习资料和演示文档</span>
              </li>
            </ul>
          </Card>

          <Card className="p-6 mb-6">
            <h2 className="text-lg font-semibold text-ink mb-4">💡 适用场景</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-surface-1 rounded-lg p-4">
                <div className="text-accent-secondary font-semibold mb-2">技术分享</div>
                <p className="text-sm text-ink-muted">团队内部技术分享和培训</p>
              </div>
              <div className="bg-surface-1 rounded-lg p-4">
                <div className="text-accent-secondary font-semibold mb-2">在线教学</div>
                <p className="text-sm text-ink-muted">远程教学和互动式课程</p>
              </div>
              <div className="bg-surface-1 rounded-lg p-4">
                <div className="text-accent-secondary font-semibold mb-2">项目演示</div>
                <p className="text-sm text-ink-muted">项目进度汇报和成果展示</p>
              </div>
              <div className="bg-surface-1 rounded-lg p-4">
                <div className="text-accent-secondary font-semibold mb-2">文档演示</div>
                <p className="text-sm text-ink-muted">产品文档和技术文档演示</p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center mb-3">
              <Info className="w-4 h-4 text-accent-secondary mr-2" />
              <span className="text-accent-secondary font-semibold">开发中</span>
            </div>
            <p className="text-ink-muted">
              学习分享演示平台正在开发中，即将上线。请关注我们的更新公告！
            </p>
          </Card>
        </Card>
      </div>
    </div>
  );
}
