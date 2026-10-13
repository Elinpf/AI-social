# T343 · 批1：四组对照页（自包含 HTML + PNG）

## 交付
- **HTML（自包含，无构建/无联网）**：`code/frontend/fourgroups.html`（生成器：`code/frontend/tools/gen_fourgroups.py`，读证据→内联数据→绑 HEAD sha）。
- **PNG**：`v2/evidence/T343-fourgroups.png`（口径①）、`v2/evidence/T343-fourgroups-cal2.png`（口径②）；由 `shot.py --full-page` 出图。

## 口径分套（硬要求）
- 页面**顶部口径切换**：`口径① 10-12 夜跑原始四批` / `口径② 10-13 00:38 共享 cache 干净复跑`；**常驻口径角标**；URL `?cal=d2` 可直开口径②。
- **不混**：两版各自一套表；数据源与 **证据 sha** 显示在页脚。

## 内容（对齐早报，不超出证据）
- **口径①**（源 `nightly-20261012-morning-report.md`，数字逐字抄）：A 301,384 / B 301,395 / C 151,968 / D 304,607；含 事件/LLM_CALL/峰值RSS/耗时/指纹/state_hash；类型差异仅列**早报 §2 明示项**；3 条结论 + 诚实缺口①②③ **逐条对齐**。
- **口径②**（源 `t292_shared_results.json`）：A 301,332 / B 301,330 / C 301,332 / D 304,452；含 事件/LLM_CALL/cached/耗时/指纹/state_hash；**类型差异按类自动算（相对 A）**；**⚠️ C 零结果**（未真正关掉，机制缺口已修 T297b）显式标注；**峰值 RSS 未记录**（JSON 无字段，如实写"—"）；`t310_results.json` 作**同口径二次复跑备注**（不与主表混，印证跨批噪声）。

## 门禁/自证
- `shot.py` 新增 `--full-page`（整页截图）与 `--no-blank-check`（**非小镇画布的普通页面**：深色/大色块会被非空白判据误判），非空白判据默认不变。
- `make ci` → PASS（见提交）。
