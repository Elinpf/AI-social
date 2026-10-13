# T355 override E2E —— 非作者复核结论

- **复核人**：sandbox-test-lead（**非 mock 作者**）｜ **mock 作者**：kernel-dev
- **被核**：`/tmp/t355_override_e2e.log`（kernel 跑）＋ 我**独立复现**
- **独立脚本**：`v2/evidence/t355_override_e2e_review.py`（只读；不改 code/）
- **装置**：**life 业态**入口 `build_world(seed=42, n=4, config=cfg)`（→ `KernelAdapter`，**非 inline**）×2，`cfg["time"]["ongoing"]["enabled"]=true|false`，各 **24 回合**（与 kernel 同参）

---

## 1. 独立复现 vs kernel 日志（逐项一致）

| 项 | kernel 日志 | 我独立复现 |
|---|---|---|
| `ongoing=True`：`_load_time_flags(cfg)` / `adapter._ongoing` | True / True | **True / True** ✓ |
| `ongoing=False`：同上 | False / False | **False / False** ✓ |
| 族 (on, off) `MEMORY_WRITE` | (766, 769) | **(766, 769)** ✓ |
| 族 `OBSERVATION` | (756, 759) | **(756, 759)** ✓ |
| 族 `PLACE_MOVE` / `ACTIVITY_STARTED` | (30,30)/(32,32) | **(30,30)/(32,32)** ✓ |
| `arms_differ` | True | **True**（非零族：`MEMORY_FORGET/MEMORY_WRITE/OBSERVATION/RELATION_CHANGE`）|

## 2. 健壮性/反向

- **确定性**：同 arm 跑两遍族计数**全等** ⇒ 差异来自开关、非噪声。
- **修复验证**（kernel 改 `_load_time_flags` 优先 cfg）：`_load_time_flags()`（不传 cfg）= **True**（文件值）；`_load_time_flags(cfg=False)` = **False**（cfg 覆盖）；文件 `time.json.ongoing.enabled` 仍 **True**（未改文件）。
  ⇒ 证明"**回退文件值**"与"**尊重 cfg 覆盖**"两条路都在；life 路径经 adapter 读 `engine.config["time"]` ⇒ **覆盖真生效**。

## 3. 结论

**可判：`time.ongoing` 的运行时 config 覆盖在 life 业态下【真生效】（非静默丢弃），`arms_differ=True`。**
⇒ `run_override.py --override time.ongoing.enabled=false` 对 **T355（life 业态全周跑批）有效**，**无需补机制**（release 预告命令可用）。

**⚠️ 登记项（防后人踩坑）**：`time.ongoing` 的消费者有**两条**——**life=运行时 config（可覆盖）**；**standalone `engine/perceive.py::perceive()`（mini_kernel/inline）= 曾直读文件（kernel 已修为优先 cfg）**。**在 mini/inline 路径翻开关若未升级到该修复版，会得假 2×2**。

*（非作者复核结束 — sandbox-test-lead）*
