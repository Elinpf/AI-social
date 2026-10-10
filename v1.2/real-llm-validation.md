# T43 · 真实 LLM 接入验证

> 作者：freeze-layer-dev ｜ 任务：T43-real-llm-validation
> 状态：**第一步（零费用探测）✅ + 第二步（接线冒烟 + N=3×10 真跑）✅**；thinking 策略已落地
> 关联：`v1.1/00-architecture.md` §1.5/§4.6/§5.4/§5.5、§7.2；`code/freeze/`

---

## 0. 背景（Leader 查明）

当前所有「端到端跑通」的日志里 `LLM_CALL=0 / LLM_JUDGMENT=0 / NARRATIVE=0`——
真实跑走的是离线确定性回退（`life.llm.RuleBasedLLM` / freeze `MockProvider`），
**从未真正调用过 LLM**。因此「LLM 决策与内容生成」层、真 provider 上的
「首跑落盘 + 重放零调用」、以及 token 成本，均未被验证。

本任务：把真实 LLM 接入验证做实，且不花冤枉钱。

---

## 1. 第一步：零费用探测结果

**探测原则**：只做**元数据探测**（`GET /v1/models`），**不产生任何生成/付费调用**。

### 1.1 探测手段与结果

| 探测项 | 命令/方式 | 结果 |
|---|---|---|
| 环境变量中的 LLM 端点/凭据 | `env` 过滤（密钥已脱敏） | 存在：`MODEL_PROVIDER=OpenAI`、`ENDPOINT_PROFILE=openai`、`VISION_API_BASE`、`VISION_API_KEY`、`VISION_MODEL_NAME=DeepSeek-Flash` |
| 权威模型配置 | `config.yaml` `models` 段（脱敏） | 默认端点 `api_base: http://172.16.3.41:31809/v1`，`model_name: DeepSeek-Flash`，`client_provider: OpenAI` |
| 端点可达性 + 鉴权 | `GET {base}/models`（**零 token**） | **HTTP 200**，鉴权通过；返回 **1 个模型：`DeepSeek-Flash`** |
| 本地 Ollama | `which ollama` / `curl localhost:11434` | **未安装**（PATH 无）、**无服务**、无本地模型 |
| 外部付费路径 | 环境变量 | `API_BASE=https://example.com/...`、`MODEL_NAME=your-model-name` 等均为**占位符**，无可用的付费外部凭据 |
| Python SDK | `import openai` / `httpx` | `openai 3.26.1`、`httpx` 可用（但冻结层用标准库 `urllib`，**无额外依赖**） |

### 1.2 三条路评估

| 路径 | 可得性 | 模型质量 | 费用 | 与冻结层兼容 | 结论 |
|---|---|---|---|---|---|
| ① **已有 OpenAI 兼容端点**（`http://172.16.3.41:31809/v1`，`DeepSeek-Flash`） | ✅ 可达、鉴权通过 | 中上（Flash 级，够做定性判定/内容生成抽样） | **内网模型服务，预估无按量计费**（待你确认）；即便按量也极小 | ✅ 直接映射 `OpenAICompatProvider`（`/chat/completions`） | **推荐** |
| ② **本地 Ollama** | ❌ 未安装、无服务、无模型；需安装 + 拉取模型（可能受网络限制） | 取决于所拉模型（如 qwen2.5:3b） | 零费用（本地算力） | ✅ 已有 `OllamaProvider` | 不推荐（当前不可用，先不改环境） |
| ③ **其他外部付费 API** | ❌ 无有效凭据（占位符） | 高 | **按量付费** | ✅ | 不采用（花冤枉钱、无凭据） |

### 1.3 建议

**采用路径 ①**：复用环境里已配置的 OpenAI 兼容内网端点
`http://172.16.3.41:31809/v1` + 模型 `DeepSeek-Flash`（正是当前 Agent 自身所用），
**零新增环境改动、零（或极小）费用、与冻结层零改造对接**。

### 1.4 费用 / token 预估（N=3 × 小回合）

依据 `00-architecture.md` §7.2 成本模型（每 Agent 每周 ≈ 42 次调用；每 Agent 每周
token 量级见下表，N=20 一周 ≈ 2×10⁶ token → 约 2400 token/次往返）：

| 规模 | 调用次数（估） | token 量级（估） | 费用（内网，估） |
|---|---|---|---|
| **N=3 × 5–10 回合（本步）** | ≈ 3×10×0.5 ≈ **15–30 次** | **≈ 3–7 ×10⁴ token** | **≈ 0**（内网） |
| 每周 N=3 | ≈ 130 次 | ≈ 3×10⁵ token | ≈ 0 |
| 每周 N=10 | ≈ 420 次 | ≈ 1×10⁶ token | ≈ 0 |
| 每周 N=20（目标档） | ≈ 840 次 | ≈ 2×10⁶ token | ≈ 0 |

> 说明：token 量为量级估算，真实值将在第二步用日志实测 `LLM_CALL.tokens_in/out` 回填。

### 1.5 冻结层侧的改动（本步已做，零费用）

- 新增 `freeze.providers.provider_from_env()`：**从环境变量**解析端点/密钥/模型，
  **不硬编码厂商与密钥**。
  - 端点：`FREEZE_LLM_BASE_URL`（回退 `OPENAI_API_BASE`）
  - 密钥：`FREEZE_LLM_API_KEY`（回退 `OPENAI_API_KEY`）
  - 模型：`FREEZE_LLM_MODEL`（回退 `OPENAI_MODEL`）
  - 或 `OLLAMA_BASE_URL`；`auto` 无配置时回退 `MockProvider`（离线）。
- 已导出到 `freeze/__init__.py`；`21/21` 单元测试保持通过。

### 1.6 待确认项 / 接口注意

- **费用口径**：`172.16.3.41:31809` 是否为纯内网不计费服务？若计费请告知预算上限，
  我会据此设 `LLMBudget` 闸门（降级链 T2→T1→T0）。
- **嵌入端点**：`EMBED_API_BASE`/`EMBED_MODEL` 为空，**无独立嵌入端点**；
  `DeepSeek-Flash` 端点是否支持 `/embeddings` 未验证。建议：真实嵌入验证**本轮跳过**
  （嵌入冻结已由 Mock 确定性单测覆盖），或第二步顺带探测。
- **接口调整清单（暂无阻塞）**：`OpenAICompatProvider` 已覆盖 `/chat/completions`；
  可选增强：超时/重试、`response_format=json_object`、流式。如第二步暴露需要，
  记入清单并与 kernel-dev 对齐；**绝不绕过冻结层直调**。

---

## 2. 第二步计划（待 Leader 确认后执行）

1. 用路径 ① 真跑 **N=3 × 5–10 回合**（可先不跑满周）。
2. 断言日志出现 `LLM_CALL`（含 tier/model/tokens_in/out）与
   `LLM_JUDGMENT`（四要素 `decision/model/context_digest/frozen=true`），必要时 `NARRATIVE`。
3. **重放验证**：重放态 `llm_calls == 0`（真 provider 上冻结机制成立）。
4. **实测 token 与费用**，外推 N=3/N=10/N=20 每周量级。
5. **行为差异**：与 rule-based 对比，抽样几条内容/决策，评估多样性。

---

## 3. 授权与执行

用户/Leader 已授权：路径① 采纳，第二步规模 N=3 × 10 回合；密钥经**环境变量**注入
（**不进代码/仓库/日志/证据包**，已做全仓库扫描确认无泄漏）。

---

## 4. 第二步：真跑结果（真实 provider）

**端点**：`http://172.16.3.41:31809/v1`（OpenAI 兼容）｜**模型**：`DeepSeek-Flash`
｜**thinking 控制**：`POST /v1/chat/completions` + `chat_template_kwargs.thinking`（按 purpose/tier 集中裁决）。

### 4.1 接线冒烟（≤2 次真实调用）✅

- 真实调用 = **2**（plan@T1 + judge@T2）；`LLM_CALL` 正常产生；重放 `llm_calls==0`、`provider.calls==0`。
- `LLM_JUDGMENT` 四要素示例：`decision="not_formed"`、`model="DeepSeek-Flash"`、
  `context_digest="sha256:dbdf…fccd"`、`frozen=true`。
- provider 协议/超时/重试通路正常（`max_retries=2`，`http_attempts==calls`，无重试发生）。

### 4.2 N=3 × 10 回合真跑

工作项：3 Agent × 10 回合的常规决策/对话（T1）+ 2 次软判定（T2）+ 1 次叙事。

| 指标 | 真实 LLM | rule-based（离线模板） |
|---|---|---|
| 真实调用次数 | **33** | 0（离线） |
| `LLM_CALL` 事件数 | 33 | 33 |
| tokens_in 合计 | **1,587** | 264（元数据占位） |
| tokens_out 合计 | **2,755** | 264 |
| 总 token | **4,342** | 528 |
| 总耗时 | **40.43 s** | 0.011 s |
| 平均/次 | 1.23 s（max 14.0 s，judge@thinking=true） | 0.0003 s |
| 重放 `llm_calls` | **0** ✅ | — |

**按 purpose 拆分（真实）**：

| purpose | n | tokens_in | tokens_out | thinking |
|---|---|---|---|---|
| plan | 12 | 440 | 272 | false |
| dialogue | 18 | 654 | 393 | false |
| judge | 2 | 314 | **1703** | **true** |
| describe（narrate） | 1 | 179 | 387 | **true** |

> 观察：`thinking=true` 的调用（judge/narrate）输出显著更长（judge 2 次即 1703 out tokens），
> 是**主要 token 成本源**；常规 T1（thinking=false）短而快（~1.2s/次、~30 tokens/次）。

**证据实例**：
- `LLM_CALL`（judge）：`tier=T2, model=DeepSeek-Flash, tokens_in=153/161, tokens_out≈850, thinking=true, cached=false, degraded=false`。
- `LLM_JUDGMENT`：2 条，`decision` 分别为 `not_formed` / `formed`（**随上下文不同而不同**），
  均含 `model=DeepSeek-Flash`、`context_digest`（sha256:…）、`frozen=true`。
- `NARRATIVE`：1 条，`narrative_id=N-r9`、`affects_state=false`。
- **重放**：同 cache_dir + engine_version 重放全序列，`llm_calls==0`、`provider.calls==0`，
  判定读回 `decision` 一致（冻结机制在真 provider 上成立）。

### 4.3 行为差异抽样（真实 vs rule-based）

| 类型 | 真实 LLM（多样、接地） | rule-based（模板恒定） |
|---|---|---|
| plan | “上午去镇东的集市买些新鲜蔬菜，顺便到老李家取回上周订的竹篮。” / “…取回上周托他修的锄头。” / “…顺便到邮局寄封信。” | “（计划）按作息工作、休息，留出社交与休闲时间。”（三次完全相同） |
| dialogue | “青溪镇的早晨真舒服，你家的菜园子今年收成咋样啊？” / “哟，Carol，今儿个去菜市场买菜了没？” | “（寒暄）今天天气不错，一切都好。”（三次完全相同） |
| judge | 依上下文给出 `not_formed` / `formed` | 恒定 `formed` |

结论：真实 LLM 内容**明显更多样、含具体人名/地点/物件**；rule-based 为确定性模板。

### 4.4 token / 费用外推（每周 = 84 回合，线性外推）

以实测 **token/Agent/回合 ≈ 144.7**（含 judge/narrate 摊薄）与 **调用/Agent/回合 ≈ 1.1** 外推：

| 规模 | 调用/周（估） | token/周（估） | 费用（内网，估） |
|---|---|---|---|
| N=3 | ≈ 277 | ≈ 3.6 ×10⁴ | ≈ 0（内网） |
| N=10 | ≈ 924 | ≈ 1.2 ×10⁵ | ≈ 0 |
| N=20 | ≈ 1,848 | ≈ 2.4 ×10⁵ | ≈ 0 |

> 注：本表为**轻量工作负载**（每 Agent 每回合 ≈1 次调用）外推，低于 `00 §7.2`
> 的满配估（N=20 周 ≈2×10⁶ token，因其假设 42 次/Agent/周 且含更长对话/反思）。
> 若计费，费用 = `token × 单价`；`172.16.3.41:31809` 为内网服务，预估无按量计费（待用户确认）。
>
> ⚠️ 上表两套口径（轻量/满配）**仅作量级参考，均非准数**。
> **准确成本需以真实 LLM × N=20 × 完整一周实测为准。**

### 4.6 LLMBudget 安全阀默认值（防跑飞）

用户已明确"可随意使用"，故不设预算审批门槛；但闸门**默认开启**作为安全阀
（真实 LLM 单次最长 ~14s、耗时是 rule-based 的 ~3600×，一次误跑可能数小时）：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `call_limit`（单次 run 总调用） | **20000** | 覆盖 N=20 × 12 周满配仍有余量 |
| `round_call_limit`（单回合调用） | **60** | N=20 满配约 10–25 次/回合 |
| `limit`（成本单位） | 不限（None） | 不计费则无需成本闸；开启时注入 |

触顶行为：沿 `T2→T1→T0` 降级并记 `LLM_CALL(degraded=true)`；`T0` 为确定性兜底、
**零 LLM 调用**；优先级 `CRITICAL`（濒死求生）可绕过。实现见
`freeze.budget.default_safety_budget()`（`build_default_client` 默认启用）。

### 4.5 事件量/耗时相对 rule-based 的变化

- **LLM 相关事件数不变**（同为 33 条 `LLM_CALL`）——冻结层对事件结构无侵入。
- **耗时显著上升**：40.43 s vs 0.011 s ≈ **~3600×**；N=20 满配下串行每周可分钟级到小时级，
  建议保留并发/批处理与 `LLMBudget` 闸门。
- **token 从 0 变为真实 4,342**（rule-based 无真实 token 消耗）。

---

## 5. thinking 策略（用户明确要求，已落地为 config 一等参数）

| 场景 | `thinking` |
|---|---|
| AI 居民常规决策与对话（T1：协商/回信/计划/反思/重要性） | **false**（求快） |
| 软判定层 `judge` / 叙事层 `narrate`/`describe` | **true** |
| T2 重大战略决策（投资/结盟/濒死求生） | **true** |

- 实现：`freeze.config.ThinkingPolicy`（`default=false`；`true_purposes={judge,narrate,describe}`；
  `true_tiers={T2}`），**集中裁决、不散落硬编码**；`FreezeConfig.thinking_flag(purpose,tier)` 暴露。
- provider 侧：`OpenAICompatProvider` 据 `extra["thinking"]` 注入
  `chat_template_kwargs={"thinking": bool}`（`POST /v1/chat/completions`）。
- **缓存键**：`thinking` 已进 `params`（连同 `model`/`tier`/`engine_version`/`prompt_hash`）——
  同 prompt 不同 thinking → **不同缓存键**（防止错命中导致回放拿到不同质量回答）；有单测覆盖。
- **engine_version 指纹**：`FreezeConfig.engine_version_with_policy()` 将策略指纹
  （`sha256:…16`）折入 `engine_version`（本次真跑 `engine_version=v1.1-rim-run|thinking=…`）。

---

## 6. 接口调整清单（与 kernel-dev 对齐）

- `OpenAICompatProvider`：新增 `max_retries`（默认 2，仅对 429/5xx/超时重试）、`calls`/`http_attempts` 观测计数、`chat_template_kwargs.thinking` 注入。
- `LLMClient.judge`：`_normalize_decision` 去除引号/标点/多行噪声后仍**必须 ∈ envelope.options**（不放宽分支约束）。
- `freeze.providers.provider_from_env()`：环境变量驱动的可插拔工厂（不硬编码厂商/密钥）。
- **IF-2c 审计桥**：`LLMClient(audit_sink=...)`（可选，默认 `None`）——签名
  `audit_sink(kind, payload, round, phase)`，kind ∈ {LLM_CALL, LLM_JUDGMENT, NARRATIVE}；
  **仅 run 回调、replay 不回调**；由 orchestration 接线到 `engine.emit_specs`（Arbiter 仍唯一写入者，ADR-08）。
  使引擎日志可观测 LLM 维度，并从引擎日志断言重放 `llm_calls==0`（kernel-dev 已接线验证）。
- 无阻塞项。

---

## 7. 安全与复现

- 🔐 密钥**仅经环境变量**注入；全仓库扫描确认 **`evidence`/`cache`/代码/日志均无密钥**。
- 报告/证据中端点保留 `172.16.3.41:31809`，**不含任何凭据**。
- 证据文件：`v1.2/real-llm-evidence.json`（含 `LLM_CALL` 汇总、判定四要素、行为抽样、重放结果）。
- 复现：`code/scripts/smoke_real_llm.py`（≤2 次冒烟）、`code/scripts/small_run_real_llm.py`（N=3×10）。

### 待确认
- (1) `172.16.3.41:31809` 是否计费？若计费给预算上限，我设 `LLMBudget` 闸门（安全阀默认已开，见 §4.6）。
- (2) **真实嵌入未验证**：`EMBED_API_BASE/MODEL` 未配置，本轮**跳过真实嵌入**（嵌入冻结由 Mock 确定性单测覆盖）→ 见 **§8（T48 嵌入验证）**。

---

## 8. 嵌入验证（T48 · 第一步零费用探测）

> 为什么重要：记忆流检索三因子之一 `relevance` 依赖嵌入。当前嵌入为 Mock/占位，
> 意味着「记忆检索的相关性」是**假的**——Agent「想起相关往事」尚不成立，会影响
> 行为可信度与后续 A 线训练数据质量。

### 8.1 探测结论（零费用，未产生实质调用）

| 探测项 | 方式 | 结果 |
|---|---|---|
| 端点是否列出嵌入模型 | `GET /v1/models` | ❌ 仅 `DeepSeek-Flash`（vLLM，`root=DeepSeek-V4.1-Flash-0910`，`max_model_len=1048576`），**无嵌入模型** |
| 端点是否支持 `/embeddings` | `POST /v1/embeddings`（单次，模型名 `DeepSeek-Flash` / `text-embedding-3-small`） | ❌ 两者均 **HTTP 404** → **端点不支持嵌入** |
| 独立嵌入端点 | `EMBED_API_BASE/MODEL` 环境变量 | ❌ 均为空 |
| 本地嵌入模型 | `sentence_transformers` / `torch` / `transformers` | ❌ `torch` 未装、`sentence_transformers` 未装、`transformers` 装了但 **PyTorch 缺失**、无 HF 缓存 → **当前不可用** |
| 仓库现状 | `code/config/llm.json`、`engine_version.json` | `llm.json.embed_model="text-embedding-3-small"`（**占位**）；`engine_version.json` 已登记 `embedding={"model":"frozen://hash-embed-v1","version":"v1","frozen":true}` |

**结论：该内网端点不支持嵌入；本地嵌入模型当前不可用。** → 需走替代方案。

### 8.2 替代方案对比

| 方案 | 可得性 | 语义保真度 | 复现性 | 依赖 | 评价 |
|---|---|---|---|---|---|
| ① 本地 `sentence-transformers`（如 `all-MiniLM-L6-v2`/`bge-small`） | ⚠️ 需装 `torch`（大依赖）+ 下载权重；网络/离线可下行性**未验证** | **高**（真语义） | 好（版本冻结后确定） | torch/transformers/HF 权重 | 质量最佳但**当前不可用**，成本高、需联网 |
| ② **确定性哈希嵌入**（token 级 feature hashing，`frozen://hash-embed-v1`） | ✅ 零依赖、即刻可用 | **低**：仅**词面/词袋**相似度，**丢失语义**（同义/改写不命中） | **优**（纯确定性、逐位可复现） | 无（标准库） | **推荐兜底**（已在 `engine_version.json` 登记；需明确标注保真度损失） |
| ③ 降级为词法检索（BM25/关键词）替代嵌入 | ✅ 零依赖 | 低（同 ②，偏词法） | 优 | 无 | 与 ② 近似，可作为 relevance 的确定性近似 |
| ④ 外部嵌入 API | ❌ 无凭据；且付费 | 高 | 好 | 网络/凭据 | 不采用 |

**推荐：方案 ②（确定性哈希嵌入）作为兜底**，并以方案 ① 作为**未来升级项**（接口已可插拔：
`EmbeddingFreezer` 只依赖 `provider.embed()`）。**必须在报告与代码注释中明确标注：**
> ⚠️ **保真度损失**：哈希嵌入只保「词面/词袋」相似度，**不具备语义相关性**——
> 同义改写、跨表述的「相关往事」不会被检索到；`relevance` 因子退化为**词法近似**。
> 真实语义相关性**未验证**，需以方案 ① 或真实嵌入端点补测。

若采用 ②，实现建议从当前 `MockProvider` 的**纯随机向量**升级为 **token 级 feature hashing**
（对文本分词→哈希到固定维度→累加→L2 归一），使「词面重叠高的文本」向量更接近，
比随机向量更有意义，且仍零依赖、可复现。

### 8.3 对冻结 / 复现的影响

- **嵌入模型名/版本已在 `engine_version` 指纹**：`engine_version.json.embedding = {model, version, frozen:true}`（对齐 00 §5.3 AR-C5 / 08 §5.4 D7-6）。
- **换嵌入模型 → `engine_version` 变 → 旧日志/旧缓存重放被拒**（**预期行为**）：
  重放要求 `engine_version` 一致；切换嵌入模型是复现输入变更，必须**显式换版本**，
  旧运行需用旧版本重放。**此点需在文档明说**（避免误判为 bug）。
- 嵌入结果**落盘冻结、重放不重算**（`EmbeddingFreezer` 已实现），故重放对嵌入模型无调用。

### 8.4 与 `llm.json` 里 `embed_model` 的关系

`llm.json.embed_model` 目前为占位 `text-embedding-3-small`（指向不存在的端点）。应改为
**与所选方案一致的标识**（采用 ② 时改为 `frozen://hash-embed-v1`），并保持与
`engine_version.json.embedding` **同源一致**（同一 model/version，避免指纹漂移）。

### 8.5 第二步：已采纳方案②并落地（确定性词法相关度）

**裁决（Leader）**：方案② 采纳，但**定性为「确定性词法相关度」而非"降级嵌入"**——它
**可解释、可审计**（能说清「为什么想起这条记忆」= 词面/标签重叠），与「证据优先」取向一致；
且当前 Mock 是**纯随机向量 → `relevance` 现等于噪声**，本步是**净改善**。

- **命名（已落地）**：`frozen://lexical-relevance-v1`（`LexicalProvider`）。
- **实现**：token 级 feature hashing（ASCII 词 + CJK 单字 + CJK 双字 bigram → 哈希到 256 维 → L2 归一），
  零依赖、可复现；`freeze.relevance.RelevanceRanker` 提供确定性 top-k（同分按 index tie-break）。
- **配置对齐**：`config/llm.json.embed_model = frozen://lexical-relevance-v1`；
  `config/engine_version.json.embedding = {model: frozen://lexical-relevance-v1, version: v1, frozen: true}`。

#### A/B 检索命中对比（同一记忆集，8 条；query=「关于锄头的约定」）

| rank | **lexical（方案②）** | score | jaccard | **mock 随机（现状）** | score | jaccard |
|---|---|---|---|---|---|---|
| 1 | 老李上周托我修一把**锄头**，约定这周去集市取 | 0.263 | 0.143 | 今天晴朗，广场晒谷物 | 0.922 | 0.023 |
| 2 | 我把修好的**锄头**还给老李 | 0.210 | 0.108 | 我向银行申请小额贷款 | 0.916 | 0.000 |
| 3 | 图书馆读木工手艺的书 | 0.188 | 0.098 | 我还锄头给老李 | 0.840 | 0.108 |

- **lexical**：top-2 **全部命中相关记忆**（idx 0/7），且 score 与词面重叠（jaccard）**正相关**、**可解释**。
- **mock 随机**：top-1/2 为**无关**记忆（晒谷物、银行贷款），score 与相关性**无关** → **`relevance` == 噪声**。
- 证据文件：`v1.2/embedding-ab-evidence.json`（含 `real(P1)` 占位，标 `not_available`）。
- **净改善结论**：lexical 相对现状（随机）显著提升检索可信度；但**仍非语义**（见下保真度损失）。

#### 保真度损失（三处已同步标注）

> ⚠️ **真语义相关性未验证；当前为词法近似。** 哈希/词法相关度只保**词面/词袋**相似度，
> **同义改写、跨表述的「相关往事」不会被检索到**。

已写入：① 本报告 §8；② `glossary/LEXICON.md` 的 `relevance` 词条；③ `v1.2/01-implementation-architecture.md §6.1` 风险 **R-12**。

### 8.6 方案①（P1 升级项）代价评估 —— 供用户决策"是否值得装本地嵌入模型"

| 项 | 估计 | 说明 |
|---|---|---|
| 依赖体积 | **torch CPU wheel ≈ 0.2–0.5 GB**（含 CUDA 版可 >2 GB） | 当前**未安装**；`transformers` 已在但无 PyTorch |
| 模型权重 | MiniLM-L6 ≈ 90 MB；bge-small-zh ≈ 95 MB；bge-m3 ≈ 2.2 GB | 需从 HF 下载 |
| 安装/加载 | 安装 1–5 min（取决网络）；首次加载模型数秒 | **联网/离线可下行性未验证** |
| 运行时 | CPU 编码短文本 ~ 数 ms–数十 ms/条 | 批处理更优 |
| 风险 | 重依赖 + 联网失败 + 版本漂移 | 会**改变 `engine_version`**（旧日志/缓存重放被拒，预期） |

**接口已预留可插拔**：`EmbeddingFreezer` 只依赖 `provider.embed()`；A/B 模板
`code/scripts/embed_ab_compare.py` 已支持「真嵌入端点在位即并入对比」，一旦方案①就绪即可出
`lexical vs 真嵌入` 的命中对比，作为用户决策依据。

### 8.7 复现行为确认

换相关度算法 → `engine_version` 指纹变 → **旧日志/旧缓存重放被拒**，属**预期行为**
（重放要求 `engine_version` 一致；切换相关度算法是复现输入变更，必须显式换版本）。
文档已说明（本节 + `engine_version.json` 的 `embedding.note`）。

### 8.8 待办 / 待对齐

- **`life/memory.py` 仍硬编码 `version="frozen://hash-embed-v1"`**（非本模块）→ 请 life-layer-dev/kernel-dev
  对齐为 `frozen://lexical-relevance-v1`，或改为从 `engine_version` 读取，避免指纹漂移。
- 真嵌入（方案①）待用户决策后作为 P1 接入并补 A/B 证据。

---

## 9. IF-2c 审计桥端到端验证（T53 · 真 LLM 经引擎）

> 缺口：freeze 的 `LLM_CALL/LLM_JUDGMENT/NARRATIVE` 原先只写 freeze 自己的 EventLog，
> **未回流内核账本** → 引擎日志里 LLM 事件为 0、无法从引擎日志断言重放零调用、审计链不完整。

**修法（已落地）**：`freeze.LLMClient` 新增可选 `audit_sink`（默认 None，向后兼容）；
**仅 run 回调、replay 不回调**；orchestration 接线 `engine.emit_specs` → 本回合缓冲 → P6 唯一 append（ADR-08）；
freeze 不 import 内核、Arbiter 仍唯一写入者。签名 `audit_sink(kind, payload, round, phase)`。
（另：`judge` 决策解析增强——支持模型返回 JSON/包裹文本，仍强制 `decision ∈ envelope.options`。）

### 9.1 实测证据（真 LLM × N=3 × 10 回合，引擎日志）

脚本：`code/scripts/t53_audit_bridge_evidence.py`；日志：`logs/t53_real.jsonl`。

| 验收项 | 结果 |
|---|---|
| 引擎日志 `LLM_CALL` | **14** ✅ |
| 引擎日志 `LLM_JUDGMENT` | **2** ✅（四要素：decision/model/context_digest/frozen=true） |
| 引擎日志 `NARRATIVE` | **1** ✅（`affects_state=false`） |
| **从引擎日志重放 `llm_calls`** | **0** ✅（replay_records 全程不触发 provider；`replay_parity=True`，`first_run_equals_replay=True`） |
| census（`obs.llmcost`）LLM 维度 | `calls=14, tokens_in=757, tokens_out=2671, cached=5, thinking=3` ✅ |
| 密钥/端点入日志 | **否**（`leaked_key=False`、`endpoint_in_log=False`）✅ |
| `SYSTEM_ERROR` / 守恒违反 | 0 / 0 ✅ |

`LLM_CALL` 按 purpose：`plan/importance/judge/describe` 均入引擎账本；`thinking` 标志随 payload 落账（judge/narrate=true）。
> 说明：life 骨架主循环暂未调用 `judge/narrate`，本证据由驱动脚本在**回合内**（软判定层/叙事层的调用点）触发，以覆盖三类事件——即审计桥对所有 LLM 事件类型均已打通。

### 9.2 向后兼容（rule-based / Mock）

`python -m orchestration run --life`（默认 Mock，离线）：引擎日志 **`LLM_CALL=5`、`SYSTEM_ERROR=0`、`replay_parity=True`** —— 行为不变 ✅。

### 9.4 审计事件 round 语义闭环（T55 回归）

审计事件必须携带**真实当前回合**，否则会污染 `apply_event` 的 `state.round`、破坏 `TURN_SEAL`。
三层保障（已闭环）：
- **freeze**：`FreezeLLM.call` 从 `meta["round"]` 取 round（life 的 plan/reflect/importance 均带）。
- **kernel sink（权威兜底）**：`_make_audit_sink` 用 `engine.state.round` 覆盖传入 round（忽略脏值）。
- **kernel apply_event（单调不减）**：`if record.round >= state.round: state.round = record.round`，即使来脏 round 也不回拨。
- 回归测试：`tests/test_llm_audit_bridge.py`（含 T55 用例）；离线复现脚本 `code/scripts/verify_round_fix.py`。

### 9.5 Mock judge 合法性修复（T54 联调）

`MockProvider` 在 `judge` 上曾返回 `mock::<hash>`（不在 `envelope.options`）→ `InvalidDecisionError` →
整回合回滚 + `SYSTEM_ERROR`（阻塞 rule-based 验收）。修法：`judge` 把 `envelope.options` 经
`extra["options"]` 传给 provider；`MockProvider` **确定性地**从 options 中选一个
（`options[sha256(system,user) % len]`，可复现），真实 provider 不变；`_normalize_decision` 仍强制
`decision ∈ options`。回归：`seed=42/7 × n=3 × 84 回合` → `SYSTEM_ERROR=0`、`LLM_JUDGMENT=8`。

### 9.6 T59：真 LLM 跑下 judge/narrate(thinking=true) + mock↔真 LLM 分叉（T54-② / T57-①）

真实 provider（`openai_compat` / `DeepSeek-Flash`）经 **life 自然主循环**（T54 接入 soft.judge/narrate）跑
seed=42 × N=3 × 84 回合（独立 `--side-root`）：证据 `v1.2/evidence/t54_real_llm_judge_evidence.json`。

| 项 | 真 LLM | Mock |
|---|---|---|
| `LLM_CALL` / `LLM_JUDGMENT` / `NARRATIVE` | **63 / 20 / 3** | 58 / 15 / 3 |
| `SYSTEM_ERROR` | **0** | 0 |
| replay parity / first_run==replay | True / True | True / True |
| **`state_hash`** | `sha256:9790a87f…f193e` | `sha256:08d379a1…1104` |

- **judge/narrate 且 thinking=true**：`judge=20 次（thinking=true 20）`、`describe(=narrate)=3 次（thinking=true 3）`；
  抽样：`r0 judge T2 DeepSeek-Flash thinking=true tok 155/332` 等。plan/reflect/importance 均 thinking=false。
- **LLM_JUDGMENT**：20 条，四要素齐全、`decision ∈ envelope.options`（如 `weekly_focus ∈ {work,social,study,leisure,balance}`）。
- **成本**（by_purpose 分列，首次出现 judge/describe）：总 calls=63、tokens_in=10401、tokens_out=11685、thinking=23、cached=10；
  `provider_guard(openai_compat) ok=True`（仅该 provider 计数、无 mock 混入）。
- **mock ↔ 真 LLM `state_hash` 不同**（T57 落地后期望值）：归因 **`weekly_focus` 冻结标签** → **`SCHEDULE_PLANNED`**：
  真 LLM `weekly_focus` = [P001:leisure, P002:work, P003:social]；mock = [P001:balance, P002:work, P003:balance]；
  计划 slot `activity_type` 分布随之分叉（真: socialize22/leisure7/civic4/learn7 vs mock: socialize20/leisure5/civic7/learn8）。
  `GOAL_SET` 种类一致（非 LLM 驱动）。
- 密钥零泄漏（`key_leak=False`）；`pytest -q -p no:randomly` → 210 passed。

### 9.3 回归

`pytest -q` → **189 passed**（冻结层 `tests/test_freeze.py` 37 passed）。
（注：中途观察到他人模块 `obs` 一次瞬时红，单跑即 3 passed——并发编辑中间态，与本改动无关。）

---

## 9. 缓存污染事故教训（obs-stats-dev，T42 ③ 段）— **方法论必读**

> 触发：T42 三段对比的 ③（真实 LLM）段。本条由 obs-stats-dev 追加（Leader 2026-10-10 要求固化为方法论教训）。

### 9.1 事故

③ 段复用了与离线测试**共用的 FREEZE 响应缓存目录**，其中混存 `mock` 与 `openai_compat`
两种 provider 的响应 → 该段**实际命中 `mock` 响应、根本没走真 LLM**，却**从结果看不出破绽**，
一度得出**错误结论**：「真实 LLM 与 rule-based 的 20 类语义命中集合完全相同（均 5/20）」。

**更正后（独立缓存强制真实调用）**：rule(N10)=**5/20** → real-LLM(N10)=**7/20**
（新增 `E3_combat_training`、`E17_power_conflict`）。**真实 LLM 确实改变了宏观语义命中集合。**

### 9.2 根因

1. **缓存键不含 provider 身份**（`prompt_hash` 未纳入 provider）→ 仅 provider 不同时**跨 provider 命中**。
2. **缓存目录跨 run 复用且未分区**（离线/调试/正式 run 共用）。
3. **无运行级 provider 断言**：run 结束无「本次全部由 X 服务」的校验/输出 → **静默**发生。
4. **结果不可辨识**：两种情况下命中集合可能相同，下游指标看不出破绽。

### 9.3 如何避免（硬要求）

1. **缓存按 provider 分区 / 键内纳入 provider**（freeze 层落地）：目录 `freeze_cache/<provider>/…`
   或 `cache_key=H(provider, model, prompt_hash, thinking, …)` → **跨 provider 命中结构上不可能**。
2. **运行级 `served_by` 断言**：每次 run 输出 `by_provider`；真 LLM 计划**显式断言**「预期 provider 计数 > 0 且无 mock 混入」。
   - 观测侧守卫已提供：`obs.llmcost.check_provider(cost, expected)`；
     CLI：`python -m obs llm-cost --cache-dir <dir> --require-provider openai_compat`（不满足→**退出码 1**）。
3. **真 LLM 段用独立缓存目录**（不复用离线/他 run 缓存），如 `side_llm_n10`。
4. **报告单列 `by_provider`**，读者据此判断"是否真 LLM"。

> **纪律**：**任何声称"用了真实 LLM"的结论，必须附 `by_provider` 证据且无 mock 混入；看不到 provider 分布 = 不可信。**

### 9.4 ③ 段真实成本（N=10 × 完整一周 × 真 LLM）与解读

| 项 | 值 |
|---|---|
| 调用次数 | **98** |
| tokens_in / tokens_out / 合计 | 17,884 / 17,240 / **35,124** |
| 墙钟 | **227s**（rule 约 26s） |
| provider / tier | `openai_compat`（DeepSeek-Flash）/ `T1` |
| thinking / degraded | **0 / 0** |

**⚠️ 随数附注（防误读）**：98 次**远低于**早先「≈1.1 次/Agent/回合」估算（N=10×84 按此应 ≈900+）；
且**全部 thinking=0、无 judge/narrate/dialogue 类调用** → **软判定/叙事/对话路径在当前 planner 下几乎未触发**。
故这 35k token 是**当前不完整 planner 的真实下限**，**不是**完整实验成本上限。
数据：`v1.2/evidence/llm_cost_n10.json`（含 `by_provider`）。

