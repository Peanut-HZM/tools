"""内置示例中间件：模型别名

把短模型名（`fast` / `smart`）改写成实际模型，避免在每个 agent 里改配置。
用法：在网关设置里启用插件 `alias`。
"""

ALIASES = {
    "fast": "kimi/k3.1-pro",
    "smart": "zhipu/glm-5.3",
    "cheap": "deepseek/deepseek-v4.1-flash",
}


def handle(body, ctx):
    """把 body['model'] 里的别名换成真实模型名"""
    if not isinstance(body, dict):
        return None
    model = body.get("model")
    if isinstance(model, str) and model in ALIASES:
        patched = dict(body)
        patched["model"] = ALIASES[model]
        return patched
    return None
