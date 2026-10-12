# T267 · 门禁 D 段：前端资产/常量「定义了却零引用」（睡着的资产）

**背景**：今日第 4 次同族病「存在但没生效」（`truth` 两份 / `visible_events` 三份 / `iou/palette/shade` / `grassLight`）。
现有门禁拓不到（lint-imports 管依赖方向、`make art` 管资产自洽）——**没有一道管"定义了没人引用"**。

**落位**：并入 `tools/check_inert_registry.py` 的 **D 段**（与 A/B/C 同入口 / 同退出码 / 同 JSON）。
不新写第二份：以 pixel-artist 的 `frontend/tools/check_inert_assets.py`（T258e）为参考基础。

## 实现要点（对齐 sim-engine-stats-architect 骨架 + Leader 硬要求）
- **两态纪律**：三态 `referenced / zero_ref / dynamic_ref_unknown`；`zero_ref` 才报警，**`dynamic_ref_unknown` 只报"未知"，绝不写成 zero_ref**。
- **动态访问收窄到"符号所属映射"**：仅当对 `sym` 所属映射（如 `TILES`）做**非字面量键访问**（`TILES[k]`）才算动态；普通 `road[ty][tx]`/`gset[0]` **不算**。
  （否则 `dynamic_scope` 恒真 → `zero_ref` 永不出现，与反向验证自相矛盾——这正是评审时先揪出的缺陷。）
- **值(id)引用（近似）**：建 符号→值(id) 映射；仅当 id≥100 且落在**瓦片消费上下文**（`pick(`/`slice(`/`texture`/`Rectangle`/`frame`）才计入；**跳过注释行**（曾致 `745` 因注释误命中）。**<100 的小 id 不作值搜索** → 若某键**只靠小 id、无具名访问**，无名字命中时**降级为 `dynamic_ref_unknown`（不写成 zero_ref）**，防假红；靠名字命中兜底。
- **只做数据级**：顶层映射表键 vs 引用点；局部未用变量交 ESLint `no-unused-vars`，本器不判。
- **棘轮**：`frontend/tools/inert_assets.json` 的 `entries`（显式 `expected_status` + `purpose`=该键语义用途，不靠名字匹配）；不一致 → 退出码 1。
- **JSON**：只新增 `auto_assets` 键，不动 `manual/mismatches/auto_events/auto_switches`。

## 反向验证（写死；`--self-test`，全 OK）
| 用例 | 期望 | 实测 |
|---|---|---|
| 未接线 → | zero_ref | ✅ zero_ref |
| 已接线（town.js 具名） → | referenced | ✅ referenced |
| 动态键访问 `TILES[k]` → | dynamic_ref_unknown | ✅ dynamic_ref_unknown |
| 普通下标 `road[ty][tx]` → | zero_ref | ✅ zero_ref |
| 仅小 id(<100) 无具名 → | dynamic_ref_unknown（防假红） | ✅ dynamic_ref_unknown |
| **真实 assets · town.js 去掉 grassLight 引用** → | zero_ref | ✅ zero_ref |
| **真实 assets · town.js 原样（已接线）** → | referenced | ✅ referenced |

**棘轮变红**：把 `grassLight.expected_status` 故意写成 `zero_ref` → `MISMATCH` + **退出码 1**；还原 → 退出码 0。
→ **能对坏输入变红才算判据**（一个只会绿的断言没有价值）。

## 接线
`frontend/tools/ci_gate.sh` 新增 `[D]` 步：先跑 `--self-test`（反向验证），再跑 D 段表；退出码并入 CI。
`make ci` → **CI GATE: PASS**（smoke + gate_render + R9 + D 段）。

## 改动文件
- `tools/check_inert_registry.py`（新增 D 段：`_asset_defs/_refs_asset/d_state/_load_asset_ratchet/auto_assets/_self_test` + main 接线）
- `code/frontend/tools/inert_assets.json`（新增 `entries` 棘轮条目：grassLight/grass，含 purpose）
- `code/frontend/tools/ci_gate.sh`（新增 `[D]` 步）
