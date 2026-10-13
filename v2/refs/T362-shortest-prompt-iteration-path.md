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
# 2) 载入真 LLM 凭据（端点/模型走 config/llm.json）
set -a; . <repo>/code/.env.local; set +a
# 3) 基线（当前提示词）
cd /tmp/pi_copy/code
PROMPT_ITER_COPY_SHA=<committed_sha> \
python3 <repo>/tools/prompt_iter/prompt_iter.py run v0_real --n 8 --rounds 24 --seed 7
# 4) 改【一处】提示词后：
PROMPT_ITER_COPY_SHA=<committed_sha> \
python3 <repo>/tools/prompt_iter/prompt_iter.py run v1_real --n 8 --rounds 24 --seed 7
# 5) 对照
python3 <repo>/tools/prompt_iter/prompt_iter.py compare v0_real v1_real
```

## 三、多久 / 花多少
- **规模**：`n=8 × 24 回合`（约 2 仿真日）——**分钟级**。
- **调用量**：mock 下 24 回合约 ~435 次 `LLM_CALL`；真 LLM 同量级（含缓存命中）。
- **口径**：**改提示词 ⇒ `prompt_hash` 变 ⇒ `cache_key` 变 ⇒ 全部新答案**（与"改配置"同族）⇒ **只与同批 `v0` 对照**，别跨批比；**不得用整周跑批试提示词**，**不污染 `T300`/`T355` 基线**。

## 四、怎么看"深了没"
`compare` 输出三类，**只描述、不设阈值**：
1. **行为族 delta**：事件类型计数差 + 首个 `state_hash` 不等回合（**有差/无差都如实**）；
2. **正文并排**：按 `purpose` 抽同 `(agent,round)` 的 system/user/output 并排；
3. **成本/缓存**：`LLM_CALL` 次数、`cached` 命中率。
另附**长度/往复链**读数（见 `v2/evidence/T356-dialogue-depth-baseline.md` 口径）。

## 五、铁律
1. **一处一变**、可回退；每版**标版本号**，`meta` 记 `prompt_sha`/`copy_sha`/`provider`。
2. **只在副本上跑**（主树带他人 WIP ⇒ 两个变化混在一起说不清）；跑完**不脏主树**（还原留证）。
3. **"多深算够"由你定** —— 工具只给可对照的读数。
