# T368 · 只读核验片段（停手前已执行）—— Check2 静态/构造性

> 状态：**停手令期间落盘保护**。仅含**已执行**的只读核验（无世界跑、未改主树、未改世界层）。
> 基线：**worktree 分支 `t367` @ `faf4613`（读时 2026-10-13T23:42:36+08:00）**；⚠️ 该分支后续已推进到 `eed664e` —— **结论须在最新 sha + 主树落地后复核**。
> 纪律保留：**我自己的命令 + 原始输出（含反例/负例）才是过闸依据；清单通过 ≠ 实现没问题。**

## 命令与原始输出
```
$ python v2/evidence/T368/t368_verify.py --check 2 --code-root .worktrees/t367/code
[C2] 新造时间源命中 = 无
[C2] 现有 kind（WD_KINDS）= ['season','festival','opportunity','public_works','supply_shock','scarcity',
                              'tension','incident','disaster','epidemic','visitor','edict','agenda','mass_event']
[C2] 'daypart' 作为独立 kind？ False（应为 False）
[C2] 'abundance' 新增 kind 在场？ False（应为 True；14→15）
[C2] _draft 调用 (name, cadence, profile) = {season→season, festival→weekend, abundance→season}（无 daypart）
[C2] schedule.cadence/profile 含 daypart？ False（应为 False）
[C2] verdict = FAIL
```
（另：`grep -rn "import random|time.time(|uuid|Random()" worktree code/engine code/life` → 仅 `life/tests/test_t265_memory_perf_equiv.py:12` 命中，属**测试自身**用途，非 world_calendar/world_params 路径的运行时非确定源。）

## 结论（只读，未定论；待放行后复核）
- ✅ **退让不复活（DC-1）**：无新造时间源；`daypart` 非 kind；`schedule.cadence/profile` 无 `daypart`（cadence ∈ {season, weekend}）。
- ❌ **F-1【登记口径不一致·中】**：权威枚举 `engine/world_director.py::WD_KINDS` **仍 14 值、不含 `abundance`**（注释亦写"14"），而设计与已批登记要求 **14→15 新增 `abundance`**；实现却 emit `kind="abundance"`。⇒ 枚举与登记不同步（当前 `WD_KINDS` 未被使用，故无即时运行错，但"按 kind 聚合/消融"的权威口径已失真）。**待复核**：08 登记是否已落（草稿称 `a7867c4`）而代码枚举漏改。
- ⚠️ **F-2【防机械未启用·中】**：`code/config/world_director.json` 的 `calendar.season/festival/abundance` **均未配 `jitter_bp`** ⇒ `_jitter` 恒返 0 ⇒ 设计 §1.1 的"节日 `jitter_bp` 非严格等周期"**实际未生效**（festival 严格等周期，偏机械）。用例可复现：`boundary_directives` 端 `end = r + len + 0`。
- ⛔ **未执行**：Check1（事件数证据）、Check3（同seed两跑+离线重算）、Check4（dose=0 逐条等价含 state_hash）、Check5（可感度两闸）—— 均需 mock 世界跑，**停手令下不启动**；runner 已备（`v2/evidence/T368/run_mock.py`，分进程）。

*（停手期落盘 — delivery-reviewer；结论绑 worktree `t367`@`faf4613`，非主树，落地后须复核）*
