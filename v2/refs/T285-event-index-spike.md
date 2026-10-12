# T285 第0条前置 spike：`event_index` 是「占内存」还是「耗计算」？

**日期** 2026-10-12 · **作者** kernel-dev · **性质** 只读测量（未改 code/）· **骨架** sim-system-architect 提供
**环境** `build_world`（mock LLM）、`seed=7`、`rounds=24`、`N50_VEC=0`

## 结论（一句话）

**以「耗计算」为主**：`state.event_index` **每回合被多次全量扫描**（`values()`/`items()`），扫描量随 N **超线性（≈O(N²·rounds)）**；**常驻字节在同一规模下是次要项**（N=20×24 实测 ≈30MB，深尺寸估算 ±2×）。
⇒ **优先做「增量聚合」**（消除每回合全表扫）；**尾段常驻为次**（但随 rounds 线性增长，N 大/跑满周时仍会变大，两路非互斥）。

## (a)(b) 扫描与回读（骨架实测）

| 指标 | N=10, R=24 | N=20, R=24 | 倍率 |
|---|---|---|---|
| `scan_calls`（values/items 次数） | 1,616（≈67/回合） | 2,673（≈111/回合） | 1.65× |
| `scan_len`（累计已扫条目） | 10,098,723 | 66,605,623 | 6.59× |
| **avg `scan_len`/回合** | **420,780** | **2,775,234** | **6.60×** |
| avg `scan_len`/call | 6,249 | 24,918 | 3.99× |
| 墙钟 secs | 4.0 | 25.8 | 6.45× |
| RSS | 56.5 MB | 113.5 MB | — |

- **N 翻倍 ⇒ scan_len/回合 ≈ 6.6×**（`avg scan_len/call` 4×、`calls/回合` 1.65×）⇒ **近乎 O(N²)**。
- `reads`（单点回读）N=10:4,141 / N=20:17,991 —— 占比远小于全表扫。

## (c) cProfile（N=20, R=24，共 80.1s）

| 函数 | tottime | cumtime |
|---|---|---|
| `dict.get` | **24.2s**（30%） | 24.2s |
| `contracts/visibility.py::visible_events` | 8.2s | 31.9s |
| `engine/liquidity.py::recent_income` | 7.5s | 11.6s |
| `contracts/visibility.py::visible` | 5.7s | 9.5s |
| `contracts/visibility.py::_group_members` | 4.1s | 7.7s |
| `engine/hooks/econ.py::_round_ie_eff` | 3.9s | 5.5s |
| `engine/liquidity.py::recent_default_of` | 2.0s | 3.3s |
| `life/memory.py::_tokenize` | 1.9s | 3.4s |
| `contracts/visibility.py::location_of` | 1.6s | 1.6s |

**热点几乎都源于「对 `event_index` 的全表扫 + payload 读取」**：`liquidity.recent_income/recent_default_of`、`econ._round_ie_eff`、`visibility.visible_events/_group_members/location_of`、`life.settlement.events_this_round` 等，**每回合把历史事件重新遍历**。
（注：`visibility.visible_events` 与 **T264 增量索引**天然协同 —— 该热点已被 T264 部分收敛；本 spike 看到的是**其余消费点**仍全表扫。）

## 常驻字节（次要项，深尺寸估算 ±2×）

- N=20×24：`event_index` len=52,008（= `ledger.records` 同批 dict），**估算 ≈30.5 MB**（`±2×`，按前 2000 条 `json.dumps` 外推）。
- 随 rounds：跑满 **84 回合 ≈ 3.5×** ⇒ ~100MB（N=20）；**N=50 更大**。**故常驻不可忽略，但不是当前首要根因。**

## 选路建议

1. **首选：增量聚合**（在折叠时维护每类累加器，取代每回合全表扫）——直接消除上表热点，**不改事件顺序/判定/state_hash**（纯读法优化，属 storage/读路径）。⚠️ 但**若改成「不扫 event_index 而扫增量表」，需保证与全表扫逐条等价**（对照实验）。
2. **次选/并行：尾段常驻**（已封段落盘 + 轻索引）——对**常驻字节**与**replay 峰值**有效；3 硬条件见 T281 §4.4（外置 `seq_base`/`chain_head`、只封整回合、索引与段原子同替）。
3. **两路非互斥**：先做①（消计算），②按内存压力后续落。

## 未测（诚实边界）

- **N=50 未跑**（>N=20 需先报 Leader + 设内存上限，本次未做）⇒ N 曲线只到 N=20；**外推 O(N²) 需 N=50 实测坐实**。
- 真实 LLM（非 mock）下 `event_index` 份额可能被 LLM I/O 稀释；本 spike 用 mock **隔离计算热点**（目的即此）。
- `scan_len` 为「每回合快照差」累计，未含 `Arbiter.commit`/`replay` 落点的 reassign 漏计（骨架 TODO）；如需精确到 commit 点，可再挂钩。
