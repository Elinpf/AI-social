# 可复现构建与发布/回滚手册（现状 → 目标 → 缺口 → 实现顺序）

> 作者：release-engineer（发布与构建工程师）｜ 2026-10-12 ｜ 任务：T219-build-and-release
> 仓根：`social-experiment/`（下称「仓根」）｜ 代码根：`social-experiment/code/`（下称 `code/`）
> 状态：**本文是「现状盘点 + 方案」，不等同于已落地实现**。凡未实测的标 **【未验证】**。
> 定位：本线此前**不存在**（用户问「是否有部署 Agent 保证稳定可靠」→ 那是新设责任线）。本文只覆盖 **构建 / 版本与产物清单 / 发布检查 / 回滚 / 一键起服务**；
> **测试策略与门禁分级属 T217（sandbox-test-lead）与 T218（delivery-reviewer）**，本文**只引用、不另立**。

---

## 0. 红线与前提（沿用团队不变红线）

1. **证据绑版本**：任何产物必须能回答「哪个 sha / 哪份 config / 哪次运行」——本文的 `manifest.json` 就是干这个。
2. **口径唯一不复制**：指标、守恒、分布基线一律**引用** `code/obs/gate.py` 与 `code/obs/golden_baseline.json`；发布侧**不重算**。
3. **红灯不许发**：§2.6 的发布检查任一硬红 → 停，不做「先发再说」。
4. **不做静默降级**：任何 SKIP / 豁免 / 降级（含 Fork B 的「逐位可复现降为诊断」）必须**显式打印并写进 manifest**。
5. **密钥绝不落盘 / 入日志 / 入报告**：`code/.env.local` 已 gitignore（实测 ✓）；发布前置须加一道「tracked 文件无密钥」扫描。
6. **Fork B（已定）**：**「逐位可复现」不再是验收口径**；「同 seed 重跑逐位一致」类断言**显式降为诊断**（不阻塞发布）。
   注意区分三件事（§6.2）：**同数据两次重算一致**（纯函数，仍是硬门禁）、**日志自洽 replay 一致**（仍是硬门禁）、**跨进程/跨跑世界序列一致**（降为诊断）。

---

## 1. 现状盘点（as-is）

### 1.1 现有「构建 / 跑起来 / 验一下」入口清单（实测列出）

| # | 入口 | 位置 | 做什么 | 退出码语义 | 实测 |
|---|---|---|---|---|---|
| E1 | `make gate` | 仓根 `Makefile` | 术语棘轮 + `code/` pytest +（可选）`lint-imports` | 失败非 0 | ✅ 存在 |
| E2 | `make lexicon-gate / -report / -baseline / -dir-stats` | 仓根 `Makefile` | 术语合规（基线/棘轮） | 新违规非 0 | ✅ |
| E3 | `make code-test` | 仓根 `Makefile` | `cd code && pytest -q` | pytest 码 | ✅ |
| E4 | `make ci` | `code/Makefile` | 调 `frontend/tools/ci_gate.sh` | **0/1/3**（3=SKIP） | ✅ |
| E5 | `make smoke / gate / serve / art` | `code/Makefile` | 前端 smoke / 真渲染门禁 / 静态服务 8848 / 美术构建 | 0/1/3 | ✅ |
| E6 | `python -m engine run\|replay\|verify` | `code/engine/cli.py` | 纯内核跑批 / 重放 / 双跑比对 | `run` 按 `chain_ok`；`verify` PASS/FAIL | ✅ 实测 `--seed 1 --rounds 5` → chain_ok=True；verify PASS |
| E7 | `python -m orchestration run\|replay\|verify` | `code/orchestration/cli.py` | **life 规范入口**（真内核 × 生活层） | `run` 按 chain/parity/conservation | ✅（README §7） |
| E8 | `python -m obs metrics\|emergence-report\|wellbeing-report\|census\|gate\|evidence\|golden-freeze\|llm-cost` | `code/obs/cli.py` | 只读日志的度量/门禁/证据包 | `gate` 0/1 | ✅ 实测 `obs gate --baseline none` → GATE PASS |
| E9 | `python -m pytest -q` | `code/` | 单测回归（含 repro/health/hashchain 等） | pytest 码 | ✅ |
| E10 | `lint-imports` | `code/.importlinter` | 依赖边界（contracts/engine/life/freeze/orchestration） | 破损非 0 | ✅ 已装 |
| E11 | `python devtools/chronicle.py` | `code/devtools/` | 编年史可视化产物 | 0/1 | ✅（T211） |
| E12 | `python frontend/tools/serve.py` | `code/frontend/tools/` | 静态前端服务（默认 `127.0.0.1:8848`） | 0 | ✅ |
| E13 | `bash frontend/tools/{ci_gate,screenshot,art_build}.sh` | `code/frontend/tools/` | 前端门禁/截图/美术 | 各自 | ✅ |
| E14 | `python scripts/*.py` | `code/scripts/` | **各条验收脚本**（production/econ/lifecycle/dialogue…） | 各自 | ✅ 10 个脚本 |
| E15 | `python frontend/tools/gate_render.py` | `code/frontend/tools/` | 真 Chromium 渲染门禁 | **0/1/3** | ✅ 逻辑存在（硬编码 chrome 路径） |

### 1.2 重叠与命名冲突（必须收口）

- **两个 `make gate` 语义完全不同**：仓根 `gate` = 术语+pytest；`code/` `gate` = 前端真渲染门禁。**顶层同名极易误用**。
  - **处置（Leader 裁决，分两步）**：**第一步（已做，零风险）**——`code/Makefile` 增 `front-gate` 别名（指向前端真渲染门禁），两份 `make help` 各写清区别；
    **第二步（待 `make release` 落地、入口收口后一次做）**——再真正改名，避免现在打断 15 处引用。
- **同端口两套绑定**：`serve.py` 默认 `127.0.0.1`，`ci_gate.sh` 用 `0.0.0.0:8848` —— 环境变量未统一。
- **`scripts/*.py` 是「第二套入口」**：与 E6/E7/E8 CLI 并存、无 Makefile 收口、命名不成体系（`run_production_acceptance` / `run_econ_acceptance` / `lifecycle_*_run` …）。
- **「复现/守恒」断言散落 4 处**：`engine verify`（E6）、`obs gate`（E8）、`tests/test_obs_repro_gate.py`、`tests/test_run_health_gate.py` —— 需一张**分级表**统一（T218 的活，本文只引用）。
- **SKIP 语义不统一**：只有 `ci_gate.sh` / `gate_render.py` 有「3=S​KIP 不算通过」；pytest 无该概念。

### 1.3 版本与指纹现状（有基础，但不成体系）

| 机制 | 位置 | 状态 |
|---|---|---|
| **config 指纹** `compute_fingerprint()` | `code/engine/version.py` | ✅ 聚合 9 个 config 文件的规范哈希，写入 `WORLD_INIT.fingerprint` |
| **逐文件 digest** `component_digests()` | 同上 | ✅ |
| **重放前指纹断言** `assert_log_fingerprint()` | 同上 | ✅ 不一致**硬报错**（不静默回退） |
| **版本一致性** `assert_version_consistency()` | 同上 | ✅ `engine_version.json` 声明 vs 实际 |
| **引擎组件版本声明** | `code/config/engine_version.json` | ✅（含 `ROUNDS_PER_SLOT` 等复现常数） |
| **日志哈希链 / log_hash** | `code/engine/ledger.py`；`obs` census 报告 | ✅ |
| **git sha** | git 仓 | ⚠️ **仅手写在 evidence md**（如 `v2/evidence/t136_p2_end_to_end.md` 的 `sha e6d77c2`），**产物未自动绑定** |
| **batch_id** | — | ❌ **不存在** |

结论：**「配置指纹 + 版本声明 + 哈希链」是强项**，但**没有把它们和「git sha + 命令 + 产物字节」打成一枚可核对的 manifest**。

### 1.4 环境依赖现状

- Python **3.12.3**；`pytest` / `importlinter` / `PIL` / `numpy` 均可用（实测）。
- Node 在 `Makefile` 里 prepend `/root/.local/share/pi-node/node-v22.23.1-linux-x64/bin`。
- Playwright + Chromium 在 `/root/.cache/ms-playwright/chromium-1243/...`（`gate_render.py` **硬编码**）。
- **无 `requirements.txt` / `pyproject.toml` / lockfile** → 环境不可锁，跨机复现**【未验证】**。
- **无 `Dockerfile` / `docker-compose`**。
- **无 CI 编排文件**（无 `.github/workflows` 或等价）——门禁靠人肉按 Makefile 跑。
- 磁盘：`/` 用 **65%**（151G/244G）；**inode 用 89%**（1.45M/16.25M）——**跑大批量前必须查 `df -h` / `df -i`**（已是私有工作约定）。
- 密钥：`code/.env.local` 存在（600 权限）且被 `code/.gitignore` 忽略（实测 `git check-ignore` ✓）。

### 1.5 当前工作区状态（发版视角的即时红灯）

`git status`：**有未提交改动与未跟踪文件**（`code/engine/*`、`code/devtools/`、`code/plugin/`、`v2/evidence/devtools/` 等）。
→ 按红线「证据绑版本」，**dirty tree 不能发**（除非显式豁免并打 `-dirty` 标）。

---

## 2. 目标（to-be）

### 2.1 版本标识（Version ID）

```
VERSION = <short_sha><-dirty?>+cp-<config_fingerprint[:12]>
例：22ae44c+cp-3f9a1c0b7e52      （干净树）
例：22ae44c-dirty+cp-3f9a1c0b7e52（显式豁免的脏树，禁止用于对外交付）
```

- `short_sha` 来自 `git rev-parse --short HEAD`；`-dirty` 由 `git status --porcelain` 非空触发。
- `cp-<12hex>` = `engine/version.py::compute_fingerprint()` 去掉 `sha256:` 前缀的前 12 位。
- 时间戳**仅记录、不参与标识**（不进入可复现输入）。

### 2.2 一条命令可复现构建（核心诉求）

目标：**一段可复制粘贴的命令**，把「代码 + 配置 + 资产」变成一个**可验证的产物**并打印版本/指纹。

```bash
# 目标入口（建议新增；当前尚未落地 —— 见 §4 实现顺序）
cd social-experiment && make release
# 等价：bash scripts/release.sh
```

该命令应依次做（**全绿才产出**）：
1. **前置闸 —— 首行打戳 git 状态**（T220 契约，见 §6.3）：调 `bash tools/git_stamp.sh`，**输出打头三行** `sha / dirty_files / 状态`；
   随后 tree 干净（或 `RELEASE_ALLOW_DIRTY=1` 显式豁免）；`df -h` / `df -i` 富余；tracked 文件密钥扫描。
   - **发版语义**：`make release`（**产出发版**）以 **`GIT_STAMP_STRICT=1`** 调打戳 → 脏树直接 rc≠0 **停**（对齐「树干净前置闸不放松」+ git tag 条件①）。
   - **诊断语义**：`make release-check` 等**只检查不产出**的入口用**非 strict** → 脏树打印 `[DIRTY — 结论仅供参考]` 但**继续**（结果不得当作「通过」依据）。
2. **门禁闸**（调用统一聚合，不新写门禁）：术语棘轮 + `pytest -q` + `lint-imports` + `obs gate`(基准日志) + `orchestration verify`(日志自洽)。
3. **算版本**：`VERSION = …`（§2.1）。
4. **组装 `dist/<VERSION>/`**：用 `git archive` 取**仅 tracked** 的源码树；**另附 config 快照**（`config/` 是复现真源）、`personas.json`/`places.json`、`THIRD_PARTY_NOTICES.md`、`licenses/`、前端 `assets/` 清单。
5. **落清单**：`dist/<VERSION>/manifest.json` + `SHA256SUMS.txt`。
6. **打印摘要**：`VERSION / sha / config_fingerprint / artifacts 数 / gates 全绿`。

### 2.3 版本与产物清单 —— `manifest.json`（回答「这个产物哪来的」）

```jsonc
{
  "version": "22ae44c+cp-3f9a1c0b7e52",
  "git": { "sha": "22ae44c…", "short": "22ae44c", "dirty": false, "describe": "…" },
  "created_at": "2026-10-12T10:20:00+08:00",      // 仅记录
  "python": "3.12.3",
  "config": {
    "fingerprint": "sha256:…",                      // = WORLD_INIT.fingerprint 口径
    "component_digests": { "default.json": "sha256:…", "policy.json": "sha256:…", "…": "…" },
    "engine_version_file_sha256": "…"
  },
  "engine_version": { "components": { "…": {"file": "…", "version": "…"} } },
  "entry": { "module": "orchestration", "cmd": "python -m orchestration run --seed 42 --agents 20 --rounds 84 --out …", "seed": 42, "n": 20, "rounds": 84 },
  "gates": [ { "name": "pytest", "status": "PASS" }, { "name": "obs_gate", "status": "PASS", "log_hash": "sha256:…" }, { "name": "replay_verify", "status": "PASS" }, { "name": "frontend_ci", "status": "SKIP", "reason": "playwright 缺失" } ],
  "artifacts": [ { "path": "code/engine/kernel.py", "sha256": "…", "bytes": 12345 } ],
  "not_included": [
    { "glob": "**/*.jsonl",          "reason": "体积大且可由命令再生；sha256 已记录在对应证据 md/json 中" },
    { "glob": "freeze_cache/**",     "reason": "可再生（LLM 输出缓存）；不入发布物" },
    { "glob": "**/__pycache__/**",   "reason": "解释器产物" }
  ],
  "reproduce": "cd dist/<VERSION> && python -m orchestration run …（见 entry.cmd）",
  "notes": ["…显式豁免/SKIP/降级说明…"]
}
```

要点：
- **`config.fingerprint` 必须与 `WORLD_INIT.fingerprint` 同口径**（都来自 `compute_fingerprint()`）——**不复制**。
- 未纳入产物的东西**必须列在 `not_included`**（不做静默缺失）。
- 一次运行产出的**日志 + 报告**用 `obs evidence` 生成证据包；manifest 只引用其 `log_hash`。
- **证据依赖的 LLM 输出缓存必须留 sha**：若某次运行的结论**依赖某份 freeze cache**，该 cache 的 **sha256 必须记进 evidence**——
  否则那条结论**无法被复核**（Fork B 放开了「重跑一致」，但没放开「**可被复算**」）。
- **run 归档描述符（与 obs evidence 同名，口径唯一不复制，T229）**：manifest 增
  `"archive": {"sha256", "ref", "command", "in_git"}`（run 侧可附 `bytes/n_files/has_side/side_txt/side_vec`）；
  字段名与 `obs evidence --archive*` 写入 `summary.json` 的块**逐字一致**。详见 `v2/refs/run-artifact-archive.md` §6。

### 2.4 回滚（退到上一个可用版本，含配置与资产）

- `dist/<VERSION>/` **构建后只读、不可变**（产物即账）。
- `dist/current` → **symlink** 指向当前 active 版本。
- `scripts/rollback.sh <VERSION>`：校验目标 `manifest.json` 存在 → **原子切换 symlink** → 打印与当前版本的**差异**（尤其 `config.fingerprint` 变化 → 说明复现输入变了）。
- **配置与资产随 dist 快照** → 回滚代码时**同时回配置/资产**（因 config 是复现真源）。
- **日志/证据不回滚**（append-only 事实源）；回滚只回「代码 + 配置 + 资产」，**不改写已发生的事实**。
- 需要「上一版」时若无 dist，可用 `git tag`（建议发版打 `rel/<VERSION>` tag）作为兜底。

**git tag 策略（Leader 裁决，四条条件）**：
1. **仅当 `make release` 绿灯（含树干净）** 才可打 tag；
2. 命名**沿用现有风格**（如 `v2-p2-milestone`）；
3. **打 tag 前 `manifest.json` 必须已落盘**；
4. **tag 只是标记，回滚靠 `dist/`** —— **别把 tag 当回滚机制**。

### 2.5 一键起服务（本地开发与评审）

统一环境变量（先定，再写脚本）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `HITT_PORT` | `8848` | 静态服务端口 |
| `HITT_HOST` | `127.0.0.1` | 评审本地；CI 用 `0.0.0.0` |
| `HITT_PYTHON` | `python3` | 解释器 |
| `HITT_LOG` | 空 | 传入一份日志 → 地址带 `?log=` |

```bash
# 目标入口（建议新增）
make dev            # 起前端静态服务（= python frontend/tools/serve.py --host $HITT_HOST --port $HITT_PORT）
# 其余为「打印即用」的只读命令（不常驻）：
#   python -m obs metrics   --log <log> --out /tmp/metrics.json
#   python -m obs gate      --log <log>
#   python devtools/chronicle.py --log <log> --out frontend/sample/devtools_chronicle
```

- 后端「跑批」是**长任务**，**不塞进 `make dev`**（避免误起大任务）；长跑用 `python -m orchestration run`（显式）。
- 说明：前端需要的浏览器运行时（Chromium）在 `gate_render.py` 里**硬编码绝对路径**，跨机需参数化 **【未验证】**。

### 2.6 发布检查清单（红灯不许发）

| ID | 检查 | 命令 | 红灯条件 |
|---|---|---|---|
| R1 | 单测全绿 | `cd code && pytest -q` | 有 fail / error |
| R2 | 依赖边界 | `cd code && lint-imports` | 有 broken contract |
| R3 | 术语棘轮 | `make lexicon-gate` | 基线外**新**违规 |
| R4 | 观测门禁 | `python -m obs gate --log <基准日志>` | `GATE FAIL` |
| R5 | 日志自洽重放 | `python -m orchestration verify --log <log>` | 两次哈希不等 / FAIL |
| R6 | 树干净 | `bash tools/git_stamp.sh`（发版用 `GIT_STAMP_STRICT=1`） | 非空且未显式豁免（strict → rc≠0） |
| R7 | 无密钥入库 | tracked 文件扫描（见下） | 命中 `.env`/`*.key`/`secret*` |
| R8 | 磁盘/inode | `df -h . && df -i .` | 磁盘 >85% 或 inode >90% |
| R9 | 前端门禁 | `bash code/frontend/tools/ci_gate.sh` | 返回 1（**返回 3=SKIP 必须记录，不得当通过**） |

R7 扫描建议（纯本地、不联网）：

```bash
git -C social-experiment ls-files -z \
  | grep -zEi '(^|/)(\.env[^/]*|.*\.key|secrets?[^/]*)$' \
  && { echo "红灯：tracked 含疑似密钥文件"; exit 1; } || echo "R7 PASS"
```

---

## 3. 缺口 → 目标 映射

| 缺口（as-is） | 目标（to-be） | 影响 |
|---|---|---|
| G1 无「一条命令」构建 | §2.2 `make release` | 发布不可复现、靠人肉多步 |
| G2 两个 `make gate` 同名异义 | 顶层 `gate` 收口所有门禁；前端门禁改名 `front-ci` | 误用风险 |
| G3 无产物 manifest | §2.3 `manifest.json` | 无法回答「产物哪来的」 |
| G4 版本弱（仅手写 sha） | §2.1 `VERSION` + git tag | 产物与代码无法对账 |
| G5 无回滚 | §2.4 dist/ symlink + rollback.sh | 出事只能手改 |
| G6 无环境锁 / Docker | 建议 `requirements.lock`（先报 Leader）；Docker 暂缓 | 跨机复现【未验证】 |
| G7 无 CI 编排 | 顶层 `make release` 可作 CI 单入口 | 门禁靠自觉 |
| G8 一键起服务不完整 | §2.5 `make dev` + env 统一 | 评审启动多步 |
| G9 无密钥扫描 | §2.6 R7 | 误提交风险 |
| G10 无发布清单文档 | §2.6 | 红灯口径不统一 |

---

## 4. 建议实现顺序（先无依赖、后编排；每步附反向验证）

> 原则：**先盘点（本文）→ 再最小可跑 → 再加清单 → 再加回滚 → 最后 CI 编排**。**每加一道闸必须附「故意弄坏确实变红」的证明**（红线⑤）。

1. **P1 · 统一入口消歧（分两步）**
   - **第一步（已做，零风险）**：`code/Makefile` 增 `front-gate` **别名**（= 前端真渲染门禁）；两份 `make help` 均写明「仓根 `gate` = 术语+测试 / `code/` `front-gate` = 前端渲染」。
   - **第二步（待 `make release` 落地后再做）**：真正改名 + 顶层 `gate` 增补调用前端门禁（可选 `front-ci`）。
   - 反向验证：制造一个前端渲染错误 → `make -C code front-gate` 返回非 0；改回 → 复绿。
2. **P2 · `scripts/release.sh` 最小版**（仅前置闸 + 跑门禁 + 算 VERSION + 打印，不出 dist）
   - 反向验证：`RELEASE_ALLOW_DIRTY` 未设时，touch 一个 tracked 文件 → 前置闸红。
3. **P3 · manifest 生成 + `dist/<VERSION>/` 组装**
   - 反向验证：改 `config/policy.json` 一个 default → `VERSION` 的 `cp-` 段变化（证明配置进了指纹）；对旧日志跑 `obs gate`/`replay` → 红。
4. **P4 · 回滚 `scripts/rollback.sh`**
   - 反向验证：切到「不存在的 VERSION」→ 报错非 0；切回 → `dist/current` 指向正确、打印指纹差异。
5. **P5 · 一键起服务 `make dev` + env 统一**
   - 反向验证：占用 8848 → 报「端口被占」而非静默失败。
6. **P6 · 发布检查清单落成一键 `make release-check`（不产出，只检查）**
   - 反向验证：逐条 R1–R9 各注入一次故障，确认**仅对应项**变红。
7. **P7（需 Leader 批准）· 环境锁 / CI 编排文件**（引入前**先报 Leader**，遵守「不引入联网重依赖」）。

---

## 5. 可复制执行命令（现状可跑 vs 目标命令）

**现状（今天就能跑，已实测标记 ✅）**

```bash
cd social-experiment/code

# 纯内核最小跑通 + 自洽重放（✅ 实测 --seed 1 --rounds 5）
python -m engine run --seed 1 --rounds 5 --out /tmp/hitt_probe.jsonl
python -m engine verify --log /tmp/hitt_probe.jsonl        # PASS

# life 世界（规范入口）
python -m orchestration run --life --seed 42 --agents 10 --rounds 84 --out /tmp/hitt_life10.jsonl
python -m orchestration verify --log /tmp/hitt_life10.jsonl

# 观测门禁（✅ 实测 --baseline none → GATE PASS）
python -m obs gate --log /tmp/hitt_probe.jsonl --baseline none
python -m obs evidence --log /tmp/hitt_life10.jsonl --out-dir /tmp/hitt_evidence

# 门禁聚合（仓根）
cd .. && make gate            # 术语棘轮 + pytest + lint-imports
cd code && make front-gate    # （改名后）前端真渲染门禁
cd code && bash frontend/tools/ci_gate.sh   # 前端双门禁，注意退出码 3=SKIP
```

**目标命令（建议新增，尚未落地 —— 见 §4）**

```bash
cd social-experiment
make release                  # 一条命令：门禁全绿 → dist/<VERSION>/ + manifest.json
cat dist/current/manifest.json
make rollback VERSION=<prev>  # 回滚（代码+配置+资产）
make dev                      # 一键起前端服务
```

---

## 6. 与 T217 / T218 的接口（口径唯一不复制）

### 6.1 分工
- **T217（测试策略）**：覆盖率基线/棘轮、四类「假」、反向验证方法论 —— **本文不定义**，发布清单**引用**其分级。
- **T218（门禁分级 + 独立评审）**：门禁等级表 —— 本文的**发布红灯 = 其「阻塞级」**；我只做**发布侧编排**，**不重定义**等级。
- **本文（T219）**：只把既有门禁**串成一条命令**、加**版本/manifest/回滚/起服务**，**不新造指标、不新造守恒、不新造分布基线**。

### 6.2 Fork B 下的「三类一致性」必须分清（避免假 FAIL / 假 PASS）

| 类别 | 例子 | Fork B 后 | 理由 |
|---|---|---|---|
| (a) **同数据两次重算** | `obs gate` 的 `metrics_bitwise_equal` / `census_bitwise_equal` | **保留硬门禁** | 纯函数、**不涉及 LLM、不重跑世界**；它证明的是「度量确定」，不是「世界可复现」 |
| (b) **日志自洽重放** | `orchestration verify`（同一日志折叠两次哈希相等） | **保留硬门禁** | 折叠 `replay(log)` 是确定性 reduce，**不依赖重跑世界**；它证明「日志→状态」自洽 |
| (c) **跨跑/跨进程世界序列一致** | 若断言「同 seed 两进程 state_hash 相同」（如 T136 的对照） | **降为诊断（不阻塞）** | 正是 Fork B 放开的那类；**显式标注为诊断**，避免假 FAIL |

→ 建议把这张表交给 **T218** 纳入门禁分级表的「诊断级 / 阻塞级」两栏；**obs 侧不复制**，仅**引用**。
> **Leader 2026-10-12 裁决：同意**将此三分法交 T218 并入分级表。

### 6.3 门禁打戳契约（T217/T220，唯一实现 `tools/git_stamp.sh`）

**复用**（不另写第二套）：

```bash
bash tools/git_stamp.sh                       # 打头三行：sha / dirty_files / 状态；rc 恒 0
GIT_STAMP_STRICT=1 bash tools/git_stamp.sh    # 脏树 → rc 1（供「脏即不通过」的入口）
```

- 输出契约：`sha: <short>` / `dirty_files: <N>` / `状态: [CLEAN] | [DIRTY — 结论仅供参考] | [NO-GIT — 结论仅供参考]`。
- **发布入口的接线**（T219 落实，脚本落地时执行）：
  - `release.sh` / `rollback.sh` **开头即调**打戳；
  - **发版** `make release` → **strict**（脏树停）；
  - **只检查** `make release-check` → 非 strict（脏树**继续但标注仅供参考**，**不得当作通过依据**）。
- manifest 里 `git.sha` / `git.dirty` 直接取打戳结果，**不另算**。

---

## 7. 未验证项与开放问题

- **【未验证】** `gate_render.py` 硬编码 Chromium 绝对路径 → 迁移到别的机器会 SKIP（3），需参数化。
- **【未验证】** `make release` / `rollback.sh` / `make dev` 均为**建议设计**，本文未落地代码。
- **【注意】** 本机 **inode 89%**，`dist/` 长期堆放多个版本会推高 inode —— 建议保留最近 N 版 + 自动清理策略。
- **【注意】** 工作区 **dirty 是当前预期常态**（多成员并行在飞）；「树干净」前置闸 **不放松** —— 发版只能在**波次收口后**做。

> 以下原「待定」项已由 Leader 于 2026-10-12 裁决（见 §8）。

---

## 8. 裁决记录（Leader 2026-10-12，T219 验收后）

| 项 | 裁决 | 落地要点 |
|---|---|---|
| `requirements.lock` | **做 ✓** | 环境可复现是「稳定可靠」地基，且**不需要联网重依赖** |
| Docker | **暂缓 ✗** | 本机无 GPU + inode 89%；收益不明确、代价明确 |
| CI 编排文件（yaml） | **暂不做 ✗** | 已有事实上的 CI（`make ci`/`ci_gate.sh`/pre-commit）；写没人跑的 yaml = 死文件，待真 CI 环境 |
| git tag | **允许，四条件** | ①`make release` 绿灯（含树干净）②命名沿用现有风格 ③tag 前 manifest 已落盘 ④**tag 只是标记，回滚靠 dist** |
| `freeze_cache/` 入发布物 | **不纳入 ✓** | manifest 写 `not_included` + **一行原因**（可再生）；**且**：结论若依赖某份 cache，**该 cache 的 sha 必须记进 evidence** |
| 两个 `make gate` | **分两步** | 现在**加别名 + help 写清区别**（零风险，第一步已做）；**真正改名待 release 落地后一次做** |
| Fork B 三分法 → T218 | **同意** | 交 T218 并入门禁分级表「诊断级 / 阻塞级」 |

（完整裁决原文见 T219 验收消息；本表为执行口径。）
