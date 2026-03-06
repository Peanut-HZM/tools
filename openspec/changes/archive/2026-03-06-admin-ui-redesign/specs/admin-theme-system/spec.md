## ADDED Requirements

### Requirement: 后台主题颜色系统

定义后台管理的统一颜色使用规范，确保视觉一致性。

#### Scenario: 背景色使用
- **WHEN** 设置页面背景
- **THEN** 使用 `bg-slate-900` 作为主背景，`bg-slate-800` 作为卡片背景

#### Scenario: 边框色使用
- **WHEN** 设置卡片、表格边框
- **THEN** 使用 `border-slate-700` 作为默认边框，`border-slate-600` 作为内部元素边框

#### Scenario: 主题色使用
- **WHEN** 设置强调色、激活状态
- **THEN** 使用 `cyan-500` 作为主题色，`cyan-600` 作为按钮背景，`cyan-400` 作为高亮文字

#### Scenario: 文字色使用
- **WHEN** 设置文字颜色
- **THEN** 标题使用 `text-white`，正文使用 `text-slate-300`，次要文字使用 `text-slate-400`，禁用文字使用 `text-slate-500`

### Requirement: 间距和圆角规范

定义统一的间距和圆角使用规范。

#### Scenario: 卡片内边距
- **WHEN** 设置卡片内边距
- **THEN** 使用 `p-6` (24px) 作为标准内边距

#### Scenario: 表格单元格间距
- **WHEN** 设置表格单元格间距
- **THEN** 使用 `px-4 py-3` 作为标准单元格内边距

#### Scenario: 圆角使用
- **WHEN** 设置卡片、按钮圆角
- **THEN** 使用 `rounded-xl` (12px) 作为卡片圆角，`rounded-lg` (8px) 作为按钮圆角，`rounded` (4px) 作为小元素圆角

### Requirement: 过渡动画规范

定义统一的过渡动画使用规范。

#### Scenario: Hover 过渡
- **WHEN** 用户 hover 到可交互元素上
- **THEN** 显示 `transition-colors` 或 `transition-all` 过渡效果

#### Scenario: 按钮激活
- **WHEN** 用户点击按钮
- **THEN** 显示 `active:scale-95` 缩放效果（如适用）

#### Scenario: 模态框动画
- **WHEN** 打开模态框
- **THEN** 背景使用 `bg-black/70` 半透明效果
