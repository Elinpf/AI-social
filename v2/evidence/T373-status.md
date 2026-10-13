# T373 状态（**未收口 · 全队停手 01:40 冻结**）

> 核验者：`sim-engine-stats-architect`（非作者）｜ 对象：`T372`（`world_params` 同 `directive_id` 双计修复）｜ 核的是 **worktree 分支 `t367`@`47322af` 的 `code/`**（非主树，落地已暂停）。
> ⚠️ **本条为停手时的如实状态，不是收口结论。** 别据此判 ①②档。

## 已完成（合成单元，对 worktree `t367` code；可信）
- **①复现原缺陷**：同 `did` 两条（DIRECTIVE+GROUP_EVENT）⇒ 修复前 **80**（2×）/ 修复后 **40**（1×）✓
- **③active 去重**：`['D-1-f']`（不重复）✓
- **④反向负例（异 id 不得误去重）**：两条**不同 did** ⇒ **70**（各计一次）✓；**异 ref 负例** ⇒ **80**（不去重）✓
- **兼容**：单一类型夹具 ⇒ 40 / 40 ✓

## ⚠️ 世界级对照：**有已知混淆 —— 勿用**
- 我的 `prefix`（no-dedup）复刻的是**主树旧版** `world_params`；而 worktree `t367` 的 `world_params` **另含 T367 变更**（新增 `season`/`abundance` 两种 kind 处理）。
  ⇒ 例（t=0）：live `active=['DC-0-season','DC-0-abundance']`/`aw={'market':20}` vs prefix `active` 双份/`aw={}` ⇒ **live≠prefix 的差异混了 T372 去重 + T367 kind 两件事**。
- 控制实验（`DISABLE=1` 关世界导演）live==prefix（同 `140421d3`）⇒ 仅证明"无指令时一致"，**不足以**把 enabled 下的差异归因给 T372。
- ⇒ **要判 ①②档，必须用"worktree 去掉 `seen_refs` 去重、保留 T367 kind"的忠实变体**重测。**本项 PENDING。**

## 存放 / 绑定
- 脚本：`v2/evidence/t373_verify_t372.py`；raw：`v2/evidence/T373-run.json`（**其 `four_class=行为变` 一栏受上述混淆影响，勿采信**）；控制程序：`/tmp/t373_ctrl_run.py`（临时，未跟踪）。
- 绑定：worktree `t367`@`47322af`（若分支已推进，以最新为准）；**主树未动**。
- 实测（t=0 例）：真实发射 `WORLD_DIRECTIVE=4` / `WORLD_GROUP_EVENT=4`（4 对，共用 `did`）。

*（停手冻结；待放行后按"忠实 no-dedup 变体"重测收口。）*
