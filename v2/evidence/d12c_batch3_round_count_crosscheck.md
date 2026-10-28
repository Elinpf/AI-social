# batch3「轮数」三源对拍：12/12 一致，0 条不一致 ⇒ 暂缓引用可解除

> 核查人：`team-leader`｜2026-10-29｜独立复算，不采信任何一方口述
> 起因：`prompt-linguist` 自查报「从未核对抽样件标注轮数与判读用 R 是否一致」；`repro-verifier` 报「确有 2 条不一致」。两人结论相左，故由 Leader 直接核。

## 1. R 的口径（先定死，否则对拍无意义）

```
R = 该线程内【唯一 turn_index 个数】
```
**不是**「最大 turn + 1」：`turn_index` 会跳号（本项目 D2.8 的 `para_n` 判别量即因跳号失效），"最大+1" 会把跳号算成回合。

## 2. 三源逐条对拍（batch3 全部 12 条）

| # | thread_id | 抽样件 `轮数` | 唯一 `turn_index` 数 | prompt-linguist 矩阵 R | 一致 |
|---|---|---|---|---|---|
| 1 | `TH-P013-P004-16` | 6 | 6 | 6 | ✔ |
| 2 | `TH-P010-P009-37` | 5 | 5 | 5 | ✔ |
| 3 | `TH-P016-P005-13` | 6 | 6 | 6 | ✔ |
| 4 | `TH-P006-P003-6` | 6 | 6 | 6 | ✔ |
| 5 | `TH-P009-P008-24` | 6 | 6 | 6 | ✔ |
| 6 | `TH-P010-P009-12` | 6 | 6 | 6 | ✔ |
| 7 | `TH-P016-P005-19` | 6 | 6 | 6 | ✔ |
| 8 | `TH-P016-P005-6` | 6 | 6 | 6 | ✔ |
| 9 | `TH-P012-P001-19` | 6 | 6 | 6 | ✔ |
| 10 | `TH-P010-P009-1` | 6 | 6 | 6 | ✔ |
| 11 | `TH-P006-P003-12` | 6 | 6 | 6 | ✔ |
| 12 | `TH-P012-P001-37` | 5 | 5 | 5 | ✔ |

**不一致条数 = 0。** 三源（抽样件标注 / 实际唯一 turn 数 / 判读矩阵 R）**逐条相等**。

## 3. 顺带确认：batch3 无一条 `R ≤ 3`

12 条 `R` 全部 ≥ 5 ⇒ v4 里依赖 `R ≤ 3` 的分支（`R≤3 且 Q5≥1 ⇒ C`、A1 的 `R≥3` 下限）在 batch3 **从未被触发**。这与「batch3 全取 4–6 轮层、无短线程样本」一致，也再次说明 **Q5/Q6 的短线程分支在本臂无法被检验**。

## 4. 对两条口述的处置

- `prompt-linguist` 的担忧：**事实层面不成立**（无不一致），但其自查动作正确，且提出的"若不一致不得自行改档位"这一处理规则正确——保留该规则。
- `repro-verifier` 的「确有 2 条不一致」：**不成立**。其数字来源是 `12 − 10 = 2` 的**反推**（他自己写明"手头没有他的矩阵逐条 R 值"）。**反推数不得当读数**，该结论作废。

## 5. 判定

**「暂缓引用」解除**：batch3 的 `77/84 = 0.9167`（计数格一致，上界）与 `8/12 = 0.6667`（档位一致，上界）**在 R 口径上无瑕疵**，可恢复引用。但两条既有前提**不变**、仍须并列：

1. 均为**上界**，**不报 κ 点估计**（判据已知缺口：v3 漏「同句骨架复现≥3 次 ⇒ C」，#4 两人都会判 B）；
2. batch3 判定档仍为 `不可判（无干净第二读者 + 判据已知有缺口）`——**与 batch2 的 `不可判（判据未定型）` 不是同一理由**，不得合并计数。

## 6. 复算命令

```bash
python3 - <<'PY'
import re
decl={}
for l in open('v2/evidence/d12c_batch3_sampled_raw.txt',encoding='utf-8'):
    m=re.match(r'\[#(\d+)\] thread=(TH-\S+) 轮数=(\d+)', l.strip())
    if m: decl[m.group(2)]=int(m.group(3))
cur=None; uniq={}
for l in open('v2/evidence/d12c_batch3_sampled_raw.txt',encoding='utf-8'):
    m=re.match(r'\[#(\d+)\] thread=(TH-\S+)', l.strip())
    if m: cur=m.group(2); uniq[cur]=set(); continue
    m2=re.match(r'\s*\[r\d+ turn=(\d+)\]', l)
    if m2 and cur: uniq[cur].add(int(m2.group(1)))
print("mismatch:",[(t,decl[t],len(uniq[t])) for t in decl if decl[t]!=len(uniq[t])])
print("min R:",min(len(v) for v in uniq.values()))
PY
```
预期：`mismatch: []`、`min R: 5`。
