# D9t 起跑前置清单（`G0`–`G7` 之外的**执行闸门**，不是判据）

> 性质：**执行前检查表**。不含阈值、不含判定档；只规定"起跑前必须证明什么"。
> 依据：`v2/refs/D9t-prereg-opening-menu.md`（sha256 `954ee2c9…`，`master` ≥ `27b825b`）+ `repro-verifier` V-6 四道自查 + 本线历史事故（`d9s-on` 48.7% 真调用、`d9s-off` 3.7% 缓存重放、`d5c386e` 内容倒退）。
> 作者：TeamLeader｜2026-10-31 08:1x

## 0. 双臂定义（引自预登记 §3，不改）

| 臂 | 配置 |
|---|---|
| `OFF` | **复用 `d9s-on2_n16r24_s42`**（`S-1 + S-2`，`SYNTAX=1`），**不重跑** |
| `ON` | 同上 + `LIFE_PROMPT_NARRATION_OPENINGS=1` |

## 1. 闸门 L1：OFF 臂"复用"必须有内容寻址证明

**这条是整轮的命门。** 预登记要复用旧臂，但旧臂是在**旧代码**上跑的；一旦 OFF 路径有任何一字节差异，"单变量"立刻失效。

必须交：
1. `narration_tail(kind)` 在 `OPENINGS` 未设/`=0` 时的输出，与 `d9s-on2` 那版代码的 `narration_tail(kind)` **逐字节相同**（`kind ∈ {initiate, reply}` 各一份，`==` 实跑，不是"肉眼看着一样"）；
2. 其余进入 prompt 的路径同样逐字节相同（至少：`_dialogue_prompt` / `_reply_prompt` 产出的完整 prompt 在固定 fixture 上 `sha256` 相等）；
3. 若 1 或 2 不成立 ⇒ **OFF 必须重跑**，不得复用。此时预算与串行排期要一并重算。

> 反例：`d9s-off`（191 MSG）当时被当成 OFF 基线，后来查出 `dialogue` 真调用只有 **7/191 = 3.7%**（缓存重放）⇒ 整条对比作废。**复用旧臂必须先证明"同物"，再用"同批"。**

## 2. 闸门 L2：跑批串行与代码冻结

```bash
pgrep -fa "run_batch|integration.py|life.agent" | grep -v pgrep    # 起跑前必须为空
git status --short code/life code/orchestration code/config code/engine   # 跑批期间必须为空
```

- 起跑前 `pgrep` 为空才准起跑（两个臂不许并行）；
- 跑批期间**禁止**改 `code/life|orchestration|config|engine`——中途改一处，两臂就不是同一棵树。

## 3. 闸门 L3：双真跑自证（R-11 四数并列，缺一不得写"100%"）

每臂必须四数并列报：

```
本臂：MSG 数 / dialogue 调用数 / 真调用数(tokens_in>0) / 缓存回放数
例：   183   /        183        /          183            /     0
```

- 真调用判定：`LLM_CALL.payload.tokens_in > 0`（`code/freeze/llm_client.py`）；
- **命中缓存时 `tokens_in = 0`** ⇒ 这是唯一可靠判据；
- 另须 `obs llm-cost` 的实跑输出（rc=0）佐证外部计量。

## 4. 闸门 L4：两臂同 `code_sha` 与同一份输入

- `meta.json` 的 `code_sha` 两臂必须**相同**（ON 是新代码、OFF 复用旧代码 ⇒ 二者 `code_sha` 天然不同，**因此 L1 的等价证明是唯一能替代"同 sha"的东西**，必须显式写进判定件）；
- `n=16 / rounds=24 / seed=42` 与 OFF 臂相同；
- `provider = openai_compat`，`degraded=0`，`dialogue.cached=0`。

> 说明：预登记写的是"同 sha 配对"，而本实验复用旧 OFF ⇒ **等价性证明 = 事实上的同 sha**。判定件里必须同屏写这句，否则读者会认为配对链断了。

## 5. 闸门 L5：服务端与提交纪律（V-6 四道）

```bash
git log --oneline origin/master..master | wc -l                  # 必须 0
git merge-base --is-ancestor origin/master <新sha>; echo rc=$?   # 必须 0
git push origin <新sha>:refs/heads/master; echo "push rc=$?"     # 不用管道
git ls-remote origin refs/heads/master                           # 服务端直读
```

## 6. 闸门 L6：判据表自检

```bash
P='≥10|≤2|≤7|≤8%|≥4|≥1\.0|≥1\.7578|≤50%|≤5%|>5%|<1\.0|<10|>2|>7|>8%|<4|>50%|<1\.7578'
sed '/^## 4\./,/^## 5\./d' v2/refs/D9t-prereg-opening-menu.md | grep -nE "$P" \
  | grep -v '仅示意' | grep -v '见 §4' | grep -v '机械检查' | grep -v 'P='
# 期望 rc=1（无输出）——阈值只在 §4 定义一次
```

## 7. 闸门 L7：G7 的规模前提（A2 写死的限制）

`G7 = 短旁白占比 ≤5%` **只在 `174±10` 片段规模下有效**。起跑后若 ON 臂片段数落在该区间外，**G7 记 `CANNOT-JUDGE`**，不得按同比例外推。

## 8. 起跑前必须能回答的四句（写进判定件件头）

1. **OFF 凭什么等于旧臂**（L1 的三份逐字节证据）；
2. **两臂各跑了多少真调用**（L3 四数）；
3. **`code_sha` 不同时，配对链靠什么成立**（L4 那句）；
4. **G7 的规模是否落在 `174±10`**（L7）。

四条答不全 ⇒ 不出判定件，先补证据。

## 9. 本轮补充（2026-10-31 11:4x，P-A 复核后定稿）

### 9.1 L0 基座闸门（**先于一切**，B-1 的产物）

```bash
grep '^HEAD=' v2/evidence/<OFF臂>/launch_cmd.txt     # 必须与实现分支的基座逐字相同
git merge-base --is-ancestor <该HEAD> <实现分支>; echo rc=$?   # 必须 0
```
⇒ **不读 `launch_cmd.txt` 就宣布"OFF 可复用"= 用一个不知道出处的数字当基线。**（B-1 的成因）

### 9.2 L1 的口径必须写**五元组**

```
(HITT_WORLD_SEED, agent_id, round, role_id, ROTATION 状态)
```

本轮实证：同一棵树、同一 `agent_id=P004`、同一 `round=7`、`seed` 未设，仅 `role_id` 不同：
| `role_id` | 四开 + `OPENINGS` 未设 | 来源 |
|---|---|---|
| `None`（默认 `ROLE_OPENINGS_DEFAULT`） | **200** / `f2c994a1` · **206** / `f50325c7` | Leader + 复核方 |
| `"cook"` | **203** / `6837dc56` · **209** / `fbdabb58` | 实现方旧表 |

⇒ **只写"长度不同"不写五元组，是不可判的争议。** `narration_tail` 签名已含 `role_id`（`f2b3230d` 起）。

### 9.3 L1 的证据形式：`ast` 函数级比对 > "删除行 0"

派件原写"删除行 0"，实测 `cef1c58` 有 **9 行删除**（全是加 `drop_s1` 参数与短路 `ROTATION` 所必需）⇒ **原判据会误杀正确改动**。
改用（`repro-verifier` 提出，采纳）：
```
73 个共有函数：变更 3（narration_tail / syntax_clause / _apply_syntax_clause）
              新增 2（openings_enabled / openings_clause）
              未变 70、被删 0
```
⇒ 更强：同时排除"行数抵消但逻辑被改"。

### 9.4 `drop_s1` 的三句话（判定件必须照写）

1. **是干预的一部分**：`OPENINGS=1` 时 S-1 禁令句**由 OPENINGS 段的轮换要求替代**（预登记 §2 原话即"表述被替换"）；
2. **OFF 路径的 S-1 一字未动**（`S1_CLAUSE` 两版相同，**两条独立证据、均为源码文本口径**：①文本切片 `dc85c62b…`（`grep -A2 "^S1_CLAUSE" | head -3 | sha256sum`）②文本正则 `64405139…`；**运行时对象长度 44、无缩进换行**——不要把运行时值和文本哈希混引）；`drop_s1=openings_enabled()`；
3. ⇒ `OPENINGS=1` 与基线之差 = **S-1 让位（−45 字）+ `openings_clause`（+266 字）+ 示例句回原句（+1/+2）**，**不得单归因给"8 个出口"**。

### 9.5 已复核通过的状态（`master` 侧可引）

| 项 | 值 |
|---|---|
| 实现分支 | `feat/d9t-openings-2 @ cef1c58`（**冻结**） |
| 基座 | `f2b3230d`（产生 OFF 臂的同一 commit） |
| 独立复核件 | `v2/evidence/d9t-cef1c58-PA-verified-by-verifier.md`（`5ca75d76…` / 120 行） |
| 复核结论 | 五项全 PASS + 闸门句"足以支撑两臂配对链" |
| 实测 | 四开 200/206 → `OPENINGS=1` 422/429；`O=1` 时 `R` 无效；`tools/`、`code/config/` 零 diff |
