# 结构约束：同一回合内同一个线程只能有一个发言者 ⇒ `lag = 0` 恒不可能

> 立件：Leader（team-leader）｜2026-10-29
> 性质：**只读分析**（零跑批、零改码），两臂交叉验证，可逐条复算
> 输入：`mock_d9b_rw2_ctrl_n16r84_seed42/run.jsonl`（`bd00afd9…`）、`run_d1_f6off_seed42_n16r84/run.jsonl`（真 LLM OFF 对照臂）
> 上游：`d9b_reply_window_on_A1_base_result.md`（窗口 2→4 零差异）、`D9c-prereg-reply-pick-order.md`（挑选顺序）

## 0. 一句话

**663 条回复里 `lag=0` 有 0 条；43 组「同一线程同一回合出现多条消息」的作者全部是同一个人（43/43）。真 LLM 臂独立复现同一形态（27/27）。** ⇒ 「即时往返」（A 说一句、B 当回合就接）在当前架构下**结构上不可能**，不是参数没调好。

## 1. 两臂交叉验证（关键：一个是 mock、一个是真 LLM，参数也不同）

| 项 | mock ctrl（`rw=2`） | **真 LLM `d1_f6off` r84（OFF 对照臂）** |
|---|---|---|
| MSG 总数 | 929 | 686 |
| 回复条数（带 `reply_to` 且父消息可索引） | 663 | 480 |
| **`lag` 分布** | `{1: 656, 2: 7}` | **`{1: 327, 2: 153}`** |
| **`lag = 0` 条数** | **0** | **0** |
| 「同一 `(thread_id, round)` 出现多条 MSG」组数 | 43 | 27 |
| 其中 author **全是同一人** | **43 / 43** | **27 / 27** |
| 其中 author 有 ≥2 个不同人 | **0** | **0** |
| 父消息与回复同 `round` | **0** | **0** |

两臂唯一的共同点是**架构**，代码配置、provider、规模全都不同 ⇒ **这是结构约束，不是 mock 产物、也不是某个参数没调**。

**附带发现（对 D9c 有用）**：真 LLM 臂 `lag=2` 占 **153/480 = 31.88%**，mock 臂只占 7/663 = 1.06%。⇒ **"晚一轮才回"在真 LLM 下是常见行为**（模型自己会选），mock 下几乎不会。这意味着 D9c 的 mock 判读**只能证"开关是否改变了结构"，不能证"真人式的延迟回复会不会自然出现"**——后者必须看真 LLM 臂。

## 2. 机制定位（**标注：机制假设，未逐行验证 emit/fold 时序**）

- `code/orchestration/integration.py:341 perceive()`：`r = st.round`，随即 `recs = self.visibility_query(agent_id, r, ...)` ⇒ 可见集是**以当前 round 为上界的一次快照**。
- `code/engine/kernel.py:199 phase_decide()`：注释「life 模式下调用被注入的 `agent.step()`（**经 IF-2 即时入缓冲**）」——**入缓冲**，未声明即时折叠进账本。
- 对照 `phase_life()` 的注释：「**逐 hook 即时折叠**——后续 hook 必须看到前面 hook 产出的已折叠事件」。

⇒ 合理推断：**`phase_decide` 内各 agent 依次 `step()`，先 step 者产出的 MSG 只在缓冲里、尚未折叠**，故后 step 者的 `perceive()` 快照里看不到它 ⇒ 同回合无法接话。

**这条是推断，不是已验证的实现事实。** 要坐实须读 `_emit` 与缓冲折叠的确切时机（`kernel._emit` / `Ledger` fold 调用点），本件未做——**因为它不影响本件结论**：结论已由两臂数据直接观测（43/43、27/27、0/663、0/480），机制只是解释。

## 3. 对已做实验的直接影响（必须并读，不得单独引用 D9b/D9c）

1. **D9b（窗口 2→4）**：`lag` 上界只有 2，而窗口是「**超过 N 轮就不许回**」。既然 `lag` 实测 ≤ 2（两臂均在 `recent_first` 下），窗口 ≥ 2 就永远不是约束。
   - **限定（2026-10-29 追加，因 D9c 复算出反例）**：只能说「**在 `recent_first` 与当前结构下**，窗口 ≥ 2 恒非约束」。**不得**升格为「上界由结构决定」——D9c 实测 `lag_turn` 上界随挑选顺序 **1→2 变化**，说明上界至少在某些维度**可以**被参数改变。D9b 的零差异是「该顺序下 `lag` 已顶到 2」的结果，不是「上界不可动」的证明。
   - 仍然成立的那半句：**不得**因此把窗口类参数一律判死——它们只是被卡在了无作用区。
2. **D9c（挑选顺序）**：可动范围也只有 `lag ∈ {1, 2, …}`，**改顺序最多把回复推到 lag=3/4，永远推不到 lag=0**。所以 D9c 的价值上限是"**让回复晚一点到**"，**不是**"让对话变成即时往返"。
3. **一切"回复时机"类参数都无法产出 `lag=0`**。若北极星目标里含"像真人那样你一句我一句立刻接上"，那**加参数解决不了**。

## 4. 若要突破，代价与风险（**未预登记，仅列选项，不推荐执行**）

| 选项 | 做法 | 代价/风险 |
|---|---|---|
| **A. 让 `phase_decide` 内消息即时折叠** | 先 step 者产出的 MSG 立即进账本，后 step 者 `perceive` 能看到 | **最高风险**：账本顺序与确定性重放强耦合（`replay_parity` / `chain_ok` / 守恒闸）；同回合内账本随 step 顺序增长，可能破坏 `first_run_equals_replay` |
| **B. 回合内多轮子相位** | 在一个 round 内设 k 个子轮，A→B→A 可在同 round 内完成 | 改的是**回合语义**，波及所有按 round 计的口径（R 值、lag、窗口、`max_turns_per_round`），等于重定义坐标系 ⇒ 全部历史读数不可比 |
| **C. 不改内核，改"回合长度"** | 把 slot/round 的时间粒度调细（同一 slot 拆两个子回合） | 看似温和，实则同 B：`round` 语义变化，历史不可比 |
| **D. 接受现状，转向"语言层"** | 不动时序，把"生活气息"做在**措辞与内容**上（迟到补白、忙完才想起、话题跳转、误会与和解） | 不破确定性，但**无法产出即时往返**；且需真 LLM 批验证 |

**我的倾向：先 D，不碰 A/B/C。** 理由：A/B/C 都会让现有全部读数（R 值、lag 分布、`≥3 轮` 占比、各臂对照）**失去可比性**，而项目当前最值钱的东西恰恰是"一批可比的历史臂 + 一套已校准的口径"。在语言层还没验证过"内容够不够生活"之前，先动坐标系，等于把已有的尺子全扔了。

## 5. 边界与局限

1. 两臂都**不是**"同回合可见"的对照组（没有这样的臂存在）⇒ 本件是**观测约束**，不是**干预实验**，**不能**说"若改成同回合可见，对话会更好"。
2. `lag` 的两种口径在本件不混用：本件一律用 `lag_round`（`round` 差）。`lag_turn`（`turn_index` 差）见 `d9b_metrics_recalc_by_verifier.md`。
3. 真 LLM 臂的 `lag=2` 占 31.88% 是**该臂配置下**的值，不得当作"真人延迟回复率"的估计。
4. 本件**不改**任何预登记、不改 D9b/D9c 判定；只在引用它们时**必须并读本件第 3 节**。

## 6. 复算（一行可跑）

```bash
python3 - <<'PY'
import json, collections
for p in ['v2/evidence/mock_d9b_rw2_ctrl_n16r84_seed42/run.jsonl',
          'v2/evidence/run_d1_f6off_seed42_n16r84/run.jsonl']:
    msgs=[]; by_uid={}
    for l in open(p):
        d=json.loads(l)
        if d['type'].startswith('MSG'):
            pp=d['payload']; msgs.append((d['round'],pp))
            if pp.get('msg_uid'): by_uid[pp['msg_uid']]=d['round']
    lags=[r-by_uid[m['reply_to']] for r,m in msgs if m.get('reply_to') in by_uid]
    g=collections.defaultdict(list)
    for r,m in msgs: g[(m['thread_id'],r)].append(m)
    multi=[v for v in g.values() if len(v)>1]
    print(p.split('/')[-2], dict(sorted(collections.Counter(lags).items())),
          'lag0=',sum(1 for x in lags if x==0),
          'multi=',len(multi),'same_author=',sum(1 for v in multi if len({x['author'] for x in v})==1))
PY
# 期望：{1:656,2:7} lag0=0 multi=43 same_author=43
#       {1:327,2:153} lag0=0 multi=27 same_author=27
```
