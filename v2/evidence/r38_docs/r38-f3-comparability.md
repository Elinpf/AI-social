# R38 / F-3 两臂可比性证据块（可原样复算）

- 作者：`repo-scout`（项目现状侦查员），2026-10-31 12:0x–12:1x +0800
- 性质：**只读取证**。未改 `code/life`、`code/orchestration`、`code/config`、`code/engine`；未起跑批。
- 当前状态提示（2026-10-31 12:10 更新）：**ON 臂（`on/`，10:50–11:14，内层 rc=0）已由 Leader 裁定撤销重跑、作为正式证据件保留**；**OFF 臂正在重跑**（12:05 起，全新 `--side-root /tmp/r38_f3_side_off_fresh`）。第 1 节的两臂对比用的是「12:03 的 OFF 回放件」与「11:14 的 ON 真跑件」——**`prompt_hash` 与开关声明是"构造期"事实，不受缓存回放影响**，故 §1–§3 的结论对最终两臂仍然适用；但**读数（F-3 rate）必须等 OFF 重跑收批后重算**，不得引用本文件的两臂 rate。
- 脚本内容寻址：`tools/f3/prompt_hash_overlap.py` sha256 = `1bbb11bcf458b85821d92389c95ef534030593eda79c5b9ab6ce0933d9a7c5d8`

---

## 1. `prompt_hash` 交集复算（核心：证明「只改了一个变量」）

### 1.1 一条可原样重跑的命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/f3/prompt_hash_overlap.py \
  --arm off=v2/evidence/r38_f3_batch/off_INVALID_cached_replay/run.jsonl \
  --arm on=v2/evidence/r38_f3_batch/on/run.jsonl \
  --purpose dialogue
```

（OFF 重跑收批后，把第一个 `--arm` 换成 `v2/evidence/r38_f3_batch/off/run.jsonl` 即可，其余不变。）

脚本语义（`tools/f3/prompt_hash_overlap.py` 头注同款）：读 `LLM_CALL` 事件的 `payload.prompt_hash`，按 `purpose` 过滤，输出每臂 `calls` / `unique`，以及两臂 `set_intersection`（集合口径，推荐）、`multiset_intersection`（`sum(min(count_a,count_b))`）、`only_in_*`、`jaccard`。纯确定性、无时间戳，同输入必得同输出。

### 1.2 实测结果（本轮原样输出，非引用他人数字）

两臂输入：

| 臂 | 文件 | sha256 |
|---|---|---|
| off | `v2/evidence/r38_f3_batch/off_INVALID_cached_replay/run.jsonl` | `0a2932ed3478f60947ada260a4090b56fe3d63bac3f15baf81d04a02136e5b7a` |
| on | `v2/evidence/r38_f3_batch/on/run.jsonl` | `af120876cd314b8f1b31a3f380081374da1c32db863ae4c1c21854bc16410a7f` |

`dialogue` 口径（与 exp-runner 的 191 vs 191 / 交集 38 **复核一致**）：

```
off.calls=191  off.unique=191
on.calls =191  on.unique =191
set_intersection = 38      → 两臂相同的 dialogue 提示词只有 38 条
union            = 344
jaccard          = 0.11046511627906977
only_in_first    = 153     only_in_second = 153
identical_set    = false
```

⇒ **153/191 = 80.1% 的 dialogue 提示词因注入「情绪呼应」那一行而不同**，与 `F3-IMPL-NOTE.md` 的说法一致；相同的那 38 条正是「上一句无情绪线索 / 强度未达阈值 ⇒ 不产 echo」的调用，属**机制设计内的不应变样本**，不是可比性缺陷。

### 1.3 逐 purpose 全表（这是比「只翻一个开关」更硬的证据）

| purpose | off calls | on calls | 交集 | 并集 | 集合是否完全相同 |
|---|---|---|---|---|---|
| dialogue | 191 | 191 | **38** | 344 | ❌（预期不同：开关作用点） |
| judge | 425 | 425 | 425 | 425 | ✅ 完全相同 |
| importance | 1523 | 1523 | 136 | 136 | ✅ 完全相同 |
| negotiation | 7 | 7 | 7 | 7 | ✅ 完全相同 |
| plan | 16 | 16 | 16 | 16 | ✅ 完全相同 |
| reflect | 90 | 90 | **18** | 162 | ❌ 见下 |

**`reflect` 为什么会不同（必须写清，否则会被读成"多个变量"）**：`code/life/agent.py:926-935` 的反思提示词 = `persona.compressed_profile(...) + memory.summary_for_prompt(src_ids)`，其输入是**记忆摘要**，而记忆摘要来自对话正文。⇒ 开关改变对话措辞 ⇒ 下游记忆 ⇒ 下游 reflect 提示词改变。这是**因果链下游传播**，不是第二个独立变量。判据：`judge`/`importance`/`plan`/`negotiation` 四个**同一时刻、同一输入侧**的 purpose 全部逐条完全相同，说明提示词装配路径本身没有任何其它改动。

> 结论句（可直接进报告）：**6 个 purpose 中 4 个逐条完全一致，dialogue 有 80.1% 不同（开关作用点），reflect 有 80.0% 不同（对话→记忆→反思的下游传播，`agent.py:926-935`）。没有第二个独立变量。**

---

## 2. `engine_version` 指纹两臂相同 —— 以及「因此不能靠它证可比性」

### 2.1 事实

| 证据 | off | on |
|---|---|---|
| `WORLD_INIT.payload.engine_version` | `v0.1-skeleton` | `v0.1-skeleton` |
| `WORLD_INIT.payload.config_components`（12 键） | 见下 | 见下 |
| 两臂 `config_components` 逐键比较 | **完全相等（`True`），差异键 `[]`** | 同左 |
| `emotion_echo.json` 是否在 `config_components` 里 | **否** | **否** |
| `LLM_CALL.payload.engine_version` | `sha256:c0090da83282cc836945dc81161373809c843d38be8bd1f829405869ae161c10` | **同值** |
| `meta.code_sha` | `afde63cebe3d25c0836ce4974047d9dafefe4070` | **同值** |

根因在 `code/engine/version.py:18-31`：`FINGERPRINT_FILES` 只含 12 个文件
`default.json / perception_scope.json / topology.json / narrative_weights.json / llm.json / engine_version.json / policy.json / activity_templates.json / social.json / life_v2.json / world_director.json / time.json`，
**不含 `emotion_echo.json`**（该事实由 `code/config/emotion_echo.json` 文件头自述确认：「本文件**不进** `engine/version.py::FINGERPRINT_FILES`，开/关都不改 `engine_version` 指纹」）。

### 2.2 方法论要点（报告可直接引这一句）

> **`engine_version` 指纹相同、`config_components` 相同，不能用来证明两臂可比** —— `emotion_echo.json` 结构上就不在指纹计算范围内，开关翻转必然不改变指纹。**能证明"只改了一个变量"的是 §1 的 `prompt_hash` 逐 purpose 对比 + §3 的开关声明/启动命令，而不是指纹。**

反过来说，这两项相同仍然是**必要条件**：若两臂 `config_components` 不同或 `code_sha` 不同，则必须按 L4 给等价性证明，否则判不可比。

---

## 3. 两臂启动命令逐 token 对比

| 位置 | OFF | ON | 差异判定 |
|---|---|---|---|
| 启动器 | `bash tools/d2/run_batch.sh --out-dir v2/evidence/r38_f3_batch/off --seed 42 --agents 16 --rounds 24 --side-root /tmp/r38_f3_side_off[_fresh]` | `bash tools/d2/run_batch.sh --out-dir v2/evidence/r38_f3_batch/on --seed 42 --agents 16 --rounds 24 --side-root /tmp/r38_f3_side_on` | 仅 `--out-dir` 与 `--side-root`（**必须**不同，否则串味） |
| 环境前缀 | 无（`unset HITT_DIALOGUE_EMOTION_ECHO`） | `env HITT_DIALOGUE_EMOTION_ECHO=1` | **唯一变量** |
| `--seed/--agents/--rounds` | 42 / 16 / 24 | 42 / 16 / 24 | 相同 |
| 前置闸 | `tools/d5/preflight.sh --tag run_batch`（`tools/d2/run_batch.sh:41`） | 同 | 相同 |

`meta.switch_declared` 逐开关对照（**比命令行更可信，因为它由 `emit_run_meta` 在运行期从 `os.environ` 取值**）：

| 开关 | off.raw | off.effective | on.raw | on.effective |
|---|---|---|---|---|
| `HITT_DIALOGUE_EMOTION_ECHO` | `None` | False | **`'1'`** | **True** |
| `HITT_DIALOGUE_REPAIR` | `None` | False | `None` | False |
| `HITT_WEATHER` | `None` | False | `None` | False |
| `LIFE_PROMPT_ADDR_EVOLVE` | `None` | False | `None` | False |
| `HITT_WORLD_SEED` | `None`（解析为 0） | — | `None`（解析为 0） | — |

开关语义（`code/life/emotion_echo.py:63` `ECHO_ENV`；`:32,133`）：`1|true|on|yes` → 开；其它任意值（含 `0/off/空串`）→ 关；**未设 → 跟随 `code/config/emotion_echo.json`（现值 `"enabled": false`）**。
⇒ OFF 臂用 **unset**（而非 `=0`）是正确的：少一个"是否读到旧 env"的怀疑点。

另有 `meta.switch_effective`（从日志结构字段反推，不依赖声明）：ON 臂 `ctx_echo_msgs=110`（`MSG_DM`）、`distinct_signs=[-1]`、`sources=['cue+mood','mood','text','text+mood']`、`tiers=['很强','明显','轻']` ⇒ **日志侧也能证明开关真打开了**，不是只靠声明。

---

## 4. 证据世代：rc 与产物必须同代（两个活体反例）

> **本节唯一可执行纪律（一句话，建议原样进 R1 方法论与所有跑批 SOP）**：
> **「任何退出码必须与同目录产物比 mtime，且 rc 只允许一份、路径唯一。」**
>
> 拆成三条可机械检查的动作：
> ① `rc` 与 `run.jsonl`/`meta.json` **同目录**（`<out-dir>/run_batch.rc`）；
> ② `rc.mtime` 必须**晚于** `run.jsonl.mtime`，且落在 `meta.started_at..meta.finished_at` 窗口内；
> ③ 外层编排脚本**不得**在批根另写一个 `<arm>.rc` —— 若必须有，文件名不得与内层同名域重名（本轮 `on.rc` 与 `on/run_batch.rc` 就是被重名害的）。

### 4.1 反例 A：`off_INVALID_cached_replay/`（rc 与产物相差 75 分钟）

```
2026-10-31 10:48:06  off_INVALID_cached_replay/run_batch.rc     ← 10:21 那次跑留下的 rc
2026-10-31 12:03:26  off_INVALID_cached_replay/run.jsonl        ← 12:03 那次回放写的日志
2026-10-31 12:03:27  off_INVALID_cached_replay/meta.json
```

`meta.started_at=12:03:11 finished=12:03:27 duration=16`（**16 秒**跑完 16×24 回合 ⇒ 只可能是全缓存回放），且按 purpose 拆解 `cached=2252/2252=100%`、`tokens_in=tokens_out=0`（逐 purpose 均为 0）。
⇒ **rc 文件显示 rc=0 成功，但它属于另一次运行**。若只看「rc=0 + jsonl 存在」，会把一次零真实调用的回放当成有效臂。

### 4.2 反例 B：`on.rc`=9 与 11:14 的 ON 产物不同代（本轮最易误判处）

```
2026-10-31 12:03:28  v2/evidence/r38_f3_batch/on.rc       内容=9   ← 12:03 two_arms_serial.sh 的 preflight 失败
2026-10-31 11:14:49  v2/evidence/r38_f3_batch/on/run_batch.rc  内容=0   ← 内层启动器写的，与产物同代
2026-10-31 11:14:47  v2/evidence/r38_f3_batch/on/run.jsonl
2026-10-31 11:14:48  v2/evidence/r38_f3_batch/on/meta.json
```

`/tmp/r38_f3_on.stdout` 尾部：`[preflight] FAIL exit=9 reasons=concurrency:run_batch=1`（外层脚本被自己的 `pgrep -f run_batch` 自匹配，非真实并发）。
`/tmp/r38_f3_timeline.txt`：`on_start=2026-10-31T10:50:15+08:00 HITT_DIALOGUE_EMOTION_ECHO=1 head=afde63ce…` / `on_rc=0 on_end=11:14:49`。
`on/meta.json`：`started_at=10:50:16 finished=11:14:48 duration=1472`，`derived_from_log_sha256` **等于** `run.jsonl` 实际 sha256。
⇒ **同名 rc 文件有两个层级（外层 `on.rc` 与内层 `on/run_batch.rc`），取错层级就会把一次成功的真跑判成失败。** 判据必须写死：**rc 取内层、且 mtime 必须落在 `meta.started_at..finished_at` 之内**。

### 4.3 由此产生的两条可复制纪律（建议进 R1 方法论）

1. **rc 与产物必须同代**：`stat -c '%y %n'` 对比 rc / run.jsonl / meta.json 三个 mtime，rc 必须晚于 jsonl、且落在 `meta.started_at..finished_at` 窗口内；不满足即判「rc 不可归属」。
2. **rc 必须取内层**：`<out-dir>/run_batch.rc` 才是该次跑自己的退出码；`<out-dir>/../<arm>.rc` 是外层编排脚本的退出码，两者不是一回事。

---

## 5. side_root 新鲜度判定法（本轮两次踩坑后的硬口径）

判「缓存有没有可能被跨跑复用」，**不能**只看 `ls <side_root>/responses`（那里根本没有该目录），正确路径与判据如下：

```bash
S=<side_root>
# ① 必须是真目录、不是软链
[ -L "$S" ] && echo "SYMLINK(FAIL)" || echo "real dir"
realpath "$S"                      # 必须等于 $S 自身
find "$S" -type l | wc -l          # 必须为 0

# ② 正确路径是 freeze_cache/responses（orchestration/integration.py:1004 的布局）
ls "$S/freeze_cache/responses" | wc -l

# ③ 关键判据：所有 responses 文件的 mtime 必须落在本次 run 的 [started_at, finished_at] 内
find "$S/freeze_cache/responses" -type f -printf '%T+\n' | sort | sed -n '1p;$p'
```

本轮实证：
- **旧 ON 臂** `/tmp/r38_f3_side_on`：`freeze_cache` 建於 `10:50:16`，865 个 responses **全部**落在 `10:50–11:14` ⇒ 是本轮新写（**不是**跨跑回放）。
- **被污染的 OFF** `/tmp/r38_f3_side_off`：`freeze_cache` 建於 `10:21:42`，865 个 responses 落在 `10:21–10:48`；12:03 那次重跑复用它 ⇒ 100% 回放。
- 盘上「1290 vs 865」不是矛盾：**1290 = 整个 `freeze_cache` 文件数（含 `embeddings/` + `judgments/` + `responses/`），865 = 仅 `responses`**。判空与判新鲜一律只看 `responses`。

## 6. 判据修正：「缓存回放=0」不能按全局 `cached` 判

### 6.1 问题：全局 `cached` 会把正常真跑判成无效

原判据（CYCLE-37 §5.1 第⑥条与 §6 跑批命令注释）要求「缓存回放 = 0」。实测发现这条**按全局 `cached` 计数无法执行**，因为引擎对**同一 prompt 的批内重复调用会命中自己的缓存**，而这是设计内的去重、不是跨跑回放。

按 purpose 拆解 ON 臂（11:14 真跑）：

| purpose | calls | cached | cached% | tokens_in | tokens_out |
|---|---|---|---|---|---|
| dialogue | 191 | **0** | 0.0% | 65747 | 9731 |
| judge | 425 | 0 | 0.0% | 51730 | 98368 |
| reflect | 90 | 0 | 0.0% | 42895 | 5759 |
| negotiation | 7 | 0 | 0.0% | 839 | 279 |
| plan | 16 | 0 | 0.0% | 1447 | 1091 |
| importance | 1523 | 1387 | **91.1%** | 2312 | 37924 |
| **TOTAL** | 2252 | 1387 | 61.6% | 164970 | 153152 |

`importance` 的 91.1% 命中是**同一 prompt 在批内重复调用**造成的天然去重（同一条记忆被反复估重要性），不是跨跑回放——判据：它的 `tokens_in` 只有 2312（≈136 次真调用 × 约 17 token），与 1387 次命中不匹配，说明**首次调用是真的、后续是批内命中**。⇒ 若按「全局 `cached` 必须为 0」判，**任何一次真跑都会被判无效**（新 OFF 臂同样会有 `importance` 批内命中）。

### 6.2 修正后的判据（**两条并列，必须同时满足**；Leader 已下发）

1. **`dialogue` purpose `cached == 0` 且 `tokens_in > 0`** —— F-3 的作用点就在这一 purpose，它必须是真生成；
2. **`side_root/freeze_cache/responses` 的全部文件 mtime 落在本次 run 的 `[started_at, finished_at]` 窗口内** —— 这一条同时否掉「跨跑复用旧 cache」（详见 §5）。

并附**真调用四数同屏**：`MSG` 数 / `dialogue` 调用数 / `dialogue.tokens_in` / **跨跑缓存回放数**（后者按 §5 判定，**不是**全局 `cached`）。

### 6.3 用修正后判据对 ON 臂（11:14）做的独立正式验收

| 判据 | 实测 | 判定 |
|---|---|---|
| ① `dialogue.cached == 0 && dialogue.tokens_in > 0` | `cached=0`、`tokens_in=65747`、`tokens_out=9731` | **PASS** |
| ② `responses` mtime 全落在 `[10:50:16, 11:14:48]` | 865 个文件，最早 `2026-10-31+10:50:19.456`、最晚 `11:14:44.173`，`-newermt 10:50:16 ! -newermt 11:14:49` 计数 **865/865** | **PASS** |
| 附：真调用四数 | MSG_DM 168 + MSG_PUBLIC 24 = 192；`dialogue` 191；`tokens_in` 65747；跨跑回放 **0** | **PASS** |
| 附：`degraded` | 0（全 purpose） | **PASS** |
| 附：内容自洽 | `meta.derived_from_log_sha256` == `run.jsonl` 实际 sha256（`af120876…`）；`wc_l == events == 33853` | **PASS** |

⇒ **ON 臂（11:14）按修正后判据正式验收为 PASS**（我的独立核验，非引用 exp-runner 结论）。

---

## 7. 第三方复核清单（照着跑即可，全部只读）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
S=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① prompt_hash 逐 purpose 交集（§1）
python3 tools/f3/prompt_hash_overlap.py --arm off=$S/v2/evidence/r38_f3_batch/off/run.jsonl \
        --arm on=$S/v2/evidence/r38_f3_batch/on/run.jsonl --purpose dialogue

# ② 指纹与配置组件相同（§2）
python3 - <<'EOF'
import json
def init(p):
    for line in open(p):
        if '"WORLD_INIT"' in line: return json.loads(line)['payload']
a=init('v2/evidence/r38_f3_batch/off/run.jsonl'); b=init('v2/evidence/r38_f3_batch/on/run.jsonl')
print('engine_version', a['engine_version'], b['engine_version'])
print('config_components 相等', a['config_components']==b['config_components'])
print('emotion_echo 在指纹内', 'emotion_echo.json' in a['config_components'])
EOF

# ③ 开关声明与日志侧生效（§3）
python3 -c "
import json
for d in ['off','on']:
    m=json.load(open(f'v2/evidence/r38_f3_batch/{d}/meta.json'))
    print(d, m['switch_declared']['HITT_DIALOGUE_EMOTION_ECHO']['raw'],
             m.get('switch_effective',{}).get('HITT_DIALOGUE_EMOTION_ECHO',{}).get('ctx_echo_msgs'))"

# ④ rc 与产物同代（§4）
stat -c '%y %n' v2/evidence/r38_f3_batch/off/run_batch.rc \
                v2/evidence/r38_f3_batch/off/run.jsonl \
                v2/evidence/r38_f3_batch/off/meta.json
python3 -c "import json;m=json.load(open('v2/evidence/r38_f3_batch/off/meta.json'));print(m['started_at'],m['finished_at'])"

# ⑤ side_root 新鲜度（§5）
find /tmp/r38_f3_side_off_fresh/freeze_cache/responses -type f -printf '%T+\n' | sort | sed -n '1p;$p'
```

---

## 8. 未解决 / 待补

- **读数未出**：OFF 臂重跑收批前，本文件不含任何 F-3 rate，`dialogue` 交集 38 的两臂对比只证明「提示词不同」，**不证明「LLM 接住了」**（`F3-IMPL-NOTE.md` §7 同款边界）。
- **10:21 的原始 OFF 日志已被 12:03 回放覆盖**，现盘上 `off_INVALID_cached_replay/run.jsonl` 是回放件（内容与原始可能同文，但**不满足同代**，不得当原始证据引用）。该事实应由 report-publisher 在方法论节登记。
- **`reflect` 下游传播**目前是**代码结构推断 + 时间序一致**（`reflect` 首次调用 `mono_ts=4120` 晚于 `dialogue` 首次 `52`），**未做逐条因果追踪**（日志里没有「这条 reflection 由哪条 MSG 派生」的显式字段）。标 **未验证**。
