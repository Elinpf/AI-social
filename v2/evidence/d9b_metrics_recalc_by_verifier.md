# D9b 指标核算（M1–M4）· 核验方独立复算

> 作者：`repro-verifier`（核验方，**不做档位判断**）｜2026-10-29｜只读两臂日志，不跑批、不调 LLM、不改 `code/`
> 预登记口径依据：`v2/refs/D9b-prereg-reply-window-A1-base.md`（`seed=42/n=16/rounds=84/max_turns=6/provider=mock`）
> 任务方给的臂名：`run_d9b_after_n16_seed42` / `run_d9b_before_n16_seed42`（**实际不存在**，见 §0）

---

## 0. 输入定位（**与任务方给的路径不符，先报后算**）

```
$ ls -la runs/
ls: cannot access 'runs/': No such file or directory        ← 任务方给的 runs/<arm>/run.jsonl 不存在

$ ls -d v2/evidence/*d9b*
v2/evidence/d9b_reply_window_on_A1_base_result.md
v2/evidence/mock_d9b_rw2_ctrl_n16r84_seed42
v2/evidence/mock_d9b_rw4_treat_n16r84_seed42

$ ls -la mock_d9b_rw2_ctrl_n16r84_seed42/ mock_d9b_rw4_treat_n16r84_seed42/
  93194531 B  11:43  run.jsonl          ← 仅 run.jsonl，**无 meta.json**
  93194531 B  12:11  run.jsonl          ← 同上

$ sha256sum 两臂 run.jsonl
bd00afd983c79dc7d4e141ec2f891128d17c25f3115311ca2910e534e93f3a8c  mock_d9b_rw2_ctrl_n16r84_seed42/run.jsonl
4a6aca5df1ffc21a870b9a8ccb6d970606fd777be82b156db621ae8bf2748a88  mock_d9b_rw4_treat_n16r84_seed42/run.jsonl
```

| 臂 | 目录（实） | run.jsonl sha256 | 字节 | 行数 | mtime |
|---|---|---|---|---|---|
| ctrl（rw=2） | `mock_d9b_rw2_ctrl_n16r84_seed42` | `bd00afd9…93f3a8c` | 93,194,531 | 197,771 | 2026-10-29 11:43 |
| treat（rw=4） | `mock_d9b_rw4_treat_n16r84_seed42` | `4a6aca5d…2748a88` | 93,194,531 | 197,771 | 2026-10-29 12:11 |

**两处输入口径问题（不影响本次计算，但必须记）**：
1. **臂名/路径不符**：任务方给 `runs/run_d9b_*_seed42`，磁盘实为 `v2/evidence/mock_d9b_rw{2,4}_*_n16r84_seed42`。本次按**实际存在的两目录**算（且其与预登记 §1 的 `{2,4}` 单变量对应）。
2. **`meta.json` 缺失**：两目录只有 `run.jsonl`。⇒ 本次**不做 meta 对拍**（seed/n/rounds 只能从日志推），也不写"meta 一致"。

---

## 1. M1 回复间隔分布（**两口径并列，不合并**）

任务方口径为"相邻回合间隔（`turn_index` 差）"；预登记 §3.3 口径为"回复所在 `round` − 父消息 `round`"。二者**不同物**，故分列：

| 口径 | n（reply_to 非空且父可达） | 分布 | 计数 | `lag ≥ 3` 绝对条数 |
|---|---|---|---|---|
| **M1a `lag_round`**（预登记 §3.3 口径） | 663 | mean 1.01 / p50 1 / p90 1 / max **2** | `{1: 656, 2: 7}` | **0** |
| **M1b `lag_turn`**（任务方口径） | 663 | mean 1.00 / p50 1 / p90 1 / max **1** | `{1: 663}` | **0** |

- **两臂 M1a/M1b 逐格完全相同**（ctrl 与 treat 计数一字不差）。
- `reply_to` 非空 663 条，**父消息找不到（悬空）= 0**。
- 预登记 §5 反事实 3（ctrl 出现 `lag ≥ 3` ⇒ 单变量前提作废）：**未触发**（ctrl `lag_round≥3` = 0）。

## 2. M2 线程长度分布（`R` = 唯一 `turn_index` 个数）

| 项 | ctrl | treat |
|---|---|---|
| 线程数 | **266** | **266** |
| R 分布 | mean 3.09 / p50 1 / p90 6 / max 6 | 同 |
| R 计数 | `{1:139, 2:7, 3:8, 4:11, 5:4, 6:97}` | 同 |
| `R ≥ 3` 绝对条数 / 占比 | **120 / 266 = 45.11%** | **120 / 266 = 45.11%** |

## 3. M3 尾截断候选（卡面公式实际口径，**不用 census 的 θ=66**）

判定式：`min_round + T − 1 ≥ maxround`，`T` = 该线程实际轮数（此处取唯一 `turn_index` 数 `R`），`maxround` = 本 run 最大 `round` = **83**。

**结果：两臂各 3 条（不是 0 条）**，且两臂明细完全相同：

| thread_id | min_round | max_round | R (=T) | last_turn_index | 台词行 |
|---|---|---|---|---|---|
| `TH-P005-Gplace-plaza-78` | 78 | 83 | 6 | 5 | 10 |
| `TH-P007-P006-80` | 80 | 83 | 4 | 3 | 4 |
| `TH-P016-Gplace-plaza-78` | 78 | 83 | 6 | 5 | 24 |

**复核结论与任务方所述"全批 0 条"不一致**。差异原因须分开看（此点涉及判读口径，我只列事实、不裁）：
- 命中的 3 条**恰等于**"触及最后一轮（`round=83`）的线程数 = 3"（两臂均 3），说明公式命中的就是末轮触顶者；
- 其中 2 条 `R=6` = `max_turns` 上限（`turn_index` 已用满 0–5）⇒ **被 turn 上限结束**，非"被 run 末尾截断"；
- 1 条 `R=4`（`last_turn=3` < 上限 5）在末轮结束 ⇒ **是"可能被截断"的真候选**。
- ⇒ 若判读需要"尾截断 ⇒ 后续没机会出现"，**建议按 `R < max_turns` 再筛一次**（本批即 3 → **1**）；若按公式字面，则 **3**。**两值并列，不合并。**
- 对本次"两臂零差异"结论**无影响**（两臂同 3 条、同明细）。

## 4. M4 真跑门禁（**本批为 mock 臂，门禁必 FAIL——这是预期，不是缺陷**）

```
$ python3 -m obs llm-cost --log <arm>/run.jsonl                       → rc=0
$ python3 -m obs llm-cost --log <arm>/run.jsonl --require-provider mock          → rc=0
$ python3 -m obs llm-cost --log <arm>/run.jsonl --require-provider openai_compat → rc=1
  provider_guard: {"by_provider":{"mock":3647},"expected":"openai_compat","ok":false,
    "problems":["出现非预期 provider：['mock']（预期仅 openai_compat）","预期 provider openai_compat 计数为 0"]}
```

| 项 | ctrl | treat |
|---|---|---|
| provider 集合（`LLM_CALL.payload.provider`） | `{'mock': 3647}` | `{'mock': 3647}` |
| model 集合 | `{'mock-1': 3647}` | `{'mock-1': 3647}` |
| `--require-provider openai_compat` rc | **1** | **1** |
| cached / total calls | 1664 / 3647 | 1664 / 3647 |

⇒ **M4 结论：两臂均 100% mock，无任何真 provider**。按"真跑"标准记 **FAIL（不适用）**；**不得写 PASS**。与预登记 §1「`provider=mock`、未 source `.env.local`」一致，属**设计如此**。预登记 §2 已限定：mock 下**只能看结构量**，不得对"生活气息"下结论。

## 5. 与既有结果件的交叉核对（不做判定）

既有件 `v2/evidence/d9b_reply_window_on_A1_base_result.md` 记「`MSG` 总数两臂 929、197,771 行、两臂 sha 不同」，我这边独立算出：**MSG=929（DM 643 / GROUP 195 / PUBLIC 91）、197,771 行、sha 各异**——**三项对得上**。该件的判定（T-不可判）属档位/判定范畴，**本件不作判断**。

## 6. 复算命令（自包含）

```python
import json, statistics, collections
def pct(v,q):
    s=sorted(v); k=(len(s)-1)*q; lo,hi=int(k),min(int(k)+1,len(s)-1)
    return s[lo]+(s[hi]-s[lo])*(k-lo)
def run(path):
    msgs=[]; prov=collections.Counter(); mx=-1; nl=0
    for line in open(path,encoding="utf-8"):
        nl+=1
        try: r=json.loads(line)
        except Exception: continue
        t=r.get("type")
        if t and t.startswith("MSG_"):
            p=r.get("payload") or {}
            msgs.append({"uid":p.get("msg_uid"),"rt":p.get("reply_to"),"th":p.get("thread_id"),
                         "ti":p.get("turn_index"),"round":r.get("round")})
        elif t=="LLM_CALL":
            prov[str((r.get("payload") or {}).get("provider"))]+=1
        if isinstance(r.get("round"),int) and r["round"]>mx: mx=r["round"]
    by={m["uid"]:m for m in msgs if m["uid"] is not None}
    lr=[]; lt=[]
    for m in msgs:
        if not m["rt"]: continue
        par=by.get(m["rt"])
        if par is None: continue
        if isinstance(m["round"],int) and isinstance(par["round"],int): lr.append(m["round"]-par["round"])
        if isinstance(m["ti"],int) and isinstance(par["ti"],int): lt.append(m["ti"]-par["ti"])
    th=collections.defaultdict(list)
    for m in msgs: th[m["th"]].append(m)
    R=[]; trunc=[]
    for k,l in th.items():
        r_=len({m["ti"] for m in l if isinstance(m["ti"],int)}); R.append(r_)
        rs=[m["round"] for m in l if isinstance(m["round"],int)]
        if rs and min(rs)+r_-1>=mx: trunc.append((k,min(rs),r_))
    print(path,"lines",nl,"MSG",len(msgs),"threads",len(th),"maxround",mx)
    print(" M1a lag_round",dict(sorted(collections.Counter(lr).items())),"max",max(lr))
    print(" M1b lag_turn ",dict(sorted(collections.Counter(lt).items())),"max",max(lt))
    print(" M2 R",dict(sorted(collections.Counter(R).items())))
    print(" M3 trunc",trunc)
    print(" M4 provider",dict(prov))
run("v2/evidence/mock_d9b_rw2_ctrl_n16r84_seed42/run.jsonl")
run("v2/evidence/mock_d9b_rw4_treat_n16r84_seed42/run.jsonl")
```

**实际输出（两臂）**：
```
 lines 197771  MSG 929  threads 266  maxround 83
 M1a lag_round {1: 656, 2: 7} max 2
 M1b lag_turn  {1: 663} max 1
 M2 R {1: 139, 2: 7, 3: 8, 4: 11, 5: 4, 6: 97}
 M3 trunc [('TH-P005-Gplace-plaza-78', 78, 6), ('TH-P007-P006-80', 80, 4), ('TH-P016-Gplace-plaza-78', 78, 6)]
 M4 provider {'mock': 3647}
（treat 臂逐行相同）
```

---

## 7. 本件不做 / 不成立的事

- **不判档位**（V/W/I+/T/I- 五档不做，交判定方）；不报 κ（本批无判读者）；
- 不写"meta 一致"（meta.json 缺失）；
- 不把 mock 臂的结果外推到语言侧；
- 不合并两臂数字，不合并 M1 两口径，不合并 M3 的 3 / 1 两值。
