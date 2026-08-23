/**
 * 全局登录弹框状态（Zustand）
 * 任何组件可通过 openLoginModal / closeLoginModal 控制弹框；
 * LoginModal 组件订阅本 store，不再使用 props 传参。
 */
import { create } from 'zustand';

interface LoginModalState {
  isOpen: boolean;
  openLoginModal: () => void;
  closeLoginModal: () => void;
}

export const useLoginModalStore = create<LoginModalState>()((set) => ({
  isOpen: false,
  openLoginModal: () => set({ isOpen: true }),
  closeLoginModal: () => set({ isOpen: false }),
}));
