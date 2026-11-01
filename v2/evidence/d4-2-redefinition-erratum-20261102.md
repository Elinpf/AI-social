# 勘误：**`dialogue_repair` 不是"修复"** —— D4-2 分子重定义（2026-11-02 02:1x）

> 作者：TeamLeader｜**勘误件，不改原数据，只改读法**
> 触发：`repro-verifier` 核码发现，Leader 逐行复核确认
> 影响：**`v2/evidence/d4-rates-pilot.md`、`v2/evidence/d4-rates-dron-batches.json`、候选池中一切"和解率"表述**

## 1. 事实（代码）

`code/life/dialogue_repair.py::repair_audit()` **不做任何词表匹配**：

```python
rows = [v for v in rifts.values()
        if v.get("thread_id") == thread_id and (peer is None or v.get("with") == peer)]
return {"v": "f4/repair/1", "thread": thread_id,
        "rift_ids": [v["rift_id"] for v in rows], ...}
```

⇒ 它返回的是「**本条回复所在线程（+peer）里仍然存在的旧账列表**」= **"被回复**涉及**的旧账"**，
**不是"被修复的旧账"**。字段名叫 `dialogue_repair` / `v="f4/repair/1"`，**但语义不是修复**。

## 2. 更正对照表

> ### ⚠ 本节于 2026-11-02 02:2x **再次更正**（`repro-verifier` 指出 Leader 把两套数混成一套）
>
> **三套数必须分开**：
>
> | 数 | 来源 | 真实语义 | 处置 |
> |---|---|---|---|
> | **`4/33`、`3/23`、`26/166`**（即 `0.1212 / 0.1304 / 0.1566`） | `tools/dr/d4_rates.py` **口径 B：离线重放 + `ingest_one()` 的 `has_repair` 词表匹配** | **真·和解率（预估口径）** | **语义正确，保留原名**；只需强调"**离线重放假想台账，是预估，不是该臂运行期读数**" |
> | **`7 / 16 / 0`** | `dialogue_repair.rift_ids` 去重 | **涉及率分子**（回复涉及过多少笔旧账） | **改标为 `D4-2′ 涉及率分子`** |
> | **`0`**（本批） | `RIFT_CLOSE{reason="repair"}` 去重 | **真·修复数（运行期真值）** | 新增，语义正确 |
>
> ⇒ **Leader 上一版勘误把"离线重放+词表"的和解率也改标成"涉及率"，方向反了 —— 错的是 `7/16/0` 那一套，不是旧件。**

**真正的和解率分子 = `RIFT_CLOSE{reason="repair"}` 去重**（只有带 `rift_events` 的批才有）。

## 3. 实证：两个口径**不重叠**

首跑 `v2/evidence/rift-on_n16r24_s42/run.jsonl`（内容 sha `38820c9d22880f6e…`）：

| 口径 | 值 |
|---|---|
| `RIFT_CLOSE{reason="repair"}` 去重（`(agent_id, rift_id)`） | **0** |
| `dialogue_repair.rift_ids` 去重 | **2**（distinct rift；4 条 MSG） |
| **两者交集** | **空** |

⇒ **它们测的是两件不同的事**，不可互代。

## 4. 结论（三条，必须随任何引用同屏）

1. **旧三批（`emo-on` / `run_f4_on` / `run_r6_treat`）没有 `RIFT_CLOSE` ⇒ D4-2 在那三批上"不可算"，不是 0。**
2. **本批（`rift-on_n16r24_s42`）可算，但 `repaired = 0 / rift_total = 49`** —— 原因是**语料**（负向话 7 条、修复词命中 0），**不是机制未生效**。
3. **`dialogue_repair` 这个字段名会持续误导** —— 凡引用写全：**`dialogue_repair`（= 涉及旧账审计，非修复）**。

## 5. 未变的部分

- `rift_id` 主键仍是 **`(agent_id, rift_id)`**（`rift_id` 不含 agent 域）；
- `dialogue_rift` 仍是 **peer 视野**（不是全台账）；
- `repair` / `expire` 在真实批**仍零样例**，拼写风险未排除；
- **本勘误不改任何原始数据**，只重命名与重定义读法。

---

## 6. 第二次更正（2026-11-02 02:2x）

上版把 `0.1212 / 0.1304 / 0.1566` 一起改标为"涉及率"，**错了**：
- `d4_rates.py` 口径 B **走 `DR.ingest_one()`，其 pop 条件是 `if has_repair(body)`** ⇒ **真词表匹配** ⇒ 那三个数**是和解率（预估口径）**；
- `d4-rates-pilot.md` 里 D4-2 的定义"同线程后续出现**修复词**而注销的 rift 数" **本身是对的**，无需改。

⇒ **本勘误的适用范围收窄为：只改标 `7/16/0`（`dialogue_repair` 口径）**；`d4-rates-dron-batches.json` 的 D4-2 **保留原名原值**，只加粗其已有的边界句：
> **口径 B ＝ 离线重放假想台账（`enabled=True`），是预估，不是该臂运行期读数。**

**教训（Leader 自记）**：**"两个数都叫 D4-2"不等于"它们同源"** —— 我先按字段名把两者归并，又按归并结论去改两个件，**一步错、方向反**。
⇒ 凡"改标/重命名"，**先逐件核其计算路径**，再决定动哪个。
