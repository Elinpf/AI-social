# T363 独立核验：`T354` 期②a（`current_activity` 消费 + 活性）

> 核验者：`sim-engine-stats-architect`（**非作者**）｜ 状态：**完成（四项出结论，交 Leader 复核）**
> 对象：`T354` 期②a（`D11` 期② 最小切片；提交 `b69055f`/`8432adc`）｜ 读时主树 HEAD：`1ffd7eb`
> 装置：mock（无网络）、`N50_VEC=0`、同 seed=7；脚本 `v2/evidence/t363_verify_t354.py`（**不 import 作者测试**）+ 机读 `v2/evidence/T363-run.json` + N=20 探针 `/tmp/t363_liveness20.py`。

---

## 结论速览

| 项 | 结论 | 依据（一句话） |
|---|---|---|
| ① 开关真通路（防 inert） | **PASS** | `on vs off`：len 50384 vs 50202、`state_hash` 不同 + **族级 delta 非空** ⇒ `current_activity` **真被 life 消费**；`off ≡ neu`（`state_hash` 相等）⇒ **关臂干净 ≡ 现状** |
| ② 活性（gate） | **PASS（gate 未触发）**⚠️ 附风险 | **无「不再行动」个体**（N=8 与 N=20 居民 moves 46–56、acts 28，零移动/零活动为空）；但「**永久进行中**」普遍存在（§2.3 定性） |
| ③ 作者证据三件前提 | **【未补】** | `v2/evidence/` 无 T354 专用作者证据文件（判词须为「未补」，非「补了不合规」） |
| ④ 无其它行为面偷跑 | **PASS** | `ACTIVITY_INTERRUPTED`（on）=**0**；`code/` 内 `[ongoing:` 残留=**无** |

> ⚠️ **给 Leader 的更正**：首版 `T363-run.json`（16:0x 产物）里的 `FAIL①（off 与中和变体不等价）` 是**我脚本的假红**，**不是 `T354` 缺陷**（详见 §1 口径注）。以本报告为准。

---

## 0. 被核对象（只读侦察）

| 项 | 位置 | 结论 |
|---|---|---|
| 派生逻辑 | `engine/perceive.py::current_activity` | 纯派生 = 本人最后 `ACTIVITY_STARTED` 之后**无**对应 `ACTIVITY_COMPLETED`；不新增真相源 |
| 暴露（引擎） | `engine/perceive.py::perceive` | `time.ongoing.enabled` 真时填字段，否则 `None` |
| 暴露（adapter） | `orchestration/integration.py::KernelAdapter.perceive` | 读**运行时** `engine.config["time"]["ongoing"]["enabled"]`（供同 seed 开/关对照）；`_ongoing` 真才填 `ca` |
| 契约字段 | `life/ports.py::WorldView.current_activity: dict|None = None` | 有默认值（getattr 容错 ⇒ 无字段则行为不变） |
| **life 消费点** | `life/agent.py::_act` | 仅当 `ca.place == wv.location` **且** `ca.activity_type == 本slot目标` ⇒ `return None`（不重复发起同活动 move） |
| 开关 | `config/time.json` | `time.ongoing.enabled=true`（默认开）；`time.json` **已在 `FINGERPRINT_FILES`** |

---

## ① 开关真通路（防 inert）—— **PASS**

命令：
```
python3 v2/evidence/t363_verify_t354.py --seed 7 --n 8 --rounds 84 --json v2/evidence/T363-run.json
```
原始输出（摘）：
```
on : len=50384  state_hash=sha256:de9c0525f1c356361c5bb3615c3c3cebcc2e680a1c29141b23e3896df49e1adf
off: len=50202  state_hash=sha256:5f6a5679ab03554c4dd48997e32e7ea0cc579759126d882ed8dafa110192c6f8
neu: len=50202  state_hash=sha256:5f6a5679ab03554c4dd48997e32e7ea0cc579759126d882ed8dafa110192c6f8  （开关 on 但 ca 强制 None）
on vs off 族级 delta：{'LLM_CALL': -2, 'LLM_JUDGMENT': 5, 'MEMORY_FORGET': 16, 'MEMORY_WRITE': 71,
                      'OBSERVATION': 71, 'PERSONA_DRIFT': 2, 'PERSONA_DRIFT_CANDIDATE': 6, 'RELATION_CHANGE': 13}
on vs off 首个差异 seq：0
off ≡ neu（state_hash 相等 + 族计数相等 + 去哈希链后差异仅 WORLD_INIT/TURN_SEAL）：True
```

- **有可观测差异 ⇒ 非 inert**：`on` 比 `off` 多 **182 条**事件、`state_hash` 不同；族级差集中在其**消费面**（移动→`MEMORY_WRITE`/`OBSERVATION` 各 +71、`RELATION_CHANGE` +13 等）。
- **`off ≡ neu`（关臂 ≡ 现状，权威判据 = `state_hash` 相等）**：`off` 与「开关 on 但 ca 强制 None」的**折叠世界态 hash 完全相同**（`5f6a5679…`）⇒ 行为一致、关臂干净（`T355` 的 2×2 关臂不被污染）。
  - ⚠️ **口径注（首版假红根因）**：`off`/`neu` 的**日志**不是逐字节相同——`WORLD_INIT(seq0)` 含**运行时 config 摘要**（`time.ongoing` off vs on 不同）⇒ **哈希链级联**使后续 `prev_hash/hash` 及 `TURN_SEAL.last_hash` 变。**去哈希链后差异行类型仅 `{WORLD_INIT, TURN_SEAL}`**（`TURN_SEAL.last_hash`=链头=WORLD_INIT hash 的派生）——**均为指纹行及其链派生，非行为**（正是 `08 §5.10` 立的"唯一差异=指纹行及其派生"口径）。**故"逐字节一致"不能作此项判据**（首版脚本如此、误报 FAIL；已修）。
- **负例（判据反向）**：若 `on vs off` 族级 delta 为空**且** `state_hash` 相等 ⇒ 应判 **FAIL（inert）**。本跑非此。

---

## ② 活性（gate）—— **PASS（无卡死）**，附风险观察

### 2.1 N=8（与 ① 同跑，最不利 = on）
```
agent    max_run permanent   moves  acts zero_move zero_act  runs
P001          85      True      54    28     False    False  [85]
...（P002–P008 同形，moves 46–56、acts 28）...
『永久进行中』个体：['P001'...'P008']
⚠️ 卡死个体（整周零移动且零活动 ⇒ gate）：无
```
### 2.2 N=20（目标规模，单世界，`/tmp/t363_liveness20.py`）
```
n_agents 20   perm_all True   zero_move []   zero_act []
per_agent: P001..P020 → max_run 85, perm true, moves 46–56, acts 28, zero_move/zero_act false
state_hash=sha256:1ede6305...cd484a56
```
- **逐人点名（不得只看均值）**：N=8 与 N=20 的**全部居民** moves≥46、acts=28 ⇒ **无一人「整周零移动/零活动」** ⇒ **无卡死个体 ⇒ gate 未触发**。
- **非居民已排除**：`MARKET` 等非 Agent 账户（T248）按 `contracts.actors.is_agent_actor` **不计入逐人活性**（首版脚本曾误报 `MARKET`；已修）。

### 2.3 ⚠️ 「永久进行中」定性（根因已核，非 FAIL 但请 Leader 知悉）
- **现象**：所有居民"进行中"连续段 `max_run=85`（整周无 `None`）。
- **根因（已核，非"从不发 `COMPLETED`"）**：`ACTIVITY_COMPLETED` **确有发射**。证（P001，n=8）：
  `STARTED(seq51,r0) → COMPLETED(seq360,r3) → STARTED(seq365,r3) → COMPLETED(seq707,r6) → STARTED(seq710,r6) → …`
  ⇒ **每 slot 一闭环**；真因 = 活动在 **slot 边界背靠背**（`COMPLETED` 与下一 `STARTED` **同回合**、seq 后者大）⇒ 派生 `current_activity` **几乎恒非 None**。
- **当前非 bug**：居民**仍在行动**（移动 46–56、每 slot 一活动），不构成"不再行动"。
- **⚠️ 隐患**：消费门 `_act` 在 `ca` **恒非 None** 时**恒 armed**，仅靠 `(place,type)` 随 slot 变化释放。Leader 曾预判「`T358`（移动占回合）会让"进行中"更长 ⇒ 消费点现在就得有界」。**建议**：`T358` 落地前给门控加**有界**（超时 / 只前 N 回合抑制 / 仅关键活动不打断）。**本核验范围止于"当前无卡死"**；"T358 后是否有界"未证伪，作**风险转交**。

### 2.4 负例（判据反向）
脚本离线自测（合成日志）：对"`STARTED` 后永不 `COMPLETED` 且零移动"的个体**正确判为卡死**（`zero_move=True`）⇒ 判据**能红**，非永真。

---

## ③ 作者证据三件前提 —— **【未补】**

命令：`ls v2/evidence | grep -iE "t354"`（脚本按名排除 `363`）
结果：仅命中**我自己的** `T363-t354-phase2a-verify.md` / `t363_verify_t354.py` ⇒ **无任何 T354 专用作者证据文件**。
判定：**【未补】**（照 Leader 裁定：`T350` 前缺=预期；**跑重活那一刻仍缺 ⇒ 不合格，但判词须写「未补」**）。
- **整改动作（与"补了不合规"不同）**：请作者补 `life` 的主树开/关对照证据，**含四件**：① 绑 sha ② 逐文件未提交清单（谁写的）③ 明确声明该 sha **不可复现** ④ 明写「**仅设计验证，不作 `T355` epoch 对照**」。补齐后若缺任一 ⇒ 届时判**【补了不合规】**并列缺项。

---

## ④ 无其它行为面偷跑 —— **PASS**

- `ACTIVITY_INTERRUPTED`（on 跑）事件数 = **0** ⇒ 与 `T354` 声明一致（**口径未登优先级规则 ⇒ 本期不做 = 非漏项**）。
- `code/` 内 `[ongoing:` 残留 = **无** ⇒ `_retrieval_query` 未重加该标记。

---

## 5. 复核指引（交 Leader）

- ①③④ **PASS**；② **gate 未触发**（无"不再行动"个体）。
- **两点请 Leader 裁定**：
  1. **②「永久进行中」普遍存在**：我判**不 FAIL**（无"不再行动"）；若 Leader 采**字面项即 FAIL** 口径，我按你口径改判，请明示。
  2. **②的隐患**：建议**在 `T358` 前把消费门有界化**（不必回炉本期）。
- ③ 为**未补**（作者侧待补）；**不阻断 `T354` 机制本身**，但证据链待齐。
- **更正记录**：首版 `T363-run.json` 的 `FAIL①` 系脚本假红（把"逐字节"当判据、含哈希链级联）；本报告已按 `state_hash`+链派生口径更正。

---

## 6. 复现命令与 sha

```
# 主核验（3 跑 n=8×84）
python3 v2/evidence/t363_verify_t354.py --seed 7 --n 8 --rounds 84 --json v2/evidence/T363-run.json
# N=20 目标规模活性探针（单世界）
python3 /tmp/t363_liveness20.py
```
绑定：读时主树 HEAD `1ffd7eb`；装置=mock、单核、无网络；**未跑 `make verify`**（同刻只一个）。
