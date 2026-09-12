# 阶段⑧–⑨ 延后项与裁决记录（发布前验收依据）

> 来源：阶段⑧–⑨ 执行（9 任务 + 终审 + 修复波次，11 提交 `415cea1f..0eebb301`）。终审结论：可合并，2 项 Important + 2 项顺带修复已落地并复验（`0eebb301`）。工作区已清理。
> **发布硬门槛**：`mini-program/docs/glass-glow-acceptance.md` 是唯一走查依据——真机项优先级：svg data-URI 图标渲染 → backdrop-filter 双态（方法 B/C）→ custom 导航状态栏三机型 → tabBar 图标 27px。

## 合并前已修复（commit 0eebb301）

- openclaw stop-btn `:active` 按压反馈回归（改 `var(--p-red-500)`）
- 根 `.gitignore` 追加 `!mini-program/docs/` 例外（保护活跃编辑期的验收清单）
- message 页 expand-btn 品牌字叠品牌底不可读（字/箭头改白，json 深底区观感保留）
- calendar usage-tips "粉色"→"紫色"文案校订

## 延后项（后续迭代）

### 小程序工程卫生
- lock 注册源混用（13 npmjs / 1488 npmmirror，下次 install 自然归一）
- `generate-miniapp-tokens.js`：parseRootTokens 只取首 `:root` 块（建议加多块告警）；头部时间戳致重生成必有 diff 噪声
- `gen-tabbar-icons.js` CONTENT_HALF 死常量；SDF 1px 抗锯齿局限（真机可辨性低）
- `_glass.scss` 与 `utils/tint.ts` 双处维护 tint 色板（建议一致性单测或脚本生成）
- `.tool-card-icon` 与 `.tint` 冗余 flex 定义；EmptyState 字符串分支成死代码（兼容保留）
- StatusBarSpacer 用废弃的 `getSystemInfoSync()` + 模块级求值一次（旋转/折叠屏需重估）
- app.scss 旧 `.btn-primary:active` 死规则清理；tsc src 41 存量错（44→41，全为历史遗留）

### 小程序功能/内容（需产品决策或接口）
- message 页 text 类型消息图标 mail 语义略歪（Icon 表补 chat 后顺带）；Icon 表扩充候选：table/check/chat/clipboard
- stop-btn 类需求：token 层补 `--accent-danger-press` 档（本次用 --p-red-500 就近解决）
- 课程进度条：等 `coursePlatform` API 补 progress 字段 + "我的课程"页后按 Web CourseCard（accent→accent-info 渐变）补齐
- openclaw 两枚 base64 头像 SVG 仍为旧品牌蓝 #3B82F6（建议品牌色重生成）
- weapp `<button>`→`<Button>` 四页的主按钮 `::after` 发丝描边走查项

## 全项目跨阶段遗留汇总（建议开 issue 跟踪）

1. **后端**：课程详情 view_count 行锁（阻塞级，走查中多次冻结后端）
2. **前端**：GUI 注册不生效（AuthModal）；TechContent 点赞/收藏无 onClick；reading_time 字段名
3. **API**：市场/OpenSpecCourse 404、LLM 流式 500
4. **测试账号清理**：t15smoke / t9walktest / probe-noop / t14smoke2 / t67walktest（本地 dev 库）
5. **CI 留证**：干净环境 `npm ci && npm run build`（frontend lockfile 重生成留证）
6. **Web 端小专项**：AdminLayout 抽屉 JSX 去重 + focus trap；MobileTabBar TABS 收敛 navigation.ts；按钮语义变体统一；CategoryTabs 40px 豁免记录；Toast 联动范式统一（resolved vs observer 二选一）
