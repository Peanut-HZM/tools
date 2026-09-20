/**
 * 自定义导航占位组件（玻璃光晕改版 Task 4 + 遮挡修复）。
 *
 * 背景说明：首页/我的页开启 navigationStyle: 'custom' 后，原生导航栏消失，
 * 页面内容从屏幕最顶端（含状态栏）开始渲染，需要在页面顶部放一个
 * 与"状态栏 + 胶囊按钮区"等高的占位 View，避免内容被状态栏/胶囊遮挡。
 *
 * 高度计算策略（组件渲染期计算，非模块加载期）：
 * - 状态栏高度：Taro.getSystemInfoSync().statusBarHeight（单位 px，系统真实像素）
 * - 微信小程序下再叠加胶囊按钮区：取 getMenuButtonBoundingClientRect()，
 *   按「状态栏 + (胶囊 top - 状态栏高度) × 2 + 胶囊高度」计算——即胶囊上下
 *   边距对称，得到的内容区高度在各机型上视觉居中（微信自定义导航通用做法）
 * - 非微信环境（H5 等）无胶囊 API 或返回非法值：try/catch 降级为纯状态栏高度
 * - 所有路径均保证最低 44px 间距，避免 API 未就绪时内容为 0
 *
 * 注意：不能用模块级常量缓存（旧实现 366bc827），因为模块加载时微信运行时
 * 可能尚未初始化，API 返回 0 或异常值，导致 spacer 高度不足、内容被状态栏遮挡。
 */
import Taro from '@tarojs/taro';
import { View } from '@tarojs/components';

/** 安全下限：任何情况下至少留出 44px（约状态栏 + 胶囊的最小高度） */
const MIN_SPACER_PX = 44;

/**
 * 计算自定义导航区总高度（状态栏 + 胶囊内容区）。
 * 在组件渲染期调用，确保 API 已就绪。
 * 返回：高度值（px），异常环境兜底 MIN_SPACER_PX。
 */
function calcNavBarHeight(): number {
  let statusBarHeight = 20;

  try {
    statusBarHeight = Taro.getSystemInfoSync().statusBarHeight || 20;
  } catch {
    // 降级：保持兜底值
    return MIN_SPACER_PX;
  }

  try {
    const rect = Taro.getMenuButtonBoundingClientRect();
    if (rect && rect.top > 0 && rect.height > 0) {
      return Math.max(
        statusBarHeight + (rect.top - statusBarHeight) * 2 + rect.height,
        MIN_SPACER_PX
      );
    }
  } catch {
    // 非微信环境无此 API，保持纯状态栏高度
  }

  return Math.max(statusBarHeight, MIN_SPACER_PX);
}

/**
 * 自定义导航占位：渲染一个与状态栏+胶囊区等高的透明 View。
 * 用法：置于开启 navigationStyle: 'custom' 的页面根节点第一个子元素。
 * 高度在每次渲染时重新计算（极轻量，系统信息不变时结果一致）。
 */
export default function StatusBarSpacer() {
  const height = calcNavBarHeight();
  return <View style={{ height: `${height}px` }} />;
}
