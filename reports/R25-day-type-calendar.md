# R25 · 日历臂「今天是什么日子」：机制接通 + 独立审计盖章

> 角色：evidence-auditor（证据与报告审计师）｜性质：**独立证伪复核 + 报告定稿**，未跑批、未调 LLM、未改实现代码、未动主工作树。
> 审计与定稿时刻：2026-10-23 12:15–12:26 (+08:00)
> 仓库：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment`
> 改动基线 sha：`2a99344ead2e16be15ecd0feb415f250f1e6ce3f`（`master`，2026-10-23T11:56:07+08:00）
> 分支 / worktree：`feat/day-type-calendar` @ `.worktrees/feat-day-type-calendar`
> 实现归属：life-dim-engineer（R2）；本报告对 R2 的每条结论**自行复跑**后才盖章。

---

## 0. 一句话结论 & 审计裁定

`day_type`（workday/weekend）与 `day_of_week`（周一…周日）现在能被写进 `_dialogue_prompt` / `_reply_prompt` 各**一行人话**（如「今儿是什么日子：周六，今天不用上工。」）；开关 `LIFE_PROMPT_CALENDAR` **默认 OFF**，OFF 时两条提示词与 `2a99344` **逐字节一致**（我用**自写独立脚本**复核，两路 sha256 相同）；`engine_version` 指纹与 `code/config/**` **完全未变**。

**审计裁定：`PASS-WITH-CAVEATS`（机制接通，可入库；不得写"生活气息改善"）**

- ✅ 四项硬验证全部独立复跑通过：OFF 全量单测、ON 三态渲染、OFF 提示词 sha 对基线等价、指纹对比。
- ✅ R2 的关键读数（`dialogue b6347529…` / `reply c5148cb5…` / ON `8fe92eb3…` / `792e0a9e…`、N=207+597 单测、指纹 `a8d403bd→213f0f4a`、`engine_version` 未变）**逐条复现，无一处不符**。
- ⚠️ 三处**口径瑕疵**（不影响机制成立，但必须登记，见 §8）：①「ON 每条 +63 字符」不是普适常量（实测 +62~+66，随周几措辞长度变化）；② `tree_fingerprint world` 在**主树**测得 `8f8c1151…`（≠R2 的 `a8d403bd…`），差异来自主树 7494 个未入库文件，R2 的基线口径是"干净树"，我已用 `git archive 2a99344` 独立复现出 `a8d403bd…`，故 R2 基线成立但**引用时必须带口径**；③ 本分支 `reports/README.md` 索引表止于 R20（R21/R22 行缺失，属既有欠账，本轮不替他人补）。

**本轮无任何效果读数**：没跑批、没调 LLM、没有 `obs llm-cost`。**机制接通 ≠ 效果改善**（见 §5）。

---

## 1. 本轮维度与目标

| 项 | 内容 |
|---|---|
| 维度（生活气息维度池 C1） | **「今天是什么日子」**：世界里早就算出了 `day_type` / `day_of_week`（`code/engine/time.py::derive_time`，`code/life/ports.py::TimeCoord` 已透传），但**从未进过任何一条对话提示词**——居民不知道今天是周几、是上工还是歇着 |
| 为什么是它 | 生活气息两个最朴素来源＝「日子有节奏」「日子有差别」。既有 `LIFE_PROMPT_SCENE` 只给了"一天四时段 + 我在哪儿 + 手上做什么"，缺了"今天是什么日子"这一层 |
| 本轮目标（机制层，不含效果） | ① 让两个既有字段以**人话**进两条提示词，且默认 OFF；② OFF 时提示词与 `2a99344` 逐字节一致；③ 不新增真相源、不读墙钟、不发事件、不改 `state_hash`、不碰 `code/config/**` 与 `code/engine/**`；④ 纯函数单测覆盖三种日子状态 |
| 本轮**不做** | 不跑批（存量批在跑）、不出效果读数、不做「日历 + 处境锚」组合臂 |

---

## 2. 改动摘要（3 文件，+393 / −0，全部新增，无删改既有逻辑）

```bash
cd .worktrees/feat-day-type-calendar
git add -N code/life/calendar.py code/life/tests/test_calendar_day_type.py
git diff --stat
#  code/life/agent.py                        |  41 ++++++
#  code/life/calendar.py                     | 125 ++++++++++++++++
#  code/life/tests/test_calendar_day_type.py | 227 ++++++++++++++++++++++++++++++
#  3 files changed, 393 insertions(+)
git diff --numstat
#  41	0	code/life/agent.py
#  125	0	code/life/calendar.py
#  227	0	code/life/tests/test_calendar_day_type.py
git reset -q     # 仅撤销 intent-to-add
```

**内容绑定（审计用，不依赖 commit 即可核对内容）**

```bash
sha256sum code/life/calendar.py code/life/tests/test_calendar_day_type.py
# d742a914af67d50ac706c657b4109df57e480a1842c9eec857e864e8a8650520  code/life/calendar.py
# 07c2b39772435b75081c119b26297bf406187d7a6335bd360903b8c047810d09  code/life/tests/test_calendar_day_type.py
git diff code/life/agent.py | sha256sum
# 22e4ae798c86eb8f578ffdc65e2509d434b4a54667166a9c14cdc3fe5f22855d  -
```

| 文件 | 改动 | 性质 |
|---|---|---|
| `code/life/calendar.py`（新，125 行） | 纯函数：`enabled()` / `render()` / `audit()` / `lexicon_sha256()`；两张固定词表 `DAY_TYPE_WORDS`（workday/weekend 各 3 句人话）、`WEEKDAY_WORDS`（0..6 → 周一..周日）；措辞由 `sha256(agent_id|round|calendar)` 确定性选 | 无副作用纯函数 |
| `code/life/agent.py`（+41/−0） | `from . import calendar as CAL`；`__init__` 增 `self._calendar`（纯审计）；新增 `_calendar_line(wv)`（只读 `wv.time.day_of_week` / `day_type`，字段缺失静默退化）；两条提示词各插一行 `+ self._calendar_line(wv)`；`_ctx_snapshot` 增 `ctx["calendar"]`（仅 ON 时产） | additive，不动既有段落 |
| `code/life/tests/test_calendar_day_type.py`（新，227 行） | 28 条单测：开关 / 三态渲染 / 确定性 / 词表自洽 / OFF 零影响 / ON 只差一行 / 审计 sha 对齐 / 字段缺失退化 | 纯单测，无 LLM |

> **禁改区自查（我复核）**：`git status --porcelain -- code/life code/engine code/config code/orchestration` 在 worktree 只报 `M code/life/agent.py` + 两个新文件；`code/config`、`code/engine`、`code/orchestration` 一行未动。

---

## 3. 独立证伪复核（命令原文 + 输出关键行）

> 复核原则：**不引用实现者的输出**。除 §3.2 的"两把尺子对拍"外，全部数字来自我本轮实跑。

### 3.1 开关 OFF 下的全套单测（三种日子状态 + 零影响）

```bash
cd .worktrees/feat-day-type-calendar/code
env -u LIFE_PROMPT_CALENDAR python3 -m pytest life/tests/test_calendar_day_type.py -q
# 28 passed in 0.18s
env -u LIFE_PROMPT_CALENDAR python3 -m pytest life/tests -q
# 207 passed in 183.13s (0:03:03)
env -u LIFE_PROMPT_CALENDAR python3 -m pytest tests -q
# 597 passed, 1 skipped in 83.57s (0:01:23)
```

- `life/tests` 基线 179（R2 记载）+ 新增 28 = **207**，**0 失败**，与 R2 声称一致。
- `tests`（引擎/编排侧）**597 passed, 1 skipped**，与 R2 声称一致。

### 3.2 OFF 提示词 sha 对 `2a99344` 等价 —— **自写独立脚本，两把尺子交叉对拍**

**独立性声明**：下面脚本由我自写，**未 import `r2_prompt_sha.py`、未复用其常量**，输入按审计口径自行构造（`P003`↔`P007`、`round=62`、`time={slot:"evening", day:5, day_of_week:5, day_type:"weekend"}`，另加 4 个自造 case 覆盖 workday/weekend/周几单侧）。

脚本全文（`/tmp/audit_prompt_sha.py`，只读、不调 LLM、不跑批、不写仓库）：

```python
from __future__ import annotations
import hashlib, json, os, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
from life import dialogue_threads as DT
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel

CONFIG = Path("config").resolve()
MARK = "今儿是什么日子："
CASES = [  # (label, round, slot, day, day_of_week, day_type)
    ("workday_dow2", 13, "morning", 2, 2, "workday"),
    ("weekend_dow5", 5, "afternoon", 5, 5, "weekend"),
    ("weekend_dow6", 62, "evening", 6, 6, "weekend"),
    ("workday_dow4", 30, "night", 4, 4, "workday"),
    ("r2input_r62_dow5_weekend", 62, "evening", 5, 5, "weekend"),
]

def build_agent():
    places = {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}
    personas = load_personas(CONFIG / "personas.json"); persona = personas["P003"]
    k = MiniKernel(seed=7, places=places)
    k._emit("AGENT_BORN", {"agent_id": "P003", "home_place": persona.home_place,
                           "needs_init": persona.needs_init}, phase=0, actor="SYSTEM")
    k._emit("AGENT_BORN", {"agent_id": "P007", "home_place": personas["P007"].home_place,
                           "needs_init": personas["P007"].needs_init}, phase=0, actor="SYSTEM")
    tmp = tempfile.mkdtemp(prefix="audit_side_")
    return LifeLayerAgent("P003", persona, k, side_store=SideStore(Path(tmp) / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peer_names={"P007": "阿禾"})

def prompts_for(agent, rnd, slot, day, dow, dtype):
    wv = SimpleNamespace(round=rnd, visible_events=[], location="market",
                         current_activity=None, inventory=(),
                         time=SimpleNamespace(slot=slot, day=day, day_of_week=dow, day_type=dtype))
    cfg = dict(DT.DEFAULTS)
    history = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=wv),
            agent._reply_prompt("P007", "rel_maintain", history, cfg, wv=wv, turn=1))

def sha(t): return hashlib.sha256(t.encode("utf-8")).hexdigest()

def main():
    print(f"calendar_env={os.environ.get('LIFE_PROMPT_CALENDAR', '<unset>')}")
    agent = build_agent(); out = {}
    for label, rnd, slot, day, dow, dtype in CASES:
        d, r = prompts_for(agent, rnd, slot, day, dow, dtype)
        out[label] = (d, r)
        print(f"[{label}] dialogue_sha256={sha(d)} len={len(d)} mark={d.count(MARK)}")
        print(f"[{label}] reply_sha256={sha(r)} len={len(r)} mark={r.count(MARK)}")
    Path("/tmp/audit_prompt_dump.json").write_text(
        json.dumps({k: {"dialogue": v[0], "reply": v[1]} for k, v in out.items()}, ensure_ascii=False),
        encoding="utf-8")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

跑三路（基线 / 改动后 OFF / 改动后 ON）：

```bash
# (a) 基线：主工作树（HEAD=2a99344，code/life 无改动）
cd social-experiment/code && env -u LIFE_PROMPT_CALENDAR PYTHONPATH="$PWD" python3 /tmp/audit_prompt_sha.py | tail -4
# [r2input_r62_dow5_weekend] dialogue_sha256=b634752921de85824b795675549e63ae527989a4d3ff5930db4d53a02bce24a1 len=343 mark=0
# [r2input_r62_dow5_weekend] reply_sha256=c5148cb59997b5b2ec98ab115e936080a24c132e76a3ac5162394d653a0a55d7 len=363 mark=0

# (b) 改动后、开关 OFF（worktree）
cd .worktrees/feat-day-type-calendar/code && env -u LIFE_PROMPT_CALENDAR PYTHONPATH="$PWD" python3 /tmp/audit_prompt_sha.py | tail -4
# [r2input_r62_dow5_weekend] dialogue_sha256=b634752921de85824b795675549e63ae527989a4d3ff5930db4d53a02bce24a1 len=343 mark=0   ← 与 (a) 相同
# [r2input_r62_dow5_weekend] reply_sha256=c5148cb59997b5b2ec98ab115e936080a24c132e76a3ac5162394d653a0a55d7 len=363 mark=0   ← 与 (a) 相同

# (c) 改动后、开关 ON（对照）
cd .worktrees/feat-day-type-calendar/code && LIFE_PROMPT_CALENDAR=1 PYTHONPATH="$PWD" python3 /tmp/audit_prompt_sha.py | tail -4
# [r2input_r62_dow5_weekend] dialogue_sha256=8fe92eb39bfd9bbf26676e2014caf9250f8109bc3a39ec0df835c59f80d199ba len=406 mark=1
# [r2input_r62_dow5_weekend] reply_sha256=792e0a9e8601b97e4ae52b792802f67a58c174939723c077f4bb1d2c1ac91c7f len=426 mark=1
```

**逐字节对拍（5 个 case，全量 JSON 比对，不只看 sha）**

```
=== A. master(OFF) vs worktree(OFF) 逐字节 ===
all_equal= True cases= 5
=== B. worktree(ON) 减行 == worktree(OFF) 逐字节 ===
workday_dow2: dialogue_strip_equal=True reply_strip_equal=True marks=1,1
weekend_dow5: dialogue_strip_equal=True reply_strip_equal=True marks=1,1
weekend_dow6: dialogue_strip_equal=True reply_strip_equal=True marks=1,1
workday_dow4: dialogue_strip_equal=True reply_strip_equal=True marks=1,1
r2input_r62_dow5_weekend: dialogue_strip_equal=True reply_strip_equal=True marks=1,1
=== C. ON 相对 OFF 的增量长度 ===
workday_dow2: delta_len=66 | weekend_dow5: 65 | weekend_dow6: 63 | workday_dow4: 62 | r2input: 63
```

**结论**：两把尺子在**同一输入**下 sha256 **完全一致**（`b6347529…` / `c5148cb5…` / `8fe92eb3…` / `792e0a9e…`），**无差异段落**；OFF 等价成立且不止 1 个 case；ON 相对 OFF 是**精确插入一行**（每提示词只出现 1 次该行，减掉后逐字节回到 OFF），非改写。

### 3.3 ON 三态渲染（workday / weekend / 仅周几）

```bash
cd .worktrees/feat-day-type-calendar/code && LIFE_PROMPT_CALENDAR=1 PYTHONPATH="$PWD" python3 /tmp/audit_prompt_sha.py | grep 'line='
# [workday_dow2] line=今儿是什么日子：周三，今儿个不是歇的日子。（…）
# [weekend_dow5] line=今儿是什么日子：周六，今儿是歇着的日子。（…）
# [weekend_dow6] line=今儿是什么日子：周日，今天不用上工。（…）
# [workday_dow4] line=今儿是什么日子：周五，今天得干活。（…）
```

三种状态（`day_type` 未知时只写周几 / 只给 day_type / 两者皆缺）：

```bash
LIFE_PROMPT_CALENDAR=1 PYTHONPATH="$PWD" python3 /tmp/audit_extra.py
# render_missing_all= ''
# render_dow_only= '\n今儿是什么日子：周日。（…）'
# render_dt_only= '\n今儿是什么日子：今天得干活。（…）'
# token_leak_workday_weekend= False        ← 人话里不含 workday/weekend 内部 token
# render_deterministic= True               ← 同 (agent,round) 两次完全一致
# lexicon_sha256= eee8ba1d2b4ba62848a7e5efdd72d078411889d870075c5fd874f742e7f9dd17
```

### 3.4 审计键 `ctx.calendar` 只在 ON 时出现，且 sha 对齐真实提示词行

```bash
# OFF
off_ctx_has_calendar= False   off__calendar_attr= None
# ON
off_ctx_has_calendar= True    off__calendar_attr= {'day_of_week': 5, 'day_type': 'weekend',
                        'line_sha256': '01a01a0214dc221e26d0f2ac1d1a4a2c327305f35b2476424c237e328a5ab857'}
# 独立核对：该行文本的 sha256 是否等于审计记的值
sha256("今儿是什么日子：周六，今天不用上工。（…）") = 01a01a0214dc221e26d0f2ac1d1a4a2c327305f35b2476424c237e328a5ab857  → match=True
```

### 3.5 指纹对比（`engine_version` 未变 / 树指纹变化=新增 life 文件，**不是回归**）

```bash
# engine_version（= 只对 config/*.json 的规范化哈希，进 WORLD_INIT）
(cd code && python3 -c "from engine.version import compute_fingerprint; print(compute_fingerprint())")
# 主树    → sha256:a871e36c44acbda9ac4aadeebe829a821219b2fec22642ea2b372f6ec88f3b1c
# worktree → sha256:a871e36c44acbda9ac4aadeebe829a821219b2fec22642ea2b372f6ec88f3b1c   ← 完全一致

# code/config 子树内容 sha
git ls-files -- code/config | sort -u | while IFS= read -r f; do sha256sum "$f"; done | sha256sum
# 主树   6e490b49237b5f5bfb802eec02a99b6aed4b1b1bea634757a3950535e43ec624
# worktree 6e490b49237b5f5bfb802eec02a99b6aed4b1b1bea634757a3950535e43ec624   ← 完全一致

# 树级指纹（口径 B）
bash tools/tree_fingerprint.sh world   # 干净基线(2a99344) a8d403bd… → 改动后 213f0f4a…
bash tools/tree_fingerprint.sh front   # 干净基线            b86aba09… → 改动后 b86aba09…（未变）
```

> **口径说明（本轮最易被误引的一行，务必连读）**：`tree_fingerprint.sh world` 覆盖 `code/**` 全内容，
> 因此**必然**因新增 `code/life/calendar.py` 而变——**这不是回归**，是"本臂确实改了 life 层"的如实反映。
> 决定旧日志可比性的是 **`engine_version` 指纹（只含 `code/config/*.json`），前后完全一致**。
> 反之，`world` 变了也说明本改动**不能**直接合进正在跑的批所用树 ⇒ 本轮因此走 worktree 隔离、未动主树。

**基线 `a8d403bd…` 的独立复现**（不采信实现者的"改动前"读数，我自己从 `2a99344` 内容重算）：

```bash
mkdir -p /tmp/base_2a99344 && git archive 2a99344 code | tar -x -C /tmp/base_2a99344
cd /tmp/base_2a99344   # 与 tree_fingerprint.sh 同口径：每个 tracked 文件 sha256sum 后汇总（排除 code/frontend）
# world → a8d403bd250a03cded0a89dd75b64fb6e04cf5de84bfcc5865f7feb2db4efefd   ← 与 R2 声称一致
# front → b86aba094254fdf3d041730c81f78aee40eaf0b9dc6386da9afa4db333efacf9   （同理）
```

**注意（口径瑕疵 ②）**：在**主工作树**直接跑 `tools/tree_fingerprint.sh world` 得 `8f8c1151…`，**不等于** `a8d403bd…`——
因为该脚本把 `git ls-files --others --exclude-standard`（未入库文件）一并计入，而主树此刻有 **7494** 个 `code/` 下未入库文件（frontend 另有 10 个）。
⇒ 引用该指纹时**必须**注明"干净树口径"，否则会得出"基线对不上"的假红。

---

## 4. 真实截图（1 张；性质＝纯函数输出渲染图，**不是**居民对话截图）

**图**：`v2/evidence/r25_calendar/r23-calendar-prompts.png`（3000×3000，2× DPR 全页截图；HTML 源 `v2/evidence/r25_calendar/r23-calendar-prompts.html`）

```bash
sha256sum v2/evidence/r25_calendar/r23-calendar-prompts.png  # a7e9d5ce3e5a8ec50656ed00…
sha256sum v2/evidence/r25_calendar/r23-calendar-prompts.html # 7455c68b039f02376d05b7ff…
```

**图注（请勿误读，字面口径）**：本图是 `code/life/calendar.py::render()` 与 `LifeLayerAgent._dialogue_prompt()` 的**真实装配输出的渲染图，不是居民真实对话截图**。本轮**未跑批、未调用任何 LLM**，因此不存在"跑出来的台词"。本图只证明「日历事实能被写进哪一行、写成什么人话」，**不构成任何效果读数**。

生成命令（可复算；无头 Chromium 经 Playwright 驱动，`--no-sandbox` 起在本地静态服务上）：

```bash
cd .worktrees/feat-day-type-calendar
python3 /tmp/gen_r23_shot.py          # 调真实 render()/_dialogue_prompt() 生成 HTML（此脚本全文见 §附A）
cd v2/evidence/r25_calendar && (python3 -m http.server 8899 --bind 127.0.0.1 &)
python3 - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome",
                          args=["--no-sandbox", "--disable-gpu"])
    pg = b.new_page(viewport={"width":1500,"height":1500}, device_scale_factor=2)
    pg.goto("http://127.0.0.1:8899/r23-calendar-prompts.html", wait_until="networkidle")
    pg.screenshot(path="r23-calendar-prompts.png", full_page=True); b.close()
PY
pkill -f "http[.]server 8899"
```

**限制（必须并列披露）**
1. **无本批对话截图**：本轮零批、零 LLM，`dialogue_shots.sh` 需要 `threads.json`（真跑日志派生），物理上没有样本 ⇒ 按 `reports/README.md` 纪律，**不挪用任何历史批旧图**。
2. 图里的提示词是**单条固定输入**（`P003`↔`P007`、`round=62`）的装配结果，不代表分布；长度差 `+62~+66` 字符也只是这条输入的实测。
3. 下一轮跑完两臂后，可用下面命令补真实对话截图（现在没有数据，仅登记命令）：

```bash
cd code && python frontend/tools/serve.py --host 127.0.0.1 --port 8848 &
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 sample/<batch>/threads.json   # 出 chat/rhythm/spread/600 四图
```

---

## 5. 未做什么（本轮不可引用项，必须明写）

1. **未跑批**：没有 `run_batch.sh` / `orchestration run` / `nightly.py`；存量批（PID 3898812/3898819，D12-E best-of-3 n16r60 seed42）全程在跑，本轮只读不干预（`pgrep` 复核命中，正因如此才走 worktree 隔离）。
2. **无 LLM 调用 ⇒ 无 `obs llm-cost` 证据**：该命令只能对真跑批的 `run.jsonl` 运行；本轮无批，故**不伪造**。
3. **无效果读数**：`F-8` / `L-7` / `L-15` / `len_p50` / 日历词频 **一律未测**。
4. **未动**：`code/config/**`、`code/engine/**`、`code/orchestration/**`、`state_hash` 输入、事件类型、记忆写入。
5. **未做组合臂**：「日历 + 处境锚（`LIFE_PROMPT_SCENE`）」是独立第三臂，本轮不跑——理由：一次只推进一个单变量，组合臂会把两处提示词增量混在一起，无法归因。

> **措辞纪律（本报告唯一允许的结论强度）**：**机制接通 ≠ 效果改善**。本报告只说「模型现在能看到今天是周几、是上工还是歇着」，**不说**"对话更有生活气息"，**不说**"提升"。R4 §3.2 三条陷阱（景物描写≠生活气息、提示词多一行≠更自然、长度/重复可能反噬）继续适用。

---

## 6. 结论绑定的 sha

| 绑定物 | 值 |
|---|---|
| 改动基线（`master`） | `2a99344ead2e16be15ecd0feb415f250f1e6ce3f` |
| 实现分支 / worktree | `feat/day-type-calendar` @ `.worktrees/feat-day-type-calendar` |
| 交付 commit（本报告 + 实现 + 证据同批入库） | 见 `git log -1 --format=%H feat/day-type-calendar`；完整 40 位 sha 由本轮 push 回报记录在 `team-workspace/reports/r23-brief.md` |
| 内容级绑定（不依赖 commit 可核对） | `calendar.py d742a914…`／`test_calendar_day_type.py 07c2b397…`／`agent.py diff 22e4ae79…`／图 `a7e9d5ce…` |
| 尺子身份 | `lexicon_sha256 = eee8ba1d2b4ba62848a7e5efdd72d078411889d870075c5fd874f742e7f9dd17`（`LEXICON_VERSION=calendar-v1`） |

> 说明：报告无法自指自身的 commit sha，故交付 sha 记录在 push 回报与团队简报中；内容级 sha256 已足够把"结论 ↔ 代码字节"钉死。

---

## 7. 下一轮待办（口径已按队长修订，**不是** n16r24）

1. **效应测量必须覆盖满一周**：`--seed 42 --agents 16 --rounds 84`（7 天 × 12 回合）OFF/ON 两臂。**24 回合只能走 3 天多，结构性看不到周末差异，不采用。**
2. **单变量口径**：两臂**均固定 `LIFE_PROMPT_SCENE` 为 OFF**，只让 `LIFE_PROMPT_CALENDAR` 变化；「日历 + 处境锚」是**独立第三臂，本轮不跑**（避免两处提示词增量混算）。
3. **前置条件**：等存量 D12-E 批收批、且 `pgrep` 三重并发检查干净后才起跑（`tools/d5/preflight.sh` 第 1 项，脏树检查亦须过）。
4. **判据**：主指标＝日历词频（周末 / 歇 / 收工 / 上工 / 周几）＋沿用 R21 的 **G1–G5 守卫**；`obs llm-cost --require-provider openai_compat` 验真（rc=0、`degraded=0`）。
5. **预登记内并列披露项（写死二值处置）**：`L-1` 长度分布、`L-7` 8-gram 重复——**越带即记 `BELOW_BAND`，不得记为改善**（沿用 R16/R22 措辞纪律）。
6. 跑完补真实对话截图（`serve.py` + `dialogue_shots.sh`，四视图，落 `v2/evidence/`）。

---

## 8. 审计发现与风险登记（3 项口径瑕疵 + 3 项遗留风险）

| # | 类型 | 内容 | 处置 |
|---|---|---|---|
| ① | 口径瑕疵 | R2 §5 写「ON 每条提示词 +63 字符」——实测 **+62~+66**（随周几措辞长度变化：`周三`/`周六`/`周日`/`周五` 均 2 字但句子长度不同）。+63 只在 `dow=5` 那一输入成立 | 本报告改为「+62~+66 字符，依具体日期措辞而变」；解释 `L-1` 时不得当常量用 |
| ② | 口径瑕疵 | `tree_fingerprint world` 在**主树**测得 `8f8c1151…` ≠ R2 的 `a8d403bd…`——因主树有 7494 个 `code/` 未入库文件被该脚本计入 | 已在 §3.5 登记"干净树口径"，并用 `git archive 2a99344` 独立复现 `a8d403bd…`，确认 R2 基线成立 |
| ③ | 既有欠账 | 本分支 `reports/README.md` 索引表止于 **R20**，R21/R22 行缺失（文件在主树为未入库件） | 本轮只追加 R25 一行，**不替他人补行**（避免改他人内容、避免大 diff） |
| ④ | 遗留风险 | `day_of_week → 周几` 是**命名层约定**（依赖 `TIME_CONFIG["DAY_TYPES"] = ["workday"]*5 + ["weekend"]*2` 的下标语义）；若该顺序变化，词表须同步 | `lexicon_sha256` 可检出词表变化，但**检不出** `DAY_TYPES` 变化 ⇒ 下一轮跑批前应加一条断言（登记为待办，不属本轮改动范围） |
| ⑤ | 遗留风险 | 提示词 ON 时长 +62~66 字符，`L-1` / `L-7` 是否漂移**本轮无数据** | 已在 §7.5 写死二值处置；**不预判** |
| ⑥ | 遗留风险 | 单变量只在 life 层成立：`world` 树指纹变化意味着本臂**不可直接合入正在跑的批所用树** | 保持 worktree 隔离；合并前须等跑批结束并重算派生物 |

---

## 附A：生成截图的脚本（`/tmp/gen_r23_shot.py` 核心）

```python
# 只读：调真实 render() 与 _dialogue_prompt()，输出 HTML 供截图；不调 LLM、不写仓库其他文件
import os, json, hashlib, sys
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(".worktrees/feat-day-type-calendar"); sys.path.insert(0, str(ROOT / "code")); os.chdir(ROOT / "code")
from life import calendar as CAL
from life.agent import LifeLayerAgent
from life import dialogue_threads as DT
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel
# …（建 agent、取 OFF/ON 两条提示词、对 OFF/workday/weekend/仅周几/全缺 五种输入调 CAL.render，
#    把「输入 → 真实输出行 → sha256」与「OFF/ON 提示词逐行对照」写进 HTML，
#    再按 §4 的 Playwright 命令截图）
```
