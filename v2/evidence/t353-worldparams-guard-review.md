# 非作者复核：`GuardedKernel` 门禁白名单补 `world_params`（`1ffd7eb`）

- **复核人**：sandbox-test-lead（**非改动方**）｜ **改动方**：life-layer-dev
- **被核**：`1ffd7eb` 中 `code/life/tests/test_skeleton.py` 的 `GuardedKernel`
- **判定**：⭐ **这是"补真实端口"，不是"放宽门禁"**（理由见 §3）。

---

## 1. 改动范围（`git show 1ffd7eb -- code/life/tests/test_skeleton.py`）

**仅两处**，均围绕 `world_params`：
- `ALLOWED = ("perceive","submit_intent","current_round","derive_time", **"world_params"**)`（只加一项）；
- 新增**同形转发**方法 `world_params(self, round_no)`（转发 `inner.world_params`）。
- **未见其它断言/白名单被改动**（无"顺手加别的"）。

## 2. 非作者复跑

**命令**：`cd code && python3 -m pytest life/tests/test_skeleton.py::test_no_world_state_bypass -q`
**输出**：`1 passed in 0.19s` ⇒ **绿** ✓

**反向验证（硬）**：访问**未声明**属性须**仍红**：
```
ALLOWED = ('perceive','submit_intent','current_round','derive_time','world_params')
state/ledger/kernel/foo/round_events/engine → 全部 AssertionError OK
```
⇒ **门未放宽**：非端口属性一律 `AssertionError`，`__getattr__` 语义未变。

## 3. 判定理由（方向：门 vs life）

- **`world_params` 是真实声明的端口**：`life/ports.py::KernelPort.world_params`（声明）+ `KernelAdapter.world_params`（实现）+ `engine/world_params.py`（派生）；life `agent.py::_read_world_params`（T364）**经此端口**消费。
- ⇒ 该门此前**红**的原因是 **`GuardedKernel.ALLOWED` 认得比真实端口少**（漏了新增的合法端口），**不是 life 越权**（未触碰 `.state/.ledger` 等）。**方向 = 改门（补端口），正确**。
- **未放宽断言**：`__getattr__` 仍对任意未声明属性抛 `AssertionError`（§2 反例证）；改动**只增** `world_params`，没有把门变成"什么都能过"。

## 4. 结论

**可采信**：该门为**补真实端口**，`test_no_world_state_bypass` 复跑**绿**，**反向负例仍红** ⇒ **不是"把门放宽换来的绿"**。

*（非作者复核结束 — sandbox-test-lead）*
