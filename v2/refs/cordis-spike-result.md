# Cordis spike 结果（T206）：四步实测与「跨语言值/不值」二值结论

> 作者：solution-architect ｜ 任务：T206-cordis-spike-execute ｜ 依据：T201 §5 spike 设计
> 环境：Linux 容器；Node **v22.23.1**、npm 12.0.1、**pnpm 存在**、Python 3.12.3；磁盘 85G 余量、inode 充足（跑前已查 `df -h`/`df -i`）。全部工作目录 **`/tmp/cordis-spike`**，**未触碰本项目 `code/`**（收工 `git status code/` 为空）。
> 安装物：`@deepseek-ai/dsh@0.2.0-rc.2`、`@deepseek-ai/cordis@4.0.4`（npm，共 538 包）；Python SDK `deepseek-harness-sdk==0.1.5rc1`（PyPI；其依赖 `deepseek-harness-runtime-bin` 平台 wheel 未安装——改用 `dsh_bin` 指向 npm 的 `dsh`）。

---

## 0. 结论（二值）

**依据 T201 §5 写死的决策规则**（S1–S4 全过 → 建议 C；S2/S4 不过 → 建议 B）：

> **S1 ✅ · S2 ✅ · S3 ✅ · S4 ✅（全部通过）→ 二值结论：为 Cordis 跨语言「值」→ 建议路线 C（窄混合，Python 世界引擎为唯一真值 + Cordis/DSH 承接 agent 内容层）。**

**通过数字（一句话）**：IPC **单次往返 p50 0.19 ms / p95 0.89 ms**（阈值 ≤50 ms，**宽裕约 55×**）；冻结语义胶水 **27 行**（阈值 <150 行）；DSH 插件复用与自定义插件注入 **零 fork**（纯配置）。

> **诚实边界（必须与结论同时读）**：本 spike 证明的是**跨语言边界的「机制代价」极低**，**不是**证明「我们一定需要 DSH 的那组插件」。**「要不要用 DSH 插件」是产品决策**（T201 §1.2 已查明 DSH **无任何社会模拟/经济/生命周期/观测领域插件**，只有 llm/session/skill/compaction 等叶子能力）。**若决定不用这些叶子插件，则路线 B 仍成立**（跨语言无收益）。

---

## 1. 环境与前置（实测）

| 项 | 结果 |
|---|---|
| `df -h /` | 244G，余 **85G**（跑前 86G → 跑后 85G） |
| `df -i /` | 1,986,141 空闲 inode（88% 已用，仍充足） |
| `node` / `npm` / `pnpm` | v22.23.1 / 12.0.1 / 存在（`/usr/local/bin/pnpm`） |
| npm registry / github | 均可达（`npm ping` PONG 202ms；github HTTP 200） |
| `@deepseek-ai/dsh` | `0.2.0-rc.2`（npm `latest`） |
| `@deepseek-ai/cordis` | `4.0.4`（npm `latest`） |
| Python SDK | `deepseek-harness-sdk` PyPI：真实版 **0.1.5rc1**；另有占位包 0.0.0.dev0（“name reservation placeholder”） |

---

## 2. S1 — 挂自定义插件（✅ 通过）

**动作**：(a) 独立脚本用 `@deepseek-ai/cordis` 直接 `Context` 编程挂载；(b) 通过 `cordis.yml` + `cordis` bin（官方 launcher）配置式挂载。

**实测输出（S1a，独立脚本 `s1-standalone.mjs`）**：
```
plugin:apply
effect:acquired
plugin:apply-done
event:app/ready:hello
probe.ping=1          ← 服务注入 inject:['probe'] 生效
effect:disposed       ← 卸载时副作用被自动回收（可逆副作用）
root:disposed
```
**实测输出（S1b，`cordis.yml` 配置式）**：
```
[S1-loader] apply, config={"greeting":"S1-loader-hello"}
[S1-loader] effect:acquired
[S1-loader] apply-done
```
**判定**：插件可挂载、`inject` 依赖等待生效、类型化事件生效、**卸载时 effect 自动 dispose**。→ **S1 通过**（无 S1 判据里的“需改源码”情形）。

**复现命令**：
```sh
cd /tmp/cordis-spike
node s1-standalone.mjs                 # S1a
./node_modules/.bin/cordis             # S1b（读本目录 cordis.yml）
```

---

## 3. S2 — 零 fork 复用真插件（✅ 通过）

**动作**：① 列 DSH 组合树；② 用 **`--patch` overlay** 向组合树**插入**自定义插件；③ 用 patch **改写一个真实 DSH 插件**的配置。

**实测数字**：
- `dsh --profile headless --dump-config` 成功，组合出 **95 个不同插件包**（96 条 name 条目）。示例真插件：`@deepseek-ai/dsh-llm`、`@deepseek-ai/dsh-session`、`@deepseek-ai/dsh-session-title`、`@deepseek-ai/cordis-plugin-timer` 等。
- **insert patch**（`overlay.yml`）成功插入自定义插件，dump-config 末尾出现：
  ```
  # == /tmp/cordis-spike/overlay.yml
  - id: s1-loader-plugin
    name: file:///tmp/cordis-spike/s1-loader-plugin.mjs
    config: { greeting: S2-patch-hello }
  ```
  → **相对路径被锚定在 patch 文件旁**（`file://`），**无需改 DSH 源码**。
- **改写真插件配置**：`overlay2.yml` 把 `session-title.fallbackMaxWords` 由 5 改为 7，dump-config 确认生效。→ **零 fork**。

**判定**：**复用与扩展均通过 config/patch 完成，零 fork、零改源码**。→ **S2 通过**。

**复现命令**：
```sh
cd /tmp/cordis-spike
DSH_HOME=/tmp/cordis-spike/home ./node_modules/.bin/dsh --profile headless --dump-config | grep -c "name:"
DSH_HOME=/tmp/cordis-spike/home ./node_modules/.bin/dsh --profile headless --patch ./overlay.yml --dump-config | grep -A3 s1-loader-plugin
DSH_HOME=/tmp/cordis-spike/home ./node_modules/.bin/dsh --profile headless --patch ./overlay2.yml --dump-config | grep -A3 "id: session-title"
```

---

## 4. S3 — Python SDK 往返与延迟（✅ 通过）

**动作**：用 `deepseek_harness.DeepSeekHarness(dsh_bin=<npm dsh>, profile="sdk")` 起子进程 JSON-RPC 运行时；测启动/握手与逐次 RPC 往返。

**实测数字**（本机，40 次采样）：
| 指标 | 值 |
|---|---|
| 启动 + initialize（子进程 spawn + Node boot + 握手） | **1929 ms**（首跑）/ **1033.9 ms**（复跑）——**一次性** |
| **JSON-RPC 单次往返** n=40 | **mean 0.25 ms · p50 0.19 ms · p95 0.89 ms · min 0.15 · max 0.98** |
| 一次完整 turn 的管线耗时（无 key → 走到 LLM 报 error） | 251 ms |
| 该 turn 回传给 Python 的结构化会话事件 | **14 条**（`turn/start`、`step/start`、`request/header`、`assistant/attempt`、`turn/end`、`session/title`…） |

**阈值对照**：**p95 0.89 ms ≪ 50 ms**（宽裕约 **55×**）。→ **S3 通过**。

**另证**：DSH 会把会话持久化为 **append-only JSONL + zstd**：`$DSH_HOME/sessions/--tmp-cordis-spike--/<sid>/session.v4.jsonl.zstd`（**这是与我们一起实现无关的“第二套日志”**，见 §7 未决项）。

**复现命令**：
```sh
cd /tmp/cordis-spike
./venv/bin/python s3.py      # 启动/握手 + turn（无 key → error，但事件流可读）
./venv/bin/python s3c.py     # 40 次 RPC 往返延迟分布
```

---

## 5. S4 — 嫁接「冻结语义」测胶水（✅ 通过）

**动作**：写一个**与生产者无关**的胶水 `FrozenProducer`（首跑：调生产者 → 落 append-only 日志 + 内容寻址缓存；重放：只读缓存，**不调生产者**），并**真实**接到 DSH 之上（生产者 = `harness.run(prompt).final_response`）。

**实测数字**：
| 指标 | 值 |
|---|---|
| 胶水规模 | **27 行**（非空非注释；整文件 30 行）——**阈值 <150 行** |
| 需 fork DSH 吗 | **否**（只在外层包装；DSH 侧只改配置） |
| 端到端真实 turn（对本地 mock LLM） | 首跑文本 `'MOCK-REPLY-OK'`，耗时 **269 ms**；重放文本**逐字相同**，`producer_calls == 1`（重放未再调 DSH） |
| mock 收到的请求 | `POST /v1/messages`，头含 `anthropic-version: 2023-06-01`、`x-api-key`、`user-agent: deepseek-harness/0.2.0-rc.2` → **base_url 覆盖生效、请求确实经我们的 mock（零 fork）** |

**判定**：冻结语义可用 **27 行胶水**嫁接，**重放不重调、结果逐字一致**，**零 fork**。→ **S4 通过**。

**复现命令**：
```sh
cd /tmp/cordis-spike
./venv/bin/python s4_demo.py                                    # 冻结/重放机制（mock 生产者）
./venv/bin/python mock_llm.py 8931 &                            # 本地 mock Anthropic LLM
./venv/bin/python s4_real.py                                    # 真实 DSH turn + 冻结 + 重放
```

---

## 6. 汇总判据表与决策

| 步 | 判据（T201 §5） | 阈值 | 实测 | 通过? |
|---|---|---|---|---|
| S1 | 自定义插件可挂载、卸载副作用自动撤销 | 无需改 Cordis | 挂载 ✅、effect dispose ✅、config 式挂载 ✅ | ✅ |
| S2 | 零 fork 复用 ≥1 真插件 | 零 fork | 95 插件组合树；insert patch + 真插件改配置，全配置化 | ✅ |
| S3 | Python→DSH 往返成功、IPC ≤ 50ms | ≤50 ms | **p95 0.89 ms**；事件可读回 | ✅ |
| S4 | 冻结语义胶水 < 150 行、零 fork | <150 行 | **27 行**；重放逐字一致、不重调 | ✅ |

**决策规则（写死）**：S1–S4 全过 → **建议 C（窄混合）**。
**本 spike 输出：建议 C。** 但**附条件**：C 的**收益**取决于我们是否真的采用 DSH 的叶子插件（T201 已证其**无领域插件**）；**成本侧**（IPC/胶水/fork）本 spike 已证极低。**若产品决定不用这些叶子插件 → 回退 B**（跨语言无收益）。

---

## 7. 本次 spike 没能回答的问题（留给后续）

1. **真实模型质量未验证**：全程用**本地 mock**（无 `DEEPSEEK_API_KEY`），**未跑过真实 LLM**。DSH 的 LLM 适配器对真实 DeepSeek 账号的可用性/质量**未测**。
2. **50 agent 单进程规模未测**：T201 §5.5 的 N=10→50 递增验证**未执行**（本 spike 只测了单会话/单 turn 的机制代价）。
3. **双日志一致性未决**：DSH 的 `session.v4.jsonl.zstd`（append-only）与我们内核的哈希链日志是**两套事实源**；**如何把 DSH 日志降级为“仅 agent 内容缓存”、把世界真值收敛到 Python** 未设计/未验证。
4. **版本稳定性未测**：DSH 标注 developer preview、vendored Cordis 有 18 项本地补丁；**跨版本行为漂移**（尤其影响“冻结/复现”）未评估。
5. **50 规模下的进程/内存/费用会计未测**：单次 RPC 开销极低（0.19ms），但**长驻 50 会话的内存与 token 计量**未测。
6. **Cordis 的“服务消失自愈 / HMR”在仿真场景的实际价值未测**：机制成立（S1 已证 dispose），但**对离线确定性仿真是否有用**未评估。
7. **runtime-bin 未装**：改用外部 npm `dsh`（`dsh_bin`）绕过平台 wheel；**官方打包运行时**（`deepseek-harness-runtime-bin`）未验证。

---

## 8. 证据文件位置

**均在 `/tmp/cordis-spike/`（未入项目仓）**：
`s1-standalone.mjs`、`s1-loader-plugin.mjs`、`cordis.yml`、`overlay.yml`、`overlay2.yml`、`headless-config.yml`（95 插件基线）、`patched-config.yml`、`s3.py`、`s3b.py`、`s3c.py`、`s4_demo.py`、`s4_real.py`、`frozen_harness.py`、`mock_llm.py`、`mock_req.log`、`home/sessions/**/session.v4.jsonl.zstd`。

*（v2/refs/cordis-spike-result.md 完成 — solution-architect）*