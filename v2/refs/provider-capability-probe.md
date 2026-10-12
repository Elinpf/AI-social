# 内网模型端点能力探测（T208）

> 作者：freeze-layer-dev ｜ 日期：2026-10-12
> 目标：打掉 **M2b（判别式化）** 的未验证前提——本内网端点是否支持
> ① logprobs/top_logprobs、② 受限选择/约束解码、③ 前缀缓存、④ 并发与限流。
> 端点：`http://172.16.3.41:31809/v1`（OpenAI 兼容）｜模型：`DeepSeek-Flash`
> （`GET /models` 显示 `owned_by=vllm-frontend-rs`，`root=/models/DeepSeek-V4.1-Flash-0910`）。
>
> **安全**：密钥**仅从 env 读取**（`set -a; . code/.env.local; set +a`），**未落盘/未入日志/未入本报告**；
> 探测脚本与原始响应均在 **`/tmp/provider-probe/`**，**未改动本项目 `code/`**；未装新依赖、未用外部付费服务。

---

## 0. 结论速览

| # | 能力 | 结论 | 对 M2b 的含义 |
|---|---|---|---|
| ① | **logprobs / top_logprobs** | ✅ **支持** | **置信度回退可行**（可取候选概率）——不必砍 |
| ② | **受限选择/约束解码** | ✅ **支持**（`response_format` json_schema/json_object 生效；`logit_bias` 接受） | M2b 可直接用 **schema 受限选择**，非法输出率≈0 |
| ③ | **前缀缓存** | 🟡 **部分支持**（延迟显著下降→疑似自动；但 `usage` 不返回 `cached_tokens`） | 计算侧疑似省；**账单侧无法确认** |
| ④ | **并发与限流** | ✅ **支持**（≥16 并发 0×429）；上限未触到 | 50 agent 调度**并发可用**；更高并发【未验证】 |

> ⚠️ **最重要的一个非我原计划的发现**：该端点模型是**推理模型**——**若不开 `chat_template_kwargs.thinking=false`，
> 输出预算会被 `reasoning` 吃光**（`content=null, finish_reason=length`）。
> **M2b 的判别式调用必须显式 `thinking=false`**，否则“廉价判别”会退化成“昂贵生成”（正是我们要消灭的成本）。
> 开 `thinking=false` 后，一次受限判定 `completion_tokens=13, reasoning_tokens=0`。

---

## 1. ① logprobs / top_logprobs —— ✅ 支持

**结论**：`logprobs=true` + `top_logprobs=k` 返回每个 token 的 `logprob` 与 top-k 候选及其 `logprob`。

原始响应片段（脱敏）：
```json
"logprobs": { "content": [
  { "token": "We", "logprob": -4.6491514e-06, "bytes": [87,101],
    "top_logprobs": [
      {"token":"We","logprob":-4.6491514e-06},
      {"token":"The","logprob":-13.000005},
      {"token":"我们需要","logprob":-13.250005},
      {"token":"好的","logprob":-15.500005} ] }
] }
```

可复现命令：
```bash
set -a; . code/.env.local; set +a
curl -s "$LLM_ENDPOINT/chat/completions" -H "Authorization: Bearer $LLM_API_KEY" -H 'Content-Type: application/json' -d '{
  "model":"DeepSeek-Flash","temperature":0,"max_tokens":3,"logprobs":true,"top_logprobs":5,
  "messages":[{"role":"user","content":"The capital of France is"}]}' | python3 -m json.tool | head -40
```
（`LLM_ENDPOINT` 见 `code/config/llm.json`；密钥来自 env，勿外泄。）

**M2b 含义**：候选标签的**校准置信度**可经首个生成位的 `top_logprobs` 取得 → **「置信度回退」保留**。

---

## 2. ② 受限选择 / 约束解码 —— ✅ 支持

**结论**：
- `response_format={"type":"json_schema", ...}`：**被接受且生效**——返回严格落在 `enum` 内的 JSON。
  - 6 次 temperature=1.0 抽样，**6/6 合法**（`{"label":"not_formed"}`），`finish_reason="stop"`。
- `response_format={"type":"json_object"}`：**生效**（返回 `{"x": 1}`，可 `json.loads`）。
- `logit_bias`：**被接受（HTTP 200，未报错）**；**是否真正生效【未验证】**（未做 token-id 级对照实验）——
  但受限选择已可由 `response_format` 覆盖，`logit_bias` 非必需。

原始响应片段（脱敏）：
```json
// json_schema（thinking=false）
{"choices":[{"message":{"role":"assistant","content":"{\n  \"label\": \"not_formed\"\n}"},"finish_reason":"stop"}],
 "usage":{"prompt_tokens":28,"completion_tokens":13,"completion_tokens_details":{"reasoning_tokens":0}}}
// json_object
{"choices":[{"message":{"content":"{\"x\": 1}"},"finish_reason":"stop"}]}
```

**非法输出率实测**（prompt-only 约束，无 schema，temperature=0.8，12 次）：
- 输出必须 ∈ `{formed, not_formed}`；**非法 0/12（非法率 0.0）**，12 次均为 `not_formed`。
- ⚠️ 说明：该组样本**多样性低**（全同），故 0.0 是「约束被遵守」的证据，**但不是分布估计**；
  更大温度/更多候选下的非法率仍【未验证】。

可复现命令：
```bash
set -a; . code/.env.local; set +a
curl -s "$LLM_ENDPOINT/chat/completions" -H "Authorization: Bearer $LLM_API_KEY" -H 'Content-Type: application/json' -d '{
  "model":"DeepSeek-Flash","temperature":0,"max_tokens":120,"chat_template_kwargs":{"thinking":false},
  "response_format":{"type":"json_schema","json_schema":{"name":"judge_out","schema":{
    "type":"object","properties":{"label":{"type":"string","enum":["formed","not_formed"]}},
    "required":["label"],"additionalProperties":false}}},
  "messages":[{"role":"user","content":"Judge whether a mentor relation formed. Answer in schema."}]}' | python3 -m json.tool
```

**M2b 含义**：**受限选择可直接落地**——用 `response_format=json_schema(enum)` 强制合法标签，
叠加**硬内核校验（decision ∈ envelope.options）**兜底；prompt-only 路径实测非法率亦为 0（小样本）。

---

## 3. ③ 前缀缓存 —— 🟡 部分支持

**结论**：**疑似自动前缀缓存生效**（同前缀第二次延迟显著下降），但 **`usage` 不返回 `cached_tokens`**，
**账单侧无法确认**是否按缓存命中计费。

实测（同一 ~1806 token 前缀，连续两次）：
| 调用 | HTTP | 延迟(s) | prompt_tokens | cached 字段 |
|---|---|---|---|---|
| #1 | 200 | **0.144** | 1806 | `prompt_tokens_details=null`、无 `prompt_cache_hit_tokens` |
| #2 | 200 | **0.053** | 1806 | 同上 |

- 延迟 **0.144 → 0.053（≈2.7×↓）**，且第 2 次 `prompt_tokens` 未下降 → **计算侧疑似命中缓存，账单口径不变**。
- 【未验证】：是否为 vLLM `enable-prefix-caching`；显式缓存 API；计费是否折减。

**M2b 含义**：对**重复 system prompt** 的降本，**计算延迟侧可信、token 计量侧不可信**；
预算建模请**保守按全量 prompt 计费**。

---

## 4. ④ 并发与限流 —— ✅ 支持（≥16），更高未验证

**结论**：并发 1→16 **全部 HTTP 200，0×429，0 其他错误**；延迟随并发缓慢上升（p50 0.035→0.076s）。

| 并发 | 请求数 | ok | 429 | p50(s) | max(s) | wall(s) |
|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 0 | 0.035 | 0.035 | 0.036 |
| 2 | 2 | 2 | 0 | 0.038 | 0.038 | 0.040 |
| 4 | 4 | 4 | 0 | 0.041 | 0.041 | 0.043 |
| 8 | 8 | 8 | 0 | 0.065 | 0.067 | 0.069 |
| 16 | 16 | 16 | 0 | 0.076 | 0.081 | 0.085 |

- 用短 prompt + `max_tokens=1`，故延迟是**调度/网络**量级；**生成型**负载的并发曲线不同。
- 【未验证】：并发上限（是否 >16 触发 429）、长生成下的限流、是否为排队而非拒绝。

**M2b 含义**：50 agent 的判别式调用**可并发**；建议接入**保守并发池**并**实测生成型负载曲线**后再定上限。

---

## 5. 对 M2b 的直接裁决建议

| M2b 组件 | 依赖 | 裁决 |
|---|---|---|
| **受限选择**（候选标签判别） | ② | **采纳**：`response_format=json_schema(enum)` + `thinking=false`；内核侧再校验 `decision ∈ envelope.options`（不放水）。 |
| **置信度回退**（候选概率） | ① | **保留**：`logprobs`/`top_logprobs` 可用 → 取候选概率做校准；回退阈值可用候选 `logprob` 差。 |
| **成本** | ⚠️ 推理模型 | **必须 `thinking=false`**：否则 `reasoning` 吃光预算（判别退化成生成）。实测受限判定 `completion_tokens=13`。 |
| **账单** | ③ | **保守按全量 prompt 计费**（`usage` 无 cached 字段）。 |
| **调度** | ④ | **可并发**（≥16 无 429）；上限与生成负载曲线待测。 |

**逐条对齐任务裁决规则**：
- 若①不支持→砍置信度回退：**① 支持，故不砍**。
- 若②不支持→只能 prompt 约束 + 校验兜底 + 实测非法率：**② 支持（schema 生效 6/6）**，且 prompt-only 非法率实测 **0/12**（小样本）；
  即便退化到 prompt-only 路径，也有兜底证据。

---

## 6. 未验证项（**不得以推断代替**）

- `logit_bias` **是否真正生效**（仅验证“被接受/200”）。
- 前缀缓存**是否为自动缓存 / 是否计费折减**（仅观察到延迟下降）。
- 并发**上限**与**生成型负载**下的限流行为（仅测 ≤16、短输出）。
- prompt-only 约束在**更高温度/更多候选**下的真实**非法输出率分布**（本组 12 次全同，非分布估计）。
- `top_logprobs` 在 `thinking=false` 下的取值（本次 logprobs 测试未关 thinking，不影响“支持”结论）。

---

## 附：探测脚本位置（临时）
- `/tmp/provider-probe/probe.py`（四项主探测）、`/tmp/provider-probe/probe2.py`（受限选择 + 非法率）。
- 原始响应（脱敏）：`/tmp/provider-probe/raw/*.json`。
- 均为 `/tmp` 临时产物，**未写入项目 `code/`**；如需入库请由编排方决定。
