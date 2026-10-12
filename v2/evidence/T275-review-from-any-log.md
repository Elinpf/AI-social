# T275 · review/盲测管线吃得住新日志（指定任意日志 → 5 片段 + 汇总表 + 版本角标）

**背景**：今晚起每晚跑真实世界 → 用户下次"看"用新日志重渲；新基线 ~30 万事件（旧 canonical ~130k）。
**只动 `frontend/`**（不碰夜间冻结的世界层）。

## 交付 1：`review.html` 参数化（指向任意日志）
- 新增 `?log=<url>`（默认旧 canonical）+ `?rounds=a,b,c,d,e`（默认 5 段）；**保留 `/__gitstamp` 版本角标**（分数仍可绑 sha）。
- 页头显示当前日志名。

## 交付 2：一条命令 `frontend/tools/review_pack.py`
```
python3 frontend/tools/review_pack.py --log <任意日志> [--measure] [--shots DIR] [--base http://host:8848]
```
- **自动选 5 段且覆盖昼夜**（晨/午/暮/夜各取中位；夜段必进样本）；
- 日志若不在 `frontend/` 下自动拷进 `sample/` 供静态服务；
- 输出 review.html URL（片段 + 汇总表 + 版本角标）。

**示例（canonical 128k）**：
```
片段(覆盖昼夜): r0 第1日 06:00 晨 | r37 第4日 08:00 晨 | r40 第4日 14:00 午 | r43 第4日 20:00 暮 | r46 第4日 02:00 夜
夜段在样本内: ✅ [46]
▶ http://127.0.0.1:8848/review.html?log=sample/run_p1_final_n20_llm.jsonl&rounds=0,37,40,43,46
```

## 交付 3：30 万事件实测（数字，非"可以跑"）
无头 Chromium / still 单帧 / view=default：

| 日志 | 行数(≈事件) | 日志→画面就绪 | JS 堆 used / limit |
|---|---|---|---|
| canonical `run_p1_final_n20_llm` | 128,564 | **5.36 s** | 173 MB / 4396 MB |
| `n20_week` | 148,869 | **4.50 s** | 194 MB / 4396 MB |
| **perf 夹具 `t275_perf_300k`** | **297,738** | **5.33 s** | **324 MB / 4396 MB** |

**结论**：~30 万事件 **5.3s 到画面就绪、JS 堆 324MB（上限的 ~7%）** → **吃得下，无需降质**。
瓶颈在**一次性解析/折叠**（时间随事件数近似平缓），非逐帧；单帧渲染成本与事件量基本无关。
> ⚠️ perf 夹具是把 `n20_week` **平铺 2 份、第 2 份 round+84** 造的**纯性能样本（非世界数据）**，仅用于压力测试，不提交入库。

## 交付 4：覆盖昼夜
`pick_rounds()` 按 `(round%12)//3 ∈ {0晨,1午,2暮,3夜}` 四槽各取一 → **夜段必在样本**（用户曾疑"夜段最低"）。

## 证据
- `T275-review-param.png`（指定日志 + 5 段昼夜 + 版本角标 + 汇总表）、`T275-review-gitstamp.png`（旧）。
- `make ci` → **PASS**（含 D 段）。

## 已知边界（如实）
- 5 个片段**逐个切换**时 iframe 各自重新加载日志（≈每段一次解析）→ 5 段全看约 25s（30 万级）；用户一次看一段，可按需再优化（预取/复用）。
- 夜间冻结批的日志到位后，**按同一命令实跑一次**即可（`review_pack.py --log <今晚A批产物>`）。

---

## 实跑补证（今晚 A 批真日志，2026-10-12 21:4x）
**日志**：`v2/evidence/run_t236_canon_n20_llm.jsonl` —— **301,384 行 / 140.9 MB**（新基线，旧 canonical 的 ~2.3×）。

命令（一条）：
```
python3 code/frontend/tools/review_pack.py --log v2/evidence/run_t236_canon_n20_llm.jsonl --measure
```
输出：
```
片段(覆盖昼夜): r0 第1日 06:00 晨 | r37 第4日 08:00 晨 | r40 第4日 14:00 午 | r43 第4日 20:00 暮 | r46 第4日 02:00 夜
夜段在样本内: ✅ [46]
▶ http://127.0.0.1:8848/review.html?log=sample/run_t236_canon_n20_llm.jsonl&rounds=0,37,40,43,46
实测（无头 Chromium, still）：日志→画面就绪: 5.92 s · JS 堆 used=355.0 MB / limit=4396 MB
```

**结论**：真 30 万数据上 **5.92s / 355MB**，与合成 300k 的 **5.33s / 324MB** 一致 ⇒ **T275 的"吃得下"在真数据上成立**。
证据截图：`T275-review-real-A-batch.png`（页头日志名 + 5 段昼夜 + 汇总表 + `/__gitstamp` 角标）。
`shot.py` 观察哨：`blank_cumulative=0/7`（无空白、重试 0）。
