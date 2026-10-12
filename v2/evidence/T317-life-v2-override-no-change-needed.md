# T317 结论：`switch_mode: override` 支持 `life_v2` —— **release 侧无需改动**

> 作者：release-engineer ｜ 2026-10-13 ｜ 判定标准（leader）：「**不改代码，`--override life_v2.sleep.enabled=false` 能不能生效？**」
> 结论：**能** ⇒ **无需加表项、无需改任何 release 侧代码** ⇒ 本任务以"结论"收口。

## 读码依据（HEAD）
1. **`tools/t271/run_override.py:36-46` 是【通用 dot-path】，不是白名单表**：
   ```python
   for spec in a.override:
       loc, _, val = spec.partition("=")
       keys = loc.strip().split(".")
       node = cfg
       for k in keys[:-1]:
           node = node.setdefault(k, {})     # 任意路径自动建嵌套
       node[keys[-1]] = v
   ```
   ⇒ `--override life_v2.sleep.enabled=false` 直接写 `cfg["life_v2"]["sleep"]["enabled"]=False`，**与键别无关**。
2. **life 侧 hook 消费 `cfg["life_v2"]`**（`T297b`=`d2d5649`）：`build_world` 读 `config["life_v2"]` → `life.config.set_override` → `sleep_window.load_params` 合并。
3. ⇒ **我 docstring（`run_override.py:5-6`）里"只支持引擎级键 / life_v2 不覆盖"是【过时说明】，非约束** —— 该句已不成立（life hook 落地后 `life_v2` 即可覆盖）。
4. `life_v2` 不是 `default_config()` 的顶层键，但通用路径**会 `setdefault` 建它** ⇒ 不 override 时 cfg 无 `life_v2`、life 纯读盘（**默认不变**）；override 时叠加（**文件不动 ⇒ `engine_version` 指纹不变**）。

## 端到端（life 已验，我侧无新增代码）
`T297b` 实测：`--override life_v2.sleep.enabled=false --override life_v2.forgetting.enabled=false` ⇒ `SLEEP_STARTED` 基线 **2 → 0**；指纹不变；`make verify` 绿。

## 待定小项（非本任务、doc-only）
`run_override.py` **docstring 已 stale/错**（"life_v2 不覆盖"）⇒ 会误导，**建议**一次纯文档修正（把 `life_v2` 列为经通用路径可覆盖 + 写清 life 的 **fail-loud 键集**：`sleep.{enabled,slot,planned_ticks}` / `forgetting.*` / `persona_drift.{alpha_permille,delta_max,drift_max_permille,drift_dim_max_permille}`）。**按 leader "不用改任何代码" 本次未改**，待其定。
