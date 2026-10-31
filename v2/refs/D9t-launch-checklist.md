# D9t 起跑前置清单（`G0`–`G7` 之外的**执行闸门**，不是判据）

> 性质：**执行前检查表**。不含阈值、不含判定档；只规定"起跑前必须证明什么"。
> 依据：`v2/refs/D9t-prereg-opening-menu.md`（sha256 `954ee2c9…`，`master` ≥ `27b825b`）+ `repro-verifier` V-6 四道自查 + 本线历史事故（`d9s-on` 48.7% 真调用、`d9s-off` 3.7% 缓存重放、`d5c386e` 内容倒退）。
> **⚠ 本件 sha 随修订变化 —— 引用一律现取，不得照抄旧值**：`sha256sum v2/refs/D9t-launch-checklist.md`
> 修订史（引用旧 sha 时须能对上"那是哪一版"）：
> | sha256（前16） | 时点 | 变化 |
> |---|---|---|
> | `d28d9d00`（本件历史版 sha256sum） | 08:1x | 初版 L1–L7（85 行） |
> | `fa0b9344`（本件历史版 sha256sum） | 12:2x | +§9.1–9.7（L0 基座闸门 / 五元组 / ast 证据 / 分侧证据 / 不对称三分类） |
> | *（不复写自身 sha）* | 12:4x | +本修订表 / §9.7 三分类机械判据（缺件·未采集·结构性）——行内不写自身 sha，避免「改了 sha 就变」的自指循环；该版 sha 见引入它的提交说明 |
> | 现取 | — | 每次修订都会变；判定件只写"现取"，并在此表追加一行 |
>
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

### 9.0 身份口径：一个文件只有一个指纹（本线统一 `sha256sum`）

> **本线统一 `sha256sum`。`git blob sha` 只用于 git 内部翻查，不得作为文件指纹报给人。**
> 现取时必须**连口径一起写**：`sha256sum <path>`。
> 若必须报 blob，写全称「**git blob sha**」，且**不得与 sha256 值并列在同一列**。

实例（本文件自己，同一版本两个身份）：
```
git show origin/master:v2/refs/D9t-launch-checklist.md | sha256sum   → <64 位 hex>。对外口径（每次修订都变，故此处不写具体值）
git rev-parse origin/master:v2/refs/D9t-launch-checklist.md          → <40 位 hex>。git blob（仅供内部翻查）
```
⇒ **「现取」只解决"取最新"，没解决"取哪个函数"**：取错函数，取到的仍是不同东西。
⇒ 与"自我引用 sha 不可能自洽"并列看：一个管**何时取**，一个管**取什么**；两条都写死才算可用。

**自我引用的第三种形态（2026-10-31 实测，`repro-verifier` 指出）**：
> **任何"在文件里写文件自身身份"的动作，都在改变它描述的对象。**
> 实例链：修订史表写自身 sha（立刻过期）→ §9.0 示例嵌自身 sha（一改即失效）→ **补记"本件 v2 = X"**（补记本身就把它变成 v3）。
> 处置：凡在件内标注自身版本，**必须同时写「当前值请现取」**，把"翻译"闭合；否则读者会把"历史上的那一版"当成"现在这份"。

**豁免分级（本线规则，2026-10-31 定）**：`check_citations.sh --strict`（0 待审）强制用于 `v2/refs/` 与判定件；
`v2/evidence/` 作者侧实测件可按"实测值·内容 sha"整体声明。**但豁免只覆盖"我算出来的值"，不覆盖"我引用的证据"**：

| 类别 | 例子 | 是否可豁免 |
|---|---|---|
| **实测值·内容 sha** | 本件自己算出的指纹、读数哈希 | ✅ 可整体声明 |
| **对外引用** | commit sha、`v2/refs/**` 件 sha、他人件的 sha | ❌ **必须逐个可核**（`cat-file -e` 或同行带路径） |

> 判据一句话：**豁免的只是"我的读数"，不是"我引用的证据"**——**引用纪律的全部风险都在后者。**

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
| `None`（默认 `ROLE_OPENINGS_DEFAULT`） | **200** / `f2c994a1`（内容 sha）· **206** / `f50325c7`（内容 sha） | Leader + 复核方 |
| `"cook"` | **203** / `6837dc56`（内容 sha）· **209** / `fbdabb58`（内容 sha） | 实现方旧表 |

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

### 9.6 L3 的证据规格：两侧分开写（**OFF 侧无 `meta.json`**）

实测（`git ls-tree origin/master:v2/evidence/d9s-on2_n16r24_s42/`）：
```
launch_cmd.txt  run.jsonl  run_batch.log  switch_proof.txt      ← 没有 meta.json
```

⇒ L3 的"两臂 `code_sha`"必须**分侧写**，不得写成一格：

| 侧 | 证据 | 取不到时 |
|---|---|---|
| **ON（新臂）** | `meta.json` 的 `code_sha`（应为 `cef1c58`） | 取不到 ⇒ 报**缺件** + 改用 `launch_cmd.txt` 现取 |
| **OFF（复用臂）** | **无 `meta.json`** ⇒ 只有两条：`launch_cmd.txt` 的 `HEAD=f2b3230d` + `switch_proof.txt`（原始 `/proc` 取证） | 记 **`CANNOT-VERIFY（缺件）`** |

**⚠ 术语纪律**：`CANNOT-VERIFY（缺件）` **≠「不可比」**。
- 缺件 = 该字段本就不存在（记录臂的历史形态），**不影响可比性**——可比性由 `cef1c58` 的等价复核（内容 sha·字符串级 `5ca75d76…`，见 `v2/evidence/d9t-cef1c58-PA-verified-by-verifier.md`）承担；
- 不可比 = 两臂分母/口径/实现不同。
⇒ **两者混写会把"没这个文件"读成"这组数据不能用"**，那是过度否定。

### 9.7 判据与证据的"两侧不对称"是本线常态

已出现两次同型：`max_k`（`(d2)` 分母只有 9）、`F-8a`（OFF 侧结构性零）。
⇒ **凡"一臂有、另一臂无"的量，处理方式统一为**：
1. 写明**哪侧缺**、**为什么缺**，按**机械判据**分类（不得凭印象）：
   | 类 | 机械判据 | 例 |
   |---|---|---|
   | **缺件** | `git cat-file -e <path>` rc≠0，或 JSON 里该 key 不存在 | OFF 臂无 `meta.json` |
   | **未采集** | 文件存在但字段为空 / 工具没跑（`obs llm-cost` rc≠0 或未执行） | 没跑 cost 工具 |
   | **结构性** | **分母在机制上不可能非零** ⇒ **必须附代码依据**（哪一行 / 哪个开关决定它只在一侧产生） | `F-8a` OFF 侧 `0/686` |
   > **声明"结构性"必须附代码/事件定义出处，否则一律记"未采集"。**
   > 前两类可机械判（查文件 / key 即可）；第三类**必须给机制出处**——否则"结构性"会变成"我看到是 0 就说是结构性"的借口。
2. 该侧记 `CANNOT-VERIFY`，**另一侧照常报**，不得因一侧缺而整项作废；
3. **不得**把"缺"当"0"，也不得把"缺"当"不可比"。

### 9.8 L2 的具体做法：目录级指纹（`repro-verifier` 提供，采纳）

```bash
# ⚠ 补丁版（repro-verifier 2026-10-31 自我更正 b421b645（内容 sha·自件件头））：必须先证明"数到了文件"
FP() {
  local dirs="code/life code/orchestration code/config code/engine" n
  n=$(find $dirs -type f \( -name '*.py' -o -name '*.json' \) 2>/dev/null | wc -l)
  [ "$n" -ge 100 ] || { echo "FATAL: FP 只找到 $n 个文件（期望 ≥100）——路径错或不在跑批那份代码上" >&2; return 3; }
  find $dirs -type f \( -name '*.py' -o -name '*.json' \) -print0 | sort -z | xargs -0 sha256sum | sha256sum
}
FP > /tmp/d9t_code_fp_before.txt && cat /tmp/d9t_code_fp_before.txt
# 跑批结束后
FP > /tmp/d9t_code_fp_after.txt && diff /tmp/d9t_code_fp_before.txt /tmp/d9t_code_fp_after.txt && echo CODE_UNCHANGED
```

**两条必须同屏的前提**：
1. **必须在"跑批实际使用的那份代码"上取**（ON 臂 = `cef1c58`）。
   在 `master` 上取只能证明 master 没动，**证明不了跑批那份没动** —— 与 B-1 同一族错（比较对象错）。
2. 跑到一半有人切分支/改文件，`FP` 必然变。**变了就报「跑批期代码被动过」，不得解释成"无害改动"。**

**③ 取指纹前必须先证明"数到了文件"（低于阈值 FATAL，不得输出指纹）。**

> **为什么必须有第三条**：`FP` 在**路径写错 / 目录为空**时不报错，而是输出一个**稳定但无意义**的指纹（实测空目录 = `abcfa6a9…`（实测值·内容 sha），`rc=0`）。
> 跑批前后两次都取这个值 ⇒ `diff` 相等 ⇒ 报 `CODE_UNCHANGED` **假通过**，而且它**长得和真通过一模一样**。
> 阈值依据：当前工作区实测 **121** 个（`cef1c58` 那份只多不少）⇒ 取 **≥100** 留安全余量。
> 三条合起来才闭环：**①比的是对的对象 ②变了会报 ③"什么都没比到"不会被当成"没变"。**

> 与 L2 原条文（`git diff --stat` + `--numstat` + 删除文件数）互为补充：
> `git diff` 证明**已提交**的差异，`FP` 证明**工作区实际被读到的内容** —— 后者才是跑批真正用的东西。

### 9.9 白名单式判定必须复用同一个归属函数（`repro-verifier` 审计 `4611d83c` 后立）

**事故**：给"豁免要付费"新加一道门时，我用 `grep -qE '实测值|内容 sha' 整行` 判定 → 等于把已修好的"整行白名单"漏洞**原样搬回**；
`实测值` 三字在讨论本机制的文档里必然出现 ⇒ **写一句"这算不算实测值？"该行 sha 就自动豁免**。

⇒ **规则**：任何"白名单式"判定（标注/豁免/归属）**必须复用同一个归属函数**（`scripts/_ann.py`），**不得各写一份**。
> **每加一个新判据，就等于多开一扇门——门必须接同一把锁。**

**并新增词频降级（`ADJ=1`）**：`实测值` / `内容 sha` 这类**通用词**，只接受 **token 前后 6 字内的紧邻标注**；
说明文字里出现不算。依据：这类词不可能靠"最近邻"区分"标注"与"提及"。

| 词类 | 归属规则 | 例 |
|---|---|---|
| 低频词（`历史版`/`已废弃`/`非当前版`…） | 最近邻归属（`_ann.py` 默认） | `e23ae53d…（该时点 blob，非当前版）` |
| **高频词**（`实测值`/`内容 sha`） | **仅紧邻 ≤6 字**（`ADJ=1`） | `cafebabe1234`（实测值）✓ ／ 句中出现"实测值"而 sha 在句尾 ✗ |
