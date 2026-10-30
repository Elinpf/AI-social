# master 与 exp/n36-scene-anchor 两条平行主线分叉 · 首次汇流留档

> 作者：TeamLeader｜2026-10-31 05:1x｜类型：**治理留档（不是实验、不入判据）**
> 触发：heartbeat 巡查发现 `HEAD` 不在 master 上，且两条线的提交历史互不包含。
> 只读勘定 + 一次 merge；**未改任何实验读数、未重跑任何臂**。

## 0. 结论一句话

**GitHub master 上曾缺 9 份周期报告（CYCLE-28…36）与 13 个 `v2/refs` 预登记件**，用户「我会在 GitHub 上关注你进展」的发布链在 2026-10-28 起就断了；本次以 merge 提交 `e11ac43` 汇流修复。

## 1. 分叉勘定（合并前状态，分母写死）

| 项 | 值 | 取法 |
|---|---|---|
| `merge-base` | `b43033e`（`2c52238…`） | `git merge-base master exp/n36-scene-anchor` |
| 分支独有提交 | **69** | `git rev-list --count master..exp/n36-scene-anchor` |
| master 独有提交 | **119** | `git rev-list --count exp/n36-scene-anchor..master` |
| 分支独有**文件** | **202**（`v2/` 159、`tools/` 23、`reports/` 13、`code/` 7） | `ls-tree` 全树差集，分母 = 分支 3020 个文件 |
| master 独有**文件** | **167** | 同上 |

⇒ **这不是"谁落后几提交"，是两条内容互不包含的线**：master 拿不到周期报告，分支拿不到 D9t/D9u/D9v 系列。

## 2. master 上曾缺失的对外交付物（这就是发布链断点）

`reports/` 13 个文件（`comm -13`，分支有 / master 无）：

```
CYCLE-28-20261029.md   CYCLE-29-20261030.md   CYCLE-30-20261030.md   CYCLE-31-20261030.md
CYCLE-32-20261030.md   CYCLE-33-20261030.md   CYCLE-34-20261030.md   CYCLE-35-20261031.md
CYCLE-36-20261031.md   D10-address-drift-20261030.md   D9n-narration-rotation-20261030.md
R27-narration-hedge.md  R28-address-relation-basis-20261030.md
```

`v2/refs/` **13** 个（含 `D9n` 六条 amendment、`N15`/`N36` 预登记、`W-1` 天气预登记、`D10` 冻结回执）。

⇒ 后果具体：用户按报告名在 GitHub 找不到 CYCLE-28 之后**任何一份**周期报告；报告里引的预登记件也找不到。

## 3. 合并冲突：只有 1 处，且是同一份件的两次入库

- 文件：`v2/evidence/d9u1-errata-expansion-25.md`
- 形态：`CONFLICT (add/add)`——两条线各自从 nil 建了同名件
- master 版 `e27f17af` = 94 行 / 5,642 B；分支版 `d291f5ee` = 104 行 / 6,485 B
- `diff` 只有**一个 hunk**：分支版在 §5 后新增 §5.1「独立交叉核对」10 行，其余逐字节相同
⇒ **分支版是 master 版严格超集**，取分支版（无损，零内容丢弃）。

## 4. 顺带收口 `N-45` / `C36-G11`（引用链断点）

- 分支 `d9u1-errata §5.1` 写死「引用一律用 `0d26601b…`（4,353 B / 65 行）」，**该版从未进过任何一条线的仓库**，只存在于 team-workspace `artifacts/`。
- 仓内当时是它自述已取代的旧版 `c20296a9…`（3,614 B / 55 行）。
- 本次把 artifact 原样入库覆盖 `v2/evidence/d9u-lexicon-v21-five-arm-crosscheck.md`：
  实测 **`0d26601b3b45c011…` / 4,353 B / 65 行**，与 §5.1 声明**逐数吻合**。
- `CYCLE-36` 报告 §G 的 `C36-G11`「读者按 `0d26601b…` 找不到文件」**至此消解**；其修复项 `N-45` 由本提交执行。
- **尚未回填**：`reports/CYCLE-36-20261031.md` 的 G11 行状态文字仍写"失败"——该文件在主工作区有**在途草稿（+305/−28，未提交）**，归其作者收口，我不覆盖。

## 5. 合并安全性证据（合并前测的）

| 检查 | 结果 |
|---|---|
| `code/` 两线改动文件是否重叠 | **零重叠**（master：`planner.py` + 2 测试；分支：`agent.py`/`weather.py`/`encounter_metrics.py` + 8 测试） |
| 合并后语法 | `py_compile` 四个改动文件全过 |
| 回归测试 | `test_narration_toggle` + `test_addr_evolve_toggle` = **27 passed**；`test_habit_living_slot` + `test_l7_structural` + `test_life_narration_rotation` = **44 passed**（合计 **71 passed / 0 failed**） |
| 合并后文件在位 | 上表 13 个 report + 13 个 refs + D9t/D9u/D9v 系列件全部 `OK` |
| 合并后 `CYCLE-` 报告数 | **36** |

## 6. 合并后状态（服务端直读，不看 `push rc`）

```
git ls-remote origin refs/heads/master → e11ac4300c2356489f2f8727d1a94e68071e5069
git log --format="%h %p" -1 master    → e11ac43  349fab9 9dce475      (双亲＝真 merge，非 rebase 抹平)
master:.../d9u-lexicon-v21-five-arm-crosscheck.md sha256 = 0d26601b…
```

## 7. 边界（必须同屏，防下一轮误读）

1. 本件**只证明"两线已汇流"**，不证明任何实验结论、不改任何判据；
2. merge **不等于**"分支的实验被验收"——分支上 N-15/N-36 等臂的效果判定，仍按各自预登记独立判定；
3. 主工作区 HEAD 仍指 `exp/n36-scene-anchor`，其**在途草稿未提交**（`reports/CYCLE-36-…` +305/−28、`reports/README.md` +3）——**分支与 master 现在同源，后续继续在分支上做、定期回灌 master 即可，不再产生第二处分叉**；
4. 「发布链断多久」只能给下界：合并前 master 上的 CYCLE 报告是 **`CYCLE-01…CYCLE-27`（27 份，末份 `CYCLE-27-20261029.md`）**，`CYCLE-28` 起共 **9 份**（28/29/30/31/32/33/34/35/36）只在分支 ⇒ **断点起点 = CYCLE-28（2026-10-29），至本次合并已断 ≥2 天**；精确到小时的断点时刻 **CANNOT-VERIFY**（无外部读取记录）。
