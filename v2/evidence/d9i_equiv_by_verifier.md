# D9i 等价性独立核验：`env=0` 时提示词逐字节等价（`repro-verifier`）

> **件头两条（必读）**
> **① 任务载体**：本件依 **Leader 2026-10-30 01:58:10 消息**执行；**所引卡号 `#T-D9I-EQUIV` 在任务库中不存在**（`view_task get` → Task not found；`list(pending)` → No tasks found）。**以消息为准落盘**。
> **② 工作区状态（已确认是有意为之）**：本仓库主工作区**当前不在 master**，而在 `feat/prompt-narration-toggle` @ **`43bbc8a`**；工作区 **dirty**（`M tools/metrics/weather_readings.py`、`M v2/evidence/d3_noiseband_bootstrap.json`、`M v2/evidence/d9f_dr_on_mock_result.md`，另有若干未跟踪目录）。⇒ 本件所有**基准**引用一律用 `git show <rev>:code/life/agent.py`，**不读工作区文件**。

- 作者：`repro-verifier`（第三方，非改动作者）｜2026-10-30｜**只读、不跑批、不改码、只落盘不提交**
- 预登记依据：`v2/refs/D9i-prereg-narration-toggle.md`（`sha256:0555c2c809ad…38eb4eec47f` / 5074 B / 88 行）§1 硬约束 1「`env` 未设或 `=0` 时，prompt 必须与现状逐字节相同」、硬约束 4「默认值必须是 `0`」

---

## 0. 结论（一句话）

**PASS（字符串层）**：`LIFE_PROMPT_NARRATION` 未设或 `=0` 时，两句收尾指令与**改动前**逐字节相同（`initiate` `sha256:3646f049…`、`reply` `sha256:ce2cfb87…`，长度 66 / 72），且该提交**只碰这两处**（`agent.py` **−2 / +27 非注释行**，全部属该机制）。
**未覆盖**：运行时"整串 prompt"未实际构造比对（未起 world）——见 §5。

---

## 1. 方法说明：**为什么基线是 `47a7da9^` 而不是 `merge-base`**

- 引入本机制的提交是 **`47a7da9`**（`feat(d9i): 禁旁白两句收尾指令改为 LIFE_PROMPT_NARRATION 可关（默认0=逐字节等价）`）。"改动前"的准确对象是**它的父提交 `47a7da9^` = `09c69f9`**。
- 若用 `git merge-base master HEAD`（本次为 `b43033e`），diff 会把**分支上夹带的无关提交**一起算进来——实测 `merge-base..HEAD` 的 `agent.py` 差异里含**天气臂**（`from . import weather as WX`、`HITT_WEATHER`、`ctx.weather`）等与 D9i 无关的内容。**用 merge-base 会把"别人的改动"记到 D9i 头上，等价性判断随之失真。**
- 故本件一律以 **`47a7da9^` 作"改动前"基线**，并**只**审 `47a7da9` 这一个提交对 `agent.py` 的改动。

| 版本 | `code/life/agent.py` `sha256` | 行数 |
|---|---|---|
| **改动前** `47a7da9^`（`09c69f9`） | `1221af793446ac48111800c5060ca596b431e35f557c4262b646241d9af24daf` | 1810 |
| **改动后** `47a7da9`（= HEAD `43bbc8a` 同值） | `96b6262751e0cb479b2e39baca6f187e671572c942478b7efd737b0106886820` | 1844 |

## 2. 逐处 diff：两句收尾指令的逐字节比对

比对方式：从 `47a7da9^` 的源码提取两条 `+ "…"` 字面量 → `ast.literal_eval` 得**运行期字符串**；与 `47a7da9` 的 `_NARRATION_TAIL_OFF` 两值直接比较（同为运行期字符串，避免把源码转义当内容）。

| 位置 | 改动前（`47a7da9^`） | `_NARRATION_TAIL_OFF` | 判定 |
|---|---|---|---|
| `initiate`（开场白） | `sha256:3646f04995a961b12573157ccd7dc70fa4fef1828c1415209f197aab0972a77c` · len **66** | **同值** · len 66 | **IDENTICAL ✓** |
| `reply`（接话） | `sha256:ce2cfb8757b1a053b1a9e811e070c7ef91aa3a90cac2c5b6161dff6543ad324d` · len **72** | **同值** · len 72 | **IDENTICAL ✓** |

## 3. 改动范围：**只碰这两处**

`git diff --stat 47a7da9^ 47a7da9 -- code/life/agent.py` → **1 file changed, +36 / −2**；其中**非注释新增行 27 行**（其余为注释/空行），逐行归属：

```
NARRATION_ENV = "LIFE_PROMPT_NARRATION"
_NARRATION_TAIL_OFF = { …initiate/reply 两句（= 改动前字面量）… }
_NARRATION_TAIL_ON  = { …initiate/reply 两句（允许成对括号旁白）… }
def narration_enabled() -> bool: … os.environ.get(NARRATION_ENV, "") in {"1","true","yes","on"}
def narration_tail(kind): table = _NARRATION_TAIL_ON if narration_enabled() else _NARRATION_TAIL_OFF
两处调用点替换： + narration_tail("initiate")  /  + narration_tail("reply")
```
删除的 2 行 = 原来那两句字面量。⇒ **无一处触碰阈值 / 事件结构 / 调度 / 其它提示词措辞**（预登记硬约束 1/2 满足）。

**取值路径**：`narration_tail()` 内 `table = ON if narration_enabled() else OFF`；`narration_enabled()` 只在 env ∈ `{1,true,yes,on}` 时为真 ⇒ **env 未设 / `=0` / 其它值（如 `"2"`、`"off"`）一律走 OFF**。

## 4. `ON` 与 `OFF` 的差异（供"是否顺手改了别的"判定）

两值逐字比对，差异**只在"括号旁白"这一处**：

| | `OFF`（= 改动前） | `ON` |
|---|---|---|
| `initiate` | 「…（一句家常话）：**不要用括号、方括号或星号写动作、神态或心理旁白**，不要解释也不要总结；用口语短句，别反复用同一句口头禅。」 | 「…（一句家常话，**用成对的（）补一句动作、神态或眼前的景，如（把围裙往腰后一掖），但不要写心理独白或旁白叙事，不要用方括号或星号**）：不要解释也不要总结；用口语短句，别反复用同一句口头禅。」 |
| `reply` | 「…（接着刚才的话往下说一句）：**不要用括号、方括号或星号写…**…」 | 「…（接着刚才的话往下说一句，**用成对的（）补一句…如（低头刨木，木屑卷起），但不要写心理独白…**）：…」 |

⇒ 尾巴「不要解释也不要总结；用口语短句，别反复用同一句口头禅。」**原样保留**；`ON` 只把"禁括号"改为"允许成对括号 + 仍禁方括号/星号/心理独白"。**符合预登记硬约束 2（不得顺手改其它措辞）。**

## 5. **我的核验没覆盖什么**（必读，防越读）

1. **字符串层等价 ≠ 运行时整串等价**：本件证明的是"两句收尾指令的运行期取值与改动前逐字节相同"，以及"拼接方式未变"（仍是同一位置 `+ narration_tail(kind)`）。**我没有起 world 实际构造一次完整 prompt 做整体字节比对**——那需要构造 agent/world 上下文，耗时较长。⇒ 若审批要求"运行时整串等价"，须另做一次离线构造比对（不跑批）。
2. **未核 `code_sha` 与已跑臂的对应**：`43bbc8a` 那次提交信息称两臂 `code_sha=47a7da9`；本件**只核代码内容**，是否真有臂按该 sha 跑过，需查 `meta.code_sha`（另有任务负责）。
3. **未核 ON 臂是否真的产生旁白**（那是 `#T-D9I-CODE` 六项读数的事）。
4. **未核 `narration_enabled()` 在其它调用点的影响**：本件只确认两处 prompt 调用点改用它，未做全仓 `grep` 级别的"是否还有别处应改未改"审计（如需要，我可加）。
5. **dirty 工作区**：`tools/metrics/weather_readings.py` 与两份 `v2/evidence/*` 处于修改态，**与 D9i 无关**，但也意味着"当前树"不等于任何已提交版本；本件未依赖工作区文件。

## 6. 复算命令与输出

```bash
# 1) 找到引入机制的提交与其父
git log --oneline -S "_NARRATION_TAIL_OFF" -- code/life/agent.py
#   → 47a7da9 feat(d9i): 禁旁白两句收尾指令改为 LIFE_PROMPT_NARRATION 可关（默认0=逐字节等价）

# 2) 两版本 agent.py 指纹
for r in 47a7da9^ 47a7da9; do git show $r:code/life/agent.py | sha256sum; done
#   → 1221af79…(1810 行) / 96b62627…(1844 行)

# 3) 运行期字符串逐字节比对
python3 - <<'PY'
import subprocess, ast, re, hashlib
def show(rev): return subprocess.run(["git","show",f"{rev}:code/life/agent.py"],capture_output=True,text=True,check=True).stdout
base, head = show("47a7da9^"), show("47a7da9")
lits = re.findall(r'\+\s*("\\n只写台词本身[^"]*")', base)
off  = ast.literal_eval(re.search(r"_NARRATION_TAIL_OFF\s*=\s*(\{.*?\n\})", head, re.S).group(1))
for i,k in enumerate(["initiate","reply"]):
    a,b = ast.literal_eval(lits[i]), off[k]
    print(k, "IDENTICAL" if a==b else "DIFFER", len(a), len(b), hashlib.sha256(a.encode()).hexdigest())
PY
```
**实际输出**
```
initiate IDENTICAL 66 66 3646f04995a961b12573157ccd7dc70fa4fef1828c1415209f197aab0972a77c
reply    IDENTICAL 72 72 ce2cfb8757b1a053b1a9e811e070c7ef91aa3a90cac2c5b6161dff6543ad324d
```

## 7. 判定与不做

- **判定**：`env` 未设或 `=0` 时提示词收尾指令**逐字节等价** ⇒ 预登记硬约束 1/4 的**字符串层**要求 **PASS**；§5 的四项未覆盖须随结论引用。
- **不做**：不跑批、不判六项读数、不判档位（归 Leader）、不改任何被核文件（`agent.py` 与其分支一律只读）。
