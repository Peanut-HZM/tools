/**
 * 未登录提示组件
 * 受保护页面在未登录时渲染此组件：提示 + "登录"按钮（打开全局登录弹框）
 */
import { useLoginModalStore } from '../../stores/loginModalStore';
import { Lock } from 'lucide-react';

export default function RequireAuthNotice() {
  const openLoginModal = useLoginModalStore((state) => state.openLoginModal);

  return (
    <div className="flex h-full min-h-[300px] items-center justify-center p-6">
      <div className="text-center">
        <Lock className="w-10 h-10 mb-4 text-ink-faint" />
        <p className="mb-1 text-lg text-white">该功能需要登录后使用</p>
        <p className="mb-4 text-sm text-ink-faint">登录成功后数据将自动加载</p>
        <button
          onClick={openLoginModal}
          className="rounded-lg bg-accent px-6 py-2 text-white transition-colors hover:bg-accent-hover cursor-pointer"
        >
          登录
        </button>
      </div>
    </div>
  );
}
