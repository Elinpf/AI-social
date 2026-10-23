# D12-E 接线证明（采样择优 best-of-3）

> 分支 `feat/d12e-bestof`（基于 `a977cb0`），commit **`a179bea`**；`LIFE_PROMPT_D12E_BESTOF` **默认 1（关闭）**，`3`=开启。
> 工具：`tools/d12e/wiring_proof.py`（本文件所有 shae 均由它一次跑出，可复现）。

## 0. 改动范围（**5 项 + 1 个证明脚本**，逐条说明）

```
git diff --stat a977cb0 HEAD
 code/freeze/client.py      |   2 +
 code/freeze/llm_client.py  |   6 +++
 code/life/agent.py         |  94 +++++++++++++++++++++++++++++++------
 code/life/d12e_shingles.py |  47 +++++++++++++++++++++++++++
 code/life/llm.py           |   4 +-
 tools/d12e/wiring_proof.py | 113 ++++++++++++++++++++++++++++++++++++++++++++++++
```

| # | 文件 | 作用 |
|---|---|---|
| 1 | `code/life/agent.py` | D12-E 主体：`_d12e_m()`、`_d12e_score()`、`_dialogue_generate()`；仅替换 `_send_reply` / `_initiate` 两个**对话生成调用点**；`ctx.d12e` 落 payload |
| 2 | `code/life/d12e_shingles.py`（新增，**无状态**） | `normalize()` / `shingles()`（8-gram）/ `recent_bodies(wv, limit=16)`；**无模块级状态、无 env 开关、无 remember**；口径镜像 `dialogue_metrics.py::normalize_body` |
| 3 | `code/freeze/llm_client.py` | **仅新增可选参数 `params_extra`**：非空时并入 `params`（→ `prompt_hash`/`cache_key`） |
| 4 | `code/freeze/client.py` | 同上，**仅转发** `params_extra` |
| 5 | `code/life/llm.py` | Protocol 与 `RuleBasedLLM.call` 签名加 `params_extra=None`（忽略） |
| 6 | `tools/d12e/wiring_proof.py` | 本证明脚本（只读） |

> **等价性说明（第 3/4/5 项）**：三处都是**可选参数**，不传 `params_extra` 时 `params` 六个键与接入前**逐字相同** ⇒
> `prompt_hash`、`cache_key`、渲染文本、行为**全部不变**。证据即下节 **T0/T1 三态 sha 与改前登记值逐字相同**（`5cf08593…` / `effc14db…`）。

## 0.1 跑前审查 (A)(B) 两处更新的落实

**(A) 不复制 `l7_structural.py`（已落实）**
- 本臂树（`a977cb0`）**不含** `l7_structural.py`（L-7 结构臂是 `3730240` 才加入，晚于本树）；
- 已改为**新增无状态模块** `code/life/d12e_shingles.py`（47 行，纯函数 `normalize` / `shingles`(8-gram) / `recent_bodies(wv, limit=16)`）：
  **无模块级状态、无 env 开关、无 `remember()`/`plan()`/`enabled()`**；
- 「最近 16 条台词」= 从 `wv.visible_events` **只读倒序**取该 agent 可见的 `MSG_*` body（天然按 `(round, seq)` 顺序），无状态、replay 安全；
- 因此本臂**不存在**「L-7 + best-of-3」双变量的风险。

**(B) 单变量文件范围 = 5 项（已落实，见 §0 表）**
- 逐项对应：`agent.py`（主体）/ `d12e_shingles.py`（新增无状态）/ `freeze/llm_client.py`（仅新增可选 `params_extra`）/ `freeze/client.py`（仅转发）/ `life/llm.py`（Protocol + `RuleBasedLLM` 签名）；
- **写死结论**：**3/4/5 三处在不传 `params_extra` 时逐字节等价 ⇒ T0/T1 的 `prompt_fn_sha256` 与行为不变**；
- 证据：§1 三态渲染 sha（T0 `5cf08593…`、T1 `effc14db…` 与改前登记值**逐字相同**；T3 = T1）。

## 1. 三态渲染 `prompt_fn_sha256`（固定输入；本臂**不改提示词**）

| 态 | 环境 | `prompt_fn_sha256` | 期望 | 判定 |
|---|---|---|---|---|
| **T0** 中性 | 无 | `5cf08593d562dc09fdd42ab289319a819481c4882701407b039fa514ff8293f7` | `5cf08593d562dc09…` | ✅ 逐字复现 |
| **T1** = D12-C | `LIFE_PROMPT_D12C_SPECIFIC=1` | `effc14dbffdb6865aa52d9d8adab9db269ab3b92ae9a1a230a22cab6c0ed73f5` | `effc14dbffdb6865…` | ✅ 逐字复现 |
| **T3** = D12-C + D12-E | 上式 + `LIFE_PROMPT_D12E_BESTOF=3` | `effc14dbffdb6865aa52d9d8adab9db269ab3b92ae9a1a230a22cab6c0ed73f5` | **= T1** | ✅ **与 T1 逐字相同** |

渲染文本 sha（`_dialogue_prompt` / `_reply_prompt` 分开）：
| 态 | dialogue | reply |
|---|---|---|
| T0 | `d78e736266c322329e5f4b36ba2939a87b7957b6c4a30eceda081355fbbcb7c8` | `f390ca2730c674482007803743d9137f26d6b4c851e35b4042e106d3c21872bd` |
| T1 | `b79786a6c7e962952f29014c7366367c9a5412c90b7a291bc97a7dec83d48189` | `745551f27df2c77fc75d066d6bb1c87099b18ef9fd178c17f1282dac20411f7d` |
| T3 | `b79786a6c7e962952f29014c7366367c9a5412c90b7a291bc97a7dec83d48189` | `745551f27df2c77fc75d066d6bb1c87099b18ef9fd178c17f1282dac20411f7d` |

⇒ **T3 与 T1 完全相同**（D12-E 一个字都没改提示词）；T0/T1 与改前登记值逐字相同（未传 `params_extra` 时行为不变）。

## 2. 缓存键自测（mock provider；同 prompt，仅 `sample_index` 不同）

| # | `cache_key` | `cached` |
|---|---|---|
| 0 | `sha256:adc14773b525ab090031e553c093b1219d62163304026d7036926587fd69b554` | `False` |
| 1 | `sha256:e85a8fb04753941b834d6a7fe1397b71cf72a39101f70716a59ed145d8fc6b01` | `False` |
| 2 | `sha256:224e3d7894bacbb8fc6ad2126e84d9604164585e096e2062689d4daa4c1d38b1` | `False` |

- **`n_unique_keys = 3`**（=3 ⇒ 三次采样是**三次真实请求**，不会被缓存吃掉）；
- **`all_not_cached = true**。

## 3. 冒烟（mock，n=4 × 6 轮，`D12C=1` + `BESTOF=3`）

- 12 条 MSG **全部带 `ctx.d12e`**（12/12），`m=3`；
- `group` 形如 `TH-P002-PUB-0-0:0:0:P002`（`thread_id:turn_index:round:from`，**未用 msg_uid、非随机**）；
- `by_purpose`：`dialogue 36`（=12×3，符合"对话 ×3"）、`judge 34`、`importance 15`、`plan 4` —— **后三者未进采样循环**（mock 下与未开 BESTOF 时同量）；
- `chain_ok=True / replay_parity=True` ⇒ `params_extra` 方案**不破坏重放**（cache_key 由确定性 `sample_index` 派生）。

## 4. 结论

三条接线闸**全部 PASS**（`[PASS] ① T3==T1`、`[PASS] ② 渲染文本相同`、`[PASS] ③ 三 key + cached=false`）。
⇒ 可以进入跑批（**等 Leader 放行**）。
