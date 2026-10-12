# 夜跑流水线 runbook（T274）—— 一键起 / 一键收 / 失败可续 / 一页早报

> 作者：release-engineer ｜ 2026-10-12 ｜ 任务：T274-nightly-run-pipeline
> 与 **T271** 同源（T271="能活"，T274="活成日常"）。脚本：`tools/t271/`（含 `nightly.py`）。
> 状态：**已在 mock 上跑通「起 → 收 → 探中断 → 续/重叠重跑 → 清理」**；未实测处标 **【未验证】**。

---

## 0. 一句话
`nightly.py` 把 T271 的托管封装成**每晚例行**：读一张批次表 → 一键起全部批（各在自己的 transient unit、`/tmp` 只读副本、文件开关、心跳落盘）→ 一键收出**一页早报** → 中断批可续（或重叠重跑）→ 清理长期账。

## 1. 批次表（TSV，制表符分隔）
列：`name rounds agents seed switch resume_mode tree flush out side cmd`
| 列 | 取值 | 说明 |
|---|---|---|
| `switch` | `file.json:dot.path=value`，多个用 `;`；`-`=无 | 消融开关**以文件落副本**（非 dict override） |
| `resume_mode` | `native`（默认）｜`overlap`（回退） | `native`=真 runner `--resume-from/--target-round` 从 flush 前缀续跑；`overlap`=重跑（见 §4） |
| `tree` | `copy`（默认）｜`main` | `main`=在主树跑（A 批口径，无副本/无开关）；`copy`=`/tmp` 只读副本 |
| `out` | 绝对路径；留空=默认 | 覆盖批次日志落点（如 A 落 `v2/evidence/run_t236_canon_n20_llm.jsonl`）；**run 元数据仍落 `<run_root>/<name>/`** |
| `side` | 绝对路径；留空=默认 | 覆盖 `side_root`（默认 `<run_dir>/side`）。**多批填同一个 = 共享 `freeze_cache`/源正文，做干净消融（B−A 差值不被缓存冷热污染）**；`native` 续跑自动沿用 `meta.side_root` |
| `cmd` | 留空=默认 | 默认绝对 venv python：`/opt/openjiuwen/workswarm-venv/bin/python -m orchestration run … {resume_args}`（**不赌 `python3` 解析**） |

示例见 `tools/t271/batches.example.tsv`（含今晚 A/B/C/D）。

## 2. 一键起（复制粘贴）
```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
SHA=$(git -C "$REPO" rev-parse HEAD)          # 记录源 sha；副本用同一 sha
python3 "$REPO/tools/t271/nightly.py" start \
  --batches "$REPO/tools/t271/batches.example.tsv" \
  --sha "$SHA" \
  --env-file "$REPO/code/.env.local" \         # ⚠️ 只走 EnvironmentFile；绝不 --setenv
  --heartbeat 600 \                            # 每 10min 一行心跳
  --mem-high 6G --mem-max 8G
```
每批产出 `<run_root>/<name>/`：`meta.json`（sha/指纹/开关/起止/心跳/副本路径/side 根/续跑模式）、`heartbeat.tsv`、`cgroup.txt`、`provenance.txt`、`switch.diff`、`run.jsonl`、`batch.pid`、`host.log`。
- **`start` 先落盘前 `df -h`/`df -i`**（写进 `_session.json`），收尾时与盘后对比。

> ⚠️ **脏树红线（重要）**：`tree=copy` 的批次用 **`git archive <sha>`＝已提交树**，
> **不含工作树未提交改动**；`tree=main`（A 批）跑的是**活的工作树**、**会含**未提交改动。
> ⇒ **若冻结区 `code/{engine,life,freeze,config,obs,contracts,orchestration}` 在起跑时还脏，A 与 B/C/D 会跑不同代码、消融不可比。**
> `start` 会**打印脏文件告警**，并把 `source_git_dirty_count` + 冻结区脏文件清单写进每批 `provenance.txt`。
> **起跑前必须确保冻结区 clean**（不 clean 就 abort 报 leader，不拿脏树当基线）。

## 3. 一键收 + 一页早报
```bash
python3 "$REPO/tools/t271/nightly.py" collect
```
- 分类规则（**完成判据以【日志实测回合】为准，心跳 round 只作「死在哪一刻」**）：`RUN_END` 或 **日志末条 round ≥ target-1 且 rc∈{0,None}** → **SUCCESS**；进程存活 → **RUNNING**；`rc∈{137,143}` 或负 → **INTERRUPTED（被信号终止=外因中断，非批内错误）**；回合已到但 `rc≠0`（引擎自检失败）→ **FAILED**；其他非 0 → **FAILED**；未达目标 → **INTERRUPTED**。
  > ⚠️ **不要用 `heartbeat.tsv` 末行 round 判完成**：10min 心跳间隔内批可能已跑完（末行是 `EXIT`）→ 读到滞后 round 会误判未达标（T274 实测踩过：四批实际 `round=83/rc=0`，却被心跳的 71 误判为 `INTERRUPTED`）。
  > 反向验证脚本（**改判据必跑**）：`bash tools/t271/verify_collect.sh` → A) 心跳滞后但实际成功→**SUCCESS**；B) 真中断(kill, rc=137)→**INTERRUPTED**；C) `meta.ended_at`/`engine_version_fingerprint` 由 runner 退出时回填。
  > 收尾：早报**只列含 `meta.json` 的真 run 目录**；mock 演示用**独立 run_root**，不与真实夜跑混淆。
- 早报（`<run_root>/morning-report-<date>.md`）：**总览 + 逐批**（sha / `engine_version` 指纹 / 开关 / 回合进度 / 事件数 / 峰值 RSS / 起止 / 产物路径 / 续跑模式），并附**盘前/盘后 `df -h` `df -i`**。机器可读：`summary.json`。

## 4. 失败可续（⚠️ 诚实口径）
```bash
python3 "$REPO/tools/t271/nightly.py" resume --batches <表> --env-file "$REPO/code/.env.local"
```
- **`native`（默认；T276/T288 落地后）**：真 runner 用 **`--resume-from <已 flush 前缀> --target-round <目标>`**，从 flush 前缀**接着跑到目标回合**，日志被重写为**完整日志（前缀+续跑段）**，`collect` 末条 round 即 target ✓。**必须复用同一 `side_root`**（共享源正文/缓存）。
  - **前提（硬）**：该 **sha + 该配置** 上「**逐字节一致**」已被验证。**换 sha 或换配置（seed/N/rounds/开关）后须重新核**。
  - **实测（本机）**：参数正确、状态判对（`bash tools/t271/verify_native_resume.sh` 门禁 PASS）。**但该脚本的逐字节【探针】在 `seed=9/n=2/150r` 上不一致**（续跑与一次性跑在 **round 93** 的 `MEMORY_FORGET` 分叉）→ 说明「逐字节一致」**并非所有配置都成立**；native 用于新配置前**必须自证**。详见 `v2/evidence/T292-native-resume-verify.json`。
- **`overlap`（显式回退，保留）**：重跑到目标回合，输出 `rerun.jsonl` → `meta.resume_mode=overlap_rerun`（此处 `rerun` 指"重跑产物文件名"，非 `replay` 重放）。**不假装能续**；`native` 前提不满足时用它。

## 5. 长期账：清理 / 保留 / inode 监控
```bash
python3 "$REPO/tools/t271/nightly.py" cleanup [--dry-run]   # 删 /tmp 副本 + side 打包
python3 "$REPO/tools/t271/nightly.py" disk                   # 随时看 df -h / df -i
```
**策略**：
- **`/tmp/t271-<批>` 只读副本：收尾即删**（可由 sha 再生）。实测**每副本 ≈ 175.6 MB**；4 批/晚 ≈ **700 MB/晚**，不清会撑爆 `/tmp`。
- **小元数据永久保留**：`meta.json`/`heartbeat.tsv`/`provenance.txt`/`switch.diff`/`summary.json`/早报。
- **side 散文件：打包成 `side.tar.gz` + sha256 后删目录**（省 inode；T229 口径：散文件是 inode 杀手）。某批加空文件 `run_dir/keep_side` = 该批 side 不打包（**证据级**）。
- **大日志 `run.jsonl`**：证据级永久；探测级 TTL（**建议 7 天**【未验证】）后打 tar+sha 或删。
- **监控**：`collect` 每晚报盘前/盘后 `df -h`/`df -i`；`preflight.sh` 对 MemAvailable 报警。**inode 曾近 89% 水位，务必盯 `df -i`**。

## 6. 排班（今晚首夜）
- **19:00 冻结** `code/{engine,life,freeze,config,obs,contracts,orchestration}`；
- **A 19:00 起**（主树、`rounds=84`、心跳 600s、`flush_every=12`）→ ETA 22:00±；
- **B/C/D**：先 **1 路并行探针**（~15min，验端点并发/互不拖垮）→ 通过则 **2 路**；不通过则串行；
- **第一原则**：**平台 anon < 7.0G**（memguard 阈值见 T271 runbook §7）；逃逸顺带降低平台 anon。

## 7. 实测证据（mock，2026-10-12 17:09–17:10）
`bash tools/t271/demo_nightly.sh` 全链路：
1. **一键起 2 批** m1/m2 → 各自独立 unit（cgroup `.../t271-m1.service`），主树不在其中；
2. **中途 SIGKILL m2** → `collect` 报 **INTERRUPTED**（判据：被信号终止 rc=137）；
3. **resume（native）** → `[resume] 完整前缀到 round 10 → 续跑`；
4. **终收** → **m1/m2 均 SUCCESS**（round 39/40、events=121 自洽）；早报含每批元数据 + 盘前/盘后 df；
5. **cleanup** → 删副本回收 ≈351–527 MB，`df -i` 前后可查。
（overlap 路径另实测：o1 中断 → `[resume] o1: overlap 重叠重跑…` → 生成 `rerun.jsonl`、`meta.resume_mode=overlap_rerun`。）

## 8. 未验证 / 边界
- **【未验证】** 真 runner 的 `native` 续跑（等 T276；改 `resume_mode` 前先过「逐字节一致」对照）。
- **【未验证】** 真 LLM 端点并发上限（B/C/D 探针上验）；N=20 单批峰值内存（`--mem-max 8G` 兜底，看 `heartbeat.tsv` RSS）。
- **【未验证】** 探测级日志 TTL=7 天的标定。
- **边界**：`nightly.py` 默认 `RUN_ROOT=/root/t271/runs/nightly`、`COPY_ROOT=/tmp`、`REPO=<social-experiment>`；用 env `T271_RUN_ROOT`/`T271_COPY_ROOT`/`T271_REPO` 覆盖。
- **红线**：不改 `code/{engine,life,freeze,config}`；跑批在 `/tmp` 副本；密钥只走 `EnvironmentFile`。
