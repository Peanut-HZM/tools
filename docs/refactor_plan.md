# Umi-OCR 功能迁移与重构计划

## 1. 项目背景与现状

**现状：**
- **后端 (Backend)**: Python (FastAPI), 依赖 `app/config`, `app/routes`, `app/services`.
- **前端 (Frontend)**: React + TypeScript + Vite.
- **目标**: 将项目根目录下的 `umi-ocr` (Java Spring Boot + Vue Web 项目) 的核心功能（OCR + FunASR + QR Code）迁移到当前 Web 项目中。

**说明：**
项目根目录下的 `umi-ocr` 是一个基于 Java Spring Boot 和 Vue 的 Web 项目。我们的目标是将其功能迁移到当前的 Python (FastAPI) + React 架构中。虽然参考项目是 Java 实现，但鉴于 OCR 和 ASR 的核心库 (PaddleOCR, FunASR) 在 Python 生态中最为成熟且原生支持，**最佳方案是在现有 Python 后端中直接集成这些功能**。这将避免跨语言调用的性能损耗和架构复杂性，同时保持项目技术栈的统一。我们将参考原 Java 项目的业务逻辑和接口设计，遵循 Controller/Service 分层规范进行迁移。

## 2. 功能分析与需求

### 2.1 OCR 功能 (参考 Umi-OCR)
- **核心能力**: 基于 PaddleOCR 的文字检测与识别。
- **输入方式**:
  - 单张图片上传/粘贴。
  - 批量图片上传。
  - 截图（前端实现截图后上传）。
- **处理逻辑**:
  - 文本检测 (Detection)。
  - 文本识别 (Recognition)。
  - 文本方向分类 (Classification)。
- **后处理**:
  - 忽略区域（根据配置忽略特定坐标范围的文字）。
  - 排版解析（段落合并）。
- **配置**: 沿用 Umi-OCR 的配置项（语言、模型参数等）。

### 2.2 语音识别 (FunASR)
- **核心能力**: 基于阿里 FunASR (如 Paraformer 或 SenseVoice) 的语音转文字。
- **输入方式**: 音频文件上传 (mp3, wav, m4a 等)。
- **输出**: 识别出的文本及时间戳（可选）。

### 2.3 二维码工具 (QR Code)
- **核心能力**: 二维码生成与识别。
- **生成功能**:
  - 支持文本/URL 编码。
  - 纠错级别 (L, M, Q, H)。
  - 自定义尺寸与边距。
  - 输出 PNG 图片。
- **识别功能**:
  - 上传图片识别二维码内容。
  - 支持多种图片格式。

### 2.4 文档 OCR (Document OCR)
- **核心能力**: PDF 文档文字识别。
- **处理逻辑**:
  - PDF 转图片。
  - 对每一页进行 OCR。
  - 结果合并导出 (TXT/Markdown/PDF)。

## 3. 架构设计

### 3.1 后端架构 (Python/FastAPI)

遵循 Controller (Route) -> Service -> Model 的分层架构。

**目录结构变更**:
```
backend/app/
├── config/
│   └── ocr_config.py        # OCR/ASR 相关配置
├── models/
│   ├── ocr_models.py        # OCR 请求/响应模型 (DTO)
│   ├── asr_models.py        # ASR 请求/响应模型 (DTO)
│   └── qrcode_models.py     # 新增: 二维码请求/响应模型 (DTO)
├── routes/
│   ├── ocr_routes.py        # OCR 接口
│   ├── asr_routes.py        # ASR 接口
│   └── qrcode_routes.py     # 新增: 二维码接口
├── services/
│   ├── ocr_service.py       # PaddleOCR 封装与业务逻辑 (含文档处理)
│   ├── asr_service.py       # FunASR 封装与业务逻辑
│   └── qrcode_service.py    # 新增: 二维码生成与识别逻辑
└── utils/
    └── ocr_utils.py         # 图片预处理、后处理工具
```

**依赖库**:
- `paddlepaddle`, `paddleocr` (OCR)
- `funasr`, `modelscope`, `torch` (ASR)
- `numpy`, `opencv-python` (图像处理)
- `qrcode`, `pyzbar` (二维码处理)
- `pdf2image` (PDF 处理)

**接口定义**:
1.  `POST /api/ocr/predict`: 接受图片，返回识别结果。
2.  `POST /api/asr/predict`: 接受音频，返回识别文本。
3.  `POST /api/qrcode/generate`: 生成二维码。
4.  `POST /api/qrcode/scan`: 识别二维码。
5.  `POST /api/ocr/doc`: 文档 OCR (PDF)。

### 3.2 前端架构 (React/TS)

**目录结构变更**:
```
frontend/src/
├── components/
│   └── Tools/
│       ├── OCR/                 # OCR 工具组件
│       │   ├── OCRTool.tsx
│       │   ├── ImagePreview.tsx
│       │   └── ResultDisplay.tsx
│       ├── ASR/                 # 语音识别工具组件
│       │   ├── ASRTool.tsx
│       │   └── AudioUploader.tsx
│       └── QRCode/              # 新增: 二维码工具组件
│           ├── QRCodeTool.tsx
│           ├── QRCodeGenerator.tsx
│           └── QRCodeScanner.tsx
├── api/
│   ├── ocrApi.ts                # OCR 接口调用
│   ├── asrApi.ts                # ASR 接口调用
│   └── qrcodeApi.ts             # 新增: 二维码接口调用
└── types/
    ├── ocr.ts                   # 类型定义
    ├── asr.ts                   # 类型定义
    └── qrcode.ts                # 新增: 类型定义
```

## 4. 迁移与重构任务列表

### 阶段一：环境与配置 (Backend)
1.  [x] 更新 `requirements.txt` 添加 `paddleocr`, `funasr` 等依赖。
2.  [x] 创建 `app/config/ocr_config.py`，移植 Umi-OCR 的默认配置。
3.  [x] 创建 `app/models/ocr_models.py` 和 `app/models/asr_models.py` 定义 Request/Response。
4.  [ ] 更新 `requirements.txt` 添加 `qrcode`, `pyzbar`, `pdf2image`, `Pillow`。
5.  [ ] 创建 `app/models/qrcode_models.py`。

### 阶段二：后端核心服务 (Backend)
6.  [x] 实现 `app/services/ocr_service.py`: 初始化 PaddleOCR，实现识别逻辑。
7.  [x] 实现 `app/services/asr_service.py`: 初始化 FunASR，实现语音识别逻辑。
8.  [x] 实现 `app/routes/ocr_routes.py`: 封装 OCR 接口，鉴权。
9.  [x] 实现 `app/routes/asr_routes.py`: 封装 ASR 接口，鉴权。
10. [x] 在 `app/main.py` 中注册新路由。
11. [ ] 实现 `app/services/qrcode_service.py`: 二维码生成与识别。
12. [ ] 实现 `app/routes/qrcode_routes.py`: 二维码接口。
13. [ ] 扩展 `app/services/ocr_service.py` 支持 PDF 文档处理。

### 阶段三：前端界面实现 (Frontend)
14. [x] 创建 `src/api/ocrApi.ts` 和 `src/api/asrApi.ts`。
15. [x] 实现 `OCRTool.tsx`: 支持图片上传、粘贴、显示识别结果。
16. [x] 实现 `ASRTool.tsx`: 支持音频上传、显示识别结果。
17. [x] 更新首页工具列表，替换/添加入口。
18. [ ] 创建 `src/api/qrcodeApi.ts`。
19. [ ] 实现 `QRCodeTool.tsx` (含生成器和扫描器)。
20. [ ] 更新首页工具列表，添加二维码工具。

### 阶段四：验证与优化
21. [ ] 验证 OCR 准确性和性能。
22. [ ] 验证 ASR 准确性和性能。
23. [ ] 验证二维码生成与识别功能。
24. [ ] 优化 UI/UX (加载状态、错误处理)。

## 5. 配置详情 (参考 Umi-OCR)

**OCR Config**:
```python
{
    "use_gpu": false,
    "lang": "ch",
    "enable_mkldnn": true,
    "use_angle_cls": true,
    "limit_type": "max",
    "limit_side_len": 960,
    "det_db_thresh": 0.3,
    "det_db_box_thresh": 0.6,
    "det_db_unclip_ratio": 1.5,
    "use_dilation": false,
    "score_thresh": 0.5
}
```
这些配置将通过 `app/config/ocr_config.py` 管理。
