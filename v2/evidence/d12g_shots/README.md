# D12-G 真实截图（CYCLE-11 / `c11-shots`）

本目录是本轮（CYCLE-11）报告引用的**唯一**截图来源。所有 PNG 均由 `code/frontend/tools/shot.py`
对 `code/frontend/dialogue.html` 真实渲染得到，**未使用任何历史批次截图、未拼图、未占位**。

- 批次：`run_d12g_diverse2_n16r60_seed42`（16 agents × 60 rounds，seed 42）
- `run_sha256`：`dd4ad73d5a21c7485c2afbfc9701e267c25da3150b10adade3b3819a3996ff36` → **sha8 = `dd4ad73d`**
- 源日志（跑批目录，未入库）：`.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl`
  （56,333,745 B，117,393 events，`run_batch.rc=0`，finished_at=2026-10-23T20:16:25+08:00）
- 派生数据（入库）：`code/frontend/sample/dialogue_d12g_diverse2/threads.json`
  （2,382,045 B，sha256 `30b7dd831b48df80181b54b744e4c01c1612c350b5b1f8c3ed6f044c0c8e42ce`）
- 数据统计：messages=510，threads=169，multi_turn=88，threads_ge3_turns=77，max_turns=6，moves=299

## 1. 派生 + 渲染命令（原文）

```bash
# 1) run.jsonl → threads.json（带完整性断言：--require-complete，半截跑批会被拒绝、退出码 3）
D=.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42
python3 code/frontend/tools/gen_threads.py \
  --log   $D/run.jsonl \
  --meta  $D/meta.json \
  --out   code/frontend/sample/dialogue_d12g_diverse2/threads.json \
  --require-complete
# 实测输出：完整性断言通过（TURN_SEAL 60 条覆盖 round 0..59）；
#           events=117393 messages=510 threads=169 multi_turn=88 ge3=77
#           wrote .../threads.json (2382045 bytes)

# 2) 渲染（保留空白检测，未传 --no-blank-check；逐条落 render_wrap.log）
bash v2/evidence/d12g_shots/render_d12g_shots.sh \
  http://127.0.0.1:8848 \
  sample/dialogue_d12g_diverse2/threads.json \
  v2/evidence/d12g_shots
```

静态服务：`code/frontend/tools/serve.py`（root = `code/frontend`，端口 8848，pid 477109，起于本批次之前，未改动）。
每张图的实际 `shot.py` 命令行**逐条**记在 `render_wrap.log` 的 `CMD:` 行，报告引用时以日志为准。

## 2. 线程选择依据（可复算）

**筛选规则**（对 `threads.json` 的 `threads[]` 施加，全部字段来自该文件，不靠人工判断）：

1. `multi_turn == true` 且 `turns == stats.max_turns`（=6）且 `channel == "dm"` → **52 条**候选；
2. 在候选中按 `place` 分桶（park 19 / cafe 14 / plaza 8 / market 7 / community_center 2 / library 1 / workshop 1）；
3. 取**覆盖 4 个不同地点**的 4 条，每桶 1 条，优先「正文含括号动作描写 + 话题落在人情/赊账/事务协作/技艺闲谈」的线程——即"有生活气息可看性"而不是"最漂亮"。

复算命令：

```bash
python3 - <<'PY'
import json, collections
d = json.load(open('code/frontend/sample/dialogue_d12g_diverse2/threads.json', encoding='utf-8'))
mt = d['stats']['max_turns']
cand = [t for t in d['threads'] if t['multi_turn'] and t['turns'] == mt and t['channel'] == 'dm']
print(len(cand))                                   # 52
b = collections.defaultdict(list)
for t in cand: b[t['place']].append(t['thread_id'])
print({k: len(v) for k, v in b.items()})
PY
```

| 文件名（PNG） | 线程 ID | 地点 / 轮次 / 轮区间 | 选它的理由（依据字段） |
|---|---|---|---|
| `run_d12g_diverse2_n16r60_seed42-thread-mkt-dd4ad73d.png` | `TH-P004-P013-4` | market · 6 轮 · round 4–10 | 秀娘出桂花糕请人试味、铁头边打铁边回嘴，聊到"周公文嘴刁""李寡妇赊桃酥"——`turns=6`、含多段括号动作描写、话题=赊账人情，语气有来有回 |
| `run_d12g_diverse2_n16r60_seed42-thread-cafe-dd4ad73d.png` | `TH-P012-P015-4` | cafe · 6 轮 · round 4–9 | 桂婶与五味一边掐豆角炖牛腩一边商量办席分工（八凉八热改六凉六热、谁腰腿不利索别硬撑）——`turns=6`、有具体事务分工细节，是"协作型生活对话"代表 |
| `run_d12g_diverse2_n16r60_seed42-thread-park-dd4ad73d.png` | `TH-P014-P011-1` | park · 6 轮 · round 1–9 | 巧儿与小满比竹剑轻重、吐槽老石教格挡睡到打呼、鱼线缝口子、七钱小木鱼"辟邪"——`turns=6`、闲聊密度最高，是纯闲趣型 |
| `run_d12g_diverse2_n16r60_seed42-thread-cc-dd4ad73d.png` | `TH-P008-P007-6` | community_center · 6 轮 · round 6–13 | 阿林在柜台等归档、周公文贴封条，两人轮流说"我不急"并顺手讲老陈/老李/阿贵看错数的旧事——`turns=6`、日常办事场景+互相体谅，是"低冲突日常"代表 |

另两张为**整批视图**（非单线程）：

| 文件名（PNG） | 视图 | 用途 |
|---|---|---|
| `run_d12g_diverse2_n16r60_seed42-chat-dd4ad73d.png` | 对话流（`?still=1&multi=1&min=0&sort=turns`） | 整批多轮线程总览（88 条多轮，按轮次排序），用于报告里说明"本轮对话规模" |
| `run_d12g_diverse2_n16r60_seed42-rhythm-dd4ad73d.png` | 节律·串门（`+&view=rhythm`） | 5 天 × 4 时段的对话/走动看板 + 场所轨迹，用于说明"生活气息的时间分布" |

### 逐线程截图为什么要额外带 `q=`（重要，勿删）

`thread=<id>` 单独用**截不到目标线程**：`?still=1` 会给 `<body>` 加 `still` 类且 `overflow:hidden`，
`focusThreadFromUrl()` 的 `scrollIntoView` 在实际渲染里无效——实测 `window.scrollY` 恒为 `0`
（首版 4 张逐线程图因此全是页面顶部，已废弃重渲，未入库）。

修正做法：每条线程再传一个 `q=<该线程正文里全库只出现一次的短语>`，页面因此只渲染 **1 张卡**，
目标线程自然落在视口顶部。4 条短语及唯一性依据见 `threads_selected.txt`（第三列），
例：`TH-P004-P013-4` → `你们帮我评评`（全库命中集合 = {TH-P004-P013-4}，1 条）。
渲染后已用视觉核对：4 张图分别只显示 `TH-P004-P013-4` / `TH-P012-P015-4` / `TH-P014-P011-1` / `TH-P008-P007-6`，
且卡片正文首句与 `threads.json` 中该线程 `messages[0].body` 一致。

## 3. 读数表（逐张，取自 `render_wrap.log`，非口述）

判据：`max_color_frac ≥ 50%` 视为近乎单色空白帧（`shot.py` 的 `_BLANK_FRAC=0.5`）；`mean_brightness` 为 0–255 灰度均值。
本批 6 张**全部一次通过**，`blank_retries` 均为 `0/2`，无 SUSPECT。

| PNG | 体积 (B) | mean_brightness | max_color_frac | blank_retries | rc |
|---|---|---|---|---|---|
| `...-chat-dd4ad73d.png` | 290,704 | 35.6 | 30.00% | 0/2 | 0 |
| `...-rhythm-dd4ad73d.png` | 284,919 | 32.5 | 34.47% | 0/2 | 0 |
| `...-thread-mkt-dd4ad73d.png` | 338,336 | 37.5 | 28.06% | 0/2 | 0 |
| `...-thread-cafe-dd4ad73d.png` | 350,289 | 38.4 | 29.32% | 0/2 | 0 |
| `...-thread-park-dd4ad73d.png` | 315,216 | 36.8 | 29.33% | 0/2 | 0 |
| `...-thread-cc-dd4ad73d.png` | 339,785 | 37.8 | 29.32% | 0/2 | 0 |

合计：`OK_COUNT=6  FAIL_COUNT=0`（见日志末行）。**无"不可用"图**。

PNG sha256：

```
3de36b409a1b68c7844e5024d9263bf94c5e4751cd98ef2d35adeacfeb53af0e  ...-chat-dd4ad73d.png
492606df4fbea2511b17d53fec706284ef6c18fdbedb1cfb67f8725e82c4d449  ...-rhythm-dd4ad73d.png
dedfc528e8e78e9cf33e5954f79dbcf4dd90a1b1b23b4442896b5f1c3fc7a18a  ...-thread-mkt-dd4ad73d.png
a061003ea3a01c5a29b33794200b4229c64e34f904c66224b3a34b65c1406847  ...-thread-cafe-dd4ad73d.png
754b9a58be4cdaa5ddcd4456b4e6fd867f11108199548c21a8d87a05b5a2f6db  ...-thread-park-dd4ad73d.png
085ccd1b6bd9f16b8f7f296f0d814a21e251ed52be5f356b4f19cc328bd92ef1  ...-thread-cc-dd4ad73d.png
```

## 4. 复核方式（任何人都能重跑）

```bash
# 体积 / 哈希
ls -l v2/evidence/d12g_shots/ && sha256sum v2/evidence/d12g_shots/*.png
sha256sum code/frontend/sample/dialogue_d12g_diverse2/threads.json

# 读数（与第 3 节逐字对照）
grep -E "SHOT OK|SHOT FAIL" v2/evidence/d12g_shots/render_wrap.log

# 截图 ↔ 线程 一一对应（不依赖肉眼）：PNG 名里的 sha8 必须等于 threads.json 的 source.run_sha256 前 8 位
python3 -c "import json;d=json.load(open('code/frontend/sample/dialogue_d12g_diverse2/threads.json'));print(d['source']['run_sha256'][:8], d['source']['run_label'])"
```

## 5. 入库裁决（Leader 已裁，照此执行；判例供后续臂沿用）

- 入库：本目录 6 张 PNG + `render_wrap.log` + `threads_selected.txt` + `render_d12g_shots.sh` + 本 `README.md`；
  `code/frontend/sample/dialogue_d12g_diverse2/threads.json`（2.38 MB）。
- `threads.json` 入库理由：① 仓内已有 18 份被报告的 `threads.json`，D12-G 是本轮唯一被引用批次，惯例一致；
  ② 2.38 MB 属单文件可接受量级（仓库真正的体积问题是 11 个未跟踪 `dialogue_*` 目录累计约 24 MB，
  那些是**未被引用的派生数据**）；③ 不入库就无法从 PNG 反查对话原文，截图会变成孤立图片。
- **判例一句话**：「被本轮报告引用的批次，其 `threads.json` 入库；未被任何报告引用的派生目录不入库
  （保持 `??`，由 `.gitignore` 或人工清理，不得用 `git add -A` 逐步默认化）。」
- 提交方式：按 runbook §3.106，用 `git commit -m "..." -- <path...>` 限定 pathspec，提交前用
  `git diff --cached --stat` 与清单逐行对账。
