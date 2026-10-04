# 设计文档：小程序游戏中心 + 多人联机狼人杀

- 日期：2026-10-04
- 状态：待用户审阅（未批准实现）
- 范围：`mini-program/`（新分包 `package-game`）+ `backend/`（狼人杀服务端）

## 1. 背景与目标

在小程序中新增「游戏中心」功能入口，并在其中实现第一款游戏：**多人联机狼人杀**。

要求（来自用户原始需求）：
1. 仅在小程序功能中添加「游戏中心」；
2. 游戏中心内添加狼人杀；
3. 规则与实现方式必须参考市面上主流狼人杀游戏；
4. 必须提供合适的卡牌图片（允许联网搜索素材）；
5. 完整实现：根据人数自定义配置、可开房间、多人一起玩。

**待确认假设（用户未及时答复，按以下判断执行，审阅时可推翻）：**
- A1. 形态为**线上联机版**（类比「狼人杀官方 / 会玩」App）：各自手机加入房间，服务端自动主持（上帝），白天文字发言 + 投票。排除了「面杀助手」形态。
- A2. 玩家即现有注册用户（JWT 登录），不引入微信 openid / 微信登录。
- A3. V1 不做语音、不做警长竞选（上警）、不做观战（见 Non-Goals）。
- A4. 胜负规则固定为**屠边局**（主流 12 人标准局规则），不做屠城局。

## 2. Non-Goals（V1 明确不做）

| 不做 | 原因 |
|---|---|
| 实时语音 / 语音转文字 | 小程序实时语音链路复杂度高，与核心玩法正交 |
| 警长竞选（上警、警徽流） | 独立子系统，市面休闲局常不开；留作迭代 |
| 观战模式、录像回放 | 非核心 |
| AI 机器人补位 | 用「超时托管」代替（见 6.5） |
| 狼王 / 白狼王、骑士等进阶角色 | V1 角色集：狼人、村民、预言家、女巫、猎人、守卫、白痴 |
| 跨端（PC 端 frontend）参与游戏 | 仅小程序端 |

## 3. 游戏规则规范（对齐市面主流）

参考资料：知乎《狼人杀配板子的基本理论》、3DM 法官主持顺序、小米游戏 9 人局教学、什么值得买板子进阶路线（链接见文末）。

### 3.1 预置板子（屠边局，6–12 人）

| 板子名 | 人数 | 狼人 | 预言家 | 女巫 | 猎人 | 守卫 | 白痴 | 村民 |
|---|---|---|---|---|---|---|---|---|
| 6人新手 | 6 | 2 | 1 | 1 | – | – | – | 2 |
| 8人进阶 | 8 | 2 | 1 | 1 | 1 | – | – | 3 |
| 9人经典 | 9 | 3 | 1 | 1 | 1 | – | – | 3 |
| 10人守卫 | 10 | 3 | 1 | 1 | 1 | 1 | – | 3 |
| 12人标准 | 12 | 4 | 1 | 1 | 1 | – | 1 | 4 |

（12 人标准为市面主流「预女猎白」板：狼 4 + 神 4（预女猎白）+ 民 4 = 12；含守卫的 12 人局可用自定义板子组建，守卫替换白痴位。）

自定义板子：6–12 人任选角色数量，服务端校验（人数守恒、狼 ≥1、女巫/预言家 ≤1、白痴 ≤1、守卫 ≤1、猎人 ≤1；神民可缺但会提示体验风险，仅警告不禁止）。

### 3.2 角色技能（主流规则）

- **狼人**：夜晚与狼队友互认，共同选择刀杀一名存活玩家。
- **预言家**：每晚查验一名玩家阵营（好人 / 狼人）。
- **女巫**：解药、毒药各一瓶，**同一晚只能使用一瓶**；
  - 手中有解药时，夜晚被告知狼人刀口；解药已用后不再告知刀口；
  - 自救规则为板子配置项 `witch_self_rescue: never | first_night | always`，默认 `never`（市面主流标准）。
- **猎人**：被狼刀死或被投票放逐时可开枪带走一名玩家；**被毒死（含奶穿死）不能开枪**；超时可放弃开枪。
- **守卫**：每晚守护一名玩家（含自己）抵御狼刀；**不能连续两晚守护同一人**；
  - 「奶穿」：同一晚被守卫守护且被女巫解药救的玩家死亡，配置项 `witch_guard_conflict`，默认开启（市面主流）。
- **白痴**：被投票放逐时翻牌亮明身份并免死，此后保留发言权但**失去投票权**；夜晚被刀、被毒正常死亡（翻牌后不再触发）。白痴计入神职阵营（屠边判定）。
- **村民**：无技能。

### 3.3 流程（服务端为唯一权威「法官」）

夜晚顺序（缺角色的板子自动跳过该阶段）：
**守卫 → 狼人 → 预言家 → 女巫**；猎人无夜晚行动（被动）。

白天：
1. 天亮公布死讯（不公布死因与角色）；首夜死讯照常公布。
2. **发言顺序**：从本夜死者座位的下一位开始顺时针轮流发言（多死者时以死讯中第一位死者的下一位为准）；无死者时从上一发言轮末尾的下一座继续（首日无死者从 1 号开始）。每人限时（默认 60s，房主可配 30/60/90/120s）。
3. **投票**：所有存活且有投票权玩家限时投票（默认 30s），禁止投自己，可弃票；超时视为弃票。
   - 平票 → 平票者依次 PK 发言（各 30s）→ 全场只能投平票者或弃票 → 再平票则**无人出局**。
4. 放逐者留遗言（限时 30s，可跳过）；若放逐票命中白痴：翻牌亮明身份、免死、失去投票权（未死亡，故无遗言，仍保留后续白天发言权），本日无人出局。
5. 出局翻牌规则：**暗牌制**（不公布出局者角色，白痴技能触发除外）；对局结束全部翻牌。
6. 猎人满足开枪条件则进入开枪阶段，枪杀目标当场死亡（不翻牌、无遗言）。

**遗言权**（主流规则）：首夜死亡者有遗言；被放逐者有遗言；第二夜起的夜晚死亡、枪杀死亡无遗言。

### 3.4 胜负判定（屠边）

- **好人胜**：所有狼人出局。
- **狼人胜**：所有神职出局，或所有村民出局。
- 即时判定：存活狼人数 ≥ 存活好人总数 → 狼人胜。
- 判定时点：每次死亡结算后（夜晚天亮前、放逐/枪杀后）即时检查。

### 3.5 对局可配置项（房主在创建/等待页设置）

发言时长、投票时长、女巫自救、奶穿开关。板子（预置或自定义）。

## 4. 总体架构

```
小程序(Taro)                         后端(FastAPI, 单进程)
┌─────────────────┐   HTTP/JWT    ┌──────────────────────────┐
│ package-game     │ ────────────▶ │ /api/games/werewolf/*    │
│  游戏中心/大厅/   │               │   创建/加入/离开/快照      │
│  对局页          │               ├──────────────────────────┤
│                  │   WebSocket   │ werewolf/manager.py      │
│  stores/werewolf │ ◀───────────▶ │  (room_id→GameRoom 内存)  │
│  services/*Ws    │  个人视角推送  │ werewolf/engine.py       │
└─────────────────┘               │  (对局状态机, 服务端权威)   │
                                  │ 对局记录 → SQLAlchemy/Alembic
                                  └──────────────────────────┘
```

核心原则：**服务端权威**（市面联机狼人杀的标准实现方式）。所有秘密信息（身份、刀口、查验结果）只存在于服务端；WS 推送按「公共事件 + 个人视角私有消息」区分，客户端只做渲染，杜绝作弊面。

运行时房间状态存内存（`RoomManager` 单例）；对局结果落库。服务重启丢失进行中对局可接受（个人项目、单进程 `uvicorn --reload`），spec 明示此取舍。

## 5. 后端设计

### 5.1 模块划分

```
backend/app/services/werewolf/
  roles.py     # 角色枚举、技能元数据
  boards.py    # 预置板子定义 + 自定义板子校验
  room.py      # GameRoom：玩家/连接登记、广播（公共 vs 个人视角过滤）
  engine.py    # WerewolfEngine：对局状态机（阶段流转/行动结算/胜负）
  manager.py   # RoomManager 单例：room_id → GameRoom，超时回收
backend/app/routes/werewolf.py    # HTTP + WS 路由（prefix /api/games/werewolf，沿用 app/routes 自带 prefix 风格）
backend/app/schemas/werewolf.py   # Pydantic 请求/响应模型
backend/app/models/werewolf.py    # ORM：对局记录表
backend/alembic/versions/xxxx_add_werewolf_tables.py
backend/tests/test_werewolf_*.py  # pytest
```

### 5.2 HTTP API（均需 JWT，风格对齐现有 `app/routes/*.py`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/games/werewolf/boards` | 预置板子 + 可配置项元数据（前端不写死规则） |
| POST | `/api/games/werewolf/rooms` | 创建房间（body：板子/配置）→ `{room_id}`（6 位数字），创建者=房主 |
| POST | `/api/games/werewolf/rooms/{room_id}/join` | 加入（仅 WAITING、未满员） |
| POST | `/api/games/werewolf/rooms/{room_id}/leave` | 离开（WAITING 移除；对局中=逃跑标记） |
| GET | `/api/games/werewolf/rooms/{room_id}` | 个人视角全量快照（断线重连兜底） |
| WS | `/api/games/werewolf/rooms/{room_id}/ws?token=<JWT>` | 对局实时通道（token 查询参认证，沿用 openclaw_ws 先例） |

### 5.3 对局状态机（engine.py）

```
WAITING → DEALING
  → NIGHT_GUARD → NIGHT_WEREWOLF → NIGHT_SEER → NIGHT_WITCH
  → DAWN(死讯) → HUNTER_SHOT?(夜刀死亡的猎人私下询问开枪) → [WIN_CHECK]
  → DAY_SPEECH(轮流,每人限时) → DAY_VOTE(30s)
      → 平票: PK_SPEECH → DAY_VOTE_PK → (再平: 无人出局)
  → EXILE(遗言/白痴翻牌) → HUNTER_SHOT?(被放逐猎人开枪) → [WIN_CHECK]
  → 回到 NIGHT_* (day+1) 或 → RESULT(结算翻牌, 落库)
房主可 RESULT → 再来一局(重新 DEALING) / 解散
```

- 阶段推进条件：全部应行动玩家已提交 / 超时到期 / 发言轮流结束。二者取先。
- 每阶段下发 `deadline`（Unix 秒），客户端渲染倒计时；服务端 `asyncio` 定时器为真实推进依据。
- 超时托管默认值：守卫不守、预言家不验、女巫不用药、猎人不开枪、投票弃票、发言自动结束；**狼人全部超时则随机刀一名存活玩家**（避免死锁）。

### 5.4 WS 协议（前后端契约）

客户端 → 服务端：
```jsonc
{"type":"act","action":"guard_protect|werewolf_kill|seer_check|witch_save|witch_poison|vote|hunter_shot","target":3}
{"type":"speech","content":"我是预言家，验过3号好人"}   // 仅 DAY_SPEECH/PK_SPEECH 且轮到自己
{"type":"last_words","content":"..."}                 // 遗言，限时
{"type":"skip"}                                        // 放弃可选行动(用药/开枪/遗言)
{"type":"ping"}
```

服务端 → 客户端：
```jsonc
{"type":"hello","state":{...个人视角快照}}              // WS 建立后立即下发
{"type":"state","state":{...}}                          // 重连重同步
{"type":"phase","phase":"NIGHT_WEREWOLF","day":1,"deadline":1728000000,
 "you":{"acting":true,"can":["werewolf_kill","skip"]}}
{"type":"event","text":"天亮了，昨夜 3 号、7 号死亡"}     // 公共事件流(带 id 供去重)
{"type":"speech","seat":3,"nickname":"阿花","content":"..."}
{"type":"private","kind":"role","role":"WEREWOLF","mates":[2,5]}      // 仅自己可见
{"type":"private","kind":"seer_result","target":4,"is_werewolf":false}
{"type":"private","kind":"witch_victim","target":6}
{"type":"votes","detail":[{"voter":1,"target":5},{"voter":2,"target":null}],"exiled":5}
{"type":"game_over","winner":"VILLAGER","reveal":[{"seat":1,"role":"WEREWOLF","alive":false},...]}
{"type":"error","code":"NOT_YOUR_TURN","message":"还没轮到你行动"}
{"type":"pong"}
```

个人视角快照 `state`：
```jsonc
{
  "phase":"DAY_SPEECH","day":1,"deadline":1728000000,
  "players":[{"seat":1,"nickname":"...","alive":true,"connected":true,"escaped":false},...],
  "you":{"seat":2,"role":"SEER","mates":null,"can_vote":true,
         "witch":{"save":true,"poison":true}},   // 仅含与自己相关的能力状态
  "log":[{"id":12,"text":"..."}],                 // 公共事件
  "speeches":[{"seat":1,"nickname":"...","content":"..."}],
  "votes":[...]                                   // 已结束的投票记录
}
```

### 5.5 数据模型（对局记录落库）

- `werewolf_game_records`：`id, room_id, board_name, player_count, winner, day_count, duration_seconds, config(JSON), created_at`
- `werewolf_game_record_players`：`id, record_id(FK), user_id, nickname, role, alive_at_end, is_winner`
- 落库时点：对局结束（RESULT）一次性写入。房间运行时状态**不落库**。

### 5.6 连接与房间生命周期

- 每玩家在同一房间仅允许一条 WS（新连挤旧连）。
- WS 断开：座位保留 60s 等待重连；期间该玩家行动全部按托管处理，不阻塞推进。60s 未归 → 标记 `escaped`（身份/座位保留，托管直到对局结束）。
- 房主（WAITING 阶段）：踢人、改配置、开始、解散；对局中房主掉线不转移权限（RESULT 后仍可再来一局）。
- 回收：WAITING/RESULT 状态且无任何连接持续 10 分钟 → 解散并从 manager 移除；对局进行中的房间不回收（有托管兜底）。
- 心跳：客户端 25s 一次 `ping`，服务端 60s 未收到任何消息视为断开。

## 6. 前端设计（mini-program）

### 6.1 分包与页面

```
mini-program/src/package-game/            # 新增 subPackage（预估 <1.5MB 含图片）
  pages/game-center/index.*               # 游戏中心：游戏列表（狼人杀 + 占位卡片）
  pages/werewolf/index.*                  # 大厅：创建房间(板子选择/配置) / 输入房号加入
  pages/werewolf/room/index.*             # 对局页：WAITING/夜晚/白天/投票/结算 一页多态
  components/PlayerSeat | RoleCard(翻牌) | PhaseBanner | EventLog | VotePanel | BoardPicker | ResultOverlay
  assets/cards/*.png                      # 卡牌图片(见 §7)
mini-program/src/services/gameCenter.ts   # HTTP（复用 services/request.ts）
mini-program/src/services/werewolfWs.ts   # WS 封装：连接/心跳/重连/消息分发（参考 openclaw.ts 的全局 socket 用法）
mini-program/src/stores/werewolf.ts       # zustand：快照+事件流归约出可渲染状态
```

接入点：
- `src/app.config.ts`：新增 `package-game` subPackage；主包工具首页 `pages/index` 增加「游戏中心」入口卡片（沿用现有 ToolCard 数据结构，plan 阶段对齐具体写法）。
- 样式沿用全局暗色玻璃拟态 token（`styles/_tokens.scss`、`_glass.scss`），rpx 单位。

### 6.2 对局页交互要点

- **身份展示**：开局翻牌动画（RoleCard 3D 翻转），点按可随时重看自己的牌。
- **夜晚**：轮到自己行动时底部弹出可点击玩家座位选择（选择即提交，可改在阶段内以最后一次为准——与市面一致），显示倒计时；非行动阶段显示「天黑请闭眼」遮罩。
- **白天**：EventLog（公共事件流）+ SpeechFlow（逐条发言，当前发言者高亮 + 倒计时）；轮到自己出现输入框。
- **投票**：VotePanel 点选目标或弃票，结束展示票型明细。
- **结算**：ResultOverlay 全员翻牌 + 胜负横幅 +「再来一局」（房主）/「返回大厅」。
- 逃跑/断线玩家座位显示离线标记；重连走 `GET 快照` + WS `state` 全量恢复。

## 7. 卡牌图片素材方案

需要 8 张：狼人、村民、预言家、女巫、猎人、守卫、白痴、牌背。

策略（按序）：
1. **联网搜索免费可商用素材**（图片搜索工具），仅采用许可明确（CC0/可商用）且风格接近的图；逐张记录来源与许可。
2. 搜索无法凑齐风格统一的整套（大概率）→ 用 AI 生图（ai-image-generation 能力）生成**一套统一暗黑水墨卡牌风**（匹配小程序暗色主题），一次性保证风格一致性。
3. 统一后处理：裁切为统一比例（3:4）、压缩至 ≤80KB/张（tinypng/等价压缩），整套 ≤700KB，控制在分包预算内。

存放于 `package-game/assets/cards/`，随包分发，无网络依赖。

## 8. 错误处理与边界

| 场景 | 处理 |
|---|---|
| 加入已开局房间 / 满员 / 房号不存在 | HTTP 4xx，前端 toast 提示 |
| 非行动阶段提交行动 / 重复行动 | WS `error` 消息，前端忽略+提示，不改状态 |
| 非发言轮次发言 | 服务端拒绝（error），保证轮流秩序 |
| WS 挤线（同房间重复连接） | 旧连接关闭，新连接接管 |
| 服务重启丢房间 | 客户端 WS 连接失败 → 提示房间已解散，返回大厅 |
| 全员掉线 | 托管推进至对局结束，落库，房间按无连接回收 |
| 非法板子（人数不守恒等） | 创建时 422 + 明确错误信息 |
| 行动冲突 / 误触 | 确认制：选人 → 确认弹窗 → 提交即生效不可撤回（市面主流 App 做法） |

## 9. 测试计划

**后端 pytest**（引擎为纯 Python 可直接驱动）：
- 板子：5 个预置板生成正确、自定义校验（非法/警告）、角色发放随机性与守恒
- 夜晚：阶段顺序与跳过、各角色行动结算、女巫同晚一瓶/无解药不知刀口/自救配置、守卫连守限制、奶穿、狼刀结算与守卫抵消
- 白天：发言轮转（死者下一位/无死者轮转）、投票平票 PK 与再平、弃票、白痴翻牌免死与失投票权
- 猎人：被刀/被放逐可枪、被毒不可枪、超时弃枪、枪杀链（枪死目标是猎人不再触发）
- 胜负：屠边各分支、狼数≥好人即时判定、当日结算后立即终局
- 房间/连接：加入离开踢人、断线 60s 保留与重连快照一致性、房主权限、托管与超时推进（time mocking）

**前端 Vitest**：`stores/werewolf` 消息归约（phase/private/event/speech/votes/game_over）、倒计时状态、板子选择表单逻辑。

**人工验收**（AGENTS.md 门禁）：`python dev-services.py` 起后端；微信开发者工具多实例（2–3 个账号）从创建→加入→完整对局→结算→再来一局全流程联机验收；后端 `ruff check` + `pytest`、前端 `npm run test` + `npm run build` 全绿；`git diff` 仅含本任务改动。

## 10. 里程碑（供实施计划展开）

1. **M1 规则引擎**：roles/boards/engine + pytest 全绿（纯后端，不涉网络）
2. **M2 房间与协议**：manager/room + HTTP API + WS 路由 + Alembic 迁移 + 集成测试
3. **M3 前端联机**：分包骨架、大厅、对局页、WS 封装与 store，双端跑通完整对局（无图占位）
4. **M4 素材与视觉**：卡牌图片定稿入库、翻牌/倒计时等视觉打磨
5. **M5 验收提交**：完整真机多人验收 + 按提交门禁规则提交

## 参考资料

- [狼人杀配板子的基本理论 - 知乎](https://zhuanlan.zhihu.com)
- [狼人杀 12 人局板子讨论 - 知乎](https://www.zhihu.com)
- [狼人杀桌游规则玩法攻略 - 4399](https://news.4399.com)
- [标准 9 人局配置萌新教学 - 小米游戏](https://game.xiaomi.com)
- [十二人标准局游戏规则 - doyo/9game](https://www.doyo.cn)
- [狼人杀顺序法官台词 - 3DM 手游](https://shouyou.3dmgame.com)
- [狼人杀面杀遗言版完全规则 - 百度文库](https://word.baidu.com)
- [狼人杀新手入门指南 - 什么值得买](https://post.smzdm.com)
