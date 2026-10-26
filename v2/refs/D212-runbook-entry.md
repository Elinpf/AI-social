# D2.12 runbook 条目 · canonical 真 LLM 两臂（C / B′）起跑

> 立此存照：2026-10-27。作者：kernel-engineer（`T-D212-RUN-PREFLIGHT`，mock 干跑产出）。
> 预登记：`v2/refs/D212-prereg-inround-visibility.md`（版本 **`c4a3212`** + 文字收口 **`a972b9f`**）。
> 臂代码：分支 **`feat/d212-inround` @ `1a6a3e1`**（基于 `master` `fbf1ff3`；**不含预登记文件**，引用须带 `c4a3212`）。
> 前置：runbook §3.116/§3.117/§3.118/§3.120；`tools/d2/run_batch.sh`（单一真源：跑世界 + 落 `meta.json` + 真跑门禁）。

---

## 0. 边界（先读）

- 本条目**只描述流程**；**是否开跑由用户放行**（P1：canonical 基线将被事件链变更打断）。
- **不与 D2.10 / D2.11 / D2.5a / A 对端 同批**（同批即双变量；P2 = 不同批）。
- 全程在 **worktree `.worktrees/d212-inround`** 内执行，**不动 master、不改主工作树**。

## 1. 四臂串行规格（写死）

| 顺序 | 臂 | 树 / worktree | commit | 开关 | seed | 规模 | 预计 calls |
|---|---|---|---|---|---|---|---|
| 1 | **C**（基线） | `.worktrees/d212-inround` | `1a6a3e1` | **无**（env 未设 / config 缺键 ⇒ 默认 OFF） | 42 | n16 r60 | ~2.8k |
| 2 | **B′**（轮内两阶段） | 同上 | `1a6a3e1` | `HITT_D212_INROUND=1` | 42 | n16 r60 | ~2.8k |
| 3 | **C** | 同上 | `1a6a3e1` | 无 | 43 | n16 r60 | ~2.8k |
| 4 | **B′** | 同上 | `1a6a3e1` | `HITT_D212_INROUND=1` | 43 | n16 r60 | ~2.8k |

- **单一变量**：同 sha（`1a6a3e1`）、只变一个开关（env `HITT_D212_INROUND`）；**genesis `config_digest` 不变**（env 通道不写 config）。
- **新基线同批重跑**：事件链变更 ⇒ T0/T5/D12 全系列**不可当 C**（`run_batch.sh` 直接现跑 C）。

## 2. 起跑命令（worktree 内逐臂）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d212-inround

# —— 一次性准备：worktree 是全新树，缺 code/.env.local（run_batch.sh 需要） ——
cp ../../code/.env.local code/.env.local        # 或不落盘、改走 host_batch --env-file（见 §5）

# 臂 1：C seed42
bash tools/d2/run_batch.sh --out-dir v2/evidence/run_d212_C_s42 \
     --seed 42 --agents 16 --rounds 60            # 注意：真跑【不加 --mock】

# 臂 2：B′ seed42
HITT_D212_INROUND=1 bash tools/d2/run_batch.sh --out-dir v2/evidence/run_d212_B_s42 \
     --seed 42 --agents 16 --rounds 60

# 臂 3：C seed43
bash tools/d2/run_batch.sh --out-dir v2/evidence/run_d212_C_s43 \
     --seed 43 --agents 16 --rounds 60

# 臂 4：B′ seed43
HITT_D212_INROUND=1 bash tools/d2/run_batch.sh --out-dir v2/evidence/run_d212_B_s43 \
     --seed 43 --agents 16 --rounds 60
```

- `run_batch.sh` 退出码：`0`=OK；`3`=`wc -l != meta.events`；`4`=非真跑；`5`=spec 不一致；`6`=llm-cost 门禁失败；`7`=meta 未生成；`9`=preflight 失败。
- **串行**：**必须**一条跑完再下一条（preflight 会因并发 `exit 9` 拦住）。

## 3. 收批第一件事（判别量 / 防跑错树）

对每臂产物目录：

```bash
# (a) 门禁 + 锚点
wc -l <RUN>/run.jsonl ; cat <RUN>/meta.json     # meta.code_sha 应 == 1a6a3e1…；meta.provider 应含 openai_compat
# (b) 判别量（从 run.jsonl 复算）
python3 - <<'PY'
import json,sys,collections
p=sys.argv[1] if len(sys.argv)>1 else None
# 见 v2/evidence/d212_preflight_dryrun.md 附录的 gap 复算；此处略
PY
```

| 臂 | 必核 | 判词 |
|---|---|---|
| **C** | `gap=0 == 0`（且无任何 phase-B 痕迹） | 否则 **停，判「跑错树」**（§3.120） |
| **B′** | `gap=0 > 0` | 否则 **停，判「可见性未生效（接线）」** |

> ⚠ **已知读数缺口**：`run_batch.sh` 产物（`run.jsonl`/`meta.json`）**不含 `phase_B_decision_count`**（该量只在 in-process 探针 `code/scripts/d212_mock_probe.py` 里可读）。**建议真臂主判据以 `gap=0`（可从 run.jsonl 复算）为准**，并考虑加一个 additive 的 `D212_INROUND` 逐回合聚合事件（见 §7 障碍 O-1）。

## 4. 真跑门禁（provider 验真）

`run_batch.sh` 真跑路径**内置**该门禁（rc=6 即失败）；手动复核：

```bash
cd code && python3 -m obs llm-cost --log "<RUN>/run.jsonl" --require-provider openai_compat
# 预期：rc=0；输出 provider_guard.ok=true，by_provider 含 openai_compat（非 mock）
```

## 5. 内存 / 并发安全

```bash
pgrep -fa "orchestration run|run_batch|nightly.py"   # 期望空（注意排除本命令自匹配）
free -h                                              # 当日实测：total 31Gi / available 15Gi / swap 已用 3.8Gi
```

- 长跑批**托管**（防平台重启连坐，`tools/t271/host_batch.sh`）：
  ```bash
  bash tools/t271/host_batch.sh --name d212_C_s42 --out RUN_DIR/run.jsonl \
       --workdir <worktree>/code --env-file <主树>/code/.env.local --heartbeat 600 \
       --meta sha=1a6a3e1 --meta switch=OFF --meta side_root=<path> \
       -- bash tools/d2/run_batch.sh --out-dir RUN_DIR --seed 42 --agents 16 --rounds 60
  ```
  其 `systemd-run` 默认 **`-p MemoryHigh=6G -p MemoryMax=8G`**（`--collect`，`Type=simple`，`KillMode=control-group`）。
- **B′ 臂**：`--meta switch=HITT_D212_INROUND=1`，且**必须**把该 env 传进托管单元（env 通道，勿写入 unit 之外）。

## 6. 时与量级估算 + 早停

- **calls 估算口径**：真臂 `llm_calls` ≈ 与 canonical 同期臂同量级（**~2.8k/臂·seed**；mock 干跑 OFF/ON=2838/2789 为结构参考，真跑以实数为准）。
- **时长**：单臂 n16r60 参考历史 ~50–60min ⇒ **4 臂串行 ≈ 3.3–4h**（真 LLM 延迟主导）。
- **1/3 处早停**：第 20 回合后抽 `<RUN>/run.jsonl` 的 **C 臂 `gap=0` 应=0、B′ 臂 `gap=0` 应>0**；B′ 若 1/3 处仍 `gap=0`=0 ⇒ **立即停**（省预算），报「可见性未生效（接线）」，标 `partial`。

## 7. 障碍与建议

- **O-1（需处理）**：`phase_B_decision_count` 不落 `run.jsonl`/`meta.json`。**建议** additive 加一个逐回合 `SYSTEM` 事件（如 `D212_INROUND {calls,replies}`，仅 ON 时发），使主判据可复算；否则真臂主判据降级为 `gap=0`。
- **O-2（已解决）**：worktree 缺 `code/.env.local` ⇒ `run_batch.sh` line 49 报错。**修复**：`cp ../../code/.env.local code/.env.local`（或 `host_batch --env-file`）。
- **O-3（提示）**：`check_clean_tree` 只看 `code/{life,orchestration,config,engine}`；`code/.env.local`、新脚本/测试不在冻结区，不影响 preflight。

---

*（本条目为 mock 干跑产出；干跑证据见 `v2/evidence/d212_preflight_dryrun.md`。未 git 提交、未 push。）*
