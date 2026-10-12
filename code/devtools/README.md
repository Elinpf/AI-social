# devtools — 研发侧工具（P0：DT-1 / DT-2 / DT-3）

> 世界观编年史可视化：**事件时间线 / 编年史大纲 / 关系网 + 溯源跳转** + **角色记忆素材导出**。
> 需求依据：`v2/refs/devtools-requirements.md`（emergence-researcher，T207）§1 / §5。

## 铁律（需求 §0，已写死在实现里）
- **只读优先**：经 `obs.reader.ReadOnlyLog` 读取；构造即**校验哈希链**（`require_chain`）；**不写世界**（无任何写事件）。
- **来源可追溯**：时间线节点 / 大纲条目 / 关系边 / 角色素材**每一项**都带**真实 `event_seq`**，界面点开即见 payload。
- **口径唯一不复制**：语义普查**逐字**用 `obs.census.semantic_census`；关系权重用 `obs.folds.relation_weights`；
  周/日/时段用 `engine.time.derive_time`（纯函数）。**本工具不另立算法**。
- **不造结局 / 不改分支 / 不替 Agent 决定社会结果**；只呈现**已发生**的事实。
- **证据绑版本**：产物 header 记 `log_hash / seed / max_round / chain_ok`；生成命令见下。

## 用法
```bash
cd code
python devtools/chronicle.py \
  --log ../v2/evidence/run_p1_final_n20_llm.jsonl \
  --out ../v2/evidence/devtools/chronicle_view \
  [--personas config/personas.json] [--cap 20000]
```
- `--cap N`：时间线**嵌入查看器**的上限（0=全量）。**截断只影响查看器列表**；`meta.round_counts` 仍是**全量**每回合计数，
  且截断时优先保留"重大事件"（稳定、可复现）。
- `--no-verify`：**仅用于派生日志**（如 `*.play.jsonl`：剔除了事件 → `seq` 不连续、哈希链不成立）。
  canonical 日志请**不要**用它。
- 运行需在 `code/` 下（或 `PYTHONPATH` 指向 `code/`），使 `obs.*`/`engine.*` 可导入。

> **生成物归属（重要）**：**不要把 `--out` 指到 `code/frontend/`**——那里是**前端源码**语义；
> 生成物属**旁路证据/工件**，请写到 `v2/evidence/...`（本仓库默认）或 `/tmp`。
> 若仓库纳入版本控制，应对生成物目录做 `.gitignore`（带 `--cap` 的 timeline 可能较大）。
> 本仓库**非 git 仓库**，故以"**不写入 `frontend/`**"为准。

### 产物（写入 `--out`）
| 文件 | 内容 |
|---|---|
| `chronicle.html` | **自包含**查看器（内嵌模型）。Tab：时间线 / 编年史大纲 / 关系网 / 语义普查 / 角色素材；右侧**溯源抽屉**。支持 `#timeline`/`#outline`/`#graph`/`#census`/`#chars` 深链 |
| `chronicle.model.json` | 数据模型（真实日志派生） |
| `characters/<id>.md` | 每角色一份**记忆素材**（身份 + 生命节点 + 关系 + 关键记忆，均带 `seq`） |

### 查看（在产物目录起个静态服务即可，无需放进 `frontend/`）
```bash
cd v2/evidence/devtools/chronicle_view
python -m http.server 8899        # 打开 http://127.0.0.1:8899/chronicle.html
```

## 验收对照（需求 §1.3）
- **V-1 可溯源**：时间线每行、大纲每条、关系网每对、角色素材每条 → 均带 `event_seq`，点开显示 payload（截图 `DT1/DT2/DT3`）。
- **V-2 口径一致**："语义普查"页**逐字**呈现 `obs.census.semantic_census` 的 20 类 hits（本工具不重算）。
- **V-3 只读**：全程只读；`ReadOnlyLog` 构造即校验链；**无写事件**。
- **V-4 无编造**：大纲条目 = **类型聚合 + 来源 seq**（不做叙事性推断）；角色素材只含日志已发生事实。

## 证据（`v2/evidence/devtools/`）
- `DT1-timeline.png`、`DT2-relation-network.png`、`DT3-outline.png`
- `DT3-character-P001.md`（角色素材样例）

## 已知 / 未验证
- **派生播放视图**（`*.play.jsonl`）**无法**通过 `verify_chain`（`seq` 不连续），须 `--no-verify`；事实源应以 canonical 日志为准。**已在帮助与 `meta.derived` 标注。**
- 关系网**聚合为无向人物对**（合并 `affinity/trust/respect/familiarity` 四维；权重求和）仅为**可读性**展示口径；**原始逐维有向权重**仍在 `chronicle.model.json.graph.edges` 中（未丢）。
- **【未验证】** 角色素材"可被 life 层直接加载"的**格式对齐**未做端到端加载测试（仅按 persona schema + 记忆字段产出）；接入前需与 life 层确认格式。
- 宏观"编年史叙事化措辞"未做（仅事实聚合）——叙事润色属叙事层（`v1.1/17`），本工具**不越界**。
