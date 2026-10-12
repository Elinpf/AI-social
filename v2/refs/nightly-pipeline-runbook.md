# 夜跑流水线 runbook（T274）—— 一键起 / 一键收 / 失败可续 / 一页早报

> 作者：release-engineer ｜ 2026-10-12 ｜ 任务：T274-nightly-run-pipeline
> 与 **T271** 同源（T271="能活"，T274="活成日常"）。脚本：`tools/t271/`（含 `nightly.py`）。
> 状态：**已在 mock 上跑通「起 → 收 → 探中断 → 续/重叠重跑 → 清理」**；未实测处标 **【未验证】**。

---

## 0. 一句话
`nightly.py` 把 T271 的托管封装成**每晚例行**：读一张批次表 → 一键起全部批（各在自己的 transient unit、`/tmp` 只读副本、文件开关、心跳落盘）→ 一键收出**一页早报** → 中断批可续（或重叠重跑）→ 清理长期账。

## 1. 批次表（TSV，制表符分隔）
列：`name rounds agents seed switch switch_mode resume_mode tree flush out side cmd`
| 列 | 取值 | 说明 |
|---|---|---|
| `switch` | `file.json:dot.path=value`，多个用 `;`；`-`=无 | 消融开关（语义见下一行 `switch_mode`） |
| `switch_mode` | `file`（默认）｜`override` | `file`=改副本 `config/*.json`（**进 `engine_version` 指纹**）；`override`=**运行时 cfg 覆盖**（`tools/t271/run_override.py`，**文件不动→保指纹→保 `cache_key`→可命中共享 `freeze_cache`**）。⚠️ **`override` 只对引擎级键**（`world_director`/`policy`/`economy`/`time_config`/`genesis`）有效；**`life_v2`(sleep/forgetting/persona_drift) 由 life 层直接读盘 → 只能 `file`（会改指纹）** |
| `resume_mode` | `native`（默认）｜`overlap`（回退） | `native`=真 runner `--resume-from/--target-round` 从 flush 前缀续跑；`overlap`=重跑（见 §4） |
| `tree` | `copy`（默认）｜`main` | `main`=在主树跑（A 批口径）；`copy`=`/tmp` 只读副本 |
| `out` | 绝对路径；留空=默认 | 覆盖批次日志落点（如 A 落 `v2/evidence/run_t236_canon_n20_llm.jsonl`）；**run 元数据仍落 `<run_root>/<name>/`** |
| `side` | 绝对路径；留空=默认 | 覆盖 `side_root`（默认 `<run_dir>/side`）。**多批填同一个 = 共享 `freeze_cache`/源正文**；`native` 续跑自动沿用 `meta.side_root` |
| `cmd` | 留空=默认 | `file` 模式默认 `…/python -m orchestration run … {resume_args} {switch_args}`；`override` 模式默认 `…/python {bin}/run_override.py … {resume_args} {switch_args}`（**不赌 `python3` 解析**） |

> **"干净消融"编排 = 多批同 `side`（一方预热）+ `switch_mode=override`（开关不进行为指纹、只进 `meta`）** ⇒ B−A 差值不被缓存冷热污染。
> 实测（本机）：`base`/`override` 指纹**一致**（`sha256:23658bf8…`）、`file` 指纹**不同**（`sha256:7aa8fd3a…`）。
> ⚠️ **`life_v2` 类开关无法 override**（life 层直接读盘）→ 含 C 的"干净消融"需 life 层 hook（**当前不具备**），否则 C 只能 `file`（改指纹、不共享缓存）。

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
  - **前提（硬）**：该 **sha + 该配置 + 该 cut 点** 上「**世界语义一致**」已被验证。**换 sha/配置/cut 后须重新核**。
  - **门的新定义（T299，2026-10-12 裁定方案 (b)）**：**回答「世界语义是否一致」**，不比本地 freeze 缓存命中。比较用 **世界语义投影 sha256**（`tools/t271/semantic_log_sha.py`）：**只排除** `LLM_CALL.payload` 的 `{cached,tokens_in,tokens_out,cost_units}`；**其余全比**（含 `cache_key/prompt_hash/meta_digest/engine_version/provider/purpose/model/priority/tier/thinking/degraded` 与 **`TURN_SEAL.state_hash`**）。因 `record.hash` 覆盖含 payload 的整条、`TURN_SEAL.payload.last_hash = ledger.last_hash()`（`engine/ledger.py:24`/`kernel.py:239`）⇒ **对规范化事件【重算哈希链】**（**不排除 `last_hash`、不靠断言**）。整份原 sha 仅打印作参考。
  - **自证用法（分钟级）**：`T271_VR_GATE=1 T271_VR_REVERSE=1 T271_VR_CUT=89 bash tools/t271/verify_native_resume.sh`
    - `T271_VR_CUT`（默认 `ROUNDS/2`）逐字节比对的**截断点**；`T271_VR_KILLROUND`（默认 `ROUNDS/2`）**跑到该 round 再 kill**（**不用墙钟**——否则 cut 随负载漂移，制造假"间歇"，T299 实测踩过）；`T271_VR_GATE=1` 语义不一致即失败；`T271_VR_REVERSE=1` 加反向验证（最小语义扰动仍须报红）。
  - **实测（本机，双面真数据）**：`cut=89`（无真分歧）→ **PASS**（语义投影 byte-equal、`state_hash` 不等数=0、REVERSE ok）；`cut=75`（真分歧）→ **FAIL=真阳性**（`state_hash` 不等数=74，首个不等 round=76）。
  - **⚠️ 已知真缺陷（②类，已交 life）**：同 sha 下 **resume 对 cut 敏感** —— `@75` 续跑 round 76 起与一次性跑分叉，`@89` 一致。**非哈希序**（对 `PYTHONHASHSEED ∈{0,1,2,3,不设}` 完全不敏感）、非竞态、非 cache。最小复现：`bash tools/t271/repro_resume_cut.sh 75`（对照 `89`）。详见 `v2/evidence/T299-semantic-equality-gate.json`。
  - **备选（记此，未采用）**：(a) 预热对等——证据不足（预热后仍混合命中，单用不充分）；(c) 维持整份 sha 现状——报的是本地缓存命中状态、非世界语义。
  - **台账重述（T299 验收）**：本门此前所有"逐字节一致"结论（**T276 / T288 / T292**）**均按新口径重述为「世界语义（排除上述 4 计量字段、重算哈希链）一致」**；T288 的"逐字节"在其原测试配置成立，但**非普适**（见上"已知真缺陷"）。
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
