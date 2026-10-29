# 证据段：R1 边界 14「尾截断判定式」补必要条件 `T < max_turns`

> 作者：`repro-verifier`（核验方）｜2026-10-29｜**供 leader 并入 `reports/R1-method-and-reproducibility.md` 的「边界 14」**；本件只出证据，不改 R1。
> 数据来源：D9b 两臂 mock 批（`v2/evidence/mock_d9b_rw2_ctrl_n16r84_seed42`、`…rw4_treat_n16r84_seed42`），只读日志。
> 裁定归属：主判据由 team-leader 于 2026-10-29 裁定；本件只提供可复算证据与其适用范围。

---

## 1. 待并入的条文（建议措辞）

> **边界 14（尾截断判定）**：线程被判「尾截断」须**同时**成立
> ① `min_round + T − 1 ≥ maxround`（`T` = 该线程唯一 `turn_index` 数；`maxround` = 本 run 内最大 `round` **值**，非 `rounds` 数）；
> ② **`T < max_turns`**。
> **②不可省**：`T = max_turns` 的线程是「被轮数上限正常封口」，与「run 到头被截断」**现象相同、成因相反**；只判①会把正常封口误算成截断。

## 2. 缺陷的实证（本批两条反例）

`max_turns = 6`（见 §4 来源）。两臂各有 3 条线程满足①：

| thread_id | min_round | max_round | T（唯一 turn 数） | last_turn_index | T = max_turns? | 裁定 |
|---|---|---|---|---|---|---|
| `TH-P005-Gplace-plaza-78` | 78 | 83 | 6 | 5 | **是**（6=6） | **封口，不计截断** |
| `TH-P016-Gplace-plaza-78` | 78 | 83 | 6 | 5 | **是**（6=6） | **封口，不计截断** |
| `TH-P007-P006-80` | 80 | 83 | **4** | 3 | 否（4<6） | **计为截断（本批唯一真候选）** |

⇒ 前两条 `78 + 6 − 1 = 83 = maxround`，公式①成立，但 `turn_index` 已用满 `0..5` ⇒ **本应结束**；写成截断等于把"正常封口"记成"数据缺失"。加②后本批由 **3 条 → 1 条**。

## 3. 两值并列（引用纪律）

| 口径 | 本批计数 | 用途 |
|---|---|---|
| 仅①（旧式，公式字面） | **3** | 只可用于**对账/复现旧件**，**不得用于结论** |
| ①+②（裁定后主判据） | **1** | **结论口径** |

两值**必须并列出现**；单独引用"3"会把封口算成截断，单独引用"1"则无法与旧件对账。

## 4. 参数来源与取法（防"同名不同义"）

| 参数 | 取法 | 本批值 | 出处（可核） |
|---|---|---|---|
| `T` | 该线程**唯一** `turn_index` 的个数（**不是台词行数**、不是 `max(turn_index)+1`） | 见 §2 | 日志 `payload.turn_index` |
| `maxround` | 全部记录中 `round` 字段的**最大值**（0 起算） | **83**（`rounds=84`） | 日志 `round` |
| `max_turns` | `dialogue_threads.DEFAULTS["max_turns"]`，`life_v2.json` 未设该键 ⇒ 默认生效 | **6** | `code/life/dialogue_threads.py:27`（sha256 `4b1491418935df73dd761586404545f9af2dfd7a45177fb544b13389c79f6e76`）；读取处 `code/life/agent.py:1078` `int(cfg.get("max_turns", 6))` |

## 5. 不可判分支（**不得按 0 处理**）

- `max_turns` 缺失/非整数 ⇒ 条件② **不可判**（记 `CANNOT-VERIFY`，不得写成"未截断"）；
- `T = max_turns` 但该线程最后一个 `round` **远小于** `maxround` ⇒ 封口，不计（②的判据是"是否用满上限"，不是"是否在末轮"）；
- 线程缺 `turn_index` 或 `round` 字段 ⇒ 该线程 `不可对`，单列，不并入分母。

## 6. 复算命令与输出（自包含）

```python
import json, collections
def tail_trunc(path):
    th = collections.defaultdict(list); mx = -1
    for line in open(path, encoding="utf-8"):
        if '"MSG_' not in line: continue
        r = json.loads(line); p = r["payload"]
        th[p.get("thread_id")].append((r["round"], p.get("turn_index")))
        if isinstance(r["round"], int) and r["round"] > mx: mx = r["round"]
    lit, real = [], []
    for k, v in th.items():
        tis = {t for _, t in v if isinstance(t, int)}
        rs = [x for x, _ in v if isinstance(x, int)]
        T = len(tis); minr = min(rs)
        if minr + T - 1 >= mx:
            lit.append((k, minr, T))
            if T < 6: real.append((k, minr, T))     # max_turns=6
    print(path, "maxround=", mx, "| ①字面=", len(lit), lit, "| ①+②=", len(real), real)

tail_trunc("v2/evidence/mock_d9b_rw2_ctrl_n16r84_seed42/run.jsonl")
tail_trunc("v2/evidence/mock_d9b_rw4_treat_n16r84_seed42/run.jsonl")
```

**实际输出（两臂）**：
```
 ctrl : maxround= 83 | ①字面= 3 [('TH-P005-Gplace-plaza-78',78,6), ('TH-P016-Gplace-plaza-78',78,6), ('TH-P007-P006-80',80,4)]
                     | ①+②= 1 [('TH-P007-P006-80', 80, 4)]
 treat: 同上，逐项相同
```

## 7. 适用范围与限制

- 本证据来自 **mock 结构批**（`seed=42/n=16/rounds=84`），只支持"判定式的计数后果"，不支持任何语言侧或档位结论；
- 本批**无 `meta.json`**（`tools/t271/run_override.py` 不产 meta，`run_batch.sh` 才产）⇒ **本批无 meta 对拍**，不得写成"meta 一致"，也不得据此推断 seed/n 之外的配置；
- 本条不改变任何**已发布的一致率/档位数**，只改"哪些线程算作不可判"的边界定义。
