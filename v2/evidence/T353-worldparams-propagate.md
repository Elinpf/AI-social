# T353 · `D3` 口径②：`WorldParams` 传导 —— 证据（骨架，待 T350 解冻后填实测）

**日期** 2026-10-13 · **作者** kernel-dev · **状态** 实现+落地就绪；**实测待 `T350` 结束**
**口径**：**默认 `conservative`（影响稀疏，T347/T289 ≈1 次/周）；受控剂量用 `moderate` 证通路**。
**判 inert 看"消费点被读"，不看最终 delta**（"Δ≈0 既非 inert 也非等价"）。

## 1. 改动（端口 + 消费**同批落地**，防 inert）

- **engine（kernel）**：`engine/world_params.py::world_params(records, round, config)`（**纯派生**，不入 `state_hash`；`activity_weight/resource_factor_bp/market_scarcity_bp/active`；**三保底**：`directed` 必需 / `[start,end)` 只对未来 / 剂量取自 `dose`）；`config/world_director.json` 加 **`propagate.enabled=true`**；`orchestration/integration.KernelAdapter.world_params(round)`；`life/ports.KernelPort.world_params` 声明。
- **life（T364，life-layer-dev）**：`life/agent.py` 每回合经端口读一次（`_read_world_params`，**端口缺失⇒不读、行为不变**）+ **计数 `_wp_reads`**；`_activity_for` 在本 slot **倾向高权重 place**（**仅当对当前活动合法** ⇒ 有界；空/`dose=0` ⇒ 恒等）。

## 2. 消费点直接证据（leader 新通则）

| # | 证据 | 状态 |
|---|---|---|
| ① | **`world_params()` 调用次数**：开 ⇒ >0、**关 ⇒ 0**（`_wp_reads` / 端口打点） | ⏳ 待实测 |
| ② | **消费者真读到值**：读到的 `activity_weight` 与基线（空）不同 | ⏳ 待实测 |
| ③ | **受控剂量**（`moderate`）同 seed **族 delta + `state_hash`** | ⏳ 待实测 |

## 3. 三保底可核（已单测，`tests/test_t353_world_params.py` 6 passed）

- (a) **`directed` 必需**：`directed=False` ⇒ 不传导 ✓
- (b) **独立开关 + 剂量**：`propagate.enabled=False` ⇒ 四键均空 ✓（剂量 0 ≡ 关）
- (c) **只对未来 `[start,end)`**：窗口外（`t<start` 或 `t>=end`）不生效 ✓
- 另：空输入 ⇒ 全空；adapter 端口形状正确 ✓

## 4. 声明

- **行为变 + 指纹变**（`world_director.json` 新增 `propagate` 键）⇒ **如实声明**（非等价）；**T355** 承接读数。
- **默认剂量下影响稀疏**（T347/T289 ≈1 次/周）⇒ **受控剂量（moderate）证通路**；**默认仍 conservative**。
- **主树 WIP**：engine 4 文件（kernel）+ `life/agent.py`（life）；**绑 sha + 逐文件清单 + "该 sha 不可复现"**（提交后补）。

## 5. 复现（待填）

```bash
# 纯函数单测（已过）
cd code && python -m pytest tests/test_t353_world_params.py -q
# 受控剂量开/关对照（解冻后）：
#   cfg world_director.dose_curve=moderate；同 seed 开/关 propagate；比族 delta + state_hash + _wp_reads
```

## 6. 交叉核对：life `T364` 消费代码（只读核对；**不替代独立核验**）

- **端口缺失 ⇒ 不读**：`_read_world_params` 用 `getattr(self.kernel,"world_params",None)`，不可调用即 return ⇒ **行为不变** ✓。
- **`[start,end)` 语义用对**：life 调 `world_params(wv.round)`，而引擎端按 `start<=round<end` 过滤 ⇒ **取的是"当前回合生效项"，未把未来窗口误当当前** ✓。
- **有界**：仅当 `activity_weight[p]>0` 且 `_valid(atype,p,slot)` 才改 `place`；空/`dose=0` ⇒ `cands=[]` ⇒ **恒等** ✓。
- **纯观测计数**：`_wp_reads/_wp_nonempty/_wp_changed_choice/_wp_last` 仅内存、不发事件/不进 `state_hash`/不入序列化 ⇒ 不需 `restore` ✓。
- 一处观察（非缺陷）：`_activity_for` 读 `self._wp_last`（上一处 `step()` 已 `_read_world_params` 刷新）；其它调用点若在 step 外调用会用上轮值 —— 当前仅 `step/_act` 调用，**顺序正确** ✓。

## 7. 受控剂量对照设计（解冻后照跑，仅设计不运行）

**矩阵**（同 seed=42, n=6, rounds=24；`world_director.dose_curve=moderate`）：
| 组 | `propagate.enabled` | `time.ongoing.enabled` | 用途 |
|---|---|---|---|
| A0 | false | true | 基线（等于"无 D3 传导"） |
| A1 | true | true | **D3 传导 ON** |
| （可选） | true | false | 隔离 D11 影响（`T354` 已成交互） |

**采集点（三档）**：
- `_wp_reads`（① 读次数：A1>0、A0=0）；`_wp_nonempty`（② 读到非空）；`_wp_changed_choice`（③ 真改变选择）。
- 族 delta：`PLACE_MOVE/ACTIVITY_STARTED(place=高权重)/RELATION_ENCOUNTER/MSG_*` 等；**`state_hash`** 比对。
- **负例**：`A0`（关）应 `_wp_nonempty=0` 且族 delta 全 0、`state_hash` 同基线。

**落笔口径**：
- **默认 `conservative`**：影响稀疏（≈1 次/周）⇒ **短程 delta≈0 属预期、非 inert**；**判 inert 看采集点①/③**。
- **`moderate`**：证"通路 + delta 可测"；**不得**据此改默认剂量（平衡属用户）。
- 绑 **sha** + **逐文件未提交清单** + **"该 sha 不可复现"**（主树 WIP）。
