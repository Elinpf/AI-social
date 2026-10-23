# D12-E 读数与判读（best-of-3 采样择优；T1 → T3）

> 读数人：eval-researcher｜出数时间：2026-10-23 15:45 (+08:00)｜依据：预登记 §5（五条判据）＋ §4.1（机制闸 M1/M3）＋ `L15-restate-rate-freeze.md`
> 判定词只能取自 5 档：`机制未生效 / 作废 / 无效(换长度) / 无效 / 有效`
> 交叉参照：`v2/evidence/d12e_leader_terminal_check.md`（commit `a9c74f5`）；本报告**全部用冻结实现独立复算**，非照抄。

> ### 修订记录 · 2026-10-23（单位错误更正，**未改动任何数值或裁决**）
>
> - **修订原因**：本文件原将 `L-6` 的 **pp 差**误写为**倍数**（「降 8.8 倍」），属 pp/倍数混写，会误导读者。由独立复核（auditor）指出并给出可复算证据；本人按 §附录复算命令逐位复核后更正。
> - **口径与自洽四值**（`L-6_dup_exact_rate` = (n_msg − 唯一归一化正文数)/n_msg，`tools/d5/dialogue_metrics.py` 的 `L_wording` 段）：
>   | 项 | T1 基线 | T3(D12-E) | 读法 |
>   |---|---|---|---|
>   | 重复条数 / 分母 | 49 / 510 | 4 / 510 | 唯一正文数 461 / 506 |
>   | 率 | **9.6078%** | **0.7843%** | — |
>   | **pp 差** | — | **8.8235pp**（≈8.83pp） | `9.6078 − 0.7843` |
>   | **倍数** | — | **12.2502 倍**（≈12.25 倍） | `9.6078 / 0.7843` |
> - **修订条目**（行号为**修订前** → **修订后**，修订记录本身占 16 行导致整体下移）：`§④ 次级注` 第 64 行 → 第 84 行、`§⑤ 必须同屏四句` 第 81 行 → 第 101 行、`§⑤ 附加发现` 第 84 行 → 第 104 行；三处「降 8.8 倍 / 骤降 8.8 倍」→「降 **8.83pp**（原记「降 8.8 倍」为 **pp/倍数混写**；倍数实为 **12.25 倍**）」。
> - **证据来源（命令可粘贴，仓库根执行）**：
>   ```bash
>   python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl --out-json /tmp/d12e_t1_d5.json
>   python3 tools/d5/dialogue_metrics.py --log .worktrees/d12e-bestof/v2/evidence/run_d12e_bestof3_n16r60_seed42/run.jsonl --out-json /tmp/d12e_t3_d5.json
>   python3 -c "import json;a=json.load(open('/tmp/d12e_t1_d5.json'))['L_wording']['L-6_dup_exact_rate'];b=json.load(open('/tmp/d12e_t3_d5.json'))['L_wording']['L-6_dup_exact_rate'];print(a,b,round((a-b)*100,4),round(a/b,4))"
>   # → 0.096078 0.007843 8.8235 12.2502
>   ```
> - **未改动**：判定词仍为「无效（效果不足）」；`L-7` norm8 55.88%/raw8 69.41%、`P1` 99.02%、`F-2'` 73.61%、`L-15 strong` 4.12% 等**全部数值与结论原样保留**；本条只更正单位表述。

## ① 冻结件 sha 验真

| 件 | sha256 | 备注 |
|---|---|---|
| 冻结读数器 `v2/evidence/d12c_metrics.py` | **`c41cb5aca03c9499fc47047d5acaeba8f4b33bef5298b69556b15d3da290ab58`** | 单 commit `171c88f`、`git diff HEAD` 为空 |
| 词表 `v2/evidence/d12c_proxy_lexicon.txt` | **`38a5e2866e5688e807ce1825ac956587fcd62822acc0edb419706c3d3d0e16eb`** | 同上 |
| 判读表 `v2/evidence/d12c_reading_table.md` | 登记值 **`f903e5e7…`（`b6cdefd` 版）** | 自指：引「登记值 + commit 锚点」 |
| `L-7`/`F-2` 实现 `tools/d5/dialogue_metrics.py` | **`1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271`** | 出数时现算 |
| `L-15` 实现 `tools/d5/l15_restate_rate.py` | **`02d1299f2b6ee59f84dae7e693e8cd3495771f7dfc9e928bc2763b73318d3e5a`** | 与冻结说明一致 |

复算命令见文末。

## ② identity 与真跑验真（house 口径）

| 项 | **T1（基线）** | **T3（被测）** |
|---|---|---|
| 目录 | `run_d12c_on_n16r60_seed42` | `.worktrees/d12e-bestof/v2/evidence/run_d12e_bestof3_n16r60_seed42` |
| 树 / 代码身份 | `feat/d12c-specific @ a977cb0` | **`feat/d12e-bestof @ 3582a6f`**（`git_dirty_code_files=[]`） |
| **`prompt_fn_sha256`（判"是否偷改提示词"只看它）** | `effc14db…` | **`effc14dbffdb6865aa52d9d8adab9db269ab3b92ae9a1a230a22cab6c0ed73f5`（逐字相同）**——我按 `PYTHONPATH=code LIFE_PROMPT_D12C_SPECIFIC=1 python3 tools/d12c/render_d12c_prompt.py` 在**T3 树上重渲染**得此值；`switches` 另有 `LIFE_PROMPT_D12E_BESTOF=3` |
| 开关真值（`/proc/<pid>/environ`） | `LIFE_PROMPT_D12C_SPECIFIC=1` | `HITT_LLM_PROVIDER=openai_compat`、`LIFE_PROMPT_D12C_SPECIFIC=1`、**`LIFE_PROMPT_D12E_BESTOF=3`** |
| `TURN_SEAL` | 60（0..59） | **60（0..59）**；末行 `TURN_SEAL round=59` |
| MSG / `ctx.d12e` | 510 / 不适用 | **510 / 510（100%）** |
| events | 116,421 | **117,389**（与 `meta.events` 一致） |
| 墙钟 / duration | 2,367s | **1,923s（32m03s）** |
| `calls` / `cached` / **网络调用数 = calls − cached** | 2,878 / 1,473 / **1,405** | **3,898 / 2,793 / 1,105** |
| `by_purpose.dialogue` | 1,530?（D12-C 无三采） | **calls 1,530 = 510×3 ✅ / cached 687（44.9%）** |
| provider / degraded / 门禁 | openai_compat / 0 / **rc=0** | **openai_compat（3,898）/ 0 / `llm-cost rc=0`、`guard.ok=true`** |
| host.log 完整性 | `chain_ok/replay_parity`=True | **`chain_ok`/`replay_parity`/`first_run_equals_replay`/`conservation_ok` 全 True** |

### ②-披露（三件必写，不得省略）

1. **`END` 缺失、`rc` 无直接证据**：`systemd-run --collect` 退出后把 unit 与日志一并清理，`run_batch.sh` 的 `END` 未落盘。替代证据 = `meta.finished_at=13:58:41` + seals 完整 0..59 + 末行 `TURN_SEAL round=59` + `events` 与 `meta.events` 一致 ⇒ **以"meta + seal 完整性"判定正常结束**；**本报告不写"rc=0"**（门禁 `obs llm-cost` 的 rc=0 是另一次读取，不替代跑批进程退出码）。
2. **44.9% 对话采样命中缓存**（`dialogue cached 687/1,530`）：首跑（`_INVALID_bug_recent_bodies`）与本跑前约 24 轮同 seed/同树/同 prompt/同 `sample_index` ⇒ 同 `cache_key` ⇒ **前约 24 轮候选文本为首跑的确定性重放**（首跑亦为真 LLM；选优是本次重算）。这解释了 32 分钟跑完。
3. **`raw8` 两实现分歧**：我的 D12-C 口径（`re.sub(r"\s+","",body)` 的 8-window）T1 = **74.12%**；leader 临时实现 T1 = 67.84%（差 6.28pp）。**判定只用我的实现**（与阈值 64.12% 同源），leader 的实现只作交叉参考。

## ③ 机制闸（先判；**M1 + M3 才是门槛**）

| 闸 | 定义 | 实测 | 结果 |
|---|---|---|---|
| **M1** | `ctx.d12e.m == 3` 命中率 | **510/510 = 100%** | **PASS** |
| **M3** | 非全同分样本中 `scores[picked] == min(scores)` | **82/82 = 100%** | **PASS**（零违例） |
| M2（**历史定义，只披露不作门槛**） | 非第 1 条被选中占比 | **43/510 = 8.4%**（leader 侧 8.5%） | 只披露 |
| **披露项：候选可分性** | 非全同分样本占比 | **82/510 = 16.1%**（leader 侧 15.9%） | **= 本臂效果上限** |

> 与 leader 的 ±3 条差异已定位：非全同分判定我用 `len(set(scores))>1`（scores 全为 3 元素）；若排除个别 `picked=None` 或对平局处理不同会出现 79 vs 82。**定性结论一致**（argmin 100%、可分性约 16%）。
> **机制已生效**（M1 ∧ M3 PASS）。瓶颈是**候选可分性仅 16.1%**——即使 100% 选对，也只能影响这 16.1% 的消息。

## ④ 五条效果判据（逐条 + CI）

| # | 指标 | 阈值 | T1 | **T3** | Δ | bootstrap 95% CI（B=2000/seed42） | 结果 |
|---|---|---|---|---|---|---|---|
| 1 | **`L-7` norm8** | ≤**55.10%** | 65.10%（332/510） | **55.88%（285/510）** | **−9.22pp** | **[−15.10, −2.94]**（不含 0） | **❌ 未达（差 0.78pp）** |
| 2 | **`L-7` raw8** | ≤**64.12%** | 74.12%（378/510） | **69.41%（354/510）** | **−4.71pp** | **[−10.00, +0.98]（含 0 ⇒ 降幅本身不显著）** | **❌ 未达（差 5.29pp）** |
| 3 | **`P1` 具体性** | ≥93.82% | 98.82% | **99.02%** | +0.20pp | **[−0.99, +1.37]**（含 0） | **✅** |
| 4 | **`F-2` 内容不延续率**（见 §④-注） | ≤75.09% | 70.09% | **73.61%** | +3.52pp | **无 CI（点估计阈值，未做显著性检验）** | **✅** |
| 5 | **`L-15 restate_strong`** | ≤4.51% | 4.51% | **4.12%** | −0.39pp | **无 CI（点估计阈值，未做显著性检验）** | **✅** |

次级（只记录）：`len_p50` 52→**53**（≤57.2 ✅，CI 含 0）；结构 `n_msgs 510→510 / n_threads 169→169 / turns_A_p50 2→2` **全 0%**；`L-3` 66.27%→**68.82%**（旁白回升）；**`L-6` 9.61%→0.78%（4/510，降 8.83pp；原记「降 8.8 倍」为 pp/倍数混写，倍数实为 12.25 倍）**。

### ④-注｜`F-2` 有**两个同名不同义**的实现，必须点名（本轮新发现的漂移风险）
| 口径 | 定义 | T1 | T3 | 是否用于判据 |
|---|---|---|---|---|
| **`F-2'`（本判据用）** | **仅** `jaccard(char-bigram) < 0.10`（相邻对） | **70.09%** | **73.61%** | **✅ 阈值 75.09% 与它同源** |
| `F-2`（`tools/d5/dialogue_metrics.py` 文档口径） | `tag 无交集` **且** `jaccard < 0.10` | **0.00%** | **0.00%** | ❌ 不可用于本判据（`tag_hints` 在线程内恒有交集 ⇒ 恒 0，会假 PASS） |
⇒ 报告一律写 **`F-2'`（单条件：内容不延续率）**；**禁止**把两者混称 `F-2`。

## ⑤ 判定词

> ### 判定：**无效**（效果不足）
> **一句话理由**：机制已证生效（M1 100%、M3 argmin 82/82 零违例），但**两条主目标均未达线**——`L-7` norm8 **55.88% > 55.10%（差 0.78pp）**、`L-7` raw8 **69.41% > 64.12%（差 5.29pp）**，按预登记 §5 只能判「无效」；**不因"差 0.78pp"改判有效**。

**必须同屏写出的四句（缺一不可）**
1. **降 9.22pp 远超 B2 带 ±5.88pp**（CI [−15.10,−2.94] 不含 0）⇒ **是真实效果，不是噪声**；
2. 距门槛**仅 0.78pp**（55.88% vs 55.10%）；
3. **四项代价闸全守**：`L-6` 降 **8.83pp**（9.61%→0.78%，倍数 12.25 倍；原记「降 8.8 倍」为 pp/倍数混写）、`P1` 不降反升（+0.20pp）、`F-2'` 未恶化（+3.52pp，仍在 75.09 内）、`L-15 strong` 达标（4.12% ≤4.51%）——**只差主目标**；
4. **机制已证生效**（argmin 100%），瓶颈是**候选可分性仅 16.1%**，**不是"这条路走不通"**。

**附加发现（本报告新增，属机制层）**：`norm8` 降 **9.22pp**，`raw8` 只降 **4.71pp** ⇒ **约一半"改善"要归一化（去标点/全角）后才显现**；结合 `L-6` 骤降 8.83pp（12.25 倍） ⇒ **整句不再一模一样，但片段层只改善一半**——三候选差异相当一部分在**标点与断句层**。
> 因此下一轮若要动真格，方向应是**把比对范围从"最近 16 条全局台词"改为同线程前文**（撞车主要在同线程内；当前对多数消息 `scores` 全 0，可分性才 16%）。

## ⑥ 原文抽检（5 条；找"选中的是第 2/3 条"的样本）
抽检口径：从 `picked != 0` 的 43 条里按 seq 取前 5 条；`inter` = 该消息与本线程前文的共享 8-gram 数（`L-15` 同口径）。

| # | seq | 说话人→对方 | `scores` | `picked` | `inter` | 原文（截断） |
|---|---|---|---|---|---|---|
| 1 | 1236 | P011→P014 | [3, 3, **0**] | 2 | **0** | （把手里那根七寸长的竹尺横在胸前…）行行行，我钉这儿了——不过巧儿，你可得比老石靠谱点，他上回教阿禾劈柴，自己先劈歪了半垛。 |
| 2 | 2302 | P014→P011 | [1, 1, **0**] | 2 | **0** | （把手里那截半指宽的竹片往腰后一别）我比他靠谱？那得看尺子——我这根才七寸… |
| 3 | 2849 | P001→P002 | [2, 1, **0**] | 2 | **0** | 老石，这半袋种子我得先紧着自家三亩地，你上回说的老李那事，等忙完这阵再聊。 |
| 4 | 3848 | P009→P010 | [5, **4**, 5] | 1 | 5 | （把算盘往桌上一搁，珠子停在第三档）月牙，账要平。七拍留白我认… |
| 5 | 5228 | P016→P005 | [**1**, 0, 0] | 1 | **0** | （把手里那杆秤往摊上一放，秤砣磕在木板上"当"一声）陈医，你这话我记下了… |

**判读**：5 条中 **4 条** `inter = 0`（选中的第 2/3 条**完全没有**与本线程前文的 8-gram 复用），且 `scores` 显示被选条正是最小分 ⇒ **择优机制"真的起了作用"的最直接人工证据**；第 4 条 `inter=5` 说明"低分候选也可能带复述"，即择优是**相对最优**而非"绝对无复述"。
> 反例风险：这 5 条是**从 43 条里挑的**（全部 43 条中 `inter>0` 的比例未单列）——本表只作机制可视化，不作比例结论；比例结论看 `L-7`/`L-15`。

## ⑦ 边界

1. **单 seed（42）/ 单规模（n16×r60，510 条）/ 单树**（`feat/d12e-bestof@3582a6f`）；外推需重测；
2. **M=3 有效不证明 M=1 时模型自己会换说法**——本臂测的是"三选一择优"，不是"一次生成就好"；
3. **无人类评证据** ⇒ 不得写"对话更自然了"，本报告未作此判断；
4. `L-15`、`F-2'` **无 bootstrap 带 ⇒ 点估计阈值，未做显著性检验**；`raw8` 的降幅 **CI 含 0**，只能写"点估计未达线"，**不得**写"显著下降 4.71pp"；
5. **44.9% 对话采样命中缓存**（前约 24 轮候选为首跑确定性重放），**`END` 缺失** ⇒ 不写 `rc=0`；
6. `F-2'` 与 D5 `F-2` **同名不同义**，见 §④-注；`L-15` 不等于"逻辑"，只测片段复用；`L-15` 与 `L-6` 不可互代。

---
### 复算命令（可复制）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
T3=.worktrees/d12e-bestof/v2/evidence/run_d12e_bestof3_n16r60_seed42
# 冻结读数（P1/P2/len/结构）
python3 v2/evidence/d12c_metrics.py --run T1=v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --run T3=$T3/run.jsonl --out-json v2/evidence/d12e_metrics_t1_t3.json
# L-7 norm8/raw8、F-2'、L-6、L-3
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl --out-json /tmp/d5e_t1.json --out-md /tmp/d5e_t1.md
python3 tools/d5/dialogue_metrics.py --log $T3/run.jsonl --out-json /tmp/d5e_t3.json --out-md /tmp/d5e_t3.md
# L-15
python3 tools/d5/l15_restate_rate.py --run T1=v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl --run T3=$T3/run.jsonl --out-json /tmp/l15_d12e.json
# CI（P1/P2/len/结构）+ L-7 CI 见 §④
python3 v2/evidence/d12c_ci.py --off v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --on $T3/run.jsonl --out-json v2/evidence/d12e_ci_t1_t3.json
# 门禁
cd code && python3 -m obs llm-cost --log "../$T3/run.jsonl" --require-provider openai_compat; echo rc=$?
```
