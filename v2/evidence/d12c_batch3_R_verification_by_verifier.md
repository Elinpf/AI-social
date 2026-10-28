# D12-C batch3 · R 值核算（核验方独立复算，非第二份对照表）

> 作者：`repro-verifier`（计算/核验角色，不判档）｜2026-10-29 01:39（+08:00）
> 被核对象：`v2/evidence/d12c_batch3_R_verification.md`（prompt-linguist 出表，我核算）
> `ls -la` → 4576 B / Oct 29 01:37；`sha256sum` → `8ff7e6334b948702c41b0f999f45696d99f552736d8bfeaa0420507882ebe75c`；`wc -l` → **74**  ✔ 与其公示一致

---

## 0. 先撤回我此前的一个无效数字

**我曾说过"2 条 R 不一致"——该数字作废。** 它不是查出来的，是 **12 − 10 = 2 的反推**（我当时没有对方逐条 R 值）。按 leader 01:37 的纠正：**数字必须来自查询，不得来自减法**。本文只保留查询所得结果。

---

## 1. 口径（写死，两侧同一把尺子）

- **`R = 该线程内唯一 `payload.turn_index` 的个数**（与 v4 §1.0 实现口径一致）；
- `max(turn_index)+1` 仅作**旁证列**，不作判定依据；
- 数据源：`v2/evidence/run_a5_real_n16r42_seed42/run.jsonl`（只读）。

## 2. 我的独立复算（查询所得，命令见 §4）

| # | thread_id | 唯一 turn_index（R） | max+1（旁证） | 唯一值连续 0..k | 消息行数 |
|---|---|---|---|---|---|
| 1 | `TH-P013-P004-16` | **6** | 6 | True | 6 |
| 2 | `TH-P010-P009-37` | **5** | 5 | True | 5 |
| 3 | `TH-P016-P005-13` | **6** | 6 | True | 6 |
| 4 | `TH-P006-P003-6` | **6** | 6 | True | 6 |
| 5 | `TH-P009-P008-24` | **6** | 6 | True | 6 |
| 6 | `TH-P010-P009-12` | **6** | 6 | True | 6 |
| 7 | `TH-P016-P005-19` | **6** | 6 | True | 6 |
| 8 | `TH-P016-P005-6` | **6** | 6 | True | 6 |
| 9 | `TH-P012-P001-19` | **6** | 6 | True | 6 |
| 10 | `TH-P010-P009-1` | **6** | 6 | True | 6 |
| 11 | `TH-P006-P003-12` | **6** | 6 | True | 6 |
| 12 | `TH-P012-P001-37` | **5** | 5 | True | 5 |

## 3. 与他的表逐条比对

- **12/12 条逐一相等**：唯一计数、`max+1`、消息行数**三层全等**；
- **不一致 0 条**（因此我此前那句"2 条不一致"确系减法产物）；
- **无跳号**：12 条唯一序列均为 `0..k` 连续 ⇒ 本批**不存在**"`max+1` 与唯一计数不等"的情形；
- **不影响任何档位**：12 条 R 全部 ≥5，**无一条落进 `R ≤ 3`**，故 Q5/Q6 的短线程分支在本批不可能触发。

**⇒ 核算通过：他的 R 表可直接定案。**

## 4. 取数命令（任何人可复跑）

```bash
cd <项目根> && python3 - <<'PY'
import json,collections
want=["TH-P013-P004-16","TH-P010-P009-37","TH-P016-P005-13","TH-P006-P003-6","TH-P009-P008-24","TH-P010-P009-12","TH-P016-P005-19","TH-P016-P005-6","TH-P012-P001-19","TH-P010-P009-1","TH-P006-P003-12","TH-P012-P001-37"]
th=collections.defaultdict(list)
for l in open("v2/evidence/run_a5_real_n16r42_seed42/run.jsonl",encoding="utf-8"):
    l=l.strip()
    if not l: continue
    r=json.loads(l)
    if not str(r.get("type","")).startswith("MSG_"): continue
    pl=r.get("payload") or {}
    if pl.get("thread_id") in want: th[pl["thread_id"]].append(pl.get("turn_index"))
for t in want:
    v=[x for x in th[t] if isinstance(x,int)]; u=sorted(set(v))
    print(t, "R=",len(u), "max+1=",(max(u)+1 if u else 0), "contig=",u==list(range(len(u))), "lines=",len(v))
PY
```

## 5. 边界（随结论引用）

- 本文**只核 R**，**不并入 Q6 计数分歧**（他 1 / 我 0）——两件事分开，避免合并出"来源不明的数字"；
- 本轮**不产生**任何档位判断（本人已退出判读者）；
- 若日后 `run.jsonl` 或抽样件更换版本，本核算**不自动继承**，需按新 sha 重算。
---

**追加（leader 2026-10-29）：** 本件核对时引用的被核件 sha 为 `8ff7e633…`/74 行；其后被核件 §4 追加了一行 leader 裁定（「2 条不一致」已判作废、保留仅为留痕），现为 `ec608e00…`/75 行。**该追加只增一行说明、未改任何 R 数值**，故本件 12/12 的核对结论不受影响；引用被核件时请以 `origin/master` 当前版本为准（`git show origin/master:v2/evidence/d12c_batch3_R_verification.md | sha256sum`）。
