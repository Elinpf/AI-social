# D9c 独立复算（核验方）：挑选顺序 `recent_first → oldest_first`

> 作者：`repro-verifier`（核验方，**不做档位判定**）｜2026-10-29｜只读两臂日志，不跑批、不调 LLM、不改 `code/`
> 被核对象：`v2/evidence/d9c_reply_pick_order_result.md`（`f062040ad63f589f5d4c7a74ff042c874ad58157b72ab9a658937f91d14c2285` / 8079 B / 116 行）
> 预登记依据：`v2/refs/D9c-prereg-reply-pick-order.md`（未读其判据细节，只按需报量口径复算）

---

## 0. 输入核验（`stat -c%s` / `sha256sum` / `wc -l` / mtime，同一次命令）

| 臂 | run.jsonl sha256 | bytes | 行数 | mtime |
|---|---|---|---|---|
| `mock_d9c_recent_n16r84_seed42` | `880ff24e39fd19451f6bf201b0c2bc13a74165ef676227313627d5b0a2d6b2d0` | 93,194,531 | 197,771 | 2026-10-29 15:40:43 |
| `mock_d9c_oldest_n16r84_seed42` | `569e5fd45d40714d80593191ecc8e492ccac46d9c4d8267499194f1c5cbe7448` | 93,210,403 | 197,786 | 2026-10-29 15:43:35 |

**三值与任务方所述逐项一致**。两目录**只有 `run.jsonl`，无 `meta.json`**（`run_override.py` 不产 meta）⇒ **本批无 meta 对拍**，本件不写"meta 一致"。
`LLM_CALL.payload.provider`：recent `{'mock': 3647}`、oldest `{'mock': 3660}` ⇒ mock 臂，语言侧结论不适用。

---

## 1. 六项复算：**我的值 = 判定件的值，六项全同**

| # | 指标 | 判定件（H0 recent / H1 oldest） | **我的值** | 对账 |
|---|---|---|---|---|
| ① | MSG 总数 | 929 / 938 | **929 / 938**（DM 643/682、GROUP 195/170、PUBLIC 91/86） | ✔ |
| ② | 回复条数（`reply_to` 非空） | 663 / 696 | **663 / 696**（悬空父 = 0 / 0） | ✔ |
| ③ | `lag_round` 分布 | `{1:656,2:7}` / `{1:439,2:257}` | **`{1:656,2:7}` / `{1:439,2:257}`**，max **2 / 2** | ✔ |
| ④ | `lag≥3` 条数 | 0 / 0 | **0 / 0**（`lag_round` 与 `lag_turn` 两口径均 0） | ✔ |
| ⑤ | 线程数 / p50 / p90 / max / mean | 266/242、1/3、6/6、6/6、3.094/3.479 | **266/242、1/3、6/6、6/6、3.09/3.48** | ✔ |
| ⑤ | `≥3 轮` 绝对 / 占比 | 120/127、45.11%/52.48% | **120/266=45.11%、127/242=52.48%** | ✔ |
| ⑤ | 单发（R=1）绝对 / 占比 | 139 / 109、52.26%/45.04% | **139（52.26%）、109（45.04%）** | ✔ |
| ⑥ | 发起条数（`reply_to` 为空） | 266 / 242 | **266 / 242** | ✔ |

派生量同批复算亦一致：`lag=2` 占比 **1.06% → 36.93%**；MSG **+0.97%**、回复 **+4.98%**、发起 **−9.02%**、`≥3轮` **+7.37pp**。

## 2. `lag_turn` 分列（**不合并**，判定件未报此项）

| 口径 | recent | oldest | 上界 |
|---|---|---|---|
| `lag_round`（`round` 差） | `{1: 656, 2: 7}` | `{1: 439, 2: 257}` | 2 / 2 |
| **`lag_turn`（`turn_index` 差）** | **`{1: 663}`** | **`{1: 602, 2: 94}`** | **1 / 2** |
| `lag=0` 条数 | 0 | 0 | — |

（两口径 n 均 663 / 696；`lag=0` 两臂均 0，与"同回合同线程只能一个发言者"的结构事实一致。）

**⇒ 重要：`lag_turn` 的上界两臂不同（1 vs 2）。** 这条直接影响判定件 §6 的因果表述（见 §4）。

## 3. 命门复核：**`lag≥3` 确实 = 0**（不需反转为 E-有效）

- 两臂、两口径、独立三遍（本件 §1/§2 一次，另用 `collections.Counter` 直接枚举一次）**均无任何 `lag≥3`**；
- 最大值：`lag_round` max=2（两臂），`lag_turn` max=1（recent）/2（oldest）；
- 因此判定件"E-有效"所需前提 `lag≥3 > 0` **不成立**，**"不可判（判据未覆盖）"不需要改判**；若有人拿"机制明显触发了"去反推有效，属把"次级结构量动了"冒充"主判据达成"。

## 4. 「`lag` 上界由结构决定、不由挑选顺序决定」——**建议删掉因果句，降级为观测**

判定件 §6 原句：*"顺序改了，`lag` 的上界仍是 2。说明上界不由挑选顺序决定，而由结构决定"*。我的判断：**该句结论不成立，须降级**。三条理由：

1. **口径反例**：`lag_round` 上界同为 2，但 **`lag_turn` 上界 1 → 2，随挑选顺序变了**。⇒ "上界与挑选顺序无关"在 `turn` 口径下被本批数据直接否证；至少必须限定为"**`lag_round` 的上界**"。
2. **同界 ≠ 同因**：两臂 `lag=2` 占比 1.06% vs 36.93%（差 35 倍）。同一个上界可以由"结构封死"造成，也可以由"两臂都没触到 3"造成；本批观测**无法区分**这两种解释。
3. **未做因果实验**：判定件自己已注"本批没有直接测量额度与上界的关系"，但 §6 首句仍写"说明…由结构决定"——**推论被写成了结论**。

**建议改写（可直接替换）**：
> 观测：两臂 `lag_round` 上界同为 2（recent `{1:656,2:7}`、oldest `{1:439,2:257}`），本批**无一条 `lag_round ≥ 3`**；但 `lag_turn` 上界为 1 vs 2，**随挑选顺序变化**。
> 假设（未验证，不写入结论）：`lag_round` 的上界可能受"同回合同线程单发言者 + 每 slot 2 条额度 + 每回合最多推进 2 轮"约束。**该因果须专门实验（改额度/改推进上限）才能建立**，本批仅数值吻合。

## 5. 判定件 §5.1 的 `starved_inbound` 分解：**数字对不上，须更正（结论仍成立）**

判定件写：*"H0 得 372 = 266 发起 + 106 真饿死"*。复算：

| 量（`msg_uid` 不在任何 `reply_to` 里，即"从未被回"） | recent | oldest |
|---|---|---|
| 合计 | **372** | **329** |
| 　其中 `reply_to` 为空（**发起**从未被回） | **139** | **109** |
| 　其中 `reply_to` 非空（**回复**未被再回） | **233** | **220** |

⇒ `266` 是**发起总数**，不是"未被回的发起数"；正确分解是 **372 = 139 + 233**（oldest：**329 = 109 + 220**）。**"该口径作废"的结论不变**，但分解须改，否则读者会以为"绝大多数发起都没人接"。

**按 `participants` 的重定义（我自己算的，仅备查、不建议直接引用）**：

| 定义 | recent | oldest |
|---|---|---|
| 有非作者对端且从未被任何消息 `reply_to` 指向的消息数 | **289** | **251** |

**该定义的局限（必须随数字一起写）**：① 公共/群发消息 `participants` 常只有作者本人 ⇒ 被判"无对端"而**跳过**（本批 PUBLIC 91/86 条属此类），故它**不是**"饿死的入站数"的上界也不是下界；② 一条消息可能有多个对端，此处按"消息"计而非按"(消息,对端)"对计。⇒ 若要正式报，须先定"按消息还是按对端计数"，本件不替判定件选口径。

## 6. 硬约束 1（默认路径等价）复核：**通过，且可给更强表述**

recent 臂 vs D9b `treat` 臂（`4a6aca5d…2748a88`）：

| 比较方式 | 差异 | 说明 |
|---|---|---|
| **原始字节逐行** | **197,771 / 197,771 行全部不同** | hash 链级联：`config_digest` 变 ⇒ 首行 hash 变 ⇒ 后续 `prev_hash`/`last_hash` 全变 |
| 剔除 `hash`/`prev_hash`/`last_hash` 后按 `(type,round,seq,actor,payload)` 比 | **1 行**（`WORLD_INIT`，`config_digest`） | `MSG_*` 差异 **0**；`TURN_SEAL` 实质差异 **0** |

⇒ 判定件"实质差异 85 = 1 digest + 84 hash 链"是**含 hash 字段的计法**；若按语义计法只有 **1 行**。两种计法都可成立，但**必须标名**，否则"85 行差异"与"行为零差异"会被读成矛盾。

## 7. 复算命令（自包含）

```python
import json, collections, statistics
def pct(v,q):
    s=sorted(v); k=(len(s)-1)*q; lo,hi=int(k),min(int(k)+1,len(s)-1)
    return s[lo]+(s[hi]-s[lo])*(k-lo)
def calc(path):
    msgs=[]; mx=-1; nl=0; prov=collections.Counter()
    for line in open(path,encoding="utf-8"):
        nl+=1
        if '"MSG_' not in line and '"LLM_CALL"' not in line: continue
        r=json.loads(line); t=r.get("type")
        if t=="LLM_CALL":
            prov[str((r.get("payload") or {}).get("provider"))]+=1; continue
        if not (t or "").startswith("MSG_"): continue
        p=r.get("payload") or {}
        msgs.append(dict(uid=p.get("msg_uid"),rt=p.get("reply_to"),th=p.get("thread_id"),
                         ti=p.get("turn_index"),rnd=r.get("round")))
        if isinstance(r.get("round"),int) and r["round"]>mx: mx=r["round"]
    by={m["uid"]:m for m in msgs if m["uid"] is not None}
    lr=[];lt=[]
    for m in msgs:
        if not m["rt"]: continue
        par=by.get(m["rt"])
        if par is None: continue
        if isinstance(m["rnd"],int) and isinstance(par["rnd"],int): lr.append(m["rnd"]-par["rnd"])
        if isinstance(m["ti"],int) and isinstance(par["ti"],int): lt.append(m["ti"]-par["ti"])
    th=collections.defaultdict(list)
    for m in msgs: th[m["th"]].append(m)
    R=[len({m["ti"] for m in l if isinstance(m["ti"],int)}) or 1 for l in th.values()]
    rep=sum(1 for m in msgs if m["rt"])
    print(path)
    print(" ①MSG=%d ②回复=%d ⑥发起=%d"%(len(msgs),rep,len(msgs)-rep))
    print(" ③lag_round=%s max=%s | lag_turn=%s max=%s"%(dict(sorted(collections.Counter(lr).items())),max(lr),
          dict(sorted(collections.Counter(lt).items())),max(lt)))
    print(" ④lag>=3: round=%d turn=%d"%(sum(1 for x in lr if x>=3),sum(1 for x in lt if x>=3)))
    print(" ⑤线程=%d R=%s p50=%.1f p90=%.1f max=%d mean=%.2f 单发=%d >=3轮=%d/%d=%.4f"%(
          len(th),dict(sorted(collections.Counter(R).items())),pct(R,.5),pct(R,.9),max(R),
          statistics.fmean(R),sum(1 for x in R if x==1),sum(1 for x in R if x>=3),len(R),sum(1 for x in R if x>=3)/len(R)))
    print(" provider=%s"%dict(prov))
calc("v2/evidence/mock_d9c_recent_n16r84_seed42/run.jsonl")
calc("v2/evidence/mock_d9c_oldest_n16r84_seed42/run.jsonl")
```

**实际输出**：
```
mock_d9c_recent_n16r84_seed42/run.jsonl
 ①MSG=929 ②回复=663 ⑥发起=266
 ③lag_round={1: 656, 2: 7} max=2 | lag_turn={1: 663} max=1
 ④lag>=3: round=0 turn=0
 ⑤线程=266 R={1:139,2:7,3:8,4:11,5:4,6:97} p50=1.0 p90=6.0 max=6 mean=3.09 单发=139 >=3轮=120/266=0.4511
 provider={'mock': 3647}
mock_d9c_oldest_n16r84_seed42/run.jsonl
 ①MSG=938 ②回复=696 ⑥发起=242
 ③lag_round={1: 439, 2: 257} max=2 | lag_turn={1: 602, 2: 94} max=2
 ④lag>=3: round=0 turn=0
 ⑤线程=242 R={1:109,2:6,3:8,4:7,5:3,6:109} p50=3.0 p90=6.0 max=6 mean=3.48 单发=109 >=3轮=127/242=0.5248
 provider={'mock': 3660}
```

**硬约束 1 的比较命令（语义计法）**：
```python
import json, collections
def norm(r):
    p=dict(r.get("payload") or {})
    for k in ("last_hash","prev_hash","hash"): p.pop(k,None)
    return json.dumps({"type":r.get("type"),"round":r.get("round"),"seq":r.get("seq"),
                       "actor":r.get("actor"),"payload":p},sort_keys=True,ensure_ascii=False)
dif=collections.Counter(); nd=0
for la,lb in zip(open("v2/evidence/mock_d9c_recent_n16r84_seed42/run.jsonl",encoding="utf-8"),
                 open("v2/evidence/mock_d9b_rw4_treat_n16r84_seed42/run.jsonl",encoding="utf-8")):
    ra,rb=json.loads(la),json.loads(lb)
    if norm(ra)!=norm(rb): nd+=1; dif[ra.get("type")]+=1
print("语义差异行=%d 类型=%s"%(nd,dict(dif)))
# → 语义差异行=1 类型={'WORLD_INIT': 1}
```

---

## 8. 本件不做 / 不成立的

- **不判档位**（E/L/T/I 四档命中与否由判定方负责；本件只核"前提量是否成立"）；
- 不读预登记判据细节，故不对"四档设计是否完备"表态；
- 不把 `lag` 时间分布读成"更真实"（mock 无语言）；
- 不合并 `lag_round` 与 `lag_turn`；不合并两臂；不把"机制触达"改写成"有效"；
- 不改判定件任何字节（`f062040a…` 未动）。
