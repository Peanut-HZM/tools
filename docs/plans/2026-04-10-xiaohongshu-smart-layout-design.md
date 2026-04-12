# 小红书配图智能布局优化设计

**创建时间**：2026-04-10  
**版本**：v8.2 - 智能布局版

## 问题背景

当前图片生成存在严重空间浪费：
- 内容密度低（每张图仅 3-5 条内容）
- 卡片高度固定，无法适配内容量
- 下方 60-75% 空间完全空白
- 文字被截断（内容超出时）

## 设计目标

1. **空间利用率提升至 75-85%**
2. **内容密度提升 2-3 倍**（每张图 8-15 条内容）
3. **自适应布局** - 根据内容量自动调整
4. **文字完整显示** - 不再截断

---

## 设计方案

### 1. 智能布局算法

```python
# 目标内容区高度 = 1100px（总高 1440px - 上下留白 340px）
TARGET_CONTENT_HEIGHT = 1100

def calculate_layout(item_count, min_height=45, max_height=80):
    """
    动态计算卡片高度和间距
    
    返回：(card_height, gap, show_background_deco)
    """
    if item_count <= 4:
        # 内容少：大卡片，填充空间
        card_height = (TARGET_CONTENT_HEIGHT - 5 * 15) // item_count
        card_height = min(card_height, max_height)  # 不超过最大值
        gap = 15
        show_background_deco = True  # 需要背景装饰
    elif item_count <= 8:
        # 标准布局
        card_height = 55
        gap = 12
        show_background_deco = False
    else:
        # 紧凑布局
        card_height = 45
        gap = 8
        show_background_deco = False
    
    return card_height, gap, show_background_deco
```

### 2. 科技网格背景

```python
def draw_tech_grid_background(draw, image_height, grid_size=60):
    """
    绘制淡蓝色科技网格背景
    
    - 网格线颜色：(30, 50, 80, 128) 半透明蓝色
    - 网格大小：60x60px
    - 只在内容项 ≤4 时启用
    """
    grid_color = (30, 50, 80)
    # 绘制水平线和垂直线
    for y in range(0, image_height, grid_size):
        draw.line([(0, y), (IMAGE_WIDTH, y)], fill=grid_color, width=1)
    for x in range(0, IMAGE_WIDTH, grid_size):
        draw.line([(x, 0), (x, image_height)], fill=grid_color, width=1)
```

### 3. GitHub 数据徽章

```python
def draw_github_data_badge(draw, y_offset, data):
    """
    绘制 GitHub 数据展示区
    
    展示：Stars | Forks | Trend | Language
    布局：4 列网格，每列一个数据项
    """
    badge_height = 60
    badges = [
        ('⭐ Stars', data.get('stars', 'N/A')),
        ('🍴 Forks', str(data.get('forks', 0))),
        ('📈 Trend', data.get('trend', 'N/A')),
        ('💻 Language', data.get('language', 'N/A') or 'N/A'),
    ]
    
    badge_width = (IMAGE_WIDTH - 100) // 4
    for i, (label, value) in enumerate(badges):
        x = 50 + i * badge_width
        # 绘制卡片背景
        draw.rounded_rectangle(
            [(x, y_offset), (x + badge_width - 10, y_offset + badge_height)],
            radius=8, fill=COLORS['bg_light']
        )
        # 绘制标签
        draw.text((x + 10, y_offset + 8), label, font=label_font, fill=COLORS['text_light'])
        # 绘制值
        draw.text((x + 10, y_offset + 32), value, font=value_font, fill=COLORS['text_primary'])
```

### 4. 自适应卡片高度

修改每个 `create_*_card` 方法，在绘制前计算：

```python
# 计算当前内容需要的总高度
total_content_height = len(items) * (card_height + gap) - gap

# 如果内容总高度 < 目标高度，增加卡片高度
if total_content_height < TARGET_CONTENT_HEIGHT:
    card_height = (TARGET_CONTENT_HEIGHT + gap) // len(items) - gap
    card_height = min(card_height, max_height)  # 不超过最大值
```

### 5. 文字自适应换行

```python
def wrap_text_to_fit(text, font, max_width, max_lines, draw):
    """
    文字换行，确保在指定行数内适应
    
    如果超过最大行数，自动缩小字体（最小到原大小的 80%）
    """
    lines = wrap_text(text, font, max_width, draw)
    
    # 如果行数超过限制，缩小字体重试
    while len(lines) > max_lines and font.size > 24:
        font = self.get_font(font.size - 2)
        lines = wrap_text(text, font, max_width, draw)
    
    return lines, font
```

---

## 各图片类型优化策略

### 封面图（Cover）

**布局结构**：
```
[顶部装饰条 8px]
[项目名 64px]
[Stars 40px]
[分隔线 2px]
[开场白 80px]
[痛点卡片 120px]
[GitHub 数据徽章 60px] ← 新增
[底部链接 30px]
```

**内容增强**：
- 添加 GitHub 数据徽章（Stars/Forks/Trend/Language）
- 痛点卡片高度自适应（根据文字量）

### 特点图（Features）

**目标**：显示 8-12 个特点

**策略**：
1. 合并 AI 生成特点 + README 提取特点
2. 去重后取前 10 个
3. 卡片高度动态计算（45-70px）
4. 内容 ≤4 时启用科技网格背景

### 场景图（Scenarios）

**目标**：显示 10-12 个场景

**策略**：
1. 使用默认场景列表（12 个）
2. 卡片高度动态计算
3. 使用两列布局（如果内容 >8 个）

### 命令图（Commands）

**目标**：显示 10-15 个命令

**布局结构**：
```
[标题区 60px]
[安装方式区 150px]
  - 5 种安装命令，代码块样式
[使用命令区 600px]
  - 8-10 个命令，卡片列表
```

**策略**：
1. 安装命令单独展示（多种安装方式）
2. 使用命令分两组：基础命令 + README 提取命令
3. 去重后取前 12 个

### 总结图（Summary）

**目标**：显示 8-10 个要点

**布局结构**：
```
[标题区 60px]
[要点列表 500px]
  - 左侧：4-5 个要点
  - 右侧：4-5 个要点（双栏布局）
[CTA 按钮 80px]
[GitHub 数据徽章 60px] ← 新增
[底部链接 30px]
```

**策略**：
1. 合并 AI 生成要点 + README Tips
2. 内容 >6 时启用双栏布局
3. 添加 GitHub 数据徽章填充底部

---

## 实施步骤

1. **添加布局计算工具方法**
   - `_calculate_layout()` - 计算卡片高度和间距
   - `_draw_tech_grid()` - 绘制科技网格背景
   - `_draw_data_badge()` - 绘制 GitHub 数据徽章

2. **优化各图片类型**
   - `create_cover_card()` - 添加数据徽章
   - `create_features_card()` - 动态卡片高度 + 网格背景
   - `create_scenarios_card()` - 双栏布局支持
   - `create_commands_card()` - 分栏布局 + 更多命令
   - `create_summary_card()` - 双栏布局 + 数据徽章

3. **测试验证**
   - 使用 OpenCode 项目测试
   - 检查空间利用率
   - 验证文字不截断

---

## 预期效果

| 指标 | 当前 | 目标 |
|------|------|------|
| 空间利用率 | 25-40% | 75-85% |
| 特点图内容量 | 3-5 个 | 8-12 个 |
| 场景图内容量 | 5 个 | 10-12 个 |
| 命令图内容量 | 3-5 个 | 10-15 个 |
| 总结图内容量 | 4 个 | 8-10 个 |
| 文字截断 | 偶发 | 0 次 |

---

## 验收标准

1. ✅ 所有图片下方空白区域 <20%
2. ✅ 特点图至少显示 8 个特点
3. ✅ 命令图至少显示 10 个命令
4. ✅ 无文字截断现象
5. ✅ 科技网格背景美观不突兀
6. ✅ GitHub 数据徽章清晰展示
