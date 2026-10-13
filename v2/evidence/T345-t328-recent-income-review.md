# T345 · 非作者独立复验：`T328③` `recent_income` 标量累加器

- **复核人**：sandbox-test-lead（**非作者**）｜ 落盘：`v2/evidence/T345-t328-recent-income-review.md`
- **被核对象**：`T328③`（`liquidity.recent_income` 改读 `state.income_net` 标量累加器）
  - 改动文件：`code/engine/event_acc.py`（新增 `_note_income`/`rebuild`/`ensure` 口径）、`code/engine/liquidity.py`、`code/engine/state.py`（新增派生字段 `income_net`）
  - **被核 sha（作者提交）**：**`8fb2263`**（`T328③: recent_income 按 agent 标量累加器`）。核在提交前的工作树内容上完成；提交后经 `git diff 8fb2263 -- code/engine/{event_acc,liquidity,state}.py` **逐文件一致（空）** ⇒ 结论绑定 `8fb2263`。
- **自建口径脚本**：`v2/evidence/t345_recent_income_verify.py`（**只读、未改 `code/`**；参考实现 = **独立全表扫**，不复用作者单测、不 import 被改函数）
- **命令**：`python3 v2/evidence/t345_recent_income_verify.py <seed> <rounds> <n>`；`window=12`（`w_income_rounds` 默认）

---

## 1. 逐条等价（新实现 vs 独立全表扫）

对全部 **(agent × round)** 逐条比对 `recent_income` 取值：

| 配置 | ① 可信态（Engine 直产） | ② 不可信态（`acc_trusted=False` 强制 rebuild） |
|---|---|---|
| seed=7, rounds=20, n=4 | **N/N (110)** | **N/N (110)** |
| seed=7, rounds=40, n=6 | **N/N (294)** | **N/N (294)** |
| seed=42, rounds=30, n=5 | **N/N (192)** | **N/N (192)** |

- 全部 **0 差异**。
- 口径常量自洽：独立写死的 `("transfer","trade")` / `frozenset{"wash","cycle","self","mule"}` 与 `liquidity._INCOME_TX_TYPES` / `_EXCLUDE_FLAGS` **逐一相等**。
- ② 覆盖了 `ensure()` 的"不可信 ⇒ 每次 rebuild"自愈路径，同样逐条等价。

## 2. `state_hash` 不变（跨版本，同 seed/rounds/n）

`state.income_net` 已列入 `state.py::_ATTR_KEYS`（duck-typing 端口，**可 setattr**），但 **`to_dict()`（`state_hash` 投影）不含它** ⇒ 派生、不入哈希。

| 配置 | 新（工作树含 T328③） | 旧（HEAD `b2944a2`） | 结果 |
|---|---|---|---|
| seed=7, rounds=40, n=6 | `sha256:a3731a6c…01bc0a` | `sha256:a3731a6c…01bc0a` | **相同 ✓** |
| seed=42, rounds=30, n=5 | `sha256:76f4c717…3ab7fd4e4`（`76f4c717…`）| `sha256:76f4c717…` | **相同 ✓** |

方法：`git archive HEAD` 导出旧树到 `/tmp`，两树各跑 `hash_probe.py`（仅 `build_world`+`run_round`+`state_hash`）。**两配置逐位一致**。

## 3. ⚠️ 反向验证（必须红 ⇒ 证断言非恒真）

对状态**故意破坏累加器**后再跑同一比对，**三项全部检出**：

| 场景 | 作恶方式 | 结果 |
|---|---|---|
| ③a 漏一回合 | 抹掉 `MARKET.round6`（200→0） | **检出**（`新=0 参考=200`） |
| ③b 错位一回合 | `MARKET.round6`(200) 迁到 `round7` | **检出**（`新=0 参考=200`） |
| ③c 漏 TRANSFER | 重建累加器仅记 `MARKET_TRADE` | **检出**（`P003.round9: 新=0 参考=200`） |

⇒ 断言**非恒真**；比对能识别"漏一个 `TRANSFER`""错位一个回合"等累加器缺陷。

## 4. 时间收益（同进程、调用数写明，**乘数不作通用结论**）

| 配置 | 调用数 | 新实现 | 独立全扫 | 比 |
|---|---|---|---|---|
| seed=7, rounds=20, n=4 | 100 次 | 0.2ms | 31.9ms | ≈198× |
| seed=7, rounds=40, n=6 | 280 次 | 0.4ms | 313.7ms | ≈766× |
| seed=42, rounds=30, n=5 | 180 次 | 0.3ms | 100.5ms | ≈358× |

- **单进程、同口径相邻调用**；比值随 agent×round 规模上升，**非通用乘数**。

## 5. 自曝：复核 harness 的一个 bug（过程留痕）

首轮跑出"参考恒 0 / 差异 20"——排查为**我参考实现的 bug**：`per_round.setdefault(rd,0)` 取出的局部 `d` 加完**未写回字典**（int 不可变；旧实现末尾有 `per_round[rd]=d`，我漏抄）。修正后为上述 N/N。
⇒ 教训：反向验证/独立口径也会自带装置 bug；**先怀疑自己的口径**再下"不等价"结论。

---

## 6. 结论（一句话）

**可判为无行为变（等价）** —— 三配置逐条等价 `N/N`（含不可信态 rebuild 路径）、`state_hash` 跨版本逐位不变、反向验证三项全检出；`recent_income` 由全扫改标量累加器**无行为变**，可用于重冻基线。

*（T345 非作者独立核结束 — sandbox-test-lead，非作者）*
