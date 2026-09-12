/**
 * 自定义导航占位组件（玻璃光晕改版 Task 4）。
 *
 * 背景说明：首页/我的页开启 navigationStyle: 'custom' 后，原生导航栏消失，
 * 页面内容从屏幕最顶端（含状态栏）开始渲染，需要在页面顶部放一个
 * 与"状态栏 + 胶囊按钮区"等高的占位 View，避免内容被状态栏/胶囊遮挡。
 *
 * 高度计算策略：
 * - 状态栏高度：Taro.getSystemInfoSync().statusBarHeight（单位 px，系统真实像素）
 * - 微信小程序下再叠加胶囊按钮区：取 getMenuButtonBoundingClientRect()，
 *   按「状态栏 + (胶囊 top - 状态栏高度) × 2 + 胶囊高度」计算——即胶囊上下
 *   边距对称，得到的内容区高度在各机型上视觉居中（微信自定义导航通用做法）
 * - 非微信环境（H5 等）无胶囊 API 或返回非法值：try/catch 降级为纯状态栏高度
 *
 * 输出：一个 style 内联 height（px）的空 View，背景透明，随页面背景走。
 * 注意：系统 API 返回的是设备真实 px，因此内联样式必须用 px 而非 rpx，
 * 也不能走全局 pxtransform（样式表转换只作用于 .scss 文件）。
 */
import Taro from '@tarojs/taro';
import { View } from '@tarojs/components';

/**
 * 计算自定义导航区总高度（状态栏 + 胶囊内容区）。
 * 返回：高度值（px），异常环境兜底 20px（常见机型的状态栏近似值）
 */
function calcNavBarHeight(): number {
  // 第一段：状态栏高度（所有环境通用）
  let statusBarHeight = 20;
  try {
    statusBarHeight = Taro.getSystemInfoSync().statusBarHeight || 20;
  } catch {
    // 部分环境（H5 早期加载等）可能抛错，保持兜底值即可
  }

  // 第二段：微信胶囊按钮适配（非微信环境 getMenuButtonBoundingClientRect
  // 不存在或抛错，整体降级为纯状态栏高度）
  try {
    const rect = Taro.getMenuButtonBoundingClientRect();
    // top/height 非法（H5 返回 0 或 API 缺失）时不算胶囊区
    if (rect && rect.top > 0 && rect.height > 0) {
      return statusBarHeight + (rect.top - statusBarHeight) * 2 + rect.height;
    }
  } catch {
    // 非微信环境无此 API，忽略走降级
  }

  return statusBarHeight;
}

// 模块级只算一次：系统信息在运行期内不会变化，避免每次渲染重复调用
const NAV_BAR_HEIGHT = calcNavBarHeight();

/**
 * 自定义导航占位：渲染一个与状态栏+胶囊区等高的透明 View。
 * 用法：置于开启 navigationStyle: 'custom' 的页面根节点第一个子元素。
 */
export default function StatusBarSpacer() {
  return <View style={{ height: `${NAV_BAR_HEIGHT}px` }} />;
}
