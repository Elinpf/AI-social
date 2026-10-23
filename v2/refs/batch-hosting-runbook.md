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
