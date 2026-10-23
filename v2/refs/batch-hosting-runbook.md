# 跑批托管 runbook —— 让长批次扛得住平台重启（T271）

> 作者：release-engineer ｜ 2026-10-12 ｜ 任务：T271-batch-hosting-survives-platform-restart
> 状态：**已实测**（mock/decoy 验证；未实测处标 **【未验证】**）。交付对象：obs-stats-dev / team-leader。
> 脚本：`tools/t271/`（本目录内，已实测）；运行产物默认落 `/root/t271/runs/<batch>/`（仓库外，不进 git）。

---

## 0. 一句话
长跑批必须**跑在 `jiuwenswarm.service` cgroup 之外**，否则 memguard 重启平台会把它连坐回收。
做法：`systemd-run --unit=<name>` 起一个**独立 transient unit**（在 `system.slice` 下、与平台服务平级）。
本 runbook 给出：**逃逸实测 + 重启存活验证 + 心跳 + 续跑口径 + 可复制粘贴启动清单**。

---

## 1. 元凶与机制（事实）
- `jiuwenswarm.service` 的 `KillMode=control-group`：**重启该单元 = 回收其 cgroup 内所有进程（含 detached 子进程）**。
- memguard 于 **15:52:24** 触发 `systemctl restart jiuwenswarm` → 服务组内进程被回收 → T236 在 round 35 **静默死亡**（无 OOM、无 traceback）。
- 实测：我们启动的进程 cgroup = `/system.slice/jiuwenswarm.service`。

## 2. 逃逸实测（三种方式对照，2026-10-12 16:41）
| 启动方式 | `/proc/<pid>/cgroup` | 逃逸？ |
|---|---|---|
| `setsid sleep 300` | `0::/system.slice/jiuwenswarm.service` | ❌ **否** |
| `systemd-run --scope --unit=X sleep 300` | `0::/system.slice/X.scope` | ✅ 是 |
| `systemd-run --unit=X sleep 300` | `0::/system.slice/X.service` | ✅ 是 |

**结论**：`setsid` 只换 session、**不换 cgroup** → 照样连坐；**必须用 `systemd-run`**。长跑批用 `--unit=<name>`（transient **service**，立即 detach、由 PID 1 托管、可查可停、可设内存上限）。

## 3. 重启存活实测（decoy 复现同一 KillMode + 反向对照，2026-10-12 16:46）
用 `t271-guard.service`（**与 jiuwenswarm.service 同为 `KillMode=control-group`**）复现杀组语义，一次重启同时观察两个对象：

| 对象 | 位置 | 重启前 | 重启后 | 判据 |
|---|---|---|---|---|
| 受害者（in-cgroup，`setsid` detached） | `.../t271-guard.service` | pid=72956 alive | **alive=no** | **反向对照**：它没死则测试无效 |
| 候选批（逃逸，独立 unit） | `.../t271-restart-cand.service` | pid=73117 alive | **alive=yes（同 pid）** | 逃逸存活 |
| 候选批心跳 | `cand/mock.hb` | 重启前有行 | 重启后仍有行 | 跨越重启时刻**连续** |

结果：**`RESULT: PASS`**。受害者心跳末行冻结在 `2026-10-12 16:46:45`（=重启时刻）——**恰好复现 T236「死在哪一刻」**。
> 语义等价说明：只重启 decoy，**绝不真重启平台**（会打断全员会话）；decoy 与平台服务**同一 `KillMode`**，唯一杀组手段相同 → 结论对平台成立。

## 3.9 【硬规则】跑批窗口内禁止改代码（2026-10-20 事故后新增）

**规则**：批从起跑那一刻到最后一条 `TURN_SEAL` 落盘为止，**任何人不得修改**
`code/life/`、`code/orchestration/`、`code/config/`、`code/engine/`。
新功能一律开分支（`git switch -c feat/<topic>`），**跑完再合并**；紧急修复也必须等批结束。

**为什么**：2026-10-20 的 A0 臂（19:19–20:09）期间，另一执行上下文在 20:05–20:06 把
F4「误会与和解」的 4 个文件改进主树 ⇒ `meta.git_dirty_files` 记成"脏"，核验方按 S0a/S0e
判 **FAIL**、整条证据链降级。事后证明无害（无 reload、`dialogue_rift` 零命中）——**那是运气，不是机制**。

**配套机制（已落地）**：
- `tools/d2/emit_run_meta.py` 现记录 `git_status_start` / `git_status_end` / `code_sha_end`，
  并给出断言 `assertions.code_unchanged_during_run`（只比 `code/` 路径）；
- **起跑时必须留快照**：`git status --porcelain > <out_dir>/git_status_start.txt`，
  生成 meta 时用 `--git-status-start <该文件>`；缺快照则该断言为 `null`（不可判，需人工说明）。

**起跑后 1 分钟内的三条自证（固定动作，缺一不可）**：
```bash
pgrep -fa "orchestration run"                    # ① 有进程
ls -la <out_dir>/                                # ② 目录/文件在长
wc -l <out_dir>/run.jsonl; sleep 30; wc -l <out_dir>/run.jsonl   # ③ 两次差值 >0
```
另：**跑批必须 `setsid` 脱离调用方进程组**；**禁止用超长 `sleep` 监控**（2026-10-20 实
测：作者侧 `sleep 600` 被工具强杀，连带杀掉了同进程组的跑批进程）。进度检查用 30 秒级短轮询。

## 3.95 【硬规则】对照臂必须证明「它处在对照状态」（2026-10-22 事故后新增）

**规则**：任何"开/关"两臂实验，起跑后**必须先抽查前 20 条产出**，确认**对照臂处于该树的预期状态**，再让其继续跑；
**不允许**用"开关文件里写了 0"或"脚本里 unset 了"来证明对照臂。

**事故经过（D12-A，2026-10-22）**：
- 树的提示词里已并入 `A1-措辞`（禁旁白）⇒ body 旁白**天然就是 0%**；
- 但对照用的是**另一棵树**（`3ec85a0`，中性提示词，旁白 78%），于是"开臂 0% vs 对照 78%"被读成"D12 让旁白归零"；
- 实际是**"拿一棵已经禁过旁白的树，去对比一棵没禁的树"** ⇒ 两个变量叠加，结论作废。
- 若起跑后先抽查 20 条：对照臂旁白已是 0%，当场就能发现"对照不存在"。

**配套动作**：
1. **按树写期望值**：每棵树的提示词状态不同，期望值必须现算（例：含禁旁白的树 ⇒ 旁白期望 **0%**；中性树 ⇒ 期望 **≈78%**）；
2. **前 20 条自检**：`python` 读首批 MSG，算关键指标，与期望值比对；偏离 >5pp ⇒ **停跑**；
3. **`switch_proof` 用 `printenv <VAR>` 真值**（不是脚本字面量）；两臂都要；
4. **对照必须同树**：跨树比较只能得到"两棵树合并效果"，不能归因到单个开关。

## 3.97 【硬规则】判定阈值必须冻结「唯一指标实现」（2026-10-22 事故后新增）

**规则**：任何用于**判定阈值**的指标，必须在预登记里**写死唯一实现**（函数源码 + `sha256`），并在结果文档里注明该实现；
**两种实现并存时，判定值取"更保守"的那个**，另一版只能作注，不得参与结论。

**事故经过（D12-A 问题 (a)，2026-10-22）**：
同一"具体性代理"（`DETAIL_WORDS`）两套实现，OFF 臂相差 **1.04pp**（95.29% vs 96.33%），
直接把 ON−OFF 的 Δ 从 **+3.14pp** 翻成 **+2.09pp**，而阈值是 **+3pp** ⇒ **同一份数据能得出相反判定**。
Leader 裁决：本轮判定值取**保守的 +2.09pp（= 不成立）**，+3.14pp 仅作注。

**为什么重要**：能被实现差异翻转的结论，本来就不该写进结论。**"指标"和"阈值"必须同时冻结，否则等于没有阈值。**

## 3.98 【硬规则】证据必须来自「被执行的那一层」，不能来自「写命令的那一层」

**规则**：任何记录"这次跑批用了什么开关/什么环境"的凭据（`switch_proof` 等），
**必须由真正执行该批的那一层产生**（unit 属性 / `bash -c` 内联 env / 被测进程自己 dump），
**不得**用"写脚本那个 shell"的 `printenv` 值代替。

**两次事故（2026-10-22/23）都在这条线上**：
1. **父 shell 的值被继承**（D12-A seed=7）：上一批 `export HITT_D12_DETAIL=1` 残留，baseline 臂实际按 ON 跑；
2. **父 shell 的值被当成子进程的值**（D12-B ON 臂）：`systemd-run` 已用 `--property=Environment=...` 注入 1，
   但写 `switch_proof` 的 `printf` 在我自己的 shell 里执行 ⇒ 记成 `<unset>`，与事实相反。

**正确写法（已验证）**：
```bash
# 1) 起跑：开关既进 unit 属性、又在 bash -c 内联（双保险，且都可审计）
systemd-run --unit=t271-<batch>-$TS --collect \
  --property=EnvironmentFile=<repo>/code/.env.local \
  --property=Environment=HITT_<SWITCH>=1 \
  --working-directory=<worktree>/code \
  /bin/bash -c "cd <worktree>/code && HITT_<SWITCH>=1 python3 -m orchestration run --life ... --out <dir>/run.jsonl ..."

# 2) switch_proof：记**起跑值**，并附 launch_cmd 原文（不要写 printenv 的父 shell 值）
cat > <dir>/switch_proof.txt <<EOF
unit=t271-<batch>-$TS
code_sha=$(git -C <worktree> rev-parse --short HEAD)
env_HITT_<SWITCH>=1        # 起跑真实值：unit 属性 + bash -c 内联
env_HITT_LLM_PROVIDER=openai_compat   # 来自 EnvironmentFile
params seed=<s> n=<n> rounds=<r>
prompt_fn_sha256=<该臂实际 prompt 的 sha>
launch_cmd=<上面那条命令原文>
EOF
```
- 若确需"关"的臂：**用 `env -u HITT_<SWITCH>` 显式清空**，并在 proof 里写 `<unset>`（此时 `<unset>` 才是事实）；
- **更强做法**（可选）：让被测进程自己把 `os.environ` 相关键 dump 到 run 目录（"被执行层"自证）。

### 3.98b 【硬规则·升级】`switch_proof` 的标准取法：读 `/proc/<PID>/environ`，**不用 `printenv`**

> 来源：2026-10-23 leader 裁决（prompt-linguist 提出，替换此前 §3.98 里"用 `printenv`"的写法）。

**为什么**：`printenv` 读的是**执行 `printenv` 的那个 shell** 的环境（即"写命令的那一层"），
`systemd-run --property=Environment=...` 注入的是**unit/进程那一层**；两者可以不一致——D12-B 的事故就是这样把 `=1` 记成 `<unset>`。

**标准做法（三件真值，缺一不算证明）**
```bash
PID=<跑批进程 pid>
# ① 执行层环境真值（唯一可信来源）
tr '\0' '\n' < /proc/$PID/environ | grep 'LIFE_<SWITCH>'   # OFF 臂应**无输出**；ON 臂应 `=1`
# ② 实际 cmdline（证明跑的确实是这条命令）
tr '\0' ' ' < /proc/$PID/cmdline; echo
# ③ unit 名
systemctl show -p Id <unit>
```
- **OFF 臂的期望是"无输出"**：证明"变量不存在"比证明"变量=1"更难，必须写成**显式期望**，不许写"未设置"含糊了事；
- 抓取时刻要记（`date -Is`），并在 60 秒硬闸时**再抓一次**（防止中途被重启成另一个进程）；
- `printenv` 仍可用于**自查你自己 shell**（如 `env_pre_*.txt`），但**不得**作为 `switch_proof` 的字段。

## 3.99 【硬规则】三件容易被"看起来对"骗过去的事（2026-10-23 三次实践后新增）

### 3.99a 证据索引必须写「路径 + 全 64 位 sha256 + 入库 commit」
只写 `sha8…`（或写成 `sha8…（全值见该件 §X）`）**不算可对拍**：
- `sha8` 只有 32 bit，碰撞与"看错一个字符"都可能；
- 「见该件 §X」经常**指向错地方**（该件的 §X 是别的表），2026-10-23 在 `R4` 上就发生过一次。
⇒ 规范写法：`<路径>`（入库 commit `<sha7>`，<该 commit 是否已含本次改动>）+ **全 64 位 sha256**。
任何人都能 `git show <commit>:<path> | sha256sum` 对拍。

### 3.99b 指标对某批"不可算"时，必须显式返回 `NOT_APPLICABLE`，不得硬算
2026-10-23 `L-15` 首版把 `thread_id` 缺失的消息按 `legacy-<msg_uid>` 归组，导致 **v0 全批被当成一条线程**，算出 **33.69%** 的假值（正确处置：187/187 缺 tid ⇒ 拒绝计算）。
⇒ 规则：**指标先自检输入前提**（如"线程边界"必需 `thread_id`），前提不成立就**拒绝出数并写明原因**；**假值一旦进了报告，比"无数据"危害大得多**。

### 3.99c 多次采样前必须确认「缓存键会变」，否则 N 次采样 = 1 次
`code/freeze/llm_client.py::make_cache_key` = `digest({cache_schema, kind, engine_version, prompt_hash, model, tier, params})`，**命中即原样返回、不调模型**。
⇒ 任何"同 prompt 多次采样"的机制（best-of-N、多次自评、重采样去重），**必须让 `cache_key` 每次都不同**（如把 `sample_index` 并入 `params`），且该变化**必须确定性派生**（随机会毁 `FREEZE_MODE=replay`：`cache_key` 不匹配 → "重放模式缓存未命中（禁止真实调用）"）。
⇒ **反例（禁止）**：把采样序号/随机种子**写进 prompt 文本**去改 `prompt_hash` —— 那会同时改掉 `prompt_fn_sha256`，等于**偷改提示词**，`prompt_fn_sha256` 与开关一致性证明立刻失效。

## 3.100 【硬规则】"接线对了"≠"取值对了"：静默兜底会把 bug 伪装成阴性结果（2026-10-23 D12-E 事故）

### 事故
D12-E（best-of-3 采样择优）起跑后 191/191 条 MSG 都带 `ctx.d12e`、三个 `cache_key` 两两不同、`cached=false` ——**三条例行接线闸全 PASS**。但中途核 M2 闸发现：
```
picked = {0: 191}（全选第 1 条）；scores 三列均值 = 0 / 0 / 0；三候选全同分 = 191/191
```
根因：`recent_bodies(wv, limit=16)` 被按 `recent_bodies(wv, self.agent_id)` 调用（**把 agent_id 当 limit**）⇒ 函数内 `len(out) >= "P002"` 抛 `TypeError` ⇒ 被调用处的 `except Exception: recent = []` **静默吞掉** ⇒ 交集集恒空 ⇒ `scores` 恒 0。
若跑完，判定会是「机制未生效」——**看起来像阴性结果，实际是 bug**。

### 规则（三条）
1. **机制链路上禁止裸 `except: pass / except: []` 兜底**。异常要么不捕获（让它炸），要么写进审计字段（如 `ctx.<arm>.error`）**并计入接线闸**；
2. **机制臂必须有"取值有效性"硬闸，不能只验"字段存在"**。例：`scores` 不得全为 0、`picked` 必须有分布、`scores` 三列不得恒等；这类闸要**与接线闸并列写进预登记**；
3. **中途快照提前核闸**：本批在 **24/60 轮**就发现（省下 36 轮 ×3 倍成本）。凡"三倍成本"或"判定词可能被判死"的臂，**跑到 1/3 时必须手工核一次核心闸**，不等收尾。

## 3.101 【硬规则】两个 `rc` 别混：`llm-cost` 的 rc ≠ 跑批进程的 rc（2026-10-23 D12-E）

**事故**：D12-E 收尾时执行者报「跑批 rc=0」，但其 `run_summary.md` 里那个 `rc=0` 是 **`obs llm-cost --require-provider` 的返回码**；产物目录里**既无 `END` 也无 `run_batch.rc`**（`systemd-run --collect` 在 unit 退出后连日志一起清理，`END` 没落盘）⇒ **跑批进程的 rc 根本没有证据**。

| 名字 | 证据 | 能证明什么 |
|---|---|---|
| `obs llm-cost --require-provider` 的 rc | `llm_cost.json` + 调用记录 | 真 LLM、无 mock、`degraded=0` |
| **跑批进程的 rc** | `END` / `run_batch.rc` | **进程正常退出**（无则**无证据**） |

**规则**：
1. 报告里**不得**把两者写成一个"rc=0"；无 `END` 时只能写「以 `meta.finished_at` + `seals` 完整 + 末行 `TURN_SEAL` + `events` 与 meta 一致判定为正常结束；**进程 rc 无直接证据**」；
2. **生产 `rc` 的正确姿势（已实现，`tools/d2/run_batch.sh` `193cd63`）**：用 **EXIT trap** 写 `run_batch.rc` + `run_batch.end`，且 trap **必须装在参数解析之前**（否则"参数错 `exit 2`"这类最常见失败会漏记）；此时 `OUT_DIR` 未解析，落兜底目录 `${RUN_BATCH_FALLBACK_DIR:-/tmp/run_batch_unknown}`；`run_batch.end` 里带 `out_dir=` 便于事后对账。自测四例（A 未知参数 / B 缺 `--out-dir` / C 兜底目录可改 / D mock 正常跑）见 `v2/refs/run_batch_rc_selftest.md`；
3. **门禁命令与日志不同源时须写明**：如本树无 `python3 -m orchestration obs`（rc=2）而改用主树 `python3 -m obs`，报告须写「门禁命令来自主树、被解析日志来自本臂」。

## 3.102 【硬规则】同一个 `F-2` 名字下有一个「死标尺」（LEGACY_DEAD_RULER，恒 0，会假 PASS）

2026-10-23 D12-E 出数时发现：D5 的 `dialogue_metrics.py` 同时输出 **两个** F-2 键：

| 键 | 口径 | 实测 | 可用性 |
|---|---|---|---|
| `F-2_topic_drift` | 相邻消息 **tag 无交集 且** jaccard<0.10 | **0.00% → 0.00%** | **`status = LEGACY_DEAD_RULER`**：新结构下 `tag_hints` 线程内恒定 ⇒ "tag 无交集"恒 False ⇒ **结构性恒 0**，误用会得到**假 PASS** |
| `F-2_content_drift`（= **`F-2'`**） | 仅 char-bigram **jaccard<0.10**（不看 tag） | 70.09% → 73.61% | **唯一可用**，判据一律用它 |

**规则**：
1. 判定/报告涉及"内容漂移"时**必须写 `F-2'`** 并注明 `= F-2_content_drift.drift_rate`；**禁止**只写 `F-2`（读者无法知道是哪个键）；
2. 凡是**结构性恒 0/恒 1** 的指标，一律**不得作为效果判据**（它只能证明"这个维度的结构不变"，不能证明"变好"）；
3. 同类前例：`turns_A_p50`（实为线程消息条数）、`paren_rate` 两义、`L-7` raw8/norm8 两口径——**引指标前先确认"这个名字下有几个实现"**。

## 3.103 【硬规则】比率型判据的六件事：分母写死 / 双口径 / 半成品自证 / `pp`≠倍 / 规则对实现实跑 / 预登记 freeze（2026-10-23 D12-F）

> 来源：D12-F（候选结构多样化）跑批期间暴露的六类口径问题，全部出在**"判据怎么写、规则怎么落到实现"**这一层，不在算法层。
> 复核：本节经 `auditor` 两轮复核（退回一次），复核意见在 `<team-workspace>/runbook_3.103_review.md`。

### 3.103.1 比率型指标必须在**预登记**里写死分母（分子 / 分母 / 分母为何是这个）

- **本轮实例（两条，都是真事故）**：
  1. `v2/refs/D12F-prereg-candidate-diversity.md` §3 的 **M4 只写「候选可分性（非全同分样本占比）≥ 25%」，没写分母是谁**；
  2. 后果已经发生：`v2/evidence/d12e_leader_terminal_check.md:68「79/497」（修订前 `:54`）把 **79/497 = 15.90%** 当终态读数写进表里，而**497 在终态日志上根本不可达**——该文件 `:67` 同一张表自己写着这一列的来源：「**42/497 中途口径**」，即 497 是**跑批中途快照的分母**。
- **终态唯一可复现读数**：**82/510 = 16.0784%**。终态日志上任何筛选都回不到 497：`n_msgs=510`、`ctx.d12e` **510/510**、`len(scores)` 恒 3、`picked` 无 `None`、`sample_index==0` 467 条。生长链自洽：快照 497 条时非全同分 **79** → 终态 510 条时 **82**（后段新增样本落到非全同分），**不是**"剔除 `picked=None`"。
- **为什么**：预登记的全部价值是「**阈值不可事后调**」。分母没写死 ⟺ 阈值可调 = 预登记作废。分母不是统计细节，是**判据定义的一部分**。

复算入口（口径写进命令，不用匿名片段；机制闸读数器同时也是 M4 的两种分母的权威实现）：
```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 v2/evidence/d12f_gate_metrics.py \
  --run-jsonl .worktrees/d12e-bestof/v2/evidence/run_d12e_bestof3_n16r60_seed42/run.jsonl \
  --ctx-key d12e --label AUD_D12E_M4 --out-json /tmp/aud_m4_d12e.json
# → n_msgs=510；M4_separability: A(全部带 ctx 的 MSG) 82/510=16.0784，B(剔除 picked=None) 82/510=16.0784 ⇒ A=B；497 不可达
# 分子定义：len(set(scores))>1；分母：全部 MSG_DM/MSG_PUBLIC/MSG_GROUP
```

### 3.103.2 分母未写死时：**双口径并列**，裁决一致才有效；「出处」只认三处

- **规则**：同一指标存在两种合理分母时，**两种都报**（各自写明分子/分母条数与出处），只有**两口径裁决一致**（同为达标或同为不达标）才能出结论；**不一致一律判「口径不明 · 不可判」**，**禁止择一**。
- **「出处」只有三种**：① **预登记原文**；② **预登记正文内的跑前修订块**（带时间戳且**早于起跑**）；③ `v2/refs/` 下的**独立修订文件**。
  **报告、终态核验文档、聊天消息里出现的分母一律不算出处**，只能记「待追项」，**不得**据此开启双口径通道。
- **本轮实例**：M4 的两口径在终态上 **A = B = 82/510 = 16.0784%**（机制闸读数器实现 `v2/evidence/d12f_gate_metrics.py:239`，输出 JSON 的 **`M4_separability.locked_ruling`** 字段写死「两种分母同时报、不得单独使用」；注意**不在顶层**）⇒ 裁决一致，对 25% 门槛**同侧（不达）**，可出「M4 未达」。
- **为什么（失效模式）**：出处不限定 ⇒ 任何人都能在**结果已知后**从某份旧文档里翻出一个对自己有利的分母并声称"有出处"；`79/497` 就躺在报告文档里，**双口径条款会立刻异化成择一通道**——与 §3.100「静默兜底把 bug 伪装成阴性结果」同病。

### 3.103.3 半成品读数必须**自证是半成品**，否则必被当终态引用

- **本轮实例（已发生，非假设）**：`d12e_leader_terminal_check.md:68「79/497」（修订前 `:54`）的 **79/497 = 15.90%** 就是**把中途快照当终态**——497 只存在于跑批中途（该文件 `:67` 自述「42/497 中途口径」），终态 510 条上不可达，终态值应为 **82/510 = 16.0784%**。全量扫描见 `<team-workspace>/partial_as_terminal_scan.md`。
- **规则（字段名以 `v2/evidence/d12f_gate_metrics.py` 的**实际实现**为准，实测见 3.103.5）**：
  - 文件名必须 `_partial_rNN.json`（`NN` = `snapshot.max_round_seen`）；**注意：当前脚本 `--out-json` 不校验文件名，此条靠人工遵守、待补断言**（见下）；
  - 体内必须带 `snapshot.partial = true`、`snapshot.snapshot_rounds_seen`、`snapshot.max_round_seen`、`snapshot.turn_seals`、`snapshot.lines_unparsable_or_partial`；
  - `snapshot.note` 在 `--partial` 时自动写「中途快照：partial=true，**不得**当作终态判读结论」；
  - 报告/消息引用时必须带 `partial` 字样与 `snapshot.max_round_seen`，**禁止**写成"当前读数"。
- **待补（登记，不在本节偷偷改实现）**：① `d12f_gate_metrics.py:16` 的 docstring 写「写 `partial=true` / `snapshot_at` / `snapshot_round` / `seals`」，而实现里**没有 `snapshot_at`**、键名是 `snapshot.partial` / `snapshot.turn_seals`、顶层无 `partial` ⇒ **docstring 与实现不符，另立修正项**；② `--partial` 应加文件名断言（不匹配 `_partial_r\d+` 直接 `exit 2`），让规则有执行力。**两项均在 D12-F 跑批结束后处理**（现改脚本会改动 `reader_sha256`，使本批 partial 前后读数不可比）。
- **为什么**：批跑几十分钟到几小时，**中途数字会被别的成员、后续会话、甚至下一轮 agent 当成事实读走**；D12-E 已经真的发生过一次（79/497 进了终态核验表）。没有自证标记的半成品，事后**无法与终态区分**，只能靠人再追一轮分母。

### 3.103.4 `pp` 与「倍」不得混写：差值一律 `Δ = X pp`，比值一律「倍（附计数比 a/b）」

- **本轮实例**：D12-E 的 `L-6_dup_exact_rate` 由 **49/510 = 9.6078%** 降到 **4/510 = 0.7843%**；**pp 差 = 8.8235pp**、**倍数 = 12.2502 倍**。原报告写「降 **8.8 倍**」——把 **pp 值当成倍数**，**3 处 + 3 处（两个文件）**：`v2/evidence/d12e_result.md:84/:101/:104`（片段锚：「降 8.83pp」）、`v2/evidence/d12e_leader_terminal_check.md:84/:101/:109`（片段锚：「降 8.83pp」/「8.83pp / 倍数 12.25 倍」）（均 2026-10-23 更正并留文件头修订记录）。全量排查见 `<team-workspace>/unit_errata_scan.md`。
- **规则**：写差值只用 `pp`；写比值必须写「N 倍（a/b = 计数比）」，让读者一步复算。**两者不得互相顶替**，也不允许只写「降 N 倍」而隐藏被除关系。
- **为什么**：8.83pp 与 12.25 倍差一个量级；混写让读者把"效果强度"判断反了，而且**错值可复算时看起来同样精确**（"8.8" 确实出现在数据里），最难被发现。

越界检查命令（机械复验"只改了该改的行"）：
```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
git show 9ae3eae -- v2/evidence/d12e_result.md v2/evidence/d12e_leader_terminal_check.md
# 期望：每个文件只有「文件头修订记录块 + 3 行正文表述」变更；d12e_leader_terminal_check.md 的脚注¹(raw8) 与 §3.1「两实现分歧」段不得出现在 diff 中
```

### 3.103.5 【新增】写进 runbook 的**字段名 / 命令 / 文件名**，必须在提交前对着实现**实跑一次**，并把输出贴进修订记录

- **本轮实例（本节自身的翻车）**：3.103.3 初稿把 `d12f_gate_metrics.py` 的 **docstring** 当成了实现，写成「输出 `partial:true` + `snapshot_round` + `snapshot_at` + `seals`」。实际跑一遍立刻暴露：顶层**没有** `partial`，字段是 `snapshot.partial` / `snapshot.snapshot_rounds_seen` / `snapshot.max_round_seen` / `snapshot.turn_seals` / `snapshot.note`，且**没有 `snapshot_at`**（全文件仅 docstring `:16-17` 提到）。被 `auditor` 以"规则与实现不一致"退回。
- **规则**：
  1. 凡 runbook 里出现**具体字段名、具体命令、具体文件名模式**，写作者必须**当场执行一次**，把命令 + 真实输出片段贴进该节（或修订记录）；
  2. **以 docstring / 记忆 / 别人转述为准一律退回**——docstring 会漂移，实现不会说谎；
  3. 若发现 docstring 与实现不符，**两者都要治**：规则按实现写，另立一条「docstring 修正项」，不得只改一边。
4. **引用必须同时给「当前行号 + 原文片段锚」**，例：`v2/evidence/d12e_leader_terminal_check.md:68「79/497」`。**只给行号视为不可定位**——行号会随每一次文件头修订无限漂移，双行号（`:68（修订前 :54）`）第三次改完又会失配，**文本锚才是稳的**。
   **行号漂移实例（本轮实测）**：给 `d12e_leader_terminal_check.md` 加「修订记录」块（占 14 行）后，`79/497` 所在行由 `:54` 移到 `:68`；同时 `:54` 变成「§1.2 披露二：44.9% 对话采样命中缓存」段——若只写 `:54`，读者会读到一段完全无关的披露。这也正是「行号必须对当前 blob 实跑」的自我适用：**写规则的人最容易违反规则**。
- **为什么**：runbook 是后续每一批的执行依据，一条错字段名会让下一批的读数器输出错键、让复核方按错键验、让报告引用不存在的字段。**这次是复核方在入库前抓住的；如果不经复核，错的规则会当天生效并写进下一轮报告**（与 §3.102 的 `F-2` 死标尺同类：名字对不上，指标就废了）。

### 3.103.6 【新增】预登记必须 **freeze → `sha256sum` → commit → 用 commit 内 blob 自核**，入库窗口内禁止再改文件，且**禁 `commit --amend`**

- **本轮实例（三态，实测，非转述）**：E1 预登记在「提交者 `git add`」与「life-designer 继续编辑 §8-D」**并发**的情形下入库，同一天在本地历史里留下三个版本：

  | commit | 文件 sha256（前 16） | 字节数 | 状态 |
  |---|---|---|---|
  | `78fdcb8` | `b97f99d5d729a70e…` | 36,569 | 中间态（有 §1.1 J-1…J-5、§6.1 两条硬声明，缺 §8-D 改写与 Amendment 1 行） |
  | `9ae3eae` | `ef666ee29762332c…` | 38,618 | 中间态（补了 §8-D/Amendment 1 的前半，仍未定稿） |
  | `0520e1e` | `17fc907574d0e750…` | 41,345 | **最终冻结态**（HEAD） |

  复验命令：
  ```bash
  cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
  for c in 78fdcb8 9ae3eae 0520e1e; do
    printf '%s ' $c; git show $c:v2/refs/E1-prereg-coop-closure.md | sha256sum | cut -c1-16
    git show $c:v2/refs/E1-prereg-coop-closure.md | wc -c
  done
  git reflog -n 5      # 可见 9ae3eae HEAD@{1}: commit (amend)
  ```
- **已发生的违规（如实登记）**：本轮对 `78fdcb8` 执行过 **`commit --amend`**（reflog `9ae3eae HEAD@{1}: commit (amend)`），后果是 `78fdcb8` 里的中间态 blob `8262d583…` **已不能从任何 ref 到达**（`git cat-file -t` 仍返回 `blob`，但只在 reflog 与 dangling 对象里）⇒ **"保留中间态"在 git 层没有做到**，只能靠文件内 Amendment 2 的文字登记兜底。同时 `0520e1e` 的 commit message 写「中间态 → 最终冻结态」，**实际中间态已被 amend 抹掉，该表述失真**（不得再据此 message 复述版本谱系，请照上表三态讲）。
- **规则（按可执行动作写，不设例外）**：
  1. **冻结**：定稿后 `sha256sum` 一次，把 **commit 短 sha + 字节数 + sha256 前 8 位 + 时刻**写进**预登记文件内的冻结记录块**；
  2. **提交**：**禁 `commit --amend`、禁 `push --force`，不设例外**（一旦 amend，前一版 blob 立即从 ref 图里消失，等于销毁证据）；
  3. **入库窗口**：从 `git add` 到 push 完成的整个窗口内，**任何成员不得再写该文件**（本轮 case：提交者 add 时 life-designer 正在改 §8-D）；
  4. **自核以 blob 为准，不以工作区为准**：`git add` 后用 `git show :<path> | sha256sum` 核**暂存区**；commit 后用 `git show <commit>:<path> | sha256sum` 核**提交内 blob**；两者都等于冻结记录里的值时才算成功。**只用工作区 `sha256sum` 自核是无效的**——add 之后工作区仍会变，核到的是错 blob，这正是本轮事故的发生机制；
  5. **已提交中间态 ⇒ 只能补 commit**，并在文件内登记「中间态 sha / 最终态 sha / 原因」；**不得用 amend 掩盖**；
  6. **冻结后不得回写冻结件**（leader 2026-10-23 16:32 批准，原文照录）：
     > **冻结后不得回写冻结件。** 预登记一旦 `commit`（无论是否 push），即为冻结件：其 sha256 与内容不得再变。此后的一切修订只能落成 **`v2/refs/` 下的独立修订文件**（如 `E1-amendment-3.md`，注明「修订对象 + 修订对象 sha256 + 写于何时 + 是否已见读数」），并由后续 commit 引入。
     > **正文内修订块仅在冻结前允许**：即「文件尚未 commit」阶段写进正文，且必须带时间戳早于起跑。冻结后在正文里追加 Amendment N，等同于事后触碰冻结件，一律不接受。
     > 理由：冻结件的唯一价值是「内容未被事后改动」；允许在它里面追加段落，等于保留了"事后编辑"的合法通道，审计上无法区分「追加」与「篡改」。
     **衔接说明（leader 已确认）**：本款与 runbook 既有口径「跑前修订只认两类（预登记正文修订块 / `v2/refs/` 独立修订文件）」**不冲突**，只是给第 ① 类加了前置条件——**必须在 `commit` 之前**。
  7. **证据检索一律用前缀精确匹配**：`LIFE_PROMPT_COOP_E1`、`run_e1_`；**`e1_` 这类宽匹配会命中 `v2/evidence/event_cards_e1_e20_map.md`**（实测存在），会污染"是否已起跑"的判断。
  8. **补：`git add -- <path>` 的边界 + 污染判据**（**这是第 3、4 款的判据，不是第四条并列规则**）：
     - `git add -- <path>` 只锁定「**我放什么进暂存区**」，它**不能**阻止并发写者在他自己的 `git add` / commit 里把**同一文件**的其它改动一并带走——本轮实例：`4dab73d`（作者名为**仓库默认 git 身份** `life-evidence-analyst`——即 `git config user.name` 的默认值，任何不显式设 author 的提交都会记这个名 ⇒ **提交者身份不可辨**，不得据此判断成员归属）在提交其「墙钟/缓存」小节时，把当时尚未提交的 §3.103 全文 94 行一并 add 入库（`git show 4dab73d -- v2/refs/batch-hosting-runbook.md | grep -cE "^\+## 3\.103|^\+### 3\.103\.[1-6]"` = 8）。
     - ⇒ 真正的防线只有两条，**缺一不可**：①**入库窗口内不发生并发写同一文件**（第 3 款）；②**提交后立刻 `git show <commit>:<path>` 自核**（第 4 款）——被掺入时能第一时间定位，而不是几天后才发现作者与提交者不一致。
     - **判据（可机械执行；"他人未提交的改动"提交后已不可见，因此不能拿它作判据）**：三条命令对着**该 commit 本身**跑——
       ```bash
       git show --stat <commit>                          # 文件数/行数是否超出你本次应提交范围
       git show <commit> -- <path> | grep -cE '^\+## '   # 同一 commit 里新增了几个一级节标题
       git log -1 --format=%s <commit>                    # message 是否只提到其中一节
       ```
       **判定**：`^+## ` 命中 **≥2** 且 commit message **只描述其中一节** ⇒ **判污染**。
       本轮实证（`4dab73d`）：`git show --stat` = 单文件 103 insertions；`grep -cE '^\+## '` = **2**（两个 `+## 3.103` 头）；
       `git log -1 --format=%s` 只讲「墙钟/缓存」一节 ⇒ 命中判据。
     - **处置**：按「**不追溯、不改历史、另行登记**」处理（登记写清：污染 commit、被掺入的内容与行数、后续定稿 commit）。**禁止**用 amend / force push "修干净"——那只会把凭据一起删掉（见第 2 款与本轮 E1 三态实例）。
- **本轮"三态都早于任何一臂"的独立验真（auditor 复验，本人复核同值）**：`grep -rl LIFE_PROMPT_COOP_E1 --include=*.py --include=*.json --include=*.sh .`（排除 `.git`/`.worktrees`）= **0 命中**；`code/life/coop_e1.py`、`code/life/tests/test_coop_e1.py`、`tools/d5/f9_coop.py` **均不存在**；无 `*coop*` / `*run_e1*` 批次目录 ⇒ 三个版本都产生于**任何一臂起跑之前**，**不构成"看到结果再改口径"**（属流程违规，非发布事故。**推送状态按 3.103.5 要求带时点**：2026-10-23 16:33 复核 `origin/master` 已前移至 `4dab73d`，`9ae3eae` / `0520e1e` 已**随 `4dab73d` 一并上远端（推送者身份不可辨）**；其后 `f052fa8` 及本次 commit 当时仍未推送——`timeout 20 git ls-remote origin master` rc=124。**16:40 网络恢复后已全部推送**：16:41 复核 `HEAD = origin/master = cbaed944b85779be8bb12294d61f165232dcadbb`，`origin/master..HEAD` = 0）。
- **为什么**：预登记的法律意义是「阈值不可事后调」。一旦同一次入库里出现两个字节数不同的预登记，"哪一版是跑前那版"就只能靠逐字比对去猜；而 **amend 会把凭据本身删掉**。补一个 commit 是成本，force push / amend 已推历史是把证据链毁掉。

## 3.104 【硬规则】别用"被缓存污染的观测"去设预期墙钟（2026-10-23 D12-F）

> **编号更正（2026-10-23 16:31）**：本节原编号为 `§3.103`，与上方「比率型判据的六件事」**撞号**（两节在同一文件里同为 `## 3.103`，成因是两次提交各自占用同一号）。此处改为 `§3.104`，**正文一字未改**。

**事故**：D12-E 只跑 **32 分钟**（因为 44.9% 的对话采样命中了历史缓存），我据此给 D12-F 设「超 120 分钟报我」。但 D12-F 的候选 prompt **全新** ⇒ `dialogue cached=0`（全 miss）⇒ 投影墙钟 **≈122 分钟**。**把正常当异常报了一次警**。

**规则**：
1. **设墙钟预期时用"无缓存命中"的基线**：`单采臂实测时间 × 采样倍数`（例：T1 49m59s × 2.4 ≈ 120 min），**不要用有高缓存命中率的批**；
2. **报告里凡给墙钟，必须同时给该批的 `cached` 命中率** —— 否则读者会把"缓存让跑批变快"误读成"这个机制便宜"；
3. **区分两个阈值**：「报我」的阈值（可以是软的、提前预警用）与「停」的阈值（要有明确异常判据）。**停的判据优先看"每轮耗时是否衰减/翻倍"，而不是绝对墙钟**——绝对墙钟会被缓存、端点、judge 比例同时扰动。

## 3.104 【硬规则】闸本身会测不准：三类已知缺陷 + 审计字段必须覆盖判据依赖（2026-10-23）

**三道闸各自栽过一次，类型不同，都要在**设计时**自查：**

| # | 闸 | 缺陷类型 | 后果 | 修法 |
|---|---|---|---|---|
| 1 | M2（D12-E）「非第 1 条被选中 ≥20%」 | **分布假设错误**（假定最优均匀分布） | 惩罚"第 1 条恰好最优"这一正确行为 | 换成 M3"非全同分样本中选中=最小值，须 100%" |
| 2 | M4（D12-F）「非全同分占比 ≥25%」 | **天花板限制**（三候选 `scores` 全 0 时必然同分） | 低估候选真实差异，几乎不动 | 换成**候选文本两两 8-gram Jaccard 距离均值**（与"是否被选中"无关） |
| 3 | `L-15` 首版 | **前提不成立仍出数**（缺 `thread_id` 时按单线程硬算） | 33.69% 假值 | 前提不成立 ⇒ 显式 `NOT_APPLICABLE` |

**规则**：
1. **闸必须与"它想测的东西"一一对应**：想测"选择逻辑对不对"⇒ 用 argmin 命中率；想测"候补之间差多少"⇒ 用候选文本距离；**不要用"分数是否不同"去代替"文本是否不同"**；
2. **审计字段必须在跑前覆盖所有判据依赖**：D12-F 的判据依赖"候选差异"，但 `ctx.d12f` 只落 `{m,picked,scores,group}`、**未落候选文本/`candidate_shas`** ⇒ 事后**无法复核**该闸。下一臂至少加 `candidate_shas: [...]`（落 sha 控体积）；
3. **闸被证明有缺陷时**：不改阈值、不改判定，但**必须在同一屏写清"闸的缺陷 + 机制本身的直接证据"**两句话，缺一不可（只写判定会误伤机制，只写证据会架空预登记）。

## 3.105 【硬规则】跨刻度不可比：换指标不是"同一件事换个数"（2026-10-23 D12-G）

**事故**：M4（非全同分比例 21.57%）被 M5（8-gram Jaccard 距离 0.9693）替换后，我口头写"换指标从 21% 跳到 97%，证明 M4 是坏闸"——**这是跨刻度修辞，不成立**：一个是"有多少样本分数不同"，一个是"候选文本差多远"，**分母与量纲都不同**，不能作比值、不能作"跳升"。

**严谨写法**（eval 校正后采用）：
> M4 的全同分里，绝大多数是三候选 `scores` 全 0（与近期台词无交集）而非候选文本相同；用与"是否被选中"无关的文本距离测得 0.9693 ⇒ **候选文本本身差异极大**，故 M4 低**不能**解释为"候选相似"。

**规则**：
1. **换指标时必须声明"刻度是否可比"**；不可比就只写"新指标给出什么结论"，**不写"从 X% 到 Y%"**；
2. 旧指标的数值要**照旧保留**（M4 21.57% 仍在报告里），新指标另起一行；
3. 任何"用两个不同分母的百分比做减法/倍数"的句子，发布前必须自问：**这两个数的分母是不是同一个东西？**

## 3.105b 候选重复：三采择优会静默退化成两采（同一批发现）
D12-G 284 条里有 **1 条**（`seq=26894`）**候选 0 与候选 1 的 sha 完全相同** ⇒ 该条的"三采"实际是"两采"，M5 的最小值 0.3763 由此而来（不是机制下限）。
⇒ **规则**：best-of-N 类机制必须检查**候选 sha 是否重复**，重复则**重采**（上限 K 次）并记账。

**§3.105b 补：想让"候选差异"事后可算，落什么才对**（2026-10-23 eval 校正，三条都采纳）
1. **不能落"集合的 sha"** —— `sha256(shingle_set)` 是**32 字节摘要**，**摘要之间算不出交集大小**，归因照样不可补算。要逐条可算必须落二者之一：
   - **排序后的 shingle hash 列表**（如 `candidate_shingle_hashes: [[h…],[h…],[h…]]`，每个 shingle 用 blake2b-8B、按值排序；体积 ≈ 每候选 30–80 项，可控）—— **推荐，精确可复算**；
   - MinHash 签名（如 k=64，128B/候选）—— **只够估计** Jaccard；若用就**必须写成"MinHash 估计值"**，不得声称可算精确交集。
2. **`scores` 已经是"候选与近期台词的 8-gram 交集数"**（argmin 依据）⇒ 不要再加 `inter_counts` 这类同量字段，否则"按 scores 归因"与"按 inter_counts 归因"会打架。正确做法：**在预登记里把 `scores` 的定义写死**（窗口 = 最近 N 条？跨线程还是仅本线程？N 多少？是否 `normalize_body` 后 8-window？），使 `scores` 本身可作归因依据。
3. **`picked_cand_sha` 冗余** ⇒ 有 `picked`（索引）+ `candidate_shas` 就够；若担心错位，加断言 `candidate_shas[picked] == picked_cand_sha`，不必存两份。

## 3.106 【硬规则】提交必须限定 pathspec：`git add` 挡不住并发写者，`git commit` 默认提交**整个 index**（2026-10-23 第二次同类事故后新增）

**事故（本轮实测，只描述机制，不追责）**：一次「先 `git add -- <我的 9 个路径>`，再裸 `git commit -m …`」的证据提交，**实际入库 12 个文件**——多出的 3 个是另一位写者在「我 `add` 之后、我 `commit` 之前」这一窗口内 `git add` 进**同一 index** 的未预期文件（`v2/evidence/d12g_l15.json`、`v2/evidence/d12g_leader_terminal_check.md`、`v2/evidence/d12g_metrics_t4_t5.json`），被我的裸 `commit` 一并带走（commit = `16111b6`）。内容无损，但**该 commit 的可归因性已破坏**：从 `git show --stat` 看不出哪些文件是提交者本意。
> 这是**第二次**同类机制事故：§3.103.6 第 8 款已记过「`git add -- <path>` 只锁定"我放什么进暂存区"，不能阻止并发写者把同一文件的其它改动一并带走」。**本款的增量是：把提交动作本身从"整个 index"改成"限定 pathspec"，从机制上取消"掺入"这个可能性**，而不是靠事后自核去发现。

**规则（三条，都可机械执行；不设例外）**

1. **提交必须限定 pathspec，禁止「先 `add` 再裸 `commit`」**：
   ```bash
   # ✅ 正例：提交动作自己指定范围，index 里别人的东西带不走
   git commit -m "<message>" -- <path1> <path2> <path3>
   # ❌ 反例（本款针对的就是它）：提交的是整个 index
   git add -- <path1> <path2>; git commit -m "<message>"
   ```
   注：`git commit -- <paths>` 等价于「只提交这些路径的当前工作区内容」，**不需要先 `add`**；若已 `add` 过，再带 pathspec 提交同样安全（pathspec 优先）。新增文件必须已 `git add`（或 `git add -N`）过才能被 pathspec 提交。
2. **提交前强制核对（两步，缺一不可）**：
   ```bash
   git diff --cached --stat     # ① 看 index 实际内容，与你打算提交的清单逐行比对
   git status --short           # ② 看工作区是否有人刚往 index 里塞东西
   ```
   **出现任何未预期文件 ⇒ 叫停本次提交**，先查清是谁在写、写到哪一步；**不得以"内容无损""反正也要进 master"为由放行**（本轮就是这条被放宽了）。
3. **并发窗口的归因口径（判「这个 commit 能不能引用」）**：多成员共用一棵工作树时，任何「先 `add`、后 `commit`、中间隔了其他写者」的提交，**默认视为不可归因**；只有当 `git show --stat <commit>` 能证明差异**全部是提交者自己改的文件**时，才可归因。
   ```bash
   git show --stat <commit>          # 文件列表必须与你声明要提交的清单**逐行相等**
   git log -1 --format='%an <%ae>' <commit>   # 身份仅供参考（默认 git 身份不可辨，见 §3.103.6 第 8 款）
   ```
   附带口径（沿用 §3.103.6 第 8 款）：**"他人未提交的改动"在提交后已不可见，不能拿来当判据**；判据只能对着 commit 本身跑。

**处置规则（事故已发生时）**：**不改写历史**（`16111b6` 之后已有 `37a4fd3`，`reset`/`rebase`/`amend` 会把证据链与下游引用一起弄断）⇒ **留在库里 + 在后续 commit message 或本节登记里写清"哪些文件是本次被裹入的、为什么无损"**；`git add --amend` 类补救一律禁止（见 §3.103.6 第 2 款）。

**正例（本款的自我执行）**：新增本节的提交本身就是按本款做的——`git add -- v2/refs/batch-hosting-runbook.md` 后，用 **`git commit -m "…" -- v2/refs/batch-hosting-runbook.md`**（限定 pathspec），并以 `git show --stat HEAD` 证明只动这一个文件。

**边界**：本款只管「提交范围」；预登记冻结件本身的并发写与 amend 禁令仍归 §3.103.6。两款的防线是叠加的：§3.103.6 第 8 款管「同一文件被掺入他人改动」，本款管「整个 index 被掺入他人文件」。

## 3.106b 【硬规则】ignore 规则不得静默吞掉证据件：`git status` 看不到证据件就是缺陷（2026-10-23 自伤后新增）

**缺陷（本轮实测，是 §3.106 之后发现的直接副作用）**：上一轮为收副产物加的 `**/*.log` 把**证据目录里的渲染日志也一并吞了**。
- 实测（改动前，规则层）：`git ls-files '*.log'` = **36 份已入库 log**，其中 **35 份**在规则层面命中 `**/*.log`（只有 `T270-motion-after.log` 有例外）——即 35 份是**靠"已 tracked"才留在库里的**，规则本身一直在吞它们；
- 直接后果：渲图成员写 `v2/evidence/d12g_shots/render_wrap.log` 后 `git status` 看不见，只能用 **`git add -f`** 强推（`5282032` 即如此入库）。
- 为什么这类缺陷特别阴：**文件在磁盘上、报告也能引路径，但 clone 后不存在**——比报告写错更难发现，因为本地一切"看起来正常"。

**规则（四条）**
1. **判据**：任何情况下「`git status` 看不到一份被报告引用的证据件」都算缺陷，**不得用 `-f` 当日常手段**；`-f` 只作应急，**事后必须补 ignore 规则并在本节记账**（补了哪条、放行哪些路径、为什么范围这么收）。
2. **例外必须按路径收窄，禁止 `!**/*.log` 这类全量反否定**（那等于把 `**/*.log` 规则作废，副产物又会回到 `git status` 里）。当前口径：**只有落在 `v2/evidence/` 下、且属渲染/取证或门禁复跑的日志放行**——
   ```
   !v2/evidence/**/render*.log      # 渲染取证日志（报告引用图的复现记录）
   !v2/evidence/**/shots/**/*.log   # 同上，shots 目录内
   !v2/evidence/**/ab_rerun.log     # 门禁复跑日志（fix-sleep-consolidation 证据引用）
   ```
   `host.log` / `batch.log`（批次宿主日志，可再生、报告只引 `meta.json`/`run_batch.rc`）**保持忽略**，不开口子。
3. **验证不能只看 `git check-ignore` 的 rc**（本轮踩到）：负向规则命中时 `git check-ignore -v` **也会 rc=0** 并打印 `!pattern`（实测），把它当"仍被忽略"就是误判；反过来 **tracked 文件默认不参与 ignore 判定**（`check-ignore` 对它们直接 rc=1），必须加 `--no-index` 才看得到规则本身。**唯一可信的验证是真实探针**：
   **探针脚本（整段可直接复制执行；含事后自清，不留残留）**：
   ```bash
   cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
   mkdir -p v2/evidence/_c11probe_shots v2/evidence/_c11probe_run v2/evidence/preflight
   : > v2/evidence/_c11probe_shots/render_wrap.log     # 应放行（render*.log）
   : > v2/evidence/_c11probe_run/host.log              # 应仍忽略（host.log 未开例外）
   : > v2/evidence/preflight/_c11probe.log             # 应仍忽略（preflight 不在例外内）
   git status --porcelain --ignored v2/evidence | grep _c11probe
   git ls-files -o --exclude-standard v2/evidence | grep _c11probe
   rm -rf v2/evidence/_c11probe_shots v2/evidence/_c11probe_run v2/evidence/preflight/_c11probe.log
   git status --porcelain --ignored v2/evidence | grep -c _c11probe || echo "probe_cleaned"
   ```
   **判读（`??` = 未被忽略会入库；`!!` = 被忽略）**，实测输出：
   ```
   ?? v2/evidence/_c11probe_shots/           ← 放行成功
   !! v2/evidence/_c11probe_run/             ← 仍忽略，符合预期
   !! v2/evidence/preflight/_c11probe.log    ← 仍忽略，符合预期
   v2/evidence/_c11probe_shots/render_wrap.log   ← ls-files -o 只能看到这一个
   0
   probe_cleaned                             ← 清理干净
   ```
   ⚠ **探针文件名必须带唯一前缀**（本例 `_c11probe`）：仓内已有 `v2/evidence/side_probe_n{20,50}.tar.gz`，若用宽匹配 `grep _probe` 会把它们也匹配上，导致「清理后仍非 0」的假报警（本轮实测踩到，故改成 `_c11probe`）。
4. **新增/修改 ignore 规则后必须跑一次全量核对并报数**：`git ls-files '*.log'` 逐个比对，确认「已入库 log 不因新规则变成只靠 tracked 状态苟活」，并给出**改前/改后的命中数**（本轮：规则层命中 35 → 18，18 份全是 `host.log`/`batch.log`，属有意保留忽略）。

**边界**：本节只管 `.log`/`.pid`/`.tsv` 类副产物规则的**证据安全问题**；提交范围与并发 index 污染仍归 §3.106。

## 3.107 【硬规则】同族臂必须标注机制类别：相邻 Δ 不得跨类别比较（2026-10-23 第五个静默失败实例）

**缺陷形态（判读层：数字全对、结论全错）**：把五个臂按时间排成一列，每行读数都对，但**相邻 Δ 跨了机制类别**就会得出两个**相反**的误读：
- 误读 A「单步最大降幅 8.63pp ⇒ 结构位换法很有效」；
- 误读 B「所有提示词臂都只小步慢走 ⇒ 提示词层到顶了」。
两者都来自同一张表 —— 因为表里混了 **「改」（换提示词结构位）** 与 **「选」（best-of-N 采样择优）** 两类机制。

**判例（实测，norm8，D5 口径 `tools/d5/dialogue_metrics.py`；分母均为 510）**

| 臂 | 机制类别 | norm8 | 相邻 Δ |
|---|---|---|---|
| T1（`run_d12c_on_n16r60_seed42`） | 基线 | 65.10%（332/510） | — |
| D12-D | 换结构位（**改**） | 64.51%（329/510） | **−0.59pp** |
| D12-E | best-of-3 采样择优（**选**） | 55.88%（285/510） | **−8.63pp** ← 跨类别，不得与上一行连算 |
| T4 = D12-F | 换结构位（**改**） | 52.55%（268/510） | −3.33pp |
| T5 = D12-G | 换结构位（**改**） | 48.63%（248/510） | −3.92pp |

⇒ 同类别（**改**）内：`−0.59 / −3.33 / −3.92pp`，同向小步，**这才是"换结构位"的斜率**；把 D12-E 的 −8.63pp 放进去会把斜率放大 2 倍以上，且它根本不是同一种干预。

> **⚠ 口径守卫（2026-10-23 22:30，Leader 纠回）**：本节表格列名是「**相邻 Δ**」= **相对上一行**。
> D12-E 的上一行是 D12-D（64.51%）⇒ 相邻 Δ = `55.88 − 64.51 = **−8.63pp**`；`−9.22pp` 是「**相对 T1(65.10%)**」，**另一列**。
> 曾有提交（`a0ad4a4`）以"原值把 D12-D 误当基线=串臂"为由把本列改成 −9.22pp —— **那是误读**：相邻 Δ 本来就以上一行为基线，改后会让同一列里 −0.59/−3.33/−3.92（相邻）与 −9.22（相对 T1）**混用两种基准**，反而制造新矛盾。**已纠回。**
> 规则：**同一列内不得混用基准**；若要同时呈现，必须**分列**（相邻 Δ / 相对基线）。

**规则（四条，可机械执行）**

1. **臂必须显式标注机制类别**，取值至少含：`改`（改输入/提示词/结构位）｜`选`（采样择优 / best-of-N / 重采）｜`删`（去掉某能力/开关）｜`采样`（换 seed/规模）｜`观测`（只测不改）。**相邻 Δ 只允许在同一类别内比较**；表里缺类别列的臂表，一律视为未完成。
2. **跨类别并列时必须先分表或分块，并在块首标注类别**，不得直接排成一列算 Δ / 斜率。允许同屏出现多类，但必须能一眼看出「这几行同类、那几行同类」。
3. **推断不得跨类别外推**：禁止用「选」类臂的降幅去论证「改」这条路径有希望（反之亦然）。机制不同 ⇒ 干预不同 ⇒ 边际收益不可借。
4. **判别顺序写死**：拿到一串 Δ，**先问「这些臂的机制是否同类」，再问「趋势如何」**。顺序颠倒必错——本条不是"更谨慎一点"，是把顺序当硬约束。

**与既有条款的关系**：§3.105 管「不同**指标**（刻度）不可比」，本条管「不同**机制**（干预）不可比」——同族缺陷（都是"看着可比其实不可比"），但一层在量纲、一层在因果；§3.104（闸的缺陷）管的是"闸测不准"，本条管的是"读表读错"。

## 3.108 【硬规则】累计可比，归因不可（2026-10-23 D12-G，同一类错误的第三次）

**错误链**（同一晚三次，都是"归因越界"）：
1. 把「选」与「改」两类臂的相邻 Δ 连成一条斜率 ⇒ 误得"边际递减/到上限"；
2. 修正后又说「改类在加速」⇒ 但相邻 Δ 的 95% CI 全含 0，点估计不能当趋势；
3. 再修正后说「三轮**结构位**干预合起来显著有效」⇒ **又犯了归因越界**：T1→T5 的累计 CI 测的是 **D12-E(选) + D12-F(改) + D12-G(改) 串联叠加的总效应**，既含"选"类，也无法剥离单类别贡献。

**规则（四条）**：
1. **相邻 Δ**：只在**同一机制类别**内比较，且**必须带 CI**；CI 含 0 ⇒ 只能说"点估计同向"，不得说"加速/衰减/有效"；
2. **累计 Δ**：只能陈述为「**某几个臂叠加的总效应**」，**不得**写成其中某一类机制的效果；
3. **归因需要"单臂对单臂 + 无叠加"的设计**（如 T1 vs 只加某一处改动的臂），否则只能说"叠加后如此"；
4. **规划用量级**：n=510 时 norm8 Δ 的 bootstrap CI 半宽 ≈ **±6pp**；要把"真值 −4pp 级"的效应测成显著，**n 需放大约 4×（≈2000 条 / rounds 240 / n64×r60）** —— 这是从现有方差反推的**规划参考**，不是承诺。

## 3.109 【硬规则】规模不是"放大样本"，是"换场景"；配对优先于放大（2026-10-23 D12-G 后规划）

**三条禁令/指引（eval 校正，全部采纳）**：

1. **轮次不可当样本量放大**。`rounds` 60→240 **会改变被测现象**：`L-7` 是"与近期台词重复"，历史越长、线程越长 ⇒ **基线重复率自然抬升**，阈值也不再同窗同分母。
   ⇒ **240 轮 ≠ 60 轮的 4 倍样本**，是**另一个测量场景**；两者读数**绝不可互译**。要放大轮次必须重定窗口/分母/同窗纪律。
2. **消息级 bootstrap 会低估不确定性（线程聚簇）**。510 条来自 169 个线程、同线程内高度相关；消息级重采样等于"假装独立"。
   ⇒ **规模规划按线程级带宽**（本项目历史值：thread 20/30/50/68/100 → ±15.1/13.3/10.0/8.8/8.0pp），**消息级 ±6pp 是乐观值**；
   ⇒ **出数必须同时报消息级与线程级两个 CI，口径不同不得互代**；规划时 `n×4` 只能写成**下限**。
3. **验"某一处改动值不值得"时，配对设计优先于盲放大 n**。把「该结构位 ON」与「该结构位 OFF、其余臂相同」配成一对（**同窗口 / 同分母 / 同 rounds**），共模噪声被抵掉一部分 ⇒ 更省，且**不改变测量场景**。
   ⇒ 若配对后方差仍不足以分辨目标效应，**必须写"本设计下无法判定"并停手**，**不得**偷偷放大轮次改场景。

## 3.110 【硬规则】"落库哪一组"是实验设计，不是实现细节——配对实验的参照系污染（2026-10-23 D12-H）

**事故**：D12-H 设计成"ON 组落库、OFF 组只用于配对"。看起来只是"用哪组语料"，实际决定了**共享历史由谁生成**：
本 run 的历史 **100% 由 ON 组产生** ⇒ ON 与"自己的方言"天然更亲，OFF 是外来方言。**同一批候选换参照系，符号直接反转**：

| 参照语料 | ON−OFF（`overlap_frac`） |
|---|---|
| **本 run 自身历史** | **+3.90pp** |
| T5 全批 | **−3.91pp** |
| T1 全批 | **−8.50pp** |
| A0 全批 | −0.16pp |

⇒ 只看自身历史会得出"ON 更重复"，换任一外部语料则"ON 更少重复"。**前者是自亲和偏差（self-affinity bias），不是效应。**

**规则（四条）**：
1. **任何"一组落库、一组不落库"的设计，必须先问：落库组会不会污染参照系？** 若判据指标依赖"与共享历史的重合"，答案必然是**会**；
2. **修法**：**落库随机化**（每条消息按 p=0.5 落 ON 或 OFF），或跑"另一组落库"的第二批，使两方言在历史中平衡；
3. **判据改双参照系**：**自身历史 + 外部语料**，**两者同向才算有效**；只报一个参照系的一律视为不可判；
4. **易混淆点**：这类偏差**不会**出现在"只与最近 N 条比"的口径上（近处历史两组都还没大量沉积）⇒ **短窗口径看不见它**，必须用长历史口径或外部语料才能暴露。

## 3.111 【硬规则】`meta.code_sha` 是「写 meta 时刻的 HEAD」，不是「起跑瞬间的 HEAD」（2026-10-23 D12-H）

**事故**：D12-H 起跑 22:11 时 HEAD = `4879b26`；跑完 23:18 才跑 `emit_run_meta`，它取的是**当时的 HEAD** = `335c659` ⇒ `meta.code_sha` 记的是 `335c659`，而本版 meta **没有 `code_sha_end` 字段**。若直接引用 `meta.code_sha` 当"起跑树身份"，就会把"跑批中途提交的证据文件"误当代码版本。

**本批为何仍有效**（必须这样证明，不能只凭 meta）：
- `git diff 4879b26 335c659 -- code/` **为空**；
- `code/life/agent.py` 的 blob 在两个 commit **同为 `14f5f42d…`**；
- `335c659` 只新增了 4 个 `v2/evidence/` 文件。

**规则（四条）**：
1. **引用 `meta.code_sha` 必须同时给出「start 时 HEAD」与「写 meta 时 HEAD」两个值**，并用 `git diff <两者> -- code/` 证明逐字节相同；只给一个值不算身份证明；
2. **跑批中途的提交只要不碰 `code/`（文档/证据）就合法**，但**必须在 `switch_proof` 里记下"跑批期间 HEAD 从 A 变为 B，`code/` 未变"**；
3. 更稳的做法：起跑脚本在**起跑瞬间**把 `git rev-parse HEAD` 写进 `switch_proof`，跑完再写一次，形成 `code_sha_start` / `code_sha_end` 两值；
4. 与 runbook 「证据必须来自被执行的那一层」并列：**代码身份也必须来自"被执行的那一刻"，而不是"事后写元数据的那一刻"**。

## 3.112 【硬规则】代价闸必须在 1/3 处先核，不能等收尾——"一行提示词"可能在形态层做两件事（2026-10-23 D12-H）

**事故**：D12-H 的 ON 组提示词只加了「开口先叫对方一声…」一行。预登记把 `L-3 ≥55%` 写成"代价闸"，**但没有安排在 1/3 处先核它**。收尾实测：
```
L-3 含括号块：T1 66.27% → T5 57.84% → D12-H 0.20%（1/510）
```
**旁白被整体清零**。机制解释：旁白在 T1/T5 里主要出现在**开头**（"（动作）台词"格式），**强制"以称呼开头"就把旁白挤出去** ⇒ **不是 bug，是这一行提示词的真实副作用**。

**两个后果**：
1. **代价闸严重不通过（差 54.80pp）** ⇒ 按反事实应落「**无效（靠砍旁白换重复）**」，连"不可判定"都轮不到；
2. **单变量在效果层破产**：ON/OFF 的差别不止"一行提示词"，还包括"**文体**与 T1/T5 根本不同" ⇒ **外部参照同向也救不了归因**（"重叠更低"可被"文体不同"解释）。

**规则（四条）**：
1. **凡在预登记里写了"代价闸/形态闸"的指标，必须在 1/3 处实测一次**，不达标立即停跑 —— 不要等到收尾才发现（本批为此多花了 6,073 次调用）；
2. **"只加一行提示词"不等于"只改一个语义"**：加之前先列出**它可能连带改变的形态**（本批：开头格式→旁白率、称呼率、句长）；
3. **形态变化本身就是第二重混淆**：当某形态指标（如 `L-3`）相对基线漂移 >5pp 时，**任何"文体层"的对比（重叠率、n-gram、具体性）都不能单独归因**；
4. **报数必须并列形态量**：`L-3`、称呼起头率、`len_p50` 至少三项与主指标同屏，否则读者无法判断"是不是换了种写法"。

## 3.113 【硬规则】口径相近的量必须**并列输出 + 名字带口径后缀**（2026-10-23/24 一晚 6 起同类事故）

**事故清单（全部在 24 小时内发生，全部是"名字相近、含义不同"）**：

| # | 两个量 | 差异 | 后果 |
|---|---|---|---|
| 1 | `F-2` vs **`F-2'`** | 旧键 `F-2_topic_drift` 为 `LEGACY_DEAD_RULER`（tag 恒定 ⇒ 结构性恒 0）vs 新键 `F-2_content_drift` | 按旧键判会得 **假 PASS（0%→0%）** |
| 2 | **shingle 层相同** vs **sha 层逐字相同** | 集合相同 ≠ 文本逐字相同 | 条数报成 33 与 54 两套 |
| 3 | `addr_head_loose` / `addr_head_strict` / `addr_head_pfx2` | 同一件事三种正则，值差 3–5pp | 引用不著名会互相矛盾 |
| 4 | **`addr_head_upper`（正则上界）** vs `addr_head_strict`（显示名精确） | T5 上 41.00% vs **36.47%**（差 4.53pp） | **把 PASS 翻成 FAIL**（D12-I 的 F2） |
| 5 | `S_ext` **本体** vs **留出集** | 对本体 `overlap_frac` 恒 ≈1.0（无信息） vs 留出集 0.2218 | 主判据对比无意义（预登记疏漏） |
| 6 | `non_all_equal_rate`（不全同） vs `argmin_unique_rate`（最小值唯一） | `[1,1,2]`：前者 True、后者 False | 报成 98.63% 与 94.12% 两套 |

**规则（五条，可机械执行）**：
1. **名字必须带口径后缀**：`_strict` / `_loose` / `_upper` / `_4g` / `_sha` / `_shingle_set` / `non_all_equal` / `argmin_unique`；
2. **相近的量并列输出，不替代**：工具一次给全，报告同时给全，**读者自己看哪个是判据**；
3. **基线必须同口径复算**：不得"本臂 strict vs 基线 upper"；**用同一脚本在基线日志上实算**（D12-I 的 4.53pp 就是这么来的）；
4. **参照语料必须声明"是否含无信息部分"**：如 `S_ext` 本体恒 1.0 ⇒ 必须用**留出集/外部语料**；
5. **凡"看起来同一个数"有两个版本，先查是不是两个量** —— 一晚 6 起事故，没有一次是"数值算错"，**全是"量选错"**。

## 3.114 【硬规则】同一仓库多执行线并发：**禁止 `git reset`、提交必须带路径、提交后必须自查 sha**

**事故实录（2026-10-24 04:57–05:05，本仓真实发生，非假设）**：
1. 我提交 `cd7adf9`（D2.2 诊断，6 个新文件）后，**另一条执行线**执行了 `git reset: moving to 2a52123`（reflog 可见），
   随后在该点重新提交 cycle14/15 系列 ⇒ **我的 commit 变成悬空、从 master 历史中消失**。`git ls-remote` 显示远程也从未有过它。
2. 恢复时撞 `fatal: Unable to create '.git/index.lock': File exists` —— 另一线正在提交。
3. `git status` 显示索引里**我的 6 个文件与另一线的 3 个文件（`reports/CYCLE-15-*.md`、`cycle15_verify.md`、`README.md`）混在一起**，
   裸 `git commit` 会把别人未完成的产物一起带走。

**规则（六条，全部可机械执行）**：
1. **主树永不 `git reset`**（含 `--hard`/`--mixed`）。要撤自己的改动用 `git revert` 或再提交一次；
   `reset` 在这个仓里等于**随机吞掉他不知道的别人的 commit**。
2. **提交一律带路径**：`git commit -m "..." -- <path1> <path2> ...`；**禁止裸 `git commit`**（会把共索引里别人的 staged 条目一起提交）。
3. 遇 `index.lock`：**先 `pgrep -a git`**。有进程 ⇒ 等；无进程且锁龄 >60s ⇒ 才可移除。**先删锁等于删别人正在写的索引。**
4. **提交后立即自查**：`git merge-base --is-ancestor <my_sha> HEAD && echo yes` —— **不要相信 commit 命令的 rc，更不要相信 push 的返回码**。
5. **汇报 sha 前先 `git log --oneline -8` 看它还在不在**；不在就 `git reflog` + `git cat-file -t <sha>` 找悬空对象重建。
6. 重建方法（本次实测有效）：reset 后文件会变成 **untracked**，`cherry-pick` 会因"文件已存在"失败；
   直接 `git add <自己的路径>` + `git commit -- <自己的路径>` 即可，**不要 `rm` 重建（会丢内容）**。

**推论**：本项目同时有多条线（D12/D2.x 实验线、cycle 报告线、verify 线）写同一 master，
**"我提交了" ≠ "它在 master 上"**。每次声称落库前，用规则 4/5 自查一次。

## 3.115 【硬规则】凡**改抽样/选择函数**的臂，必须加「等权对照档」——否则伪影会被当成机制

**实证（`v2/evidence/d22_recency_offline_verdict.md`，2026-10-24）**：
把 `_pick` 的 `options[h % len(options)]` 换成"累积权重轴取点"，**权重全部设为 1（等于不加权）**，
`repeat_pair_rate` 就从 **42.98% 变成 48.25%（+5.27pp）** —— 这 5.27pp **与任何机制无关，纯粹是映射函数变了**。
同一臂若加权真实效应是 **−1.76pp**，只看"新策略 vs 现状"会报 **+3.51pp 有效**，**符号都是反的**。

**规则（三档对照，缺一不可）**：
| 档 | 定义 | 用途 |
|---|---|---|
| **A 现状** | 原函数原映射 | **必须能 100% 复现历史**（`self_check` 不过 ⇒ 代理不可信，不许往下算） |
| **C 等权** | 新映射 + **机制权重全部置 1** | 隔离**纯映射伪影** |
| **B 机制** | 新映射 + 真权重 | 目标档 |
**判定只能用 `B − C`（净机制效应）**，不得用 `B − A`；`C − A` 单独报，命名为 `map_artifact_pp`。
若 `|map_artifact_pp| ≥ 3pp`，该臂的所有跨档结论都必须带上它。

**推论**：凡涉及 `_pick` / 采样 / 择优 / 抽签的臂（D12-E/F/G/I 皆属此类），
历史结论里 `B − A` 的口径都值得回头核一遍是否含映射伪影。

**配套（同源能力）**：`planner._participants` 的对端选择已可**离线精确复现**
（`seed = agent|day{round//12}-{SLOTS[(round%12)//3]}|{tid}|p0`，自检 114/114=100%），
⇒ 对端/模板层面的候选**一律先离线模拟再决定是否跑批**，不要拿 52 分钟去试一个能算出来的东西。

## 4. 启动清单（复制粘贴；一批一跑）
> 约定：`REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment`；批次名 `<B>`（如 `A`）；跑批产物落 `RUN=/root/t271/runs/<B>`。

**① 预检（必看：平台 anon < 7.0G 是第一原则）**
```bash
bash "$REPO/tools/t271/preflight.sh" | tee -a "$RUN/preflight.txt"   # free / df -h / df -i / MemAvailable
```

**② 建只读副本（零 git 操作；开关以【文件】落在副本里）**
```bash
SHA=$(git -C "$REPO" rev-parse HEAD)
bash "$REPO/tools/t271/make_batch_copy.sh" <B> "$SHA"     # → /tmp/t271-<B>/
# 消融批次：在此改 /tmp/t271-<B>/code/config/<file>.json（只改那一个开关，不提交、不碰 .git）
bash "$REPO/tools/t271/capture_provenance.sh" /tmp/t271-<B> "$RUN"   # 源sha + config 全文 sha256 + 开关 diff 存档
```

**③ 托管启动（脱离 cgroup）**
```bash
RUN=/root/t271/runs/<B>; mkdir -p "$RUN"
bash "$REPO/tools/t271/host_batch.sh" \
  --name <B> --out "$RUN/run.jsonl" --workdir /tmp/t271-<B>/code \
  --env-file "$REPO/code/.env.local" \
  --mem-high 6G --mem-max 8G --heartbeat 600 \
  --meta sha="$SHA" --meta copy=/tmp/t271-<B> --meta switch=<开关值> \
  --meta side_root="$RUN/side" --meta flush_every=12 \
  -- python3 -m orchestration run --life --seed 42 --agents 20 --weeks <W> \
       --out "$RUN/run.jsonl" --side-root "$RUN/side" --flush-every 12
```
> ⚠️ **凭据只走 `--env-file`（= `systemd-run -p EnvironmentFile=<主树>/code/.env.local`）**；
> **绝不用 `--setenv`**——实测 `--setenv` 会把密钥带进 `systemctl show`/`ps`/journal（永久留痕）；
> `EnvironmentFile` 方式下 `systemctl show -p Environment` 为空、**不泄**（只记录文件路径）。

**④ 跑完收尾（回填指纹/结束时刻）**
```bash
bash "$REPO/tools/t271/finalize_meta.sh" "$RUN"    # engine_version 指纹取自日志首行 WORLD_INIT
```

**⑤ 运行期观测**
```bash
watch -n 60 "bash $REPO/tools/t271/status.sh $RUN"   # 组合视图
tail -f "$RUN/heartbeat.tsv"                          # 时间 / size / round / RSS_MB
```
> **心跳必须落文件**（`heartbeat.tsv`），**绝不依赖会话内轮询**——平台重启会杀掉 Agent 会话，重启后回读文件即可判「死在哪一刻」。

**每批 run 元数据（`meta.json`，缺一不可）**：批名 / `sha` / `engine_version_fingerprint` / `switch` / `started_at` / `ended_at` / `heartbeat_file` / `copy`（副本路径）/ `side_root` / `flush_every` / `cmd`。

### 4.5 `systemd-run` 托管模板（**已实测通过**，2026-10-22T22:24）

> 结论：**本机 `systemd-run` 可用**（systemd 255；root 权限），transient unit 落在 **`/system.slice/<unit>.service`**，
> **不在 `jiuwenswarm.service` 的 cgroup 内** ⇒ 平台重启/memguard 重启不会连坐。

**生效命令模板（复制即用）**：
```bash
WT=<repo>/.worktrees/<branch>            # 代码必须来自 worktree，不碰主树
TS=$(date +%H%M%S)
systemd-run --unit=t271-<batch>-$TS --collect \
  --property=MemoryMax=2G \
  --working-directory=$WT/code \
  /bin/bash -c "cd $WT/code && unset HITT_LLM_PROVIDER HITT_D12_DETAIL; \
    python3 -m orchestration run --life --seed 42 --agents 4 --rounds 2 \
      --out /tmp/<batch>_run_$TS.jsonl --side-root /tmp/<batch>_side_$TS --flush-every 1 \
      > /tmp/<batch>_log_$TS.txt 2>&1"
```
- 真 LLM 批把 env 用 `--property=EnvironmentFile=<主树>/code/.env.local` 传入（**不要 `--setenv` 放密钥**）；
- `--collect` 会在进程退出后**自动清理 unit**（见下第 3 条），不必再 `reset-failed`。

**三件自查（冒烟实测输出，2026-10-22T22:24，unit `t271-smoke-222412`）**：

| # | 检查 | 实测 |
|---|---|---|
| 1 | `systemctl status t271-smoke-222412` | 起跑瞬间 `Active: active (running)`；退出后 `--collect` 自动清理，`LoadState=not-found`（**无需 reset-failed**） |
| 2 | `cat /proc/$MainPID/cgroup` | `0::/system.slice/t271-smoke-222412.service` ← **不含 `jiuwenswarm.service`** ⇒ 真正脱离 |
| 2b | `systemctl show <unit> --property=ControlGroup` | `/system.slice/t271-smoke-222412.service`（与 `/proc` 一致） |
| 3 | 日志/产物 | `/tmp/smoke_run_222412.jsonl` **285 行**；日志尾部 `chain_ok=True replay_parity=True conservation_ok=True` + `log written:` |

**两条普适判据（先记住，再读下面的注意）**：
> **判「跑完没跑完」，看产物与日志尾部；判「跑在哪个 cgroup」，看存活期的 `/proc/<pid>/cgroup`。两者不能互相替代。**

**为什么密钥必须走 `EnvironmentFile`、不能用 `--setenv`**：
`systemd-run --setenv=KEY=value` 会把该值写进单元属性，`systemctl show <unit> --property=Environment` **任何人都能读到**，
等于把凭据登记进了系统日志/审计链。用 `--property=EnvironmentFile=<file>` 时，systemd 只读文件内容、**不把值放进可查询属性**。
（同理：日志里不要 `echo` 密钥；`.env.local` 已在 `.gitignore`。）

**两条注意（本次实测发现）**：
1. **mock 2 回合跑得太快**（~2–3 秒）⇒ 用 `--collect` 时 unit 会在你 `systemctl status` 之前就消失；**要抓 cgroup 证据，须在命令前加 `sleep 8` 当"观察窗"**（本次即如此）或跑更长规模。
2. `MainPID` 只在单元存活期间可取；**拿不到 PID 就说明已完成并清理**，此时以"产物 + 日志尾部"为完成证据。

## 5. 平台重启后如何判读
1. `cat "$RUN/meta.json"` → 确认批次身份（sha/开关/指纹）。
2. `cat "$RUN/heartbeat.tsv"` → **末行时间 = 死亡（或结束）时刻**；末行 round/size 就是死点。
3. `cat "$RUN/cgroup.txt"` → 证明该批单元 cgroup（**不含** `jiuwenswarm.service`）。
4. 若 pid 仍活 → 该批**已扛过重启**。

## 6. 断点续跑口径
- **真 runner（`python -m orchestration run`）现状**：
  - `--flush-every N`（T262）每 N 回合把**已提交前缀原子落盘**（tmp+`os.replace`，**绝无半条记录**）→ 被 kill 后日志是**可 `replay`/`verify` 的完整前缀**。
  - **但不支持从第 k 回合续跑**（`run_e2e` 恒从创世开始）→ **真批「从死点续跑」【不可行】**（需改 `orchestration`，本次冻结不做）。
  - 因此真批断点口径 = **flush 前缀保命**：可从死点**回放状态、指标算到死亡回合**，最后不足一个 flush 周期的回合需重跑。
- **续跑模式已用 mock 证明可行**（`mock_batch.py`）：SIGKILL 后重跑同命令 → **截断未完成尾巴 → 从 flush 前缀继续**。
  - 实测：kill 于 round 6（flush 前缀）→ 重跑输出 `[resume] 完整前缀到 round 6 → 续跑` → 跑到 40，事件数自洽（161 行）。
- **[未验证]** 若日后要真批续跑，需给 runner 加 `--resume-from <prefix_log>`（**属 code 改动，本次不做**）。

## 7. memguard 触发阈值（排班依据）
| 项 | 值 |
|---|---|
| 定时器 | `jiuwenswarm-memguard.timer` 每 **2 分钟**（`OnUnitActiveSec=2min`，开机后 5min 首次，`AccuracySec=30s`） |
| 判定量 | cgroup **anon（匿名内存）**，**非** memory.current（含可回收 page cache） |
| SOFT | `7168 MB`（anon ≥7.0G 且**空闲 ≥120s** → 重启） |
| HARD | `9728 MB`（anon ≥9.5G **连续 2 次** → 不等空闲立即重启） |
| 其他 | `IDLE_SECONDS=120`、`HARD_STRIKES=2`；平台 `MemoryHigh=10G / MemoryMax=14G / MemorySwapMax=4G` |
| 今晚复盘 | 15:50 anon=10182→strikes 1/2；15:52 anon=10269→strikes 2/2 → RESTART |

**排班结论**：**平台 anon < 7.0G → 完全不触发**；7.0–9.5G 区间仅在**空闲≥120s** 才软重启（跑批有活动→只记日志）；≥9.5G 连续 4min 才硬重启。
→ **控并发/人机会话把 anon 压在 7G 以下，就根本不需要逃逸兜底**；逃逸是第二道保险（且**跑批在独立 unit，其内存不再计入平台 cgroup**——逃逸顺带降低平台 anon）。

## 8. 实测证据（本 runbook 结论的复算入口）
| 编号 | 内容 | 复现命令 | 观测 |
|---|---|---|---|
| E1 | 逃逸对照 | 见 §2 | setsid ❌ / systemd-run ✅ |
| E2 | 重启存活（反向对照+PASS） | `bash tools/t271/restart_harness.sh` | victim alive=no；cand alive=yes；心跳连续；RESULT PASS |
| E3 | 断点续跑 | `mock_batch.py` kill→重跑 | 从 round 6 续到 40 |
| E4 | env-file 不泄 | `host_batch.sh --env-file <dummy>` + `systemctl show -p Environment` | `Environment=` 空 |
| E5 | 副本+开关+托管+指纹 | §4 ①–④（mock provider） | cgroup=`.../t271-copyA.service`；指纹回填成功；`switch.diff` 19 行 |

原始产物：`/root/t271/runs/{smoke1,restart-test,resume-demo,env-test,wtmock,copyA}/`（心跳/pid/cgroup/meta/log 齐全，**仓库外**）。

## 9. 未验证 / 边界
- **【未验证】** 真 LLM 端点并发上限（B/C/D 并行探针上验证，不在此）。
- **【未验证】** N=20 真批的单批内存峰值（用 `--mem-max` 先给 8G 上限兜底；到点看 `heartbeat.tsv` 的 RSS）。
- **【不可行】** 真 runner 从死点续跑（见 §6）。
- **边界**：脚本默认路径写死 `REPO`/`T271_COPY_ROOT=/tmp`；改路径用环境变量 `T271_REPO`/`T271_COPY_ROOT` 覆盖。
- **红线遵守**：不改 `code/{engine,life,freeze,config}`；跑批在 `/tmp` 只读副本内进行，**不向主树写 pyc/缓存/中间产物**；密钥只走 `EnvironmentFile`，不落盘/不入日志/不入报告。
