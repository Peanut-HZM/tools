"""
图像生成后端 strategy 模块

两条路径并存：
  - DifyBackend: 调 Dify 工作流（保留）
  - SelfDevelopedBackend: 自研 Agent（新）

通过 BackendRegistry 按请求参数 backend 分发。
模型配置统一从 /admin/llm-configs 读取（LLMProvider + LLMModel）。
"""
