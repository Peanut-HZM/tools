# 玻璃光晕改版 · 小程序逐页自检清单（阶段⑧–⑨ 验收）

> 改版范围：token 管道重写（`src/styles/_tokens.scss`）+ 别名层换肤（`app.scss`）+ 玻璃工具类（`src/styles/_glass.scss`）+ Icon 组件（SVG data-URI）+ 23 页全量换肤。
> 主题形态：**暗色单主题**（品牌紫蓝 Glass Glow），不做运行时切主题（与 design.md §8.2 一致）。
> 验收方式：在**微信开发者工具**导入 `mini-program/`（构建产物已在 `dist/`，或本地执行 `npm run build:weapp`）逐页走查；标注【真机】的项目需真机预览核验。
>
> **页面口径说明**：计划文档写"27 页"，实际 `app.config.ts` 注册页面为 **23 个**（主包 14 + 分包 9），以实际注册页为准。

---

## 一、通用检查点（每页通走）

每页先过一遍以下 8 项，再对照第二节"逐页矩阵"核对页面特有点。

| # | 检查点 | 合格标准 |
|---|--------|----------|
| 1 | **页面背景** | 品牌暗色渐变：暗夜蓝 → 深蓝（`#0A1225 → #0F1930`），无旧版纯色/亮色残留 |
| 2 | **品牌色** | 主操作/选中/高亮为品牌紫蓝 `#5B6BF5`（hover 提亮 `#8B9BFF`、按压压暗 `#4A5AE5`）；无旧蓝 `#3b82f6` 观感残留 |
| 3 | **玻璃卡** | `.glass-card`：半透明白底 + 白色发丝描边 + 顶部内高光 + 玻璃投影；支持磨砂的内核上有背景模糊 |
| 4 | **Icon** | 所有图标为 SVG 线性图标（Icon 组件），线条 1.8 圆角风格；中性图标为 ink 灰 `#6E7A8F`、品牌强调为 `#8B9BFF`、危险为 `#F87171`；**无 emoji/Unicode 字形图标残留** |
| 5 | **空态** | 空态有图标 + 文案（EmptyState 组件或页面内联），图标为品牌色/ink 系，文案 ink 层级正确，无 emoji |
| 6 | **加载态** | Loading 组件渲染正常，颜色为 ink/品牌 token，无旧色 |
| 7 | **文字层级** | 主文字近白 `--ink-default`、辅助 `--ink-muted`、弱化 `--ink-faint`，层级分明无刺眼纯黑/纯灰残留 |
| 8 | **渐变主按钮** | `.btn-primary`：品牌渐变底（`#5B6BF5 → #A155F7`）+ 白字 + 品牌辉光阴影；禁用态压掉渐变与辉光 |

> 涉及输入框的页面附加：聚焦时描边变品牌色；按钮/图标触摸目标 ≥ 88rpx（44px）。

---

## 二、逐页检查点矩阵

### 主包（14 页）

| # | 页面 | 通用 8 项 | 页面特有检查点 |
|---|------|-----------|----------------|
| 1 | `pages/index/index`（tabBar·工具） | ✔ | **custom 导航**：StatusBarSpacer 状态栏占位与系统状态栏同高、标题不与胶囊重叠【真机】；顶部品牌渐变文字（gradient-text）；工具卡 tint 色板（低饱和色底 + 同色 Icon）；ToolCard 玻璃卡 hover 态；空态（暂无工具）走 EmptyState |
| 2 | `pages/cross-share/message/index`（tabBar·消息） | ✔ | 消息列表玻璃卡；展开/收起箭头 Icon（`#5B6BF5` 品牌色）；**已知 bug**：expand-btn 品牌字叠品牌底不可读（见第四节）；取消/关闭为 danger 红；消息类型 Icon（file/globe/edit/image/mail，ink 灰）；代码块 `'Courier New'` 深色域保留惯例 |
| 3 | `pages/cross-share/file/index`（tabBar·文件） | ✔ | 文件类型 Icon（image/file/edit/database，ink 灰）；上传按钮渐变底白字；禁用态压光；空态（暂无文件）；删除等危险操作 `#F87171` |
| 4 | `pages/profile/index`（tabBar·我的） | ✔ | **custom 导航**：StatusBarSpacer 状态栏高度【真机】；profile-header 顶部留白【真机调优】；头像圆形品牌底反白字；渐变文字；设置项右箭头 Icon（ink 灰） |
| 5 | `pages/login/index` | ✔ | 输入框聚焦品牌描边；user/lock/mail 前缀 Icon（ink 灰）；错误提示 warning Icon（danger 红）；登录按钮渐变底白字 |
| 6 | `pages/json-formatter/index` | ✔ | 代码域 `'Courier New'` 深色块保留惯例（白名单）；格式化/压缩按钮渐变底；格式错误提示 danger 红 |
| 7 | `pages/calendar/index` | ✔ | 月份切换 chevron Icon（品牌 `#8B9BFF`，上月 rotate 翻转）；农历弱化字（`--text-disabled` 别名，视觉与原版一致）；事件类型标签色板；usage-tips **文案待校订**（"粉色=传统节日"与实际紫色映射失配，见第四节）；关闭 Icon（ink 灰）；lightbulb 提示 Icon（`#FBBF24` = `--accent-warning` 同源） |
| 8 | `pages/key-generator/index` | ✔ | Switch 选中色品牌紫蓝；密钥展示 `'Courier New'` 深色域保留；复制按钮渐变底；强度指示色 |
| 9 | `pages/ocr/index` | ✔ | 图片上传区玻璃卡；识别按钮渐变底；禁用态压光；识别中 Loading |
| 10 | `pages/http-client/index` | ✔ | 方法标签色板；请求/响应代码域 `'Courier New'` 深色域保留；header 行删除 Icon（danger 红）；发送按钮渐变底；禁用态压光 |
| 11 | `pages/asr/index.tsx` | ✔ | 录音按钮（录：mic Icon ink 灰；停止：stop-square 深色块）；**已知限制**：停止按钮按压态反馈丢失（token 无 danger-press 档，见第四节）；波形/状态色 |
| 12 | `pages/change-password/index` | ✔ | 密码可见性 Icon；强度条色阶（danger/warning/success token）；提交按钮渐变底 |
| 13 | `pages/help/index` | ✔ | 帮助卡片玻璃化；折叠/展开箭头 Icon；标题层级 ink 正确 |
| 14 | `pages/openclaw/index` | ✔ | 装饰圆走品牌渐变 token（`--gradient-brand`，无旧 `#3b82f6→#8b5cf6` 残留）；终端输出深色代码域保留；会话气泡玻璃卡 |

### 分包（9 页）

| # | 页面 | 通用 8 项 | 页面特有检查点 |
|---|------|-----------|----------------|
| 15 | `package-media/pages/image-downloader` | ✔ | 链接输入玻璃卡；解析按钮渐变底；图片网格玻璃卡；下载进度品牌色 |
| 16 | `package-media/pages/video-downloader` | ✔ | 取消按钮 danger 红实底（原 `#ef4444` 语义对号）；下载中状态色；**已知限制**：tsc 存量对比错 TS2367（见第四节，不影响构建） |
| 17 | `package-docs/pages/markitdown-converter` | ✔ | 转换按钮渐变底；chevron-right Icon（ink 灰）；文件选择区玻璃卡 |
| 18 | `package-docs/pages/markdown-editor` | ✔ | Markdown 渲染：pre/代码块深色代码域保留（底 `--bg-overlay`、代码字 `--ink-default`）；编辑/预览切换选中态品牌色；glass-panel 工具栏 |
| 19 | `package-learning/pages/course-platform` | ✔ | 章节选中态 accent-primary 实底（原 `#6366f1` 语义对号）；搜索框 Icon（ink 灰）；**已知限制**：SearchBar onSearch prop tsc 存量错（见第四节）；课程进度条等价渐变（接"我的课程"接口时按 Web 补齐 accent→accent-info，见第四节） |
| 20 | `package-learning/pages/course-platform/detail` | ✔ | 章节列表选中态序号徽标 accent 实底；标题 accent 字色；播放/学习按钮渐变底 |
| 21 | `package-learning/pages/tech-contents` | ✔ | 类型标签 accent 实底；章节选中态 accent-primary；列表玻璃卡 |
| 22 | `package-learning/pages/tech-contents/detail` | ✔ | 类型标签 chip 玻璃描边；正文 Markdown 深色代码域保留；内容玻璃卡 |
| 23 | `package-stats/pages/token-usage` | ✔ | 统计数值 accent-primary 语义对号；图表配色走 chart token（cpu 蓝/memory 绿/网格弱化）；日期选择玻璃卡 |

---

## 三、tabBar 与 custom 导航专项

### tabBar（4 tab：工具 / 消息 / 文件 / 我的）
- [ ] 背景色 `#0A1225` 与页面渐变顶端衔接自然（borderStyle: black）
- [ ] 未选中文字/图标 `#5C6784`（ink 弱化系），选中 `#8B9BFF`（品牌浅紫）
- [ ] 图标（tool/message/file/profile）在 27px 规格下显示清晰、不模糊不裁切【真机】
- [ ] 选中态图标为品牌浅紫描边风格，与页面 Icon 组件风格一致

### custom 导航（仅 `pages/index` 与 `pages/profile`）
- [ ] StatusBarSpacer 占位高度 = 系统状态栏实际高度【真机：不同机型（刘海屏/普通屏）各验一台】
- [ ] 页面标题/头部内容不被系统胶囊（右上角"…"与"◉"）遮挡【真机】
- [ ] 下拉/滚动时头部与内容区边界清晰（玻璃面板 header 效果正常）
- [ ] 旋转屏/折叠屏展开时状态栏高度重估（**已知限制**：StatusBarSpacer 为模块加载时求值一次，见第四节）

---

## 四、玻璃降级验证方法

玻璃卡为渐进增强：`@supports (backdrop-filter: …)` 内启用磨砂；`@supports not (…)` 降级为实色底 `--glass-bg-fallback`（`#131C33`）。两种状态都需验证。

**方法 A：开发者工具手动关掉磨砂（验证"无磨砂时的可读性基线"）**
1. 打开调试器 → WXML 面板 → 选中任一 `.glass-card` 节点
2. 在 Styles 面板找到 `backdrop-filter: blur(14px)` 与 `-webkit-backdrop-filter: blur(14px)`，**取消勾选**
3. 合格标准：玻璃卡退化为半透明底 + 描边 + 投影，其上文字/图标仍清晰可读，不出现"文字浮在花背景上"的不可读状态

> 注意：手动取消勾选**不会**触发 `@supports not` 分支（@supports 由内核在样式匹配时评估），故此方法验证的是"磨砂缺失"的基线可读性；fallback 实色需用方法 B/C 验证。

**方法 B：低版本基础库 / 兼容内核（验证 fallback 实色分支）**
1. 开发者工具 → 详情 → 本地设置 → 调试基础库切换到较低版本（或在部分不支持 backdrop-filter 的内核环境打开）
2. 合格标准：`.glass-card` / `.glass-panel` 底色自动变为实色 `#131C33`（不再是半透明白），文字对比度不降级

**方法 C：真机自然降级**
- 用不支持 backdrop-filter 的老 Android 设备（旧 X5/UC 内核）真机预览，玻璃卡应自动走实色降级；支持磨砂的 iOS/新机型上应有明显毛玻璃效果【真机】

---

## 五、已知限制与遗留

### 5.1 真机核验项（本清单走查后仍需真机确认）
| 项 | 来源 | 说明 |
|----|------|------|
| SVG data-URI 图标基础库兼容 | Task 3 | Icon 组件以 `data:image/svg+xml` 交付 Image 渲染，需真机（低版本基础库）确认全部图标渲染正常 |
| backdrop-filter 磨砂 / 降级 | Task 5 | 见第四节方法 B/C；真机确认磨砂效果与实色 fallback |
| custom 导航状态栏高度 | Task 4 | StatusBarSpacer 在刘海屏/普通屏真机上占位正确；旋转/折叠屏展开时高度不刷新（模块加载时求值一次），需重进页面恢复 |
| tabBar 图标 27px 显示 | Task 2 | 真机确认图标清晰度与选中/未选中态对比 |
| 磨砂效果真机观感 | Task 5 | blur(14px)/blur(18px) 在真机上的性能与观感（滚动流畅度） |
| profile-header 顶部留白 | Task 4 | custom 导航下头部留白量真机调优 |

### 5.2 功能遗留（后续迭代）
| 项 | 来源 | 说明 |
|----|------|------|
| 课程进度条 | Task 8 | 当前为等价渐变近似；接"我的课程"真实接口时按 Web 实际（accent→accent-info 渐变）补齐 |
| expand-btn 品牌字叠品牌底不可读 | Task 7（既有 bug） | `pages/cross-share/message` 展开按钮品牌字叠品牌底，验收时记录、后续修复 |
| Icon 表扩充候选 | Task 7 | table / check / chat / clipboard 四个图标待需要时扩充 |
| stop-btn 按压态反馈丢失 | Task 7 | token 体系无 danger-press 档，候选补 token 后恢复按压反馈 |
| EmptyState 空状态 Icon 默认色 | Task 7 | 未显式传 color 时落默认 `#8B9BFF`，后续统一空态图标色时注意 |
| phase3-deferred 功能项 | 交付后事项 | view_count 行锁、AuthModal 注册、reading_time 等按 phase3/4-5/6-7 三份 defer 文档汇总开 issue |

### 5.3 文案校订
| 项 | 来源 | 说明 |
|----|------|------|
| calendar usage-tips | Task 6 | 提示文案写"粉色 = 传统节日"，与实际紫色映射失配，后续版本校订文案 |

### 5.4 工程已知限制（非阻塞）
| 项 | 说明 |
|----|------|
| 暗色单主题 | 小程序不迁移亮色主题（design.md §8.2 裁决） |
| iconfont → SVG 方案 | 仓库内无法生成 iconfont 字体文件，裁决用内联 SVG data-URI（Icon 组件），颜色以 prop 烘入 |
| 长度类 token 不迁移 | `--glass-blur` 等长度 token 未随管道迁移，blur 按规范用字面量（14px/18px） |
| tsc 存量诊断 | `npx tsc --noEmit`：src 41 个存量错（基线 44，改版**零新增**、顺带消除 3 个未使用导入）；node_modules 另有约 99 个 @tarojs 类型库错（`--skipLibCheck` 可跳过）。构建走 babel 无 tsc 门禁，不阻塞 `build:weapp` |
| hex/emoji 白名单 | 清零校验（Task 9）确认残留均为显式白名单：token 同源字面量（`--color-primary: #5B6BF5` 等计划规定形式）、Icon 烘色字面量（`#6E7A8F`/`#F87171`/`#8B9BFF`/`#FBBF24`/`#5B6BF5`）、深色代码域（'Courier New' 字体块、Markdown pre/xterm）、注释中的 hex；emoji 代码残留 0（仅注释提及） |

---

## 六、清零校验结论摘要（Task 9）

- **hex 残留**（`*.scss`，剔除 `_tokens.scss`/`_glass.scss` 产物文件）：非注释残留 5 处，全部归类白名单——
  - `app.scss` 别名层 `--color-primary/-dark/-light`（计划明确要求的字面量形式，与 `--accent-primary/--accent-press/--accent-hover` 同源）
  - `app.scss` 页面背景渐变 `#0A1225/#0F1930`（注释声明与 `--bg-canvas/--p-navy-800` 同源）
  - `app.scss`/`profile` 反白字 `#fff`（品牌底反白惯例，token 体系无白色 token）
  - `app.scss` `--text-disabled: #475569`（8 处使用的既有别名，注释明确"视觉与原版一致"的保值决策）
  - 其余命中全部为注释（"原 #6366f1 语义对号"等迁移说明）
- **emoji 残留**（`*.tsx`）：代码残留 **0**；命中 7 处全部位于注释（迁移说明文字）
- **构建**：`npm run build:weapp` ✔ Compiled successfully（development 未压缩：dist 总计约 780KB，主包约 410KB，分包 docs 36K / learning 48K / media 32K / stats 18K）
- **tsc**：见 5.4，不劣化（44 → 41）
