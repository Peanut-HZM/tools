/**
 * 产品经理 Agent - 工作上下文 Store
 *
 * 存放「当前打开的会话 ID」这类**工具内部上下文**。
 *
 * 为什么不放 URL：地址栏只应表达「打开了哪个工具」（/workspace/<工具编码>），
 * 会话 ID 属于工具内部状态，写进 URL 会污染地址栏，且分享出去的链接
 * 指向的是他人的会话上下文。这里用 zustand persist 落到 localStorage，
 * 刷新页面后仍能恢复上次打开的会话。
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ProductManagerState {
  /** 工作区路由下当前打开的会话 ID */
  workspaceConversationId: string | null;
  setWorkspaceConversationId: (id: string | null) => void;
}

export const useProductManagerStore = create<ProductManagerState>()(
  persist(
    (set) => ({
      workspaceConversationId: null,
      setWorkspaceConversationId: (id) => set({ workspaceConversationId: id }),
    }),
    {
      name: 'product-manager-context',
      partialize: (state) => ({
        workspaceConversationId: state.workspaceConversationId,
      }),
    },
  ),
);
