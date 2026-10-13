# 最短提示词迭代路径（给用户的一页说明）

> 目标：让你**自己就能持续迭代"更人格化"的提示词**。前提（`T356` 已证）：**mock 不读提示词**（按 `hash(system+user)` 从词池选句）⇒ **必须用真 LLM 才有意义**。

## 一、改哪一处（一处一变，可回退）
提示词构建点（按目的）：
- **对话口吻**：`code/life/agent.py::_dialogue_prompt`（`purpose=dialogue`）
- **议价措辞**：`code/life/agent.py::_maybe_negotiate`（`purpose=negotiation`）
- **周计划**：`code/life/agent.py:413` / `_weekly_focus`（`purpose=plan`）
- **反思**：`code/life/agent.py:~560`（`purpose=reflect`）
- **重要性**：`code/life/agent.py:938`（`purpose=importance`）
- **软判定**：`code/life/soft.py::judge` → freeze（`purpose=judge`）
- **叙事**：`code/life/soft.py::narrate` → freeze（`purpose=narrate`）

> 清单与"能改什么/改不到什么"详见 `v2/refs/T356-prompt-inventory.md`。**一次只改一处**。

## 二、怎么跑（在**固定 sha 的副本**上；不脏主树）
```bash
# 1) 造一个固定 sha 的副本（避免混入他人在途改动）
git -C <repo> worktree add /tmp/pi_copy <committed_sha>      # 或用现成 tree=copy 工具
# 2) ⚠️ 载入真 LLM 凭据 —— .env.local 是 gitignored，worktree 副本【不带它】！
#    ⇒ 必须【显式 source 主树凭据】（副本内不放凭据）；否则会出现"无 meta、无 run.jsonl 的假跑"。
set -a; . <repo>/code/.env.local; set +a
# 3) 基线（当前提示词）；PROMPT_ITER_CODE 指向副本 code
cd /tmp/pi_copy/code
PROMPT_ITER_CODE=/tmp/pi_copy/code PROMPT_ITER_COPY_SHA=<committed_sha> \
HITT_LLM_PROVIDER=openai_compat \
python3 <repo>/tools/prompt_iter/prompt_iter.py run v0_real --n 8 --rounds 24 --seed 7
# 4) 改【一处】提示词后：
PROMPT_ITER_CODE=/tmp/pi_copy/code PROMPT_ITER_COPY_SHA=<committed_sha> \
HITT_LLM_PROVIDER=openai_compat \
python3 <repo>/tools/prompt_iter/prompt_iter.py run v1_real --n 8 --rounds 24 --seed 7
# 5) 对照
python3 <repo>/tools/prompt_iter/prompt_iter.py compare v0_real v1_real
```
> **起跑前必核一行**：`out/<tag>/meta.json` 的 `provider` 是 `openai_compat`，**且**运行期有到端点（`config/llm.json`）的**活 TCP 连接** —— 这是"真 LLM 跑没真跑"的唯一判据。

## 三、多久 / 花多少
- **规模**：`n=8 × 24 回合`（约 2 仿真日）——**分钟级**。
- **调用量**：mock 下 24 回合约 ~435 次 `LLM_CALL`；真 LLM 同量级（含缓存命中）。
- **口径**：**改提示词 ⇒ `prompt_hash` 变 ⇒ `cache_key` 变 ⇒ 全部新答案**（与"改配置"同族）⇒ **只与同批 `v0` 对照**，别跨批比；**不得用整周跑批试提示词**，**不污染 `T300`/`T355` 基线**。

## 四、怎么看"深了没"（**可操作判据**，不是"读正文感受一下"）
0. **结构信号（首选，最省读）**：`dialogue` 输出里**"以（…）旁白/舞台提示开头"的占比**、引号/第三人称叙述占比 —— 例：`T362` v0→v1 为 **12/22 → 0/30**（去掉旁白、落到第一人称口语）。
1. **长度/成本分布**：`dialogue` 的 chars p50/p90 与 `tokens_out` —— 区分"话变多"还是"变在角色里"（`T362` 长度 p50 46→39、**没变长**，属后者）。
2. **连续性/来回**：`MSG_DM`/`MSG_PUBLIC` 事件数与连续回合长度（**注：消息事件无话题线/回复指针** ⇒ 结构上只能碎片化）。
3. **至少 1 条"改前/改后正文并排"样例**（同 seed，按 `purpose`+`(agent,round)` 对齐）。
4. **成本并排**：`LLM_CALL` 次数、`cached`、`tokens_in/out`（`T362` 为 +3% 量级）。

**判据适用边界（必写）**：`n=8 × 24r` 属**小样本** ⇒ 以上读数**只作方向、不作结论**；行为族级个位数 delta **可能是噪声**，**不许解释成"有效"**。要做结论须扩 `n`/`rounds` 并复核方差。

> 完整实测（含旁白占比、cost 并排、正文样例、首发事故交代）见 `v2/evidence/T362-real-llm-prompt-iteration.md`。

## 五、铁律
1. **一处一变**、可回退；每版**标版本号**，`meta` 记 `prompt_sha`/`copy_sha`/`provider`。
2. **只在副本上跑**（主树带他人 WIP ⇒ 两个变化混在一起说不清）；跑完**不脏主树**（还原留证）。
3. **"多深算够"由你定** —— 工具只给可对照的读数。
