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

> ⭐ **开关"消费者路径"登记（T354/T355，2026-10-13）——翻开关前必查"值从哪来"**：
> - `time.ongoing` 曾有**两条**路径：**`life` 业态（`KernelAdapter`）**读**运行时 config**（`integration.py:273-279`，缺省回退文件）⇒ **可 override**；**standalone `engine/perceive.py::perceive()`（`mini_kernel`/inline）**经 `_load_time_flags()`（`:28-34`）**直读 `config/time.json`** ⇒ 曾**不可 override（命令打印成功、实为静默无效）**。
> - ✅ **已统一**：`kernel` 已修 `_load_time_flags(config=None)` **优先读传入 cfg**（缺省回退文件）⇒ **两路径现在都尊重 override**。
> - ⚠️ **方向不对称（历史坑，仍登记）**：旧 inline 路径"override **关断**有效、**从 off 打开**无效"。⇒ **翻开关只认"端到端能翻"判据，禁止拿"打印了 override 行"当证据**；消融矩阵必须在**能翻的业态**上做，否则得到**假 2×2**。
> - `world_director.propagate`：`engine/world_params.py:15-17` 读 `config["world_director"]["propagate"]["enabled"]` ⇒ **cfg 驱动、可 override**。
> - **归因口径**：`override` 文件不动 ⇒ **`engine_version` 指纹不变**；但 **`config_digest` 变**（别把 `config_digest` 变当成"指纹变"）。

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

> 📣 **起跑预告红线（T350 采纳，2026-10-13）**：任何**在主树/副本起跑**的批/探针，**起跑时必须广播**
> （含：**起跑时刻、日志路径、预计时长、是否会改树**），并**起跑前 `pgrep -f "orchestration run"` 确认无重活**。
> 理由：**没有预告时，别人无从判断"我提交前是否有人在读主树"** —— T350 即"任务单只写『错开』、没要求广播"撞上 T338 提交的根因（主因在派单侧）。
>
> 🔑 **预告第二条（同样必写）：声明"这次读的是哪棵树"** ——
> **`tree=copy`** 填**冻结副本 sha**（`git archive <sha>`）/ **`tree=main`** 填**主树 HEAD**；
> 并**据此声明"期间别人提交/改世界层是否会影响它"**：
> - **`tree=copy`**：跑批 `cwd=/tmp/t271-<batch>/code`、`/proc/<pid>/maps` 中主树 `code` 映射数=0 ⇒ **主树后续提交不入副本** ⇒ "跑中改主树"**不影响**该批（T350 实测：起跑 12:40 用 `10428f24` 冻结副本，kernel 12:45 的 `d598f47` **零影响**，靠回头实核才发现 → 否则会为一个不存在的污染白重启）；
> - **`tree=main`**（如 A 批）：跑的是**活工作树** ⇒ 跑中改世界层**会使结果不可归因**。
> ⚠️ **provenance 记哪棵树就要写哪个 sha**：`tree=copy` 记**冻结副本 sha**（≠ 主树 HEAD），**两者不同，报告里别混**。

## 3. 一键收 + 一页早报
```bash
python3 "$REPO/tools/t271/nightly.py" collect
```
- 分类规则（**完成判据以【日志实测回合】为准，心跳 round 只作「死在哪一刻」**）：`RUN_END` 或 **日志末条 round ≥ target-1 且 rc∈{0,None}** → **SUCCESS**；进程存活 → **RUNNING**；`rc∈{137,143}` 或负 → **INTERRUPTED（被信号终止=外因中断，非批内错误）**；回合已到但 `rc≠0`（引擎自检失败）→ **FAILED**；其他非 0 → **FAILED**；未达目标 → **INTERRUPTED**。
  > ⚠️ **不要用 `heartbeat.tsv` 末行 round 判完成**：10min 心跳间隔内批可能已跑完（末行是 `EXIT`）→ 读到滞后 round 会误判未达标（T274 实测踩过：四批实际 `round=83/rc=0`，却被心跳的 71 误判为 `INTERRUPTED`）。
  > 反向验证脚本（**改判据必跑**）：`bash tools/t271/verify_collect.sh` → A) 心跳滞后但实际成功→**SUCCESS**；B) 真中断(kill, rc=137)→**INTERRUPTED**；C) `meta.ended_at`/`engine_version_fingerprint` 由 runner 退出时回填。
  > 收尾：早报**只列含 `meta.json` 的真 run 目录**；mock 演示用**独立 run_root**，不与真实夜跑混淆。
- 早报（`<run_root>/morning-report-<date>.md`）：**总览 + 逐批**（sha / `engine_version` 指纹 / 开关 / 回合进度 / 事件数 / 峰值 RSS / 起止 / 产物路径 / 续跑模式），并附**盘前/盘后 `df -h` `df -i`**。机器可读：`summary.json`。

> 📣 **跑批结束必须主动报（T355 立，2026-10-13）**：**`host.log` 出现 `[runner] batch exited rc=?` 就是"跑完了"这个事件** ——
> **owner 必须立即 `send_message` 报 leader 并广播占用释放**，**不得等下一次 collect / 别人发现**。
> 依据：**T355 17:49 就已 `batch exited rc=0`，直到 19:40 才被发现 ⇒ 全员白等 1h50m**。"跑完了"是**必须主动发出的事件**，不是自然会发生的事。
> （`t271_runner.sh` 退出时已回填 `meta.ended_at` 并打印 `batch exited rc=`；**盯这一行**，别只盯心跳。）
> ⚙️ **已机制化（T374，2026-10-13）**：`t271_runner.sh` 在**批体结束后**（含 `rc≠0`、`TERM/INT`）自动写**固定 `END` 标记** `<run_dir>/END`（JSON：`rc`/起止/`rounds_last`/`events`/`final_state_hash`/`tree`/`sha`），并**尽力通知**：固定告警路径 **`/root/t271/alert/last_end.json`**（最新）+ **`/root/t271/alert/ends.log`**（逐条 append）+ journal（前缀 `[END-MARKER]`）。**周期自检一眼看 `alert/last_end.json`**。
> - **不造第二真源**：`END` 是**汇总**（读 `meta.json`/`heartbeat.tsv`/`run.jsonl` 派生），**不改**三者；`meta.ended_at` 仍由 `finalize_meta.sh` 回填。
> - ⚠️ **被 `SIGKILL`/断电**：trap 不触发 ⇒ `END` **不写出**（"END 缺失"本身=异常信号；此时以 `heartbeat.tsv` 末行为准）。**只能留痕到 `SIGTERM/INT`**。
> - ⏱ 写标记**只在结束后**，不进热路径、不影响批体计时。

> 🔗 **核验单的 `depends_on` 纪律（T374/T376 死锁教训，2026-10-13）**：**核验单的 `depends_on` 只应指向"前置工作"，不得指向"被核对象的完成状态"** —— 否则被核单（作者不自标 completed）与核验单互卡死锁。核验"结论随时可推翻"，不必等被核单先 `completed`。

## 4. 失败可续（⚠️ 诚实口径）
```bash
python3 "$REPO/tools/t271/nightly.py" resume --batches <表> --env-file "$REPO/code/.env.local"
```
- **`native`（默认；T276/T288 落地后）**：真 runner 用 **`--resume-from <已 flush 前缀> --target-round <目标>`**，从 flush 前缀**接着跑到目标回合**，日志被重写为**完整日志（前缀+续跑段）**，`collect` 末条 round 即 target ✓。**必须复用同一 `side_root`**（共享源正文/缓存）。
  - **前提（硬）**：该 **sha + 该配置 + 该 cut 点** 上「**世界语义一致**」已被验证。**换 sha/配置/cut 后须重新核**。
  - **门的新定义（T299，2026-10-12 裁定方案 (b)）**：**回答「世界语义是否一致」**，不比本地 freeze 缓存命中。比较用 **世界语义投影 sha256**（`tools/t271/semantic_log_sha.py`）：**只排除** `LLM_CALL.payload` 的 `{cached,tokens_in,tokens_out,cost_units}`；**其余全比**（含 `cache_key/prompt_hash/meta_digest/engine_version/provider/purpose/model/priority/tier/thinking/degraded` 与 **`TURN_SEAL.state_hash`**）。因 `record.hash` 覆盖含 payload 的整条、`TURN_SEAL.payload.last_hash = ledger.last_hash()`（`engine/ledger.py:24`/`kernel.py:239`）⇒ **对规范化事件【重算哈希链】**（**不排除 `last_hash`、不靠断言**）。整份原 sha 仅打印作参考。
  - **自证用法（分钟级）**：`T271_VR_GATE=1 T271_VR_REVERSE=1 T271_VR_CUT=89 bash tools/t271/verify_native_resume.sh`
    - `T271_VR_CUT`（默认 `ROUNDS/2`）逐字节比对的**截断点**；`T271_VR_KILLROUND`（默认 `ROUNDS/2`）**跑到该 round 再 kill**（**不用墙钟**——否则 cut 随负载漂移，制造假"间歇"，T299 实测踩过）；`T271_VR_GATE=1` 语义不一致即失败；`T271_VR_REVERSE=1` 加反向验证（最小语义扰动仍须报红）。
  - **白名单维护规则（T307-i）**：`EXCLUDE` 是**白名单**，两向都致命——新增**纯计量**字段未入表 ⇒ **假红**；**语义/配置**字段误入 ⇒ **假绿**。⇒ **新增纯计量字段必须同步入 `EXCLUDE` 且重跑 `--selftest`（A/B 双向 + `链级联覆盖=True`）；语义/配置字段不得入表；拿不准一律【保留】**。**判"纯计量"**：只影响本地 freeze 缓存命中/计费、**不影响 world 语义**（不入 `state_hash`、不改事件流/前向态）。
  - **selftest 硬化（T307-ii/iii）**：`--selftest` 用**合成样本【保证压到哈希链级联】**（`LLM_CALL` 紧跟 `TURN_SEAL`）⇒ `链级联覆盖=True` **成为可断言项**（False=链覆盖失败=**红**）；语义扰动**钉死为 `PLACE_MOVE.day +1`**（跨版本可重复，字段缺失**报错**不静默换靶）；真日志的级联覆盖仅作 **info**（False="样本未覆盖链"，非红）。**负向用例（T308）**：`--selftest-missing-pin` **构造器与搜索常量已解耦**（构造一份**不含** `PLACE_MOVE.day` 的样本）⇒ CLI 可直接触发"缺字段⇒`rc=2`"（把安全网从"存在"升级为"**可断言**"）；默认 `--selftest` 行为不变。
  - **实测（本机，双面真数据）**：`cut=89`（无真分歧）→ **PASS**（语义投影 byte-equal、`state_hash` 不等数=0、REVERSE ok）；`cut=75`（真分歧）→ **FAIL=真阳性**（`state_hash` 不等数=74，首个不等 round=76）。
  - **⚠️ 已知真缺陷（②类，已交 life）**：同 sha 下 **resume 对 cut 敏感** —— `@75` 续跑 round 76 起与一次性跑分叉，`@89` 一致。**非哈希序**（对 `PYTHONHASHSEED ∈{0,1,2,3,不设}` 完全不敏感）、非竞态、非 cache。最小复现：`bash tools/t271/repro_resume_cut.sh 75`（对照 `89`）。详见 `v2/evidence/T299-semantic-equality-gate.json`。
  - **备选（记此，未采用）**：(a) 预热对等——证据不足（预热后仍混合命中，单用不充分）；(c) 维持整份 sha 现状——报的是本地缓存命中状态、非世界语义。
  - **台账重述（T299 验收 → 独立成 T306）**：本门此前所有"逐字节一致"结论按新口径重述为「世界语义（排除 4 计量字段、重算哈希链）一致」，**逐条**列【原口径 / 新口径结论 / 是否独立核 / 在哪个 sha·指纹·cut 下成立 / 是否已失效】+ 命令读数。**完整重述见 `v2/evidence/T306-byte-equality-restatement.md`**（覆盖 **T276 / T288 / T236 / T292 / T287期①**）。要点：T276/T288 的世界语义一致**仅 cut=89 成立**（cut=75 真分歧，已交 life）；T236 属 provenance（不受影响）；T292 属计数旁证；T287期① 为异配置对照（口径不同、同向互证）。
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

## 9. 看板/回放服务（本地开发，一条命令恢复）
- 机器重启或进程挂掉后：`bash code/frontend/tools/serve_ctl.sh start`（systemd **transient** + `Restart=always` 保活；无 systemd 用 `start-nohup`）。
- 自检：`bash code/frontend/tools/serve_ctl.sh status` → **running / 端口 200 / `HITT_LIVE_ROOTS`**。
- 端口 **8848**；实时跟随白名单根 **`/root/t271/runs`**；**本地开发服务，不对外暴露**。（T348）
