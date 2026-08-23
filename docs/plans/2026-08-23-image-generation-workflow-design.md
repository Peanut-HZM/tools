# 4 个 Dify 工作流设计规格

**目的**：为图像生成工具的 4 种 operation 设计具体的工作流节点配置
**适用 spec**：`docs/plans/2026-08-23-image-generation-tool-design.md` §4
**前置依赖**：Dify 已安装插件（参考 spec §C.6）

---

## 公共约定

### 输入变量（每个工作流都接受）

| 变量 | 类型 | 来源 | 说明 |
|---|---|---|---|
| `prompt` | string | 用户输入 | 文本提示词 |
| `model_preference` | enum | 用户选择 | auto / 豆包 / 通义 / 海螺 |
| `reference_image_url` | string | 后端生成 | 参考图 OSS 签名 URL（img2img/inpaint/edit 用） |
| `mask_image_url` | string | 后端生成 | 蒙版图 URL（inpaint 用） |
| `edit_type` | enum | 用户选择 | 仅 upload_edit 用 |

### 输出变量（每个工作流都返回）

| 变量 | 类型 | 说明 |
|---|---|---|
| `image_urls` | array[string] | 生成结果的图片 URL 列表（Dify 给的临时 URL） |
| `model_used` | string | 实际调用的模型（从 Dify 节点传递） |

### 后端约定

- 所有参考图 / 蒙版由后端上传到 OSS，生成 300s 签名 URL 后传给工作流
- 工作流返回的 `image_urls` 由后端下载 → 重新上传到 OSS → 1 小时签名 URL 给前端

---

## Workflow 1: text2img（文生图）

### 基本信息
- **类型**：工作流
- **名称**：`image_gen_text2img`
- **触发**：手动 / API

### 节点流程

```
[开始] → [条件分支 model_preference] → [工具节点] → [代码解析] → [结束]
```

### 详细节点配置

#### 1. 开始节点
```
Inputs:
  prompt: string (必填, max 2000)
  size: enum (1024x1024, 1024x1792, 1792x1024, default: 1024x1024)
  n: int (1-4, default: 1)
  style: enum (natural, vivid, auto, default: auto)
  model_preference: enum (auto, doubao, qwen, hailuo, default: auto)
```

#### 2. 条件分支：按 model_preference 分发

```python
if model_preference == "doubao":
    → 豆包 Seedream AIGC.text_2_image
elif model_preference == "qwen":
    → 通义 AIGC.text_2_image
elif model_preference == "hailuo":
    → 海螺 AIGC.text_to_image
else:  # auto
    → 豆包 Seedream AIGC.text_2_image  # 默认走豆包（最快）
```

#### 3. 工具节点（示例：豆包 Seedream.text_2_image）
```
Tool: sawyer-shi/seedream_aigc.text_2_image
Inputs:
  prompt: {{ start.prompt }}
  size: {{ start.size }}
  watermark: false  # 默认不加水印
  model: "seedream-4-5-250628"  # 默认模型
```

#### 4. 代码节点：解析输出
```python
# 提取图片 URL 和模型名
result = {
    "image_urls": json.loads(text_2_image_output)["images"],
    "model_used": "seedream-4-5-250628"
}
return result
```

#### 5. 结束节点
```
Outputs:
  image_urls: array[string]
  model_used: string
```

---

## Workflow 2: img2img（图生图）

### 节点流程

```
[开始] → [工具节点（下载参考图）] → [工具节点（图生图）] → [代码解析] → [结束]
```

### 详细节点配置

#### 1. 开始节点
```
Inputs:
  prompt: string (必填)
  reference_image_url: string (必填, OSS 签名 URL)
  strength: float (0.0-1.0, default: 0.6, 控制变化强度)
  size: enum (default: 1024x1024)
  model_preference: enum
```

#### 2. 工具节点：图生图（豆包 Seedream 示例）
```
Tool: sawyer-shi/seedream_aigc.image_2_image
Inputs:
  prompt: {{ start.prompt }}
  input_image_file: {{ start.reference_image_url }}
  size: {{ start.size }}
  strength: {{ start.strength }}
  model: "seedream-4-5-250628"
```

注：Dify 工具节点会自动从 URL 下载参考图

#### 3. 结束节点
```
Outputs:
  image_urls: array[string]
  model_used: string
```

---

## Workflow 3: inpaint（局部重绘）

### 节点流程

```
[开始] → [工具节点（局部重绘）] → [结束]
```

### 详细节点配置

#### 1. 开始节点
```
Inputs:
  prompt: string (必填)
  image_url: string (必填, 待编辑图)
  mask_url: string (必填, 蒙版图, 白色=重绘区域)
  size: enum
  model_preference: enum
```

#### 2. 工具节点：局部重绘

**问题**：当前已装的 3 个插件（Seedream / TongYi / Hailuo）**不一定都支持 inpaint**。
具体支持情况需要插件文档确认。

**降级方案**：如果插件不支持 inpaint，自动用 img2img + 蒙版叠加的近似方案：
- img2img 生成新图
- 用蒙版 mask 把原图未蒙版区域合成回去

#### 3. 结束节点
```
Outputs:
  image_urls: array[string]
  model_used: string
```

---

## Workflow 4: upload_edit（上传编辑）

### 子类型

| edit_type | 含义 | 推荐插件方法 |
|---|---|---|
| upscale | 超分辨率（2x/4x） | Stability / Seedream（部分支持） |
| denoise | 降噪 | Hailuo AIGC / 第三方 |
| relight | 重打光 | （Dify 插件较少，可能需要自建 HTTP 工具节点）|
| style_transfer | 风格迁移 | Hailuo AIGC |
| background_remove | 抠背景 | Stability / 第三方 |

### 节点流程

```
[开始] → [条件分支 edit_type] → [不同工具节点] → [结束]
```

### 详细节点配置

#### 1. 开始节点
```
Inputs:
  image_url: string (必填)
  edit_type: enum (upscale, denoise, style_transfer, background_remove)
  prompt: string (optional, 部分 edit 类型需要)
```

#### 2. 条件分支：按 edit_type 分发

```python
if edit_type == "upscale":
    → Stability.upscale (或 sawyer-shi/seedream_aigc 是否有 upscale)
elif edit_type == "denoise":
    → sawyer-shi/hailuo_aigc.denoise (待确认)
elif edit_type == "style_transfer":
    → sawyer-shi/hailuo_aigc.style_transfer (待确认)
elif edit_type == "background_remove":
    → 第三方插件或 HTTP 工具节点
```

> **说明**：当前国内主流图像生成插件的 edit 能力覆盖不完整，部分 edit_type 可能需要后续通过自建 HTTP 工具节点（Dify 工作流支持添加 HTTP 节点直接调厂商 API）。

---

## 工作流创建步骤

### 1. 进入 Dify 工作室
访问 `https://dify.peanuthzm.com.cn` → 工作室 → 创建空白应用 → 工作流

### 2. 配置 4 个工作流
按上述规格逐个创建。命名规范：`image_gen_<operation>`

### 3. 测试每个工作流
- 用「运行」按钮触发
- 检查输出变量 `image_urls` 是否有 1+ 张图
- 检查 `model_used` 是否正确填充

### 4. 获取 4 个 workflow IDs
每个工作流的 URL 里有 ID，形如 `wf_xxxxxxxxxxxx`

### 5. 写入本应用 `.env`
```bash
DIFY_WORKFLOW_TEXT2IMG=wf_xxx
DIFY_WORKFLOW_IMG2IMG=wf_yyy
DIFY_WORKFLOW_INPAINT=wf_zzz
DIFY_WORKFLOW_UPLOAD_EDIT=wf_aaa
```

---

## 失败降级方案

### 1. 插件不支持某 operation
如 Seedream 不支持 inpaint → 自动降级到 img2img

### 2. 模型调用超时
- Dify 工作流超时 60s（可调到 120s）
- 后端检测超时 → 释放配额 + 写 failed 历史

### 3. 全部模型不可用
- 启动 DegradationService（spec §9）
- 前端显示「服务暂时不可用」
- 自动恢复后通知用户

---

## 后续工作

1. 等待插件安装完成（25+ 国内主流）
2. 在 Dify UI 创建 4 个工作流（人工操作）
3. 测试每个工作流 + 记录 workflow_id
4. 配置本应用 `.env`
5. 后端实现 DifyClient（spec §5.2）
6. 实现 ImageGenService 编排（spec §5.3）
