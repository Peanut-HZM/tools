# 小红书配图智能布局优化实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 优化小红书系列配图生成器，实现智能布局，将空间利用率从 25-40% 提升至 75-85%，内容密度提升 2-3 倍。

**Architecture:** 在 `series-card-generator-v2.py` 中添加布局计算工具方法，修改各图片类型的卡片生成逻辑，实现动态卡片高度、科技网格背景、GitHub 数据徽章三大核心功能。

**Tech Stack:** Python 3.12+, Pillow (PIL) 图像处理，智能布局算法

**设计文档:** `/Users/huazhongmin/IdeaProjects/tools/docs/plans/2026-04-10-xiaohongshu-smart-layout-design.md`

---

## 任务列表

### 任务 1: 添加布局计算工具方法

**Files:**
- Modify: `~/.agents/skills/xiaohongshu-poster/scripts/series-card-generator-v2.py:67-900` (SeriesCardGeneratorV2 类)

**步骤:**
1. 在 `SeriesCardGeneratorV2` 类中添加常量定义（TARGET_CONTENT_HEIGHT = 1100）
2. 添加 `_calculate_layout()` 方法
3. 添加 `_draw_tech_grid()` 方法
4. 添加 `_draw_github_data_badge()` 方法
5. 添加 `_wrap_text_to_fit()` 方法
6. 测试：运行 `python3 series-card-generator-v2.py dummy.txt` 验证无语法错误

**代码片段:**
```python
# 在类开头添加常量
TARGET_CONTENT_HEIGHT = 1100  # 目标内容区高度
MAX_CARD_HEIGHT = 80
MIN_CARD_HEIGHT = 45

def _calculate_layout(self, item_count):
    """动态计算卡片高度和间距"""
    if item_count <= 4:
        card_height = (TARGET_CONTENT_HEIGHT - 5 * 15) // item_count
        card_height = min(card_height, self.MAX_CARD_HEIGHT)
        gap = 15
        show_grid = True
    elif item_count <= 8:
        card_height = 55
        gap = 12
        show_grid = False
    else:
        card_height = 45
        gap = 8
        show_grid = False
    return card_height, gap, show_grid

def _draw_tech_grid(self, draw, image_height, grid_size=60):
    """绘制淡蓝色科技网格背景"""
    grid_color = (30, 50, 80)
    for y in range(0, image_height, grid_size):
        draw.line([(0, y), (IMAGE_WIDTH, y)], fill=grid_color, width=1)
    for x in range(0, IMAGE_WIDTH, grid_size):
        draw.line([(x, 0), (x, image_height)], fill=grid_color, width=1)

def _draw_github_data_badge(self, draw, y_offset, data):
    """绘制 GitHub 数据徽章（4 列）"""
    badge_height = 60
    badges = [
        ('⭐ Stars', data.get('stars', 'N/A')),
        ('🍴 Forks', str(data.get('forks', 0))),
        ('📈 Trend', data.get('trend', 'N/A')),
        ('💻 Language', data.get('language', 'N/A') or 'N/A'),
    ]
    badge_width = (IMAGE_WIDTH - 100) // 4
    label_font = self.get_font(24)
    value_font = self.get_font(28)
    
    for i, (label, value) in enumerate(badges):
        x = 50 + i * badge_width
        draw.rounded_rectangle(
            [(x, y_offset), (x + badge_width - 10, y_offset + badge_height)],
            radius=8, fill=COLORS['bg_light']
        )
        draw.text((x + 10, y_offset + 8), label, font=label_font, fill=COLORS['text_light'])
        draw.text((x + 10, y_offset + 32), value, font=value_font, fill=COLORS['text_primary'])
    
    return y_offset + badge_height

def _wrap_text_to_fit(self, text, font, max_width, max_lines, draw):
    """文字换行，确保在指定行数内适应"""
    lines = self.wrap_text(text, font, max_width, draw)
    while len(lines) > max_lines and font.size > 24:
        font = self.get_font(font.size - 2)
        lines = self.wrap_text(text, font, max_width, draw)
    return lines, font
```

---

### 任务 2: 优化封面图（添加数据徽章）

**Files:**
- Modify: `~/.agents/skills/xiaohongshu-poster/scripts/series-card-generator-v2.py:125-186` (create_cover_card 方法)

**步骤:**
1. 在封面图底部添加 GitHub 数据徽章调用
2. 调整 y_offset 计算，为数据徽章留出空间
3. 测试：生成封面图，检查数据徽章是否显示

**布局结构:**
```
[顶部装饰条 8px]
[项目名 64px]
[Stars 40px]
[分隔线 2px]
[开场白 80px]
[痛点卡片 自适应]
[GitHub 数据徽章 60px] ← 新增
[底部链接 30px]
```

---

### 任务 3: 优化特点图（动态卡片高度 + 网格背景）

**Files:**
- Modify: `~/.agents/skills/xiaohongshu-poster/scripts/series-card-generator-v2.py:243-295` (create_features_card 方法)

**步骤:**
1. 调用 `_calculate_layout()` 计算卡片高度和间距
2. 如果内容 ≤4，调用 `_draw_tech_grid()` 绘制背景
3. 合并 AI 生成特点 + README 提取特点，目标 8-12 个
4. 使用动态卡片高度绘制所有特点
5. 测试：生成特点图，检查是否显示 8+ 个特点，无文字截断

**关键代码:**
```python
features = content_data.get('features', [])
# 合并 README 特点（如果有）
if readme_data and readme_data.get('features'):
    readme_features = [{'title': f.split(':')[0][:15], 'description': f.split(':')[-1][:50] if ':' in f else ''} 
                       for f in readme_data['features'][:5]]
    features = readme_features + features
# 去重，取前 12 个
features = list({f['title']: f for f in features}.values())[:12]

# 计算布局
card_height, gap, show_grid = self._calculate_layout(len(features))

# 绘制网格背景（如果内容少）
if show_grid:
    self._draw_tech_grid(draw, IMAGE_HEIGHT - 100)

# 绘制特点卡片
for i, feature in enumerate(features):
    card_y1 = y_offset + i * (card_height + gap)
    card_y2 = card_y1 + card_height
    # ... 绘制卡片
```

---

### 任务 4: 优化场景图（双栏布局支持）

**Files:**
- Modify: `~/.agents/skills/xiaohongshu-poster/scripts/series-card-generator-v2.py:297-350` (create_scenarios_card 方法)

**步骤:**
1. 添加默认场景列表（12 个）
2. 如果场景数 >8，启用双栏布局
3. 调用 `_calculate_layout()` 计算卡片高度
4. 测试：生成场景图，检查是否显示 10+ 个场景

**双栏布局代码:**
```python
if len(scenarios) > 8:
    # 双栏布局
    col_width = (IMAGE_WIDTH - 120) // 2
    for i, scenario in enumerate(scenarios[:12]):
        col = i % 2
        row = i // 2
        x = 60 + col * (col_width + 20)
        y = y_offset + row * (card_height + gap)
        # 绘制卡片
else:
    # 单栏布局
    for i, scenario in enumerate(scenarios):
        # 绘制卡片
```

---

### 任务 5: 优化命令图（分栏布局 + 更多命令）

**Files:**
- Modify: `~/.agents/skills/xiaohongshu-poster/scripts/series-card-generator-v2.py:352-412` (create_commands_card 方法)

**步骤:**
1. 分栏：安装方式区 + 使用命令区
2. 安装命令使用代码块样式展示所有方式
3. 使用命令合并基础命令 + README 提取命令，目标 10-15 个
4. 调用 `_calculate_layout()` 计算卡片高度
5. 测试：生成命令图，检查是否显示 10+ 个命令

**布局结构:**
```
[标题区 60px]
[安装方式区 150px]
  - 5 种安装命令，代码块样式
[使用命令区 自适应]
  - 8-10 个命令，卡片列表
```

---

### 任务 6: 优化总结图（双栏布局 + 数据徽章）

**Files:**
- Modify: `~/.agents/skills/xiaohongshu-poster/scripts/series-card-generator-v2.py:483-547` (create_summary_card 方法)

**步骤:**
1. 合并 AI 生成要点 + README Tips，目标 8-10 个
2. 如果要点数 >6，启用双栏布局
3. 在 CTA 按钮下方添加 GitHub 数据徽章
4. 测试：生成总结图，检查是否显示 8+ 个要点，数据徽章清晰

**布局结构:**
```
[标题区 60px]
[要点列表 500px]
  - 左侧：4-5 个要点
  - 右侧：4-5 个要点（双栏）
[CTA 按钮 80px]
[GitHub 数据徽章 60px] ← 新增
[底部链接 30px]
```

---

### 任务 7: 优化内容解析（整合更多 README 内容）

**Files:**
- Modify: `~/.agents/skills/xiaohongshu-poster/scripts/series-card-generator-v2.py:549-905` (parse_content_file 方法)

**步骤:**
1. 增加 scenarios 默认列表到 12 个
2. 增加 commands 默认列表到 10 个
3. 增加 summary_points 默认列表到 8 个
4. 优化 README 内容整合逻辑
5. 测试：解析文案文件，检查各类型内容量

**默认内容:**
```python
# 默认场景（12 个）
if len(data['scenarios']) < 12:
    data['scenarios'] = [
        '快速生成代码片段', '代码 review 和优化', '调试 bug',
        '学习新语言/框架', 'GitHub 工作流集成', '编写单元测试',
        '重构代码', '生成文档', '代码解释', '错误分析',
        '性能优化', '安全审查',
    ][:12]

# 默认命令（10 个）
if len(data['commands']) < 10:
    data['commands'] = [
        {'description': '初始化项目', 'command': 'opencode init'},
        {'description': '生成代码', 'command': 'opencode generate "描述"'},
        {'description': '代码审查', 'command': 'opencode review'},
        {'description': '运行测试', 'command': 'opencode test'},
        {'description': '构建项目', 'command': 'opencode build'},
        {'description': '部署', 'command': 'opencode deploy'},
        {'description': '查看日志', 'command': 'opencode logs'},
        {'description': '清理缓存', 'command': 'opencode clean'},
        {'description': '更新配置', 'command': 'opencode config'},
        {'description': '帮助信息', 'command': 'opencode --help'},
    ][:10]
```

---

### 任务 8: 测试验证

**Files:**
- Test: `~/.xiaohongshu/uploads/YYYY-MM-DD/run-NNN/series_v2_*.png`

**步骤:**
1. 运行完整发布流程：
   ```bash
   cd ~/.agents/skills/xiaohongshu-poster/scripts
   python3 one-click-publish.py anomalyco/opencode "OpenCode" "开源 AI 编程助手" series
   ```
2. 检查生成的 7 张图片：
   - 封面图：数据徽章是否显示
   - 特点图：是否显示 8+ 个特点，无文字截断
   - 场景图：是否显示 10+ 个场景
   - 命令图：是否显示 10+ 个命令
   - 总结图：是否显示 8+ 个要点，数据徽章清晰
3. 验收标准：
   - ✅ 所有图片下方空白区域 <20%
   - ✅ 特点图至少显示 8 个特点
   - ✅ 命令图至少显示 10 个命令
   - ✅ 无文字截断现象
   - ✅ 科技网格背景美观
   - ✅ GitHub 数据徽章清晰

---

### 任务 9: 更新版本号和文档

**Files:**
- Modify: `~/.agents/skills/xiaohongshu-poster/SKILL.md`
- Modify: `~/.agents/skills/xiaohongshu-poster/scripts/one-click-publish.py` (版本字符串)

**步骤:**
1. 更新 SKILL.md 版本号到 v8.2
2. 添加 v8.2 更新日志
3. 更新 one-click-publish.py 版本字符串
4. 提交 git

**更新日志:**
```markdown
**v8.2 更新日志：**
- ✅ 智能布局系统 - 根据内容量自动调整卡片高度和间距
- ✅ 科技网格背景 - 内容少时自动添加装饰，填充空白
- ✅ GitHub 数据徽章 - 展示 Stars/Forks/Trend/Language
- ✅ 内容密度提升 - 特点图 8-12 个，场景图 10-12 个，命令图 10-15 个
- ✅ 文字自适应 - 自动调整字体大小，不再截断
- ✅ 空间利用率提升 - 从 25-40% 提升至 75-85%
```

---

## 验收标准

1. ✅ 所有图片下方空白区域 <20%
2. ✅ 特点图至少显示 8 个特点
3. ✅ 命令图至少显示 10 个命令
4. ✅ 无文字截断现象
5. ✅ 科技网格背景美观不突兀
6. ✅ GitHub 数据徽章清晰展示

---

## 回滚方案

如果优化后效果不理想：
1. 备份当前文件：`cp series-card-generator-v2.py series-card-generator-v2.py.bak`
2. 回滚：`cp series-card-generator-v2.py.bak series-card-generator-v2.py`
3. 重新生成图片验证

---

## 提交信息

```bash
git add ~/.agents/skills/xiaohongshu-poster/scripts/series-card-generator-v2.py
git add ~/.agents/skills/xiaohongshu-poster/SKILL.md
git commit -m "feat: 智能布局优化 v8.2 - 内容密度提升 2-3 倍，空间利用率 75-85%"
```
