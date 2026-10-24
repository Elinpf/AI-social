# D2.7 mock 验证（旁白放开）——①prompt sha ✅ ②逐字 diff ✅ ③mock 端到端**不可测**，已用替代验证部分覆盖

- 分支 `feat/d27-narration` @ `4123628`（**实现由 `life-dim-dev` 完成**，只改 `code/life/agent.py` 2 行；我本次做的是**验证**，未改写实现）
- 预登记：`v2/refs/D27-amendment1-merge-duplicate-prereg.md`（`d24e3fd`，主判据 = `P1 具体性`；`L-7` 降幅降级为并列增益）

## 1. `prompt_fn_sha256` 前后 ✅（确实改了到提示词）

| 树 | `prompt_fn_sha256` |
|---|---|
| master（改前） | `47623c9de7f418b003e3e2a2ffeb5647f260034bf721c094496afa55c3564f58` |
| **`feat/d27-narration` @ `4123628`** | **`f553b4c4b906b31e2176be96378cd44d9213276bb896a602c7395af2643bf95a`** |

- 分项：dialogue `58f2bb53f36ebb98…`、reply `7cccd6685065ce0e…`（两处都变 ⇒ 两处收尾指令都改到了）
- 复算命令：
  ```bash
  cd <tree>/code && PYTHONPATH=. python3 -c "
  import hashlib
  from orchestration.integration import build_world
  w=build_world(seed=42,n=2); ag=w['agents'][0]; pid=ag.agent_id
  partner=[p for p in ag.peers if p!=pid][0]
  dlg=ag._dialogue_prompt('gift',[pid,partner]); rep=ag._reply_prompt(partner,'gift',[(partner,f'{partner}：来，尝尝这个。')])
  print(hashlib.sha256((dlg+'\n===\n'+rep).encode()).hexdigest())"
  ```

## 2. 两处收尾指令的逐字 diff ✅（**只改旁白半段**）

`git diff master -- code/life/agent.py` 全文只有 2 处、各 1 行（`@@1450` initiate / `@@1475` reply）：

```diff
- 只写台词本身（一句家常话）：不要用括号、方括号或星号写动作、神态或心理旁白，不要解释也不要总结；用口语短句，别反复用同一句口头禅。
+ 只写台词本身（一句家常话）：句首可用一个括号写一个具体的动作或神态（如“（把烟袋往桌上磕了磕）”），一句只一个、不超过 15 字；不要写心理活动，不要解释也不要总结；用口语短句，别反复用同一句口头禅。
```
```diff
- 只写台词本身（接着刚才的话往下说一句）：不要用括号、方括号或星号写动作、神态或心理旁白，不要解释也不要总结；用口语短句，别反复用同一句口头禅。
+ 只写台词本身（接着刚才的话往下说一句）：句首可用一个括号写一个具体的动作或神态（如“（把烟袋往桌上磕了磕）”），一句只一个、不超过 15 字；不要写心理活动，不要解释也不要总结；用口语短句，别反复用同一句口头禅。
```

**未改的四段逐字保留**：`只写台词本身（…）`、`不要解释也不要总结`、`用口语短句，别反复用同一句口头禅`、以及括号里的场景说明（initiate「一句家常话」/ reply「接着刚才的话往下说一句」）。
**唯一新增的限定**：`一句只一个、不超过 15 字` + 示例 `（把烟袋往桌上磕了磕）` + `不要写心理活动`（替代原先"连旁白一起禁"）。

## 3. mock 第三项 `paren_rate > 0`：**原判据不可测 + 替代验证**（2026-10-24 16:29–16:30，晚于 B 收批 16:23:24）

> 判定标签：**不是 ✅ 通过、也不是 ❌ 失败，而是「原判据不可测」**；第 3.3 节是**替代验证**，只证明"括号在渲染链路未被剥落"，**不能**充当原判据的通过证据。

### 3.1 起跑纪律
`pgrep -af "orchestration|run_batch"` 实测为空（无并发），`setsid` 起跑，不写 worktree 任何文件（产物落 `/tmp`）。

### 3.2 如实跑 mock 批（结果：`paren_rate = 0.00%`，**但这不能判机制失败**）
- 命令（在 B 树 `code/` 下）：
  `env -u HITT_LLM_PROVIDER PYTHONPATH=. python3 -m orchestration run --life --seed 42 --agents 6 --rounds 12 --out /tmp/d27_mock_paren/run.jsonl --flush-every 2 --side-root /tmp/d27_mock_side`
- 规模/时刻/退出码：n=6 r=12，`events=3016`，耗时 **0.96s**，收批 `2026-10-24T16:30` 前后，rc=0
- 读数：`n_msgs=37`、**`paren_rate = 0.00%`**

**为什么这个 0.00% 是结构性的**（不是接线失败，**假阴性**）：
- `code/freeze/providers.py:104-112` 的 `_NL_POOLS["dialogue"]` → `_DIALOGUE_POOL`（`:85-90`）是**4 条固定句子，一条括号都没有**；
- `_mock_nl_text()`（`:115-121`）用 `sha256(purpose+system+user)` 从池里**按下标取一句**，**prompt 内容完全不参与生成**。
⇒ mock 路径的 `paren_rate` 与提示词改动**结构性无关，恒为 0**。

### 3.3 可判定的替代测试：mock 链路会不会把括号旁白剥掉？—— **不会（paren_rate = 100.00%）**
- 做法：monkeypatch `freeze.providers.MockProvider`，注入 responder 对 `dialogue/negotiation` 返回「（把烟袋往桌上磕了磕）这话我记下了。」，其余用途沿用原池；`integration.py` 在函数内 import，故猴补生效。
- 脚本：`/tmp/d27_mock_paren_inject.py`；日志 `/tmp/d27_mock_inject/run.jsonl`
- 规模/耗时：n=6 r=12，`events=3016`，**0.81s**，rc=0
- 读数：**`paren_rate = 100.00%`，37/37 条 MSG 以 `（…）` 起头**，正文逐字保留
- 结论：**mock 链路不存在剥落/清洗环节**——上游给什么就落什么。与真实 B 臂 `paren_rate=100.00%` 一致。

### 3.4 定位（三层各自独立，不可互替）
| 层 | 由谁证明 | 证到什么 |
|---|---|---|
| **机制层** | 本节 3.3 替代验证 | 括号旁白在 agent→MSG 渲染/落盘链路**未被剥落**（37/37） |
| **mock 端到端层** | 本节 3.2 | **不可测**（mock provider 不读 prompt，池内 4 句无括号）⇒ 下一轮需补 mock 样本 |
| **运行期层** | 验收方 `v2/evidence/d27_gate_prediction_prereg.md` + `reports/D27-旁白放开.md` §5 | 真 LLM 下新 prompt 真进模型（dialogue `tokens_in` 均值 292.04→310.80，灰区结算后判生效） |

> 详细数值与判定见 `reports/D27-旁白放开.md`（同 `v2/evidence/d27_result.md`）。
