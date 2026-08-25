import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

export default function AccountHeader() {
  const navigate = useNavigate();

  return (
    <div className="mb-8">
      {/* 面包屑导航 */}
      <nav className="flex items-center gap-2 text-sm text-ink-muted mb-4">
        <button
          onClick={() => navigate('/')}
          className="hover:text-accent transition-colors"
          type="button"
        >
          首页
        </button>
        <ChevronRight className="w-4 h-4" />
        <span className="text-ink-muted">账户设置</span>
      </nav>

      {/* 页面标题 */}
      <h1 className="text-3xl font-bold text-ink-inverse">账户设置</h1>
      <p className="text-ink-muted mt-2">管理您的个人信息和账户偏好</p>
    </div>
  );
}
