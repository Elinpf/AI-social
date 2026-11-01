# R45 · C1 处境锚：`LIFE_PROMPT_SCENE` 单变量双臂（A0 基线 / A1 处境锚）

> 🔁 **本文件已被 `reports/R46-c1-effect-metrics-20261101.md` 取代（SUPERSEDED，2026-11-01）。**
> 原因：R45 停在本轮读数之前的草稿状态；本轮（C1 效果层）的定稿报告为 **R46**，它包含四条并列主结论（机制接通 / 成本可测 / 效果按预登记判据不成立 / 根因定位：锚点时序 87/191 + 尺子不区分"提到/在做"）、独立复核与真实截图。
> **请勿引用本文件的数字（本文件从未填入读数）**；需要读请直接看 R46。本文件仅作为过程留痕保留，不再更新。

> ⚠️ **文件状态：草稿（DRAFT）——读数未填，不得引用、不得单独提交。**
> 已写实：§2 维度与假设、§3 方法与预登记、§9 限制框架、§10 复算命令、§11 闸门执行口径。
> 待填（来源已注明，**严禁预填任何数字**）：§1 一句话结论、§4 对比表、§5 机制层、§6 效果层、§7 原样例、§8 真跑验真、§12 截图。
> 填满后须删除本横幅。

- 报告编号：R45
- 维度：C1「处境锚」（缺口 A：对话里没有"我在哪儿、手上干什么、今天什么天"）
- 批次：`c1-scene-a0-20261101_n16r24_s42`（A0） / `c1-scene-a1-20261101_n16r24_s42`（A1）
- 预登记卡：`v2/refs/C1-scene-prereg-20261101.md`
- 尺子：`tools/metrics/place_content_consistency.py`
- 起跑树锚：`HEAD=8b64615b0c717a5a42db8d40ae9fff5b469cfe7d`

---

## 1. 一句话结论

【待填 · 来源 `team-workspace/report/c1-comparison.md` + 预登记卡 §4/§5】
只允许三选一：**成立 / 不成立 / 不可判**。写之前必须逐条过预登记卡 §5 的 5 条不可判条件（分母 <30、env 差异不止一行、真跑验真失败、词表指纹不一致、`no_cue` 占比差 ≥10pp）。不得美化、不得写"部分成立/基本成立"。

> 口径纪律（写结论时必须同时守住）：**机制层成立 ≠ 生活气息提升**。本条只覆盖"对话内容与所处场所是否相容"这一可判子集，不外推到"居民更像在过日子"。

---

## 2. 维度与假设（缺口 A 是什么）

**缺口事实**（来源：`team-workspace/recon/repo-recon.md` §7 缺口 A，逐条可回查）：

- 对话提示词装配点唯一：`code/life/agent.py` 的 `_dialogue_prompt()`（`:1836-1853`）与 `_reply_prompt()`（`:1855-1881`）。
- 装配序列里已经预留了「处所行」与「天气行」：`_scene_line()`（`agent.py:1576`）、`_weather_line()`（`agent.py:1610`）。
- **但两者默认关**：`code/life/scene_anchor.py:57` 写明臂开关 `LIFE_PROMPT_SCENE` 默认关；`code/life/weather.py:88` 写明 `HITT_WEATHER` 未设置即 OFF。而本批启动器的 `INLINE_ENV` 不含这两个变量 ⇒ **常规跑批的对话提示词里既没有"我在哪儿"，也没有"今天什么天"**。
- 可复算证据（`d47`，既有基线批）：`MSG_PUBLIC` 的 `payload.ctx` 键集为 `{initiator, l7struct, mood, need, relation, topic, trigger, public_reply}`，**无 `scene`、无 `weather`**；而 `agent.py:1600-1601` 在臂打开时会把 `self._scene` 写入 `ctx.scene`。
- 后果（文本级反例，同一份 `d47`）：`seq=53` P002（木匠）在 `place=library` 推刨子、`seq=167` P013（铁匠）在 `place=school` 打铁 —— 模型不知道自己在哪，输出的"手上活"与场所脱钩。

**为什么这是生活气息最结构性的一处**：其余维度（措辞、接话、话题广度）都在"怎么说"这一层；缺口 A 影响的是"说的是不是这个人此刻该说的事"。一个人可以不风趣、可以接错话，但只要他说的事与他站的地方、手上的活对得上，"在过日子"的底子就在；反之，措辞再漂亮也是悬浮的。同族已有两条先例（R21 scene-pair、R42 天气感知）结论都是**默认 OFF、从未进入常规跑批**，故本维度不是重复实验，而是**把已建好的机制第一次放进常规跑批口径下做强判定**。

**两条假设**（照录预登记卡 §1）：

- **H1（效果层）**：打开 `LIFE_PROMPT_SCENE` 后，居民对话正文/旁白与其所处场所、手上活动的一致率上升。
- **H0**：开关不改变一致率，读数差异来自噪声。

---

## 3. 方法与预登记（判据先于数据）

**预登记卡**：`v2/refs/C1-scene-prereg-20261101.md`（状态词：*"本卡在读取 A0/A1 两臂任何数字之前冻结"*）。本报告的任何判定不得偏离该卡 §4 通过线或 §5 不可判条件；偏离即须在 §9 显式登记。

| 项 | A0（基线臂） | A1（处境锚臂） |
|---|---|---|
| 批次目录 | `v2/evidence/c1-scene-a0-20261101_n16r24_s42/` | `v2/evidence/c1-scene-a1-20261101_n16r24_s42/` |
| 启动器 | `launch_c1_a0.sh` | `launch_c1_a1.sh` |
| 参数 | `SEED=42 AGENTS=16 ROUNDS=24 FLUSH=2` | 同左（逐字相同） |
| `INLINE_ENV` | `HITT_LLM_PROVIDER=openai_compat HITT_WORLD_SEED=42 HITT_DIALOGUE_PUBLIC_REPLY=1` | 同左 **+ `LIFE_PROMPT_SCENE=1`** |
| 差异行数 | — | **1 行（`LIFE_PROMPT_SCENE`）** |

**单变量证据（可复算）**：两臂 `env_manifest.txt` 的 `diff` 只有三处变化，其中两处是注释头与注释行，实质差异仅 `LIFE_PROMPT_SCENE` 一行（见 §10 命令 ①）。这满足预登记卡 §5.2「两臂 `env_manifest` 差异不止 `LIFE_PROMPT_SCENE` 一行 ⇒ 不可判」的前置。

**同代码**：两臂均由同一工作树、同一 `HEAD` 起跑（`PREP.md` 记录树锚 `8b64615`），跑批期间不改 `code/{life,orchestration,config,engine}`。⚠️ 注意 `PREP.md` 同时记录：当前工作树实际在分支 `feat/r44-public-reply-inbound`（非 master），跑批用的是工作树内容而非分支名 —— 这一点在 §9 列为口径说明项。

**判据强度声明（照录预登记卡 §7）**：主指标为**纯规则版**、不使用 LLM judge，逐字节可复算；因此结论强度**弱于**人工/judge 标注，全报告不得越过"规则版一致率"的说法。

---

## 4. 两臂对比表

【待填 · 来源 `team-workspace/report/c1-comparison.md`，**照抄不加工**，不改表头、不改单位、不合并行】

---

## 5. 机制层证据（scene 键覆盖率）

【待填 · 两臂 `run.jsonl` 上复算，命令见 §10 ③；预登记卡 §4 辅助读数：A0 期望 0% / A1 期望 > 0%】

判定纪律：**机制层不成立 ⇒ 无论效果层数字如何，结论只能是「机制未接通」**（预登记卡 §4 原文）。

---

## 6. 效果层证据（处所-内容一致率）

【待填 · 两臂 `rate`、`denominator(judged)`、`no_cue` 占比、分层读数，来源 c1-comparison.md；通过线照录预登记卡 §4：`Δ ≥ +15.0pp` **且** `rate(A1) ≥ 0.55`】

关键词定义须随数字一起写全（`check_definitions.sh` 会扫）：分子＝判为「相符」的可判定对话条数；分母＝对话类事件 − 缺 `place`/`body` 条数 − `no_cue` 条数；计算式＝分子÷分母；纳入＝`type ∈ {MSG_PUBLIC, MSG_DM}` 且 `payload.place`、`payload.body` 非空且命中线索词表。

---

## 7. 原样例对照（`seq=53` / `seq=167`）

【待填 · 两臂各贴原文，用于证明措施"有效/无效"，不许只贴 A1、不许改写原文、不许跨批拼接】

---

## 8. 真跑验真（`obs llm-cost`）

【待填 · 两臂 `llm_cost.txt` 的 `provider_guard.ok` / `calls` / `tokens_total` / `degraded`，逐臂给路径；任一臂失败 ⇒ 按预登记卡 §5.3 判「不可判」】

---

## 9. 限制与未决（照实列，不得删项）

1. **分母纪律**：预登记卡 §5.1 规定任一臂 `denominator(judged) < 30` 即判「不可判」。实际分母见 §6；若达标，仍须在附录给出复算命令，供他人独立核对分母不是"凑出来的"。
2. **单批噪声**：本维度**只有一批、单 seed（42）、16 居民 × 24 轮**，无重复批、无多 seed 方差估计。任何差异都只能作**点估计**，不外推、不谈显著性区间之外的因果。
3. **weather 未开**：本轮只开了 `LIFE_PROMPT_SCENE`，`HITT_WEATHER` 保持默认 OFF ⇒「今天什么天」这条线索**本轮完全未覆盖**。缺口 A 的三分之二（处所、手上活）在本轮口径内，三分之一（天气）不在。不得把本轮结论写成"处境锚已完整落地"。
4. **meta 自身缺陷（跑批自检层，必须先跨过才能引用任何数字）**：既有 `d47/meta.json` 实测 `n_agents=null`（声明 16）、`assertions.code_unchanged_during_run=null`（未传 `--git-status-start` ⇒ 冻结区不变性**不可判**）、`assertions.participants_consistent=false`（4 处违规）。本轮两臂的 meta 实际读数：**【待填 · 逐臂照录，含 violations 条数】**。这三条不因本轮维度而消失，**引用前须人工核对**。
5. **规则版尺子的固有偏差**（照录预登记卡 §8）：词表覆盖有限（`no_cue` 比例随文体漂移，且 A1 若更多描述手上活会同时压低 `no_cue`、抬高分母，预登记卡 §5.5 对此设了降级闸）；一词多义按保守方向计；"允许场所"集合是先验设定而非客观真理；`hall`/`gate` 在任一线索命中下一律判相悖（过道型场所不承载本站词表活动）。
6. **设计者对样本非盲**（照录预登记卡卡首披露）：词表设计时已知 `seq=53`/`seq=167` 两条反例；虽未针对这两条定制词条，但解释结果时应计入。
7. **历史未决项不因本轮消失**（照录原状态词，不得改写成已解决）：`R41V-C4` **不成立**、`R41V-C1` **不可判**；`R44-C1a/C1b/C2/C3` **全部不可判**（唯一试验批 `r44` 中止于 round 9/24，无 rc/meta/llm_cost）；CYCLE-47 的 `N-1…N-7` 未销号；R43 效果层**未验证**。
8. **工作树分支口径说明**：`PREP.md` 记录当前工作树在 `feat/r44-public-reply-inbound`、`master=94e272a…` 落后于跑批树锚。本轮所有数字绑定的是**工作树内容 `8b64615`**，不是"master 分支上的 HEAD"。

---

## 10. 可复算命令附录

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 单变量核验：两臂 env 只差 LIFE_PROMPT_SCENE 一行
diff v2/evidence/c1-scene-a0-20261101_n16r24_s42/env_manifest.txt \
     v2/evidence/c1-scene-a1-20261101_n16r24_s42/env_manifest.txt

# ② 单臂一致率读数（规则版，确定性；两次运行须逐字节一致）
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl
# 幂等自检
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl > /tmp/a1_a.txt
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl > /tmp/a1_b.txt
cmp /tmp/a1_a.txt /tmp/a1_b.txt && echo BYTE_IDENTICAL

# ③ 机制层：对话类事件的 ctx.scene 键覆盖率（预登记卡 §9 同一段脚本）
python3 - v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl <<'PY'
import json,sys
p=sys.argv[1]; n=0; hit=0
for l in open(p):
    e=json.loads(l)
    if e.get("type") in ("MSG_PUBLIC","MSG_DM"):
        n+=1
        if "scene" in ((e.get("payload") or {}).get("ctx") or {}): hit+=1
print(f"dialogue={n} scene_key={hit} coverage={hit/n if n else 0:.4f}")
PY

# ④ 真跑验真
cat v2/evidence/c1-scene-a0-20261101_n16r24_s42/llm_cost.txt
cat v2/evidence/c1-scene-a1-20261101_n16r24_s42/llm_cost.txt

# ⑤ 起跑三件套完整性
ls -l v2/evidence/c1-scene-a{0,1}-20261101_n16r24_s42/{run_batch.rc,meta.json,llm_cost.txt,run.jsonl}
```

---

## 11. 引用闸门记录

执行口径（实测 `--help` 行为，2026-11-01）：

- `bash scripts/check_citations.sh reports/R45-C1-scene-anchor-20261101.md`：逐行扫 sha；**每行只配一个路径**（同行多文件会误配），历史/作废 sha 须就近标注「历史版/作废/未入库」才豁免。
- `bash scripts/check_definitions.sh reports/R45-C1-scene-anchor-20261101.md`：出现「占比 / N% / 平均」后 6 行内须含 分子/分母/计算式/纳入；「倍率/外推」后 3 行须含「假定不变」。首版精确率低，仅提示不作门禁。

【待填 · 两条命令的 rc 与输出原文】

---

## 12. 截图三件套

【待填 · 逐张：文件名 `<batch>-<view>-<sha8>.png` / 来源 run 目录 / 渲染命令 / 日志 sha256；rc≠0 时写「本轮无截图」并附原始输出，禁止复用旧图】

> 已知环境事实（前置验证，2026-11-01）：`code/frontend/tools/shot.py:125-126` 用 `executable_path=find_chrome()` 走系统 `/usr/bin/chromium-browser`，**不依赖** playwright 自带 headless shell；用既有 `d47` 批次冒烟 `--views chat,rhythm` 得 `ok_count=2 / fail_count=0`。故「无图」不能在环境层面预设，只能在实测 rc≠0 时写。
