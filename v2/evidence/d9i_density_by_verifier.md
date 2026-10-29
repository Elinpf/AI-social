# D9i 冲突信号密度与载体分离（`repro-verifier` 只读核算）

> **件头三条（必读）**
> **① 任务载体**：本件依 **Leader 2026-10-30 01:39:32 消息**执行，**所引卡号 `#T-D9I-DENSITY` 在任务库中不存在**（`view_task get` → Task not found；库内 pending 仅 `#T-D9I-CODE`）。**以消息为准落盘**。
> **② 两臂不是单变量**：`meta.code_sha` = `05636bcde2f1`（`run_d9_a1`）vs `d7d1d93fa587`（`run_d1_f6off`），`agent.py` 等 33 文件 +2861/−30 ⇒ **本件的任何跨臂差值都不得归因于"旁白"**，只能作**观测**。
> **③ 自校验通过**：`L1 + L2 = 旧词表命中数`，`d9_a1` 20+43 = **63**、`f6off` 2+17 = **19**，与 D9h 全量命中逐一对上。

- 作者：`repro-verifier`｜2026-10-30｜**只读、不跑批、不改码、只落盘不提交**
- 输入：`v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl`、`v2/evidence/run_d1_f6off_seed42_n16r84/run.jsonl`（各 **686 MSG**）
- 判定实现：**D9h 新判定** `feat/neg-words-target-filter:code/life/dialogue_repair.py` · `sha256:8534cd0dc67b…b1810a` · 453 行（`is_gripe` / `has_target` / `dialogue_only`）；旧词表 = master `sha256:2f75386f0cdf…20dbd`

---

## 1. 口径（写死，取自 Leader 消息；未自创）

| 级 | 定义 |
|---|---|
| **L1 显式冲突** | `is_gripe(body, from, participants) == True` —— 即：剥旁白后台词含指向具体人（第二人称/第三人称指名）、存在分句命中 `NEG_WORDS`、该分句不被 5 类形态（关切/生理味觉/转述/顾虑/客套）排除、且不属引述 |
| **L2 弱冲突** | `polarity(body) < 0`（旧：正文含 `NEG_WORDS`）但 `is_gripe == False` |
| **L3 无信号** | `polarity(body) >= 0`（词表未命中） |
| **旁白** | L1/L2 判定在**剥旁白后的台词层**（`dialogue_only`，成对全角/半角括号剥离）；**另单列"仅旁白命中"**（正文含负向词、但剥后台词不含） |
| **载体** | 词层判定：`台词` = 台词含负向词；`旁白` = 正文含但台词不含；`两者` = 都含 |

> **注**：`is_gripe` 的台词层判定意味着 **旁白里的负向词一律不参与判定** ⇒ 见 §3 的 3 条实例。

## 2. 任务 1：密度三级（分母 = **686**，含 `PUBLIC`）

| 臂 | L1 显式冲突 | L2 弱冲突 | L3 无信号 |
|---|---|---|---|
| **`d9_a1`**（旁白率 84.69%） | **20 / 686 = 2.92%** | **43 / 686 = 6.27%** | 623 / 686 = **90.82%** |
| **`f6off`**（旁白率 0.00%） | **2 / 686 = 0.29%** | **17 / 686 = 2.48%** | 667 / 686 = **97.23%** |
| 合计（**仅参考**） | 22 / 1372 = 1.60% | 60 / 1372 = 4.37% | 1290 / 1372 = 94.02% |

**跨臂观测**：`L1` 密度 **2.92% vs 0.29%，约 10 倍**。⚠ **这是观测，不是因果**——两臂 `code_sha` 不同（见件头②）；要证因果须**同 `code_sha` 只改 `LIFE_PROMPT_NARRATION`**（`#T-D9I-CODE` 的接线 + 真 LLM 臂，预算另议）。

## 3. 任务 2：载体分离（`L1`/`L2` 条目的词层载体）

| 臂 | L1+L2 条数 | 台词 | 旁白 | 两者 |
|---|---|---|---|---|
| `d9_a1` | 63 | **60** | **3** | 0 |
| `f6off` | 19 | **19** | **0** | 0 |

**「仅旁白命中」= 3 条，且 3 条全部落在 L2（不是 L1）**——因为台词层无负向词 ⇒ `is_gripe` 判否：

| `msg_uid` | 类型 | 命中词 | 级 | 正文（截断） |
|---|---|---|---|---|
| `42:23105` | MSG_DM | 委屈 | L2 | （揉着肚子，**一脸委屈**）周公~我肚子都在打鼓了… |
| `42:138452` | MSG_GROUP | 苦 | L2 | …评委里有一半是赞助商的人…（**苦笑**）这算哪门子的比赛。 |
| `42:161524` | MSG_GROUP | 怕 | L2 | （把吉他往身后挪了挪，像是**怕**它也被卷进这场争执，声音有点发紧）…规矩再齐整，唱出来也是空的呀。 |

⇒ **旁白独家承载态度的 3 条，全部被当前判定器归入 L2/判否**。这不是"这 3 条没态度"，而是「**判定器只看台词层**」的直接后果——与 `pl` 所说"旁白承载的负向（`（语气有点冲）`）"同一类。**该结论对"是否该把旁白纳入判定"是可用的输入，但对"冲突有多少"不可用。**

## 4. 任务 3：分母口径 + `PUBLIC` 更正

| 臂 | 全量分母 | 有对端子集（`participants−{from}` 非空） | 子集 L1 | 子集 L2 | 子集 L3 |
|---|---|---|---|---|---|
| `d9_a1` | 686 | **629** | 20 | 37 | 572 |
| `f6off` | 686 | **629** | 2 | 15 | 612 |

**更正 D9g 预登记 §1.2 的假设**（原文：*"`PUBLIC` 的 `participants` 只有发言人自己 ⇒ 天然无对端，不参与"*）：

```
两臂类型分布（逐臂）：MSG_DM 497 / MSG_GROUP 126 / MSG_PUBLIC 63
无对端（participants 仅作者）：MSG_PUBLIC 57 条（其余 6 条 PUBLIC 有多人对端，如"各位…"开场）
⇒ 有对端 = 686 − 57 = 629
```
⇒ **按 `participants` 判对端，不按 `type` 判**；"PUBLIC 一律不参与"在本批会**漏掉 6 条**。

## 5. 比冲突率更值得写的一条：`L3` 占 90.82% / 97.23%

⇒ **绝大多数消息根本没有态度信号**（不论正负）：`d9_a1` 九成、`f6off` 九成七。这意味着——
- 若目标是"让冲突维度可测"，**先决问题不是词表准不准，而是语料里这类消息密度太低**（L1+L2 合计 6.27% / 2.48%）；
- 加词/改匹配的**天花板由分母决定**：即便判定器完美，可判对象也只有 L1+L2 这 9.2% / 2.8%。

## 6. 三条限定（与结果同屏，不得拆开引用）

1. **两臂非单变量**（`code_sha` 不同，33 文件 +2861/−30，含禁旁白指令 `a637371`）⇒ 10 倍差**不可归因于旁白**；
2. 正确表述：「**有旁白的臂，其显式冲突密度约为无旁白臂的 10 倍**」——**观测**，非因果；
3. 因果需**同 `code_sha` 只改 `LIFE_PROMPT_NARRATION`**；本批 mock 亦**不作语言层证据**。

## 7. 本件禁止的读法

- ❌「旁白让冲突变多」/「去掉禁旁白就能提高冲突密度」（未控 `code_sha`）；
- ❌「L1 = 2.92% ⇒ 语料有 2.92% 的冲突」——这是**词表层**密度；`pl` 的覆盖率件已示关键词法召回仅 2/11 ⇒ 真实密度**只会更高，本件不给估计**；
- ❌「L1 = 0 ⇒ 没有冲突」（本批 L1 非零，但若某词为 0，只能写"该词词表零命中"）；
- ❌ 用 `mock` 臂或旁白率替代"生活气息/语气强度"。

## 8. 复算命令与输出

```python
import json, importlib.util, collections
REPO = "<repo>/"
def load(p, n):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
old = load(REPO + "code/life/dialogue_repair.py", "o")                                        # master 词表
new = load(REPO + ".worktrees/neg-words-target-filter/code/life/dialogue_repair.py", "n")     # D9h 新判定
NEG = old.NEG_WORDS
for k, p in {"d9_a1": "v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl",
             "f6off": "v2/evidence/run_d1_f6off_seed42_n16r84/run.jsonl"}.items():
    L1 = L2 = L3 = 0; only_narr = 0; car = collections.Counter(); sub = [0, 0, 0, 0]
    for line in open(REPO + p, encoding="utf-8"):
        if '"MSG' not in line: continue
        r = json.loads(line)
        if not str(r.get("type", "")).startswith("MSG"): continue
        pl = r.get("payload") or {}; b = pl.get("body") or ""
        frm = pl.get("from") or pl.get("author"); part = pl.get("participants") or []
        dlg, _ = new.dialogue_only(b)
        neg_d = any(w in dlg for w in NEG); neg_n = any(w in b for w in NEG) and not neg_d
        l1 = new.is_gripe(b, frm, part); l2 = (not l1) and old.polarity(b) < 0
        L1 += l1; L2 += l2; L3 += not (l1 or l2)
        only_narr += neg_n
        if l1 or l2: car["两者" if (neg_d and neg_n) else ("台词" if neg_d else "旁白")] += 1
        if [x for x in part if x != frm]:
            sub[0] += 1; sub[1] += l1; sub[2] += l2; sub[3] += not (l1 or l2)
    tot = L1 + L2 + L3
    print(k, "L1=%d/%d(%.2f%%) L2=%d/%d(%.2f%%) L3=%d/%d(%.2f%%) 仅旁白=%d 载体=%s 子集=%s"
          % (L1, tot, L1/tot*100, L2, tot, L2/tot*100, L3, tot, L3/tot*100, only_narr, dict(car), sub))
```
**实际输出**
```
d9_a1 L1=20/686(2.92%) L2=43/686(6.27%) L3=623/686(90.82%) 仅旁白=3 载体={'台词': 60, '旁白': 3} 子集=[629, 20, 37, 572]
f6off L1=2/686(0.29%)  L2=17/686(2.48%) L3=667/686(97.23%) 仅旁白=0 载体={'台词': 19, '旁白': 0} 子集=[629, 2, 15, 612]
```

## 9. 局限

1. **词表层**密度：关键词法召回约 18%（`d9h_coverage_recall_*`），故 L1/L2 是**下界性质的表层读数**，本件不给真实密度估计；
2. 两臂 `code_sha` 不同 ⇒ 全部跨臂比较仅作观测；
3. `is_gripe` 只看台词层 ⇒ 旁白里的态度系统性不计（§3 已给 3 条实例）；
4. 无人工标注 ⇒ 不产出"精确率/召回率"；本件不出档位判断（归 Leader）。
