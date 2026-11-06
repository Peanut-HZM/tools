# 技术栈识别规则

spec-review-loop 启动时按本规则识别项目技术栈，决定加载哪个栈插件。维度 3、4 的通用核心清单（`checklist-core.md`）始终加载。

## 识别规则

| 特征文件 | 判定栈 | 加载插件 |
|----------|--------|----------|
| `pom.xml` / `build.gradle` / `build.gradle.kts` | Java/Spring | `checklist-java-spring.md` |
| `package.json`（含 vue/react 依赖） | 前端 | `checklist-frontend.md`（暂未提供，缺失时降级） |
| `pyproject.toml` / `requirements.txt` | Python | `checklist-python.md`（暂未提供，缺失时降级） |

## 加载逻辑

1. 在项目根目录检测上述特征文件（可用 `git rev-parse --show-toplevel` 定位根目录，非 git 项目用当前工作目录）。
2. 命中多个特征时，加载所有命中的栈插件。
3. 命中的栈插件文件不存在时，视为未命中该栈。
4. 未命中任何栈插件时，仅执行通用核心清单（维度 3、4），并在报告中提示：
   > 未识别到技术栈插件，仅执行通用审查（维度 3、4）。维度 1、2 标记为 N/A。
5. 维度 1、2 在无栈插件时整体标记为 ⊘ N/A。

## 扩展方式

新增技术栈支持：新建 `checklist-<stack>.md`，并在本文件「识别规则」表新增一行。无需修改 `SKILL.md`。
