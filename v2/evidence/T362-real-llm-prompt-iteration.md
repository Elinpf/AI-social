# T362 — 真 LLM 提示词迭代（v0 vs v1，一处一变）

> 交付物：`v2/evidence/T362-real-llm-prompt-iteration.md`、`v2/refs/T362-shortest-prompt-iteration-path.md`（更新）。
> 回路工具：`tools/prompt_iter/prompt_iter.py`（`1e295fd` 起支持 `PROMPT_ITER_CODE` 指向副本 code）。

## 0. 口径（可复现信息）
| 项 | 值 |
|---|---|
| 树 | worktree 副本 `social-experiment/.worktrees/pi_t362` @ `1ffd7eb`（`copy_sha=1ffd7eb`，`head_sha=1ffd7eb`） |
| provider | `openai_compat`（端点 `http://172.16.3.41:31809/v1`，model `DeepSeek-Flash`）；有到端点活连接=真调用，非 mock 回退 |
| 规模 | `n=8 × 24 回合`，`seed=7` |
| 并发 | **串行、无并行**（`T355` 未起跑 ⇒ 无墙钟污染） |
| 版本 | v0 `prompt_sha=88ddbb92e20029e4`；v1 `prompt_sha=0261445defb9fdca`（**变了 ⇒ 提示词改动已生效**） |
| 变量 | **一处一变**：仅 `code/life/agent.py::_dialogue_prompt`（`purpose=dialogue`）的指令句 |

### v1 的唯一改动（副本内，可逐字回退）
```diff
-                + f"\n场景：{tid}；对象：{others}。请用一句话自然地说点什么。")
+                + f"\n场景：{tid}；对象：{others}。请用一句话说点什么，"
+                  "要贴合你的语气与此刻心情：带一个具体的由头或私心，"
+                  "像是在过日子而不是客套；只写这句话本身，不要旁白、不要引号。")
```
其余（persona 注入、用途、模板、seed、config）**全部不变**。

## 1. ⚠️ 首发事故与重启交代（必须留档，不许只在频道里）
- **首发起跑 16:04 未走完**：`/tmp/t362_v0.log` 0 字节、无进程、产物目录**只有 capture 的 `prompts.jsonl`、无 `run.jsonl`/`meta.json`** ⇒ 无有效结果。
- **根因**：`.env.local` 是 **gitignored** ⇒ `git worktree` 新建副本**不带它** ⇒ 首次启动**未 source 主树凭据** ⇒ 假跑（看起来在跑、其实没接上）。
- **处置**：采用**"显式指向主树路径、副本内不放凭据"**——从主树 `code/.env.local` `set -a; . <主树>/code/.env.local; set +a` 后再跑；副本保持 clean（`git -C pi_t362 status` 空）。首发目录已 `rm -rf`。
- **成本口径（最保守）**：正式耗时/成本**以第二次（16:12 起）为准**；首发**无 meta/无 run.jsonl ⇒ 调用数不可事后核**（产物已清除）；若首发曾发调用，属**同 seed 重复**，**成本上界 ≈ 一次 24 回合的调用量**，且**不假设任何缓存复用**。
- ⭐ **通则（写进流程）**：**新 worktree 跑真 LLM 必须显式 `source` 主树凭据**；否则会出现**"无 meta、无 run.jsonl 的假跑"**。判据：`meta.json.provider == openai_compat` **且**运行期有到端点的活 TCP 连接。

**运行命令（第二次，正式）**：
```bash
set -a; . <主树>/code/.env.local; set +a
export PROMPT_ITER_CODE=<主树>/.worktrees/pi_t362/code PROMPT_ITER_COPY_SHA=1ffd7eb
cd <主树>/.worktrees/pi_t362/code
HITT_LLM_PROVIDER=openai_compat python3 <主树>/tools/prompt_iter/prompt_iter.py run v0_real --n 8 --rounds 24 --seed 7
# 改 _dialogue_prompt 一处后：
HITT_LLM_PROVIDER=openai_compat python3 <主树>/tools/prompt_iter/prompt_iter.py run v1_real --n 8 --rounds 24 --seed 7
python3 <主树>/tools/prompt_iter/prompt_iter.py compare v0_real v1_real
```

## 2. 行为读数（世界层：**基本无差**）
| 指标 | v0 | v1 |
|---|---|---|
| events | 8852 | 8855 |
| TURN_SEAL | 24 | 24 |
| MSG_DM / MSG_PUBLIC / MSG_GROUP | 22 / 8 / 0 | 22 / 8 / 0 |
| 首个 `state_hash` 不等回合 | — | **第 10 回合** |
| 事件族 delta | — | `MEMORY_WRITE` 2788→2790、`OBSERVATION` 2731→2733、`RELATION_CHANGE` 826→827、`PERSONA_DRIFT_CANDIDATE` 17→15 |

**判读**：世界分支由种子化 RNG 决定，LLM **只写措辞**（不产世界状态）⇒ 行为族级 delta 仅为个位数、对话事件数**完全相同**，属**预期**。**诚实结论：行为面无实质差异**（不是"有效"）。

## 3. 措辞读数（`purpose=dialogue`：**结构性变好**）
| 指标 | v0 | v1 |
|---|---|---|
| dialogue 实际调用（未命中缓存） | 22 | 30 |
| 输出长度 chars：p50 / p90 / max / mean | 46 / 64 / 74 / 41.3 | 39 / 61 / 75 / 39.8 |
| **以"（…）"旁白括注开头** | **12 / 22** | **0 / 30** |

**旁白占比 12/22 → 0/30** 是最强的结构性信号：v1 **不再把对话写成第三人称旁白/舞台提示**，落到第一人称的口语。长度**没有变长**（p50 反略降）⇒ 改善**不是"话变多"**，而是"更在角色里、更具体"。

**改前/改后正文并排（同 seed，`dialogue`，节选）**：
| | v0（A） | v1（B） |
|---|---|---|
| 木匠 | `（刨子推过木料，木屑卷起）……手稳，心就稳。` | `这块榆木纹理顺，做榫卯正合适，趁天没黑再刨两下。` |
| 糕点 | `秀娘笑眯眯地递过一块刚出炉的桂花糕：“来，尝尝这个……”` | `小禾，今天试了款新配方的桂花糖糕，你过来帮我尝尝，顺便教教我怎么把糖度调得再稳些。` |
| 郎中 | `（整理着药柜，自言自语）这些药啊，每一味都得记准了分量……` | `刚把晾了三天的艾草收进药柜，手上还沾着那股苦香，倒让我想起该给自己也配副养肝的方子了。` |

## 4. 成本并排（v0 → v1）
| 指标 | v0 | v1 | delta |
|---|---|---|---|
| `LLM_CALL` | 444 | 444 | 0 |
| cached | 197 | 197 | 0 |
| tokens_in | 33515 | 34563 | **+1048 (+3.1%)** |
| tokens_out | 44005 | 45584 | **+1579 (+3.6%)** |
| `dialogue` tokens in/out | 3121 / 833 | 4101 / 886 | in +980（指令变长）/ out +53 |

**判读**：成本几乎不变（+3% 量级），主要来自 dialogue 的 **user 侧指令变长**；输出侧几乎不变。

## 5. 解释边界（**不许越界**）
- `n=8`、`llm_calls≈444`、每版 dialogue 仅 22–30 条 ⇒ **样本量小**。第 2 节的行为族个位数 delta（`MEMORY_WRITE` +2 等）**可能只是噪声**，**不得据此下"行为有变"的结论**。
- 第 3 节的**旁白占比 12/22→0/30** 是**方向性**证据（结构信号明确），但在小样本下**只作方向、不作定量结论**；扩样应复核。
- 本轮**只动了 `dialogue`**；`plan`/`reflect`/`negotiation` 的正文差异是三跑分叉的**下游**（措辞改变了后续上下文），**不单独归因**。
- **无并行、无跨批**：只与**同批 v0** 对照；**不污染** `T300`/`T355` 基线。

## 6. "怎么看深了没"——可操作判据（同步 `v2/refs/T362-shortest-prompt-iteration-path.md` §四）
1. **结构信号（首选，最省读）**：`dialogue` 输出里**"以（…）旁白/舞台提示开头"的占比**（本轮 12/22→0/30）、**引号/第三人称叙述占比**；
2. **长度/成本分布**：`dialogue` 的 chars p50/p90 与 tokens_out（判"变多"还是"变在角色里"）；
3. **连续性/来回**：`MSG_DM`/`MSG_PUBLIC` 事件数与连续回合长度（**注：消息事件无话题线/回复指针**，结构上只能碎片化——见 `T356-dialogue-depth-baseline.md`）；
4. **至少 1 条"改前/改后正文并排"样例**（同 seed，按 `purpose`+`(agent,round)` 对齐）。
- **适用边界**：以上判据在 `n=8` 小样本下**只作方向**；要做结论需扩 `n`/`rounds` 并复核方差。
