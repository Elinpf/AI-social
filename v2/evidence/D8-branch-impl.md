# D8 分支实现说明：世界事件 → 居民可见 → 对话提及（最小闭环）

- 分支：`feat/world-event-dose`（独立工作树 `.worktrees/feat-world-event-dose`）
- 基线：`2090287`（master 主跑批路径，本分支**未合并、不动 master**）
- 代码 commit：**`f7453564ccab822b6f800b15a423bcf8b3425676`**
- 性质：**链路已接通，效果待 A/B 验证**。本文件不含任何"效果更好"的结论。
- 本轮 A/B 规模（Leader 裁决）：`agents=4 × rounds=60`，同 seed 两臂。

---

## 0. 诊断结论（可复算，一句话版）

世界层的 `WORLD_DIRECTIVE` / `WORLD_GROUP_EVENT` 在 `code/config/perception_scope.json:63-64`
登记为 `global`，因此**确实进了每个 agent 的 `visible_events`**（`contracts/visibility.py::visible()`
第一个分支 `if cls == "global": return True`）。真正断的是 life 层两处消费：

| # | 断点 | 位置（基线 2090287） | 后果 |
|---|---|---|---|
| 1 | `_SALIENT_EVENTS` 白名单无 `WORLD_*` | `code/life/agent.py:41-45` + `:403` | 世界事件不进记忆 ⇒ 无 `MEMORY_WRITE`/`OBSERVATION` ⇒ "被看到"在账本里**零痕迹** |
| 2 | 对话提示词无世界参数 | `code/life/agent.py:1050-1069`（`_dialogue_prompt` / `_reply_prompt`） | 提示词里没有任何世界状态 ⇒ 措辞不可能提及 |
| 3 | `market_scarcity_bp` 无 life 侧消费点 | `code/life/agent.py:610-629`（只判"非空"） | 世界稀缺参数只是被读，不影响任何表达 |

复算命令（只读，零 LLM）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
git show 2090287:code/life/agent.py | sed -n '41,45p'          # 白名单（无 WORLD_*）
git show 2090287:code/life/agent.py | sed -n '400,406p'        # :403 的 continue
git show 2090287:code/life/agent.py | sed -n '1050,1070p'      # 两个 prompt 函数签名无世界参数
python3 - <<'PY'
import json
s=json.load(open('code/config/perception_scope.json'))['scope']
print({k:v for k,v in s.items() if k.startswith('WORLD')})       # {'WORLD_DIRECTIVE':'global','WORLD_GROUP_EVENT':'global'}
PY
```

---

## 1. 改动清单（文件:行 → 作用）

> commit `f7453564` 对 `2090287` 的 diff：7 个修改 + 4 个新增（含测试与证据脚本）。

| 文件 | 关键位置 | 作用 |
|---|---|---|
| `code/life/agent.py`（改） | `:31` `import world_awareness as WA` | 接线 |
| 同上 | `:145-152`（`__init__`） | 新增 agent-local 观测计数 `_wa_ctx/_wa_seen/_wa_observed/_wa_prompted/_wa_scarcity_prompted`（纯观测，不进 `state_hash`、不发事件） |
| 同上 | `:365`（`step()`） | 每回合 `self._scan_world(wv)`：把可见世界事件折成处境快照 |
| 同上 | `:411-436`（`_observe`） | **①白名单门控**：`if ev.type not in _SALIENT_EVENTS and not (is_world and self._wa_observe_on()): continue` —— 只放行 `WORLD_*`，**不动既有白名单集合**；世界事件写记忆时 `importance = max(imp, importance_min)`（确定性下限，不额外调 LLM） |
| 同上 | `:631-681`（新方法） | `_wa_on/_wa_observe_on/_wa_dialogue_on`、`_scan_world`、`_world_prompt_line`、`_world_ctx_payload` |
| 同上 | `:1058-1082`（`_dialogue_prompt` / `_reply_prompt`） | **③世界管道**：新增 `world_line` 形参，插在情绪行之后、收尾句之前；关闭时空串 ⇒ 拼接结果逐字不变 |
| 同上 | `:1030-1033`、`:1104-1107`（`_send_reply` / `_initiate`） | 生成时 `world_line=self._world_prompt_line()`；payload 追加 `world_ctx`（缺省不写键） |
| 同上 | `:1344-1353`（`_describe_event`） | **②人话描述**：`WORLD_*` 走显式分支 `WA.describe_event(t, kind, place)`，**不再落到**兜底 `f"{actor} 的 {TYPE} 事件。"` |
| `code/life/world_awareness.py`（新，~300 行） | 全文 | 纯函数 + 开关：`load_params/observe_on/dialogue_on/brief_lines/scarcity_line/prompt_context/describe_event`；有界（`window_rounds`/`max_lines`/`max_kinds`）、同 `directive_ref` 去重、确定性 |
| `code/config/world_awareness.json`（新） | 全文 | 开关文件（**不进 `engine_version` 指纹**；默认全关 ⇒ 旧日志指纹不受影响） |
| `code/orchestration/integration.py`（改） | `:184-190`（`_thread_fields`） | `world_ctx` **只追加**（缺省 None ⇒ 不写键），与 `dialogue_rift` 同构；`state_hash` 不含 event payload |
| 同上 | `:281-287`、`:325-340` | 从 `engine.config["world_awareness"]` 解析 `world_window_enabled`（默认 False）并传入索引；**`window_rounds=VISIBLE_WINDOW_ROUNDS(=2)` 一行未改** |
| `code/contracts/visibility.py`（改） | 新增 `world_event_in_window()` + `visible_events(..., world_event_window: bool = False)` | 世界事件 `[start,end)` 时间窗裁剪（**默认关**，见 §5） |
| `code/orchestration/visibility_index.py`（改） | `visible(..., world_event_window=False)` | 同一纯谓词叠加在**原有滑窗之外**（默认关；回归测试证明叠加后可见窗口仍为 30/31/32 三回合） |
| `code/engine/perceive.py`（改） | `world_event_window_enabled(config)` | 契约路径（L6）读取同一开关 |
| `code/engine/runner.py`（改） | `load_config()` | 把 `world_awareness.json` 并入运行配置（与 `world_director/time` 同模式） |
| `code/life/visibility.py`（改） | `visible_events(..., world_event_window=False)` | 透传开关（默认 False ⇒ 行为不变） |
| `code/tests/test_d8_world_awareness.py`（新，18 用例） | 全文 | 见 §4 |
| `v2/evidence/d8_tension_dose_recompute.py`（新） | 全文 | 剂量纯函数复算（零 LLM），见 §6。**性质：证据脚本，非代码改动**；因与实现同批提交才落入代码 commit `f7453564`（审计上应在文档/证据 commit，下次分开）。 |

---

## 2. 开关：确切键名 / 路径 / 写法

唯一文件：**`code/config/world_awareness.json`**（已 tracked，`git archive` 一定带得到）

```json
{
  "enabled": false,              // 总闸。A 臂=false；B 臂改 true
  "observe_enabled": true,       // ① 记忆/观测层（总闸开时生效）
  "dialogue_enabled": true,      // ② 提示词世界处境行（总闸开时生效）
  "scarcity_in_prompt": false,   // ③ 物价情境行（本轮不做）
  "world_window_enabled": false, // ④ 世界事件时间窗裁剪（本轮**不启用**）
  "window_rounds": 24, "max_lines": 2, "max_kinds": 3,
  "scarcity_min_bp": 1000, "importance_min": 4
}
```

- **① 与 ② 各自独立**（Leader 要求）：② 出问题可单独 `"dialogue_enabled": false`，① 仍生效，便于把副作用定位到具体层。
- 有效值 = 总闸 ∧ 子开关：`observe_on = enabled and observe_enabled`、`dialogue_on = enabled and dialogue_enabled`。
- env 逃生口（优先级高于文件）：`HITT_WORLD_AWARENESS=1|0`（总闸）、`HITT_WORLD_AWARENESS_OBSERVE=1|0`、`HITT_WORLD_AWARENESS_DIALOGUE=1|0`。
- **不启用** `config/world_director.json::enabled` 以外的任何世界层参数；世界导演总闸沿用 master 默认 `true`。

### 跑批时打开开关的准确命令（两臂各自独立副本）

```bash
# A 臂（基线）
git archive 2090287 | tar -x -C /tmp/armA            # 或 tools/t271/make_batch_copy.sh
# B 臂（本分支代码 + 只改总闸）
git archive f7453564ccab822b6f800b15a423bcf8b3425676 | tar -x -C /tmp/armB
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("/tmp/armB/code/config/world_awareness.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["enabled"] = True                                   # 只动这一行；其余保持默认
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(d, ensure_ascii=False, indent=2))
PY
# 等价 env 写法（不想改文件时）：
#   HITT_WORLD_AWARENESS=1  <跑批命令>
```

若 B 臂只想要 ①（不要 ② 的提示词改动）：额外把 `"dialogue_enabled": false`。

---

## 3. 账本侧可读字段（判据口径，给跑批/指标侧）

| 档 | 事件类型 | 关联字段 | 说明 |
|---|---|---|---|
| 世界事件发生 | `WORLD_DIRECTIVE` / `WORLD_GROUP_EVENT` | `directive_id` / `directive_ref`、`kind`、`start_round`/`end_round` | `GE` 是 `DIRECTIVE` 的派发视图（`hooks/world_director.py:35-49`），`GE` 多一个 `directive_ref` 指回 `D-*` |
| 被观察到（通路 A） | `OBSERVATION`（`agent.py::_observe`） | **`target_event_seq`** → 世界事件 seq | 本分支打开 ① 后才出现；关闭时 0 |
| 被记忆沉淀（**M-0 主判据**） | `MEMORY_WRITE` | `source_event_seq`、`refs=[str(seq)]`、`importance` | 建议只用这条做 M-0 |
| 被对话上下文带到 | `MSG_DM` / `MSG_PUBLIC` / `MSG_GROUP` | 追加键 **`world_ctx = {v:"d8/1", refs, kinds, scarcity, prompted}`** | A 臂无此键；`prompted=true` 表示该条生成时确实带了世界行 |
| 措辞真的提及（**弱判据**） | 同上 | `body` 里的 kind 中文词 | 由指标脚本判，代码内**未**做词表判定 |

⚠ **OBSERVATION 的两条通路（口径务必照抄，别简化）**：
世界事件本轮**只经一条通路**产生 `OBSERVATION`：`agent.py::_observe → INTENT.OBSERVE →`
`orchestration/integration.py:613-622`（`_do_observe`）。第二条通路 `life/settlement.py:608-627`
（`_SIGNIFICANT = {"AGENT_DIED","SEED_EVENT","NORM_VIOLATED","MARKET_TRADE","TRANSFER"}`，`:609`）
**完全未改且不含任何 `WORLD_*`** ⇒ **该通路本轮不会产生世界事件 OBSERVATION，期望值为 0**。

因此：
- M-0 主判据**只认 `MEMORY_WRITE`**（`source_event_seq` 指向世界事件 seq）。
- `OBSERVATION` 读数仍**按通路分列出表**；settlement 通路者**期望 0**，若不为 0 即为未预料路径，**须停下排查**，不得解释成"机制生效"。
- 两条通路的 OBSERVATION 都写 `target_event_seq`，可用「是否存在同 `(agent_id, round, target_event_seq)` 的 `MEMORY_WRITE`（且 `importance ≥ 4`）」或 `salience` 取值把 `agent.py` 通路与 settlement 通路（`salience=3/6`）区分开。

---

## 4. 单测 / 门禁输出原文

```text
$ cd code && python3 -m pytest tests/test_d8_world_awareness.py -q
..................                                                       [100%]
18 passed in 5.57s
```

```text
$ cd . && python3 -m pytest code/tests/test_d8_world_awareness.py \
      code/tests/test_visibility_single_source.py code/tests/test_visibility_index.py \
      code/tests/test_t353_world_params.py code/life/tests/test_t364_world_params_consume.py \
      code/tests/test_world_director.py code/tests/test_dialogue_repair.py -q
...................................................                      [100%]
51 passed in 16.77s
```

```text
$ make verify
...
660 passed, 1 skipped in 244.53s (0:04:04)      # 仓根 pytest
11 passed in 0.03s                             # plugin-skeleton
...                                            # lexicon / inert 棘轮全绿
CI GATE: PASS                                  # code/ 前端 CI（smoke + 真渲染 + R9 + D 段）
[verify-guard] OK：世界层与前端跑中均未变，门结果可信。
```

> **环境备注（照实记录，给复算者的路标）**：本分支工作树里 `code/frontend/sample/*.jsonl` 被 `.gitignore`
> 忽略（`.gitignore:8: **/*.jsonl`）、未随 `git worktree add` 落地，因此**第一次 `make verify` 是失败的**：
> 前端渲染门报 `Error: ENOENT ... code/frontend/sample/demo_run.jsonl` 与 `... run_c_n20.play.jsonl`，
> `CI GATE: FAIL`、`make verify` exit=2（世界层 pytest 部分当时已 660 passed）。
> 之后把主树这些 jsonl 拷进工作树（**被 gitignore 忽略，不进 commit，不影响代码**）再复跑，才 `CI GATE: PASS`。
> 准确表述是：「**第一次 verify 因环境缺件失败，补件（被 .gitignore 忽略的测试样本）后通过**」，
> 不是"verify 一次就通过"。第三方在自己的干净 checkout 里复算**也会撞同一个 ENOENT**，按上面两步补齐即可。

**18 个用例覆盖（对应 Leader 硬门槛）**

1. `test_memory_text_is_human_no_internal_tokens` —— 记忆正文**不含** `WORLD_` / `DIRECTIVE` / `GROUP_EVENT` / `wd.` / `_bp` / `D-30` / `GE-` / `seq:`，且不含"你该/必须/建议/所以/价格/赢/输"。
2. `test_two_world_event_types_use_distinct_templates` —— 两型描述**句子不同**（公告口吻 vs 街坊口吻），避免同一事件写两条近似文本挤占记忆。
3. `test_describe_event_not_fallback_for_world_types` —— `_describe_event()` 返回值 **≠** 兜底 `f"{actor} 的 {TYPE} 事件。"`，且等于显式分支文本。
4. `test_prompts_byte_identical_to_baseline_when_off` —— **逐字 diff**：开关全关时 `_dialogue_prompt` / `_reply_prompt` 与 2090287 的公式拼接结果字符串相等。
5. `test_observe_off_writes_nothing_for_world_events` / `test_observe_on_writes_memory_and_observation` —— ① 关=0 条；① 开=`MEMORY_WRITE`+`OBSERVATION(target_event_seq=该 seq)`。
6. `test_dialogue_prompt_untouched_when_off` / `test_dialogue_prompt_has_world_line_and_payload` —— ② 关无世界行、无 `world_ctx`；② 开有行且 `world_ctx.v == "d8/1"`。
7. `test_world_event_in_window_predicate` / `test_contract_visible_events_clips_expired_world_events` / `test_visibility_index_clips_expired_world_events` / `test_overlay_does_not_narrow_the_real_2round_window` —— 时间窗谓词正确；**叠加后可见窗口仍是 30/31/32**（`window_rounds=2` 未被改动、无回归）。
8. `test_gate_off_no_world_ctx_offline_mock` / `test_gate_on_runs_and_replays_offline_mock` —— 离线 mock 端到端：关=日志无 `world_ctx` 且可重放；开=可跑可重放、字段 schema 合法。
9. 纯函数有界/确定性/去重：`test_brief_lines_bounded_dedup_and_deterministic` 等 3 例。

---

## 5. 「过期事件还会不会出现在 visible_events 里」——明确回答

**主跑批路径：本来就不会（与本次改动无关）。**
`KernelAdapter.perceive` → `visibility_query` → `VisibilityIndex.visible(window_rounds=VISIBLE_WINDOW_ROUNDS)`
，`VISIBLE_WINDOW_ROUNDS = 2`（`code/orchestration/integration.py:276`）。因此 world event（如 tension，`round 30, end 36`）
在 `t=30/31/32` 可见、`t≥33` 不可见。**我未改动 `window_rounds` 及其裁剪逻辑（一行没动）**。

**L6 路径（`life/settlement.py:620` → `life/visibility.visible_events` → `contracts.visible_events`）原本无时间维**，
过期世界事件在该路径上仍可见。本分支已实现 `[start,end)` 裁剪（纯谓词 `contracts.visibility.world_event_in_window`，
口径与 `engine/world_params.py` 的 `start <= t < end` 一致，**不硬编码 6**，tension 那条自然得到 30–35）。

**本轮不启用该裁剪**（`world_window_enabled=false`）：主跑批已有 2 回合滑窗，启用只是多一个变量。
→ 该修复是**已实现但本轮未启用的死代码**，留待后续单独修/单独消融。报告与结论**不得**把它算进本轮效果。

**可复算验证（命令 + 期望输出）**

```bash
# 1) 纯谓词：过期即 False
python3 - <<'PY'
import sys; sys.path.insert(0,'code')
from contracts.visibility import world_event_in_window as w
rec={"seq":1,"round":30,"type":"WORLD_GROUP_EVENT","payload":{"start_round":30,"end_round":36,"directed":True}}
print([w(rec,t) for t in (29,30,35,36,40)])
PY
# 期望：[False, True, True, False, False]

# 2) 真实路径滑窗：可见回合必须是 30/31/32（与本分支改动无关）
python3 -m pytest code/tests/test_d8_world_awareness.py::test_overlay_does_not_narrow_the_real_2round_window -q
# 期望：1 passed

# 3) 关闭时的默认等价（含可见性）：开关全关的世界里，世界事件不进任何 MEMORY_WRITE/OBSERVATION
python3 -m pytest code/tests/test_d8_world_awareness.py -q -k "off or baseline"
# 期望：全 passed
```

---

## 6. 剂量（tension）：纯函数复算，不改

```bash
$ python3 v2/evidence/d8_tension_dose_recompute.py            # 84 回合
curve/prob        prob_bp     E[触发]      E[生效回合]
conservative           40     0.336        2.016  <== 当前
moderate               80     0.672        4.032
aggressive            160     1.344        8.064
$ python3 v2/evidence/d8_tension_dose_recompute.py --rounds 60
conservative 下 E[触发]=0.240
```

结论：`dose_curve=conservative` 把 `prob_bp=80` 缩放到 40 bp ⇒ 84 回合期望触发 0.336 次，观测到 1 次完全在
Poisson 波动内（P(≥1)=28.5%），**不构成"机制坏了"的证据**。本轮**不建议**改阈值：改剂量=改世界层，
会与 D8 的上下文接通混批，A/B 归因失效 → 写入"下一轮建议"。

---

## 7. 局限 / 诚实边界

1. **效果未验证**：没有任何"提及率变高/生活气息更好"的读数，需 A/B（`#d-dim-verify`）。
2. **两种世界事件是派生关系**：`GE` 只是 `D` 的派发视图，同一 `directive_ref` 会在 ① 打开时写两条记忆
   （文本不同，但语义近）。计数请按 `directive_id/directive_ref` 去重。
3. **`market_scarcity_bp` 的消费点本轮默认关**（`scarcity_in_prompt=false`）：定价 / `_scarcity_index` **完全未动**（按 Leader 裁决，属下一轮独立开关 + 独立消融）。
4. **`world_window_enabled` 本轮默认关**（详见 §5），不得计入本轮功效。
5. **OBSERVATION 通路**：世界事件只经 `agent.py::_observe → integration.py:613-622` 一条通路产生 OBSERVATION；
   `settlement.py:608-627 _SIGNIFICANT` **未改且不含 `WORLD_*`** ⇒ 第二通路**本轮期望为 0**（非 0 即未预料路径，须停下排查）。
   M-0 只认 `MEMORY_WRITE`；OBSERVATION 分路列出、不相加。
6. 观测计数（`_wa_*`）是 agent-local 内存量，**不发事件、不进 `state_hash`**，只用于自检与后续埋点参考；本轮结论证据一律取账本事件，不取这些计数。
