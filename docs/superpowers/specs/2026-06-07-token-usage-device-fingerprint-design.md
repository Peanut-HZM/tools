---
author: Peanut
created_at: 2026-06-07
purpose: Token Usage 设备维度统计引入设备指纹，解决同一物理设备因 UUID 变化产生重复记录的问题
---

# Token Usage 设备指纹识别与合并设计

## 一、背景与问题

当前 Token Usage 使用 UUID 作为 `device_id`，持久化在本地 `~/.tools/device_id` 文件中。当同一台物理设备发生以下情况时，会产生多个设备记录：

- 重装系统
- 删除 `~/.tools` 目录
- Docker 容器重建
- 在多个 Pod 中运行

这导致设备维度统计中出现多个同名设备（如截图中多个 `root@k8s-master`），用户无法区分，数据也难以聚合。

## 二、设计目标

1. 引入稳定的设备指纹作为辅助识别依据，减少同一物理设备产生多个记录的情况。
2. 在检测到指纹匹配时提示用户，由用户决定是否复用已有设备。
3. 保留现有 UUID 作为主键，保证向后兼容。
4. 提供手动合并功能，处理历史重复设备数据。
5. 前端明细表格中增加设备名称列，饼图/筛选中统一展示设备名称而非 UUID。

## 三、架构概述

核心思路：**不替换现有 `device_id`，而是新增 `device_fingerprint` 作为辅助识别依据**。

```
┌─────────┐
│ 生成UUID │
│(device_id)│
└────┬────┘
     │
┌────┴──────┐
│ 生成本地指纹 │
│(MAC哈希+主机名)│
└────┬──────┘
     │
┌────┴──────┐
│ 后端检查是否 │
│ 匹配已有设备 │
└────┬──────┘
     │
┌────┴───────────────┐
│ 匹配到已有设备？     │
└────┬───────────────┘
     │
是 ┌─┴─┐ 否
   ↓   ↓
提示用户复用  创建为新设备
或创建新设备
```

关键设计点：

- `device_id` 仍是 UUID，作为数据主键和记录关联字段。
- 新增 `device_fingerprint` 存储本地生成的哈希指纹。
- 指纹匹配触发用户确认，避免自动误判。
- 历史重复设备通过手动合并功能处理。
- 引入 `device_id_alias` 表实现设备映射，不直接修改历史数据。

## 四、数据模型变更

### 4.1 `device_registry` 表新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `device_fingerprint` | `String(256)` | `NULL` | 设备指纹（MAC 哈希 + 主机名等的组合哈希值） |
| `fingerprint_version` | `Integer` | `0` | 指纹算法版本，方便未来升级算法时兼容旧数据 |
| `id_type` | `String(16)` | `'uuid'` | 标识类型：`hardware`（基于硬件） / `uuid`（纯 UUID 降级） |

### 4.2 `token_usage_records` 表

保持不变，继续使用 `device_id` 作为外键。

### 4.3 新增 `device_id_alias` 表

用于设备复用/合并时的 device_id 映射。

| 字段 | 类型 | 说明 |
|------|------|------|
| `alias_device_id` | `String(128)` | 当前设备 UUID（主键） |
| `canonical_device_id` | `String(128)` | 归属到的主设备 UUID |
| `user_id` | `String(64)` | 用户 ID |
| `created_at` | `DateTime` | 创建时间 |

### 4.4 新增 `device_merge_log` 表

用于合并审计和撤销支持。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `BigInteger` | 自增主键 |
| `user_id` | `String(64)` | 用户 ID |
| `source_device_id` | `String(128)` | 被合并的设备 UUID |
| `target_device_id` | `String(128)` | 合并到的目标设备 UUID |
| `merged_at` | `DateTime` | 合并时间 |
| `record_count` | `Integer` | 合并影响的历史记录数 |

## 五、后端流程设计

### 5.1 设备指纹生成

在 `backend/app/utils/device_id.py` 中新增 `get_device_fingerprint()` 函数：

```python
def get_device_fingerprint() -> tuple[str, str]:
    """
    获取设备指纹。

    Returns:
        (fingerprint, id_type)
        id_type: 'hardware' 表示基于硬件特征生成；
                 'uuid' 表示硬件特征获取失败，降级为 UUID。
    """
```

生成逻辑：

1. 获取第一个非虚拟网卡的 MAC 地址。
2. 获取主机名、用户名。
3. 将 MAC + 主机名 + 固定 salt 拼接后进行 SHA256 哈希。
4. 如果 MAC 无法获取，则使用 UUID 作为指纹，并标记 `id_type='uuid'`。

隐私保护：

- MAC 地址仅在本地做哈希，不上传原始值。
- 指纹中不包含可逆信息。
- 固定 salt 仅用于防止彩虹表，不关联用户身份。

### 5.2 同步时检查设备指纹

每次同步流程：

1. 客户端获取本地 `device_id`（UUID）和 `device_fingerprint`。
2. 调用同步接口时，将 `device_fingerprint` 和 `id_type` 一并上传。
3. 后端：
   1. 用 `device_id` 查找 `device_registry`。
   2. 若设备已存在，更新其指纹信息。
   3. 若设备不存在，用 `device_fingerprint` 查找同一用户下其他设备。
   4. 若指纹匹配到已有设备，返回 `fingerprint_match` 提示，包含匹配到的设备信息。
   5. 若未匹配，注册为新设备。

### 5.3 复用设备的实现方式

使用 `device_id_alias` 表实现映射，不直接修改历史数据。

**用户选择"复用已有设备"时**：

1. 后端在 `device_id_alias` 中建立映射：`alias_device_id = 当前设备 UUID`，`canonical_device_id = 已有设备 UUID`。
2. 后续同步时，当前设备的数据仍用其 UUID 写入，但查询统计时按 `canonical_device_id` 聚合。

**查询时聚合逻辑**：

```sql
SELECT 
    COALESCE(a.canonical_device_id, r.device_id) AS agg_device_id,
    SUM(r.total_tokens) AS total_tokens
FROM token_usage_records r
LEFT JOIN device_id_alias a ON r.device_id = a.alias_device_id
GROUP BY agg_device_id
```

## 六、前端交互设计

### 6.1 同步时指纹匹配提示

当后端检测到当前设备指纹匹配到已有设备时，前端弹出确认对话框：

```
┌─────────────────────────────────────┐
│  检测到已存在的设备                  │
├─────────────────────────────────────┤
│  当前设备：root@k8s-master           │
│  匹配到已有设备：root@k8s-master     │
│                                     │
│  这可能是同一台设备。请选择：         │
│                                     │
│  [ 复用已有设备（合并统计） ]         │
│  [ 创建为新设备 ]                    │
└─────────────────────────────────────┘
```

### 6.2 设备管理页面

在 Token Usage 页面增加"设备管理"入口，功能包括：

- 列出当前用户所有设备。
- 显示每个设备的 `device_id`、默认名称、自定义名称、指纹类型。
- 支持重命名（已有功能保留）。
- 支持手动合并两个或多个设备。
- 显示"疑似重复设备"提示（基于 fingerprint 匹配）。
- 支持一键合并同名设备。

### 6.3 明细表格增加设备名称列

Token Usage 详情表格新增"设备名称"列，显示优先级：

1. 用户自定义名称（`display_name`）
2. 默认名称（`username@hostname`）
3. `device_id`（UUID）

该列支持排序和筛选。

### 6.4 饼图与筛选

设备维度饼图和设备筛选下拉框统一使用解析后的设备名称，不再显示 UUID。

## 七、设备合并机制

### 7.1 自动识别

同步时后端检测指纹匹配，仅提示用户，不自动合并。

### 7.2 手动合并

操作流程：

1. 用户在设备管理页面选择两个或多个设备。
2. 指定一个作为主设备（目标）。
3. 点击合并。
4. 后端执行：
   - 在 `device_id_alias` 表中建立映射。
   - 将被合并设备在 `device_registry` 中的状态更新为 `merged`（可选）。
   - 记录 `device_merge_log`。
5. 查询时按 `canonical_device_id` 聚合。

### 7.3 合并撤销

支持从 `device_id_alias` 中删除映射，恢复为独立设备。

### 7.4 历史重复数据处理

对于已有数据中的重复设备（如多个 `root@k8s-master`），提供：

- 一键合并"同名设备"。
- 用户手动选择设备合并。

## 八、数据迁移策略

### 8.1 现有设备数据

- 现有 `device_registry` 记录的 `device_fingerprint` 为空，`fingerprint_version=0`，`id_type='uuid'`。
- 不需要一次性回填所有历史设备的指纹。
- 设备下次同步时自动补充指纹信息。

### 8.2 数据库迁移

需要两个 Alembic 迁移：

1. **扩展 `device_registry`**：新增 `device_fingerprint`、`fingerprint_version`、`id_type` 字段。
2. **创建新表**：创建 `device_id_alias` 和 `device_merge_log` 表。

### 8.3 向后兼容

- 不修改 `token_usage_records` 表结构。
- 查询时使用 `LEFT JOIN device_id_alias`，无映射的设备保持原样。
- 现有 API 返回格式基本不变，仅新增可选字段。
- 旧版本客户端可以忽略 `fingerprint_match` 提示。

## 九、隐私安全

- MAC 地址不上传原始值，仅上传本地哈希后的指纹。
- 指纹字段仅用于同一用户下的设备识别，不用于其他目的。
- 用户删除账号时，设备指纹一同删除。
- 系统自动识别只是提示，用户可选择不合并。

## 十、错误处理

| 场景 | 处理 |
|------|------|
| 无网卡/权限不足 | 降级为 UUID，`id_type='uuid'` |
| 获取 MAC 部分成功 | 用可获取的信息生成指纹，标记 `id_type='hardware'` |
| 主机名为空 | 用 `unknown` 占位 |
| 两台不同机器指纹相同（极低概率） | 仅作为"疑似匹配"提示，不自动合并 |
| 合并目标设备已被删除 | 返回错误，要求重新选择 |
| 合并过程中同步新数据 | 使用数据库事务保证一致性 |
| 用户误合并 | 提供"撤销合并"功能 |

## 十一、接口变更

### 11.1 同步接口（POST /token-usage/sync）

**请求体新增可选字段**：

```json
{
  "device_fingerprint": "sha256_hash_value",
  "id_type": "hardware"
}
```

**响应新增可选字段**：

```json
{
  "fingerprint_match": {
    "matched_device_id": "existing_uuid",
    "matched_device_name": "root@k8s-master",
    "message": "检测到已存在的设备"
  }
}
```

### 11.2 新增设备复用接口（POST /token-usage/devices/alias）

请求体：

```json
{
  "alias_device_id": "current_uuid",
  "canonical_device_id": "existing_uuid"
}
```

### 11.3 新增设备合并接口（POST /token-usage/devices/merge）

请求体：

```json
{
  "source_device_ids": ["uuid1", "uuid2"],
  "target_device_id": "uuid_main"
}
```

### 11.4 新增合并撤销接口（DELETE /token-usage/devices/alias/{alias_device_id}）

撤销某个设备的复用/合并映射。

## 十二、验收标准

- [ ] 同一物理设备在删除 `~/.tools/device_id` 后重新同步，能被识别为疑似已有设备。
- [ ] 用户选择"复用已有设备"后，历史统计按已有设备聚合，不再出现重复项。
- [ ] 用户选择"创建为新设备"后，新数据作为独立设备统计。
- [ ] 设备管理页面支持手动合并和撤销合并。
- [ ] Token Usage 明细表格中正常显示设备名称列。
- [ ] 设备维度饼图和筛选下拉框显示设备名称而非 UUID。
- [ ] 无法获取 MAC 地址时，系统正常降级为 UUID，不影响使用。
