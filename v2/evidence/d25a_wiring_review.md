# D2.5a 接线审查（Leader）：**通过**——链路正确、无副作用，可进入 mock 复核

> 日期：2026-10-24。审查对象：`feat/d25a-override-wiring` @ `e2e7131`（`cli.py` +57、`emit_run_meta.py` +27）。
> 结论：**接法正确**，但仍有 1 个必须由实跑证明的点（见 §4），mock 通过后才可起跑。

## 1. 我核的是什么（"接线对 ≠ 取值对"）

`cli._apply_overrides` 只把 override 写进 **config dict**；而 life 层读的是
`life/dialogue_threads.load_params()` → 文件 + `life.config.override_for("life_v2")`。
**这是两条不同通道**，只改 dict 不注入 `_OVERRIDE` 就是"静默无效"（预登记 §7 的作废条件）。

逐段核对链路：

| 环节 | 代码位置 | 结论 |
|---|---|---|
| `--override life_v2.dialogue.max_messages_per_slot=3` → dict | `cli._apply_overrides`（dot-path、`json.loads` 解析、深拷贝） | ✅ 造出 `config["life_v2"]["dialogue"]["max_messages_per_slot"]=3` |
| dict → life 层 `_OVERRIDE` | **`integration.py:986  _lcfg.set_override(config.get("life_v2"))`** | ✅ **关键一环已存在**，override 真会被注入 |
| `_OVERRIDE` → `load_params` | `dialogue_threads.py:78  ov = _lcfg.override_for("life_v2")` | ✅ 读到 3 |
| 副作用：`sleep_window` 也 merge 同一 `_OVERRIDE` | `sleep_window.py:45  _lcfg.apply("life_v2", {"sleep":…,"forgetting":…,"dialogue": DEFAULTS,"observe": DEFAULTS})` | ✅ **已显式留 `dialogue`/`observe` 占位键**（源码注释写明"否则 `--override life_v2.dialogue.*` 会 fail-loud 报 unknown key"）⇒ 不崩、且只改 `dialogue.max_messages_per_slot` 一个键，**sleep/forgetting/persona_drift 不受影响** |
| 生效值落盘 | `<out>.effective.json` + `emit_run_meta` 的 `life_v2_effective` / `overrides_declared` / 一致性检查 | ✅ 声明 vs 进程内读回可互校，解析失败显式记录（不静默） |

**另一处我特意查的隐患**：`default_config()` **没有 `life_v2` 键**（已实测），
`_apply_overrides` 会用 `setdefault` 造出**只含 `dialogue` 的 `life_v2`**。
若 `sleep_window` 没有占位键，这会导致 `unknown life config key: life_v2.dialogue` **fail-loud 崩溃**，
或者更糟——静默让 sleep/forgetting 退回默认值（**非单变量**）。**该模块已有显式占位，风险不成立。**

## 2. 仍需实跑证明的一点（不能只靠读代码）

读代码只能证明"链路通"，不能证明"**实际跑起来读回的是 3**"。
⇒ 起跑前必须有一次 mock（不调模型）：打印 `life_v2_effective.max_messages_per_slot == 3`，
并且 `sleep/forgetting/persona_drift` 三段与无 override 时**逐项相等**（证明零副作用）。

## 3. 顺带修掉的一个并发问题

`§3.118` 被**两条线各写了一遍**（`cbe5366` 与我 `279cd11`）。已合并为一条（`d25bf65`）：
保留"配额→可见性→优先序"三条判据表，并补入"成本差 10 倍"对比段。**剩余条数 = 1。**

## 4. 放行条件（三条同时满足才起跑）

1. mock 读回 `max_messages_per_slot == 3`（且 `overrides_declared` 与 `overrides_from_run_process` 一致）；
2. mock 的 `sleep`/`forgetting`/`persona_drift` 三段与无 override 逐项相等（零副作用证据）；
3. `pgrep` 确认无在跑批；两臂（C 无 override → B 有 override）**串行**，C 先。
