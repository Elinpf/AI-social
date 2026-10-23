# A. CYCLE-15 commit 区间与工作树状态（描述性登记）

- **取数时刻**：2026-10-24T04:32:43 +08:00 动手（起点 HEAD = `2a52123d726a48d8d093d801e739c0bb141c2e25`）
- **取数完成时刻 HEAD**（区间止点钉住值）= `da5379d6578d6aa78507d14372906078d1de62d4`
- ⚠️ **区间止点是移动靶**：本人在 04:32–04:36 取数期间，master 被其他成员推进了 2 次（`9693b2f`、`da5379d`）。下面把「动手时 HEAD」与「完成时 HEAD」两值并列，读者按自身时刻复算时以 `git rev-parse HEAD` 为准。
- 复算命令：`git rev-parse HEAD && git log --format='%h %cI %s' 4e20256..HEAD`

## A.0 一条必须先讲的事实：区间起点 `4e20256` 在 master 上不可达

| 检查 | 命令 | 实测 |
|---|---|---|
| 是否祖先 | `git merge-base --is-ancestor 4e20256 HEAD; echo $?` | **NOT ancestor** |
| 哪些 ref 含它 | `git for-each-ref --contains 4e20256 --format='%(refname)'` | **空**（无任何分支/标签/tag 可达） |

结论（描述性事实，非判定）：`4e20256`（`report(cycle14)` @ 2026-10-24T04:29:34+08:00）是一个**游离（dangling）commit**，与 master 上的 `6c8a70d`（同 message @ 04:27:44+08:00）**同父 `d0a320b`**、是同一批交付物的两个变体。二者差异**只在 `tools/d12i/` 下 4 个新增文件**：

```
git diff --name-status 4e20256 6c8a70d
A  tools/d12i/build_external_shingles.py
A  tools/d12i/selector_stats.md
A  tools/d12i/selector_stats.py
A  tools/d12i/wiring_proof.py      # 共 394 行；reports/ 与 v2/ 两树逐字相同
```

因此「以 4e20256 为区间起点」在 master 上**等价于以 `d0a320b` 为起点**（因为 4e20256 的全部内容均已包含在 master 的 6c8a70d 中）。本文件按任务卡要求照 `4e20256..HEAD` 出列表，但**同时声明该起点不可达**，撰稿人引用时不得把 `4e20256` 写成「已入库」。

## A.1 区间内 commit（`git log --format='%h %cI %s' 4e20256..HEAD`）

| # | commit | 时间 (+08:00) | 性质 | 分类 |
|---|---|---|---|---|
| 1 | `6c8a70d` | 2026-10-24T04:27:44 | report(cycle14) F-1 生活气息推进 + D12-I 读数证据与复验留痕 | **跨周期登记**（= CYCLE-14 交付物，因起点游离而落入本区间；其内容已于 CYCLE-14 报告登记） |
| 2 | `2a52123` | 2026-10-24T04:27:51 | chore(d12i) 分支处置裁定——tools/d12i 合入 master | **跨周期登记**（同上；CYCLE-14 的收尾动作） |
| 3 | `9693b2f` | 2026-10-24T04:33:20 | report(cycle14) 回填入库 sha（README 索引行 + §1.4 提交时点说明） | **跨周期登记**（CYCLE-14 报告的回填补丁，取数期间由其他成员提交） |
| 4 | `da5379d` | 2026-10-24T04:35:43 | evidence(verify) 补记 V2 被验版与入库版对应关系 | **跨周期登记**（CYCLE-14 复验留痕补记，取数期间由其他成员提交） |

### 本周期已入库 commit 数 = **0**

理由（口径名：`cycle_scope.commit_attribution`）：上述 4 条全部是 **CYCLE-14 交付物的入库/回填/复验补记**，无一条承载 CYCLE-15 的新工作。本周期真正的推进（`tools/d21/partner_choice_stats.py`、`partner_choice_permtest.py`）**仍为未跟踪文件（`??`），尚无 commit、无产物**——见 A.2。

## A.2 工作树状态（`git status --porcelain`，取数完成时实测 **26 行**）

分类（26 = 25 `??` + 1 ` M`）：

| 类别 | 行数 | 清单 | 归属 |
|---|---|---|---|
| 已跟踪文件被改动（` M`） | 1 | `v2/evidence/d3_noiseband_bootstrap.json`（`git diff --stat` = +25 / −125） | **历史脏项**，非本周期产生；未处置 |
| 未跟踪目录/文件（`??`） | 25 | 见下 | 混合：**历史遗留 + 本周期新增** |

25 条 `??` 明细与归属判定：

| # | 路径 | 归属 |
|---|---|---|
| 1–11 | `code/frontend/sample/dialogue_{a5_full6,a5_multiturn,cycle03_ctrl,cycle04_a5,cycle06_f6off,cycle06_f6on,cycle07_d12c_off,cycle07_d12c_on,f2b_v2_off,r21_scene_off,r21_scene_on}/` | **历史脏项**（多周期累积的渲染样本目录） |
| 12 | `tools/d21/partner_choice_stats.py` | **本周期新增**（B 项主角） |
| 13 | `tools/d21/partner_choice_permtest.py` | **本周期新增**（B 项主角） |
| 14 | `tools/d21/partner_choice_permtest_conditional.py` | 本周期新增（条件版置换检验，本轮 B 项未使用，仅登记存在） |
| 15 | `tools/f2/r10e2e_forget_levels.py` | 历史脏项（他项工具） |
| 16 | `v2/evidence/cycle06_shots/_blank_check_failed/` | 历史脏项 |
| 17 | `v2/evidence/d12h_shots/` | 历史脏项（CYCLE-13/14 留痕） |
| 18 | `v2/evidence/d21_partner_choice.md` | 历史脏项（D2.1 期留痕，先于本周期） |
| 19 | `v2/evidence/d21_partner_hhi_permtest.json` | 历史脏项（同上） |
| 20 | `v2/evidence/d21_partner_hhi_permtest_conditional.json` | 历史脏项（同上） |
| 21 | `v2/evidence/d22_partner_choice/` | **本周期新增**（本证据包，即本文件所在目录） |
| 22 | `v2/evidence/e1_run_scripts/` | 历史脏项 |
| 23 | `v2/evidence/forget_levels_f2b_v2_off_a9c74f5.json` | 历史脏项 |
| 24 | `v2/evidence/forget_levels_g1_b0_d9391a3.json` | 历史脏项 |
| 25 | `v2/evidence/run_r10e2e_n16r60_seed42/` | 历史脏项（含 `run.jsonl`，受 `.gitignore:8 **/*.jsonl` 约束） |

**本周期新增未跟踪项 = 4 项**：第 12、13、14、21 行。
**历史脏项 = 22 项**：第 1–11、15–20、22–25 行。

> **并发漂移说明**：上表是 2026-10-24T04:36 前后的**时点快照**（26 行）。04:38 复检时工作树已增至 40+ 行，新增项全部来自**其他成员的并发作业**（`?? reports/CYCLE-15-20261024.md`、` M reports/README.md` 等），非本人产出；本人本周期产出仅为 `v2/evidence/d22_partner_choice/` 一个目录。读者复现时行数必然不同，**行数本身不作为任何判据**，只作「脏项分布」的描述性快照。

## A.3 复算与取证

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
git rev-parse HEAD                                  # 期望与「取数完成时刻」一致或更新
git log --format='%h %cI %s' 4e20256..HEAD
git merge-base --is-ancestor 4e20256 HEAD; echo "rc=$?"   # 期望 rc=1（NOT ancestor）
git for-each-ref --contains 4e20256 --format='%(refname)' # 期望空
git diff --name-status 4e20256 6c8a70d              # 期望 4 个 A tools/d12i/*
git status --porcelain | wc -l                      # 25 ?? + 1 M（本证据包提交后会变化）
```

证据状态：**已核实**（命令均在本机实跑，输出见上表）。
