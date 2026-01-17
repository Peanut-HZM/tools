export default function Footer() {
  const toolCategories = ['文本工具', '转换工具', '计算工具', '设计工具'];
  const supportLinks = ['使用帮助', '反馈建议', 'API 接口', '开发者文档'];
  const aboutLinks = ['公司介绍', '团队成员', '联系方式', '招聘信息'];

  return (
    <footer className="bg-slate-800 border-t border-slate-700">
      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="text-xl font-['Pacifico'] text-primary mb-4">logo</div>
            <p className="text-slate-400 text-sm">
              一站式实用工具集合，提升工作效率，简化日常任务。
            </p>
          </div>
          <div>
            <h4 className="font-semibold mb-4">工具分类</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              {toolCategories.map((link) => (
                <li key={link}>
                  <a href="#" className="hover:text-white transition-colors">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">支持服务</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              {supportLinks.map((link) => (
                <li key={link}>
                  <a href="#" className="hover:text-white transition-colors">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">关于我们</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              {aboutLinks.map((link) => (
                <li key={link}>
                  <a href="#" className="hover:text-white transition-colors">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="border-t border-slate-700 mt-8 pt-8 text-center text-sm text-slate-400">
          <p>&copy; 2024 . All rights reserved. | 京ICP备12345678号</p>
        </div>
      </div>
    </footer>
  );
}
