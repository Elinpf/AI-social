# R19 · 话题展开 / 多线索（topic-breadth）：同一条对话线程能承载第二条线索

> **证据日期**：2026-10-22
> **绑定的代码 sha**：`dd0c2bc`（改造 + 修死尺子）｜**证据 commit**：`c523fd7`（`feat/r19-topic-breadth` 当前 tip；本轮产物全部在该分支）
> **结论档位（一句话）**：**部分有效——方向为正，强度＝弱证据**（机制生效：`D 0→47`、`T=21.28%`、`landed 10`、人工 precision `8/10=0.80`、守卫四项全过；但样本 n8r24 / 单 seed / 非盲判，"擦线"通过，不外推）。
> **本轮维度**：话题展开 / 多线索。**不是**「岔题」、**不是**「换话题」（`tag_replaced` 两臂皆 0，实现只追加不替换）。
> **证据目录**：`v2/evidence/r19_topicbreadth_n8r24_seed42/`（双臂自包含：脚本 / 双 run.jsonl / meta / env_dump / 指纹 / llmcost / precision 抽样 / 读数汇总）
> **截图目录**：`v2/evidence/r19_topicbreadth_shots/`（5 张真渲染 PNG，全链 sha256 见 §7）

---

## 0. 摘要（TL;DR）

| # | 结论 | 档位 | 依据 |
|---|---|---|---|
| 1 | 机制生效：开关打开后「话题展开事件」实际下发并落地（`D 0→47`、`landed 10`、`T=21.28%`），关闭时 `D=0`（行为侧开关自证） | **已验证（机制侧）** | §4 表、`readings.md` |
| 2 | 人工 precision = **8/10 = 0.80**，Wilson95 **[0.490, 0.943]**（下界 > 门槛 0.4，但**距门槛仅 0.09**） | **部分有效** | §4.3、`precision_sample.md` |
| 3 | 排除性成立但**只赢 0.9pp**（`T` Wilson 下界 0.1199 vs off 门控假阳性上界 0.1111）——**擦线** | **部分有效（弱）** | §4.4 |
| 4 | 守卫：`L-6`/`L-5` 不恶化、`L-7` 下降（0.2577→0.1856）、`F-1` 持平、两臂 `meta.json` 齐全 | **未击穿** | §6 |
| 5 | 「F-2/F-2b 从 0 变 >0」**不是改善**，是死尺子被修好 ⇒ 只作机制侧事实 | **不得写成改善** | §5 |

---

## 1. 本轮维度与动机

**维度**：**话题展开 / 多线索**——一条对话线程能否在原本那件事之外，**自然地**带出**第二条**线索（例：从「囤布等赶集」聊到「攒钱还谷子」，再聊到「修篱笆的人情走动」）。

**一句话改进**：让**同一条对话线程能自然承载第二条线索**，而不是一件事说完就断。

**必须先交代的三件事（防误读）**：

1. **本轮实现「只追加、不替换」**：新增的第二个话题标签是**追加**到原 `tag_hints` 上，原标签不被改写 ⇒ 结构上 **`tag_replaced ≡ 0`**（两臂实测 0 / 0，见 §4）。所以本轮做成的是「多线索并行」，**不是**「换掉话题」。
2. 因此本报告量的是「一条线程能承载 ≥2 条线索的比例」，**不是**「对话是否跑题」。
3. 「F-2/F-2b 由 0 变 >0」**只能**表述为「尺子恢复可动」（§5），**不得**表述为改善——那是改造的定义本身（与 R16 的 L-7 `BELOW_BAND` 因果循环同型）。

---

## 2. 改动摘要（`dd0c2bc`）

| 文件 | 改动 | 为什么 |
|---|---|---|
| `code/life/topic_breadth.py`（**新增**，232 行） | ① 话题 id → 人话 `label`（显示层，收 `ctx.topic` 内部 token 的呈现问题）② `turn>=1` 的**确定性**岔题指派 `plan`（sha256，可复算、非随机）③ 生成后**正则双条件内容门控** `confirm`：命中 `shift` 词表**且**不命中 `base` 词表才放行 ④ 审计 `audit` | 让「线索」是**内容上真的出现了**才算，而不是"模型被要求了就算" |
| `code/life/agent.py`（+64） | 两处提示词改用 `_topic_label()`（人话化）；回复提示词插入岔题提示行；**生成后按门控结果 `ctx.topic_breadth.append(...)` 只追加第二个 tag**（`agent.py:1069` 处 `tag_hints = 原 tags + []`，**不覆盖原集**）；写入 `ctx.topic_breadth` 审计字段；**开关关闭时提示词与 payload 逐字节不变** | 单变量：off 臂 = 不设 `LIFE_PROMPT_TOPIC_BREADTH` |
| `tools/d5/dialogue_metrics.py`（+62） | 旧 `F-2_topic_drift` **保留输出并标 `LEGACY_DEAD_RULER`**；新增 `F-2_content_drift`（**纯内容** jaccard，不看 tag）、`F-2_tag_switch`、`F-2_tag_change_split`（`tag_added` / `tag_replaced` 拆分）；`F-2b` 补 `denominator_threads`，并把分子分母统一到 **`mixed_key` 线程口径**（原 `:676` 分子/分母单位不一致） | 死尺子修复：` :672` 的「tag 无交集」否决项在 tag 恒定时不再一票否决（改由 `F-2_content_drift` 表达内容侧），`:666` 的 `union≥2` 保留在机制侧并补齐分母 |
| `code/life/tests/test_r19_topic_breadth.py`（**新增**，228 行） | 22 项：OFF 逐字节不变 / 人话化 / 双条件门控 / 确定性 / 词表自洽 | 守住「关闭即旧行为」 |

**开关**：`LIFE_PROMPT_TOPIC_BREADTH`，默认 **OFF**（线上行为不变）。off 臂 = 不设该变量（`run_off/env_dump.txt` 留证），on 臂 = `=1`（`run_on/env_dump.txt` 留证）。

---

## 3. 实验设置

| 项 | 值 |
|---|---|
| seed / 规模 | `seed=42`、`n_agents=8`、`rounds=24`（**pilot 规模**，2 个 night 窗） |
| 样本量 | **97 条消息 / 30 线程 / 67 个相邻对**；`landed` 事件 10 条 |
| 模型 | `DeepSeek-Flash`（两臂 meta 一致） |
| 两臂 | `run_off/`（开关关） vs `run_on/`（开关开），**同 seed / 同 n8r24 / 同代码** |
| 真 LLM 证据 | `obs llm-cost --require-provider openai_compat` **rc=0**（两臂）；`by_provider = {"openai_compat": 512}`；`degraded = 0`；`cached = 195`（**批内去重，不是 mock**）；`thinking = 144`（judge 维） |
| calls | 两臂各 **512**；dialogue 各 **97** |
| tokens | off `in 60,277 / out 49,952`（total 110,229）；on `in 61,996 / out 46,550`（total 108,546） |
| meta.json | **两臂齐全**（`run_off/` `events=9282`、`run_on/` `events=9286`；`assertions` 通过，「真跑判定通过」见 `run_*_host.log`） |
| 证据目录 | `v2/evidence/r19_topicbreadth_n8r24_seed42/` |
| 日志 sha256 | off `4dfc26e1…`；on `6e08b25f…`（全文见 §4.5） |

**完整跑批命令**（脚本原文，可照抄重跑）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
# off 臂（不设开关）
setsid nohup bash tools/d2/run_batch.sh \
  --out-dir v2/evidence/r19_topicbreadth_n8r24_seed42/run_off \
  --seed 42 --agents 8 --rounds 24 --side-root /tmp/r19_tb_off_side \
  > v2/evidence/r19_topicbreadth_n8r24_seed42/run_off_host.log 2>&1 < /dev/null &
# on 臂（唯一差异：开关 = 1）
export LIFE_PROMPT_TOPIC_BREADTH=1
setsid nohup bash tools/d2/run_batch.sh \
  --out-dir v2/evidence/r19_topicbreadth_n8r24_seed42/run_on \
  --seed 42 --agents 8 --rounds 24 --side-root /tmp/r19_tb_on_side \
  > v2/evidence/r19_topicbreadth_n8r24_seed42/run_on_host.log 2>&1 < /dev/null &
# 验真（两臂各一次，rc 必须 0）
cd code && python3 -m obs llm-cost --log ../v2/evidence/r19_topicbreadth_n8r24_seed42/run_on/run.jsonl \
  --require-provider openai_compat --out ../v2/evidence/r19_topicbreadth_n8r24_seed42/run_on/llmcost.json
```

### 3.1 两臂 `code_sha` 不同（`dd0c2bc` vs `cf0b9404`）的解释——主动交代，不等读者发现

| 事实 | 值 |
|---|---|
| off 臂 `meta.code_sha` | `dd0c2bc` |
| on 臂 `meta.code_sha` | `cf0b9404` |
| 差异提交 | `aece50c`、`cf0b9404` —— **只改 `v2/evidence/d4_judge_run.py`（判据脚本）与 evidence 文件**，不触碰 `code/` 四子树 |
| `git diff dd0c2bc cf0b9404 -- code/life code/orchestration code/config code/engine` | **输出为空**（逐字节相同） |
| 四子树聚合指纹 | off = **`f1645dcfa9cb06cd`** / on = **`f1645dcfa9cb06cd`**（**110 文件**，逐位相同） |
| 结论 | **两臂跑的是同一份运行代码**，由「空 diff + 指纹逐位相同」双重证明；`code_sha` 差异源于**跑批期间同分支上他人落了 evidence 提交** |

> 留证：`v2/evidence/r19_topicbreadth_n8r24_seed42/code_identity_note.txt`；逐文件指纹：`run_off/code_fingerprint.txt`、`run_on/code_fingerprint.txt`。
> 纪律教训（已收口为团队规则）：**跑批进行中不做任何 commit / 渲染**，证据等收批后一次性提交。

### 3.2 precision 判定对象的修正

**precision 的判定对象已修正为「`landed=true` 的 tag 追加事件，N=10」**；原导出 13 条中 **3 条是同线程继承来的 tag（不构成追加事件）**，已单列附录**不参与 precision 分母**（`n=10`，属预注册 B.4 的 `8≤N<15` 全量判档）。修正 commit：`c523fd7`。

---

## 4. 结果（双列 + off-arm 对照）

### 4.1 主表（工具层只出数；判定见 §10）

| # | 项 | off 臂 | on 臂 | 口径 / 分母 | band_source |
|---|---|---|---|---|---|
| 1 | 下发数 `D`（`ctx.topic_breadth` 条数） | **0** | **47** | MSG 97 vs 97 | 计数，无需带 |
| 1b | 门控通过 `through`（`landed=true`） | 0 | **10** | 同上 | 计数 |
| 1c | 通过率 `T = through/D` | —（D=0） | **0.2128（21.28%）** | — | Wilson95 `[0.1199, 0.3627]` |
| 2a | `tag` 追加事件（`len(tag_hints)≥2` 的 MSG，含继承） | 0 | 13 | 含 3 条继承 ⇒ 不进 precision | 计数 |
| 2b | **`tag_added`（相邻对）** | 0 | **10** | 相邻对 **67** | 计数 |
| 2c | `tag_replaced`（相邻对） | 0 | **0** | 67 | 结构恒 0（只追加不替换）⇒ 作反证 |
| 3 | **`F-2b` 多话题线程（机制侧）** | **0/30** | **7/30 = 23.33%** | `mixed_key` 线程，分母 30 | per-thread，**无可用带**（未估上界） |
| 4a | `content_drift`（**守卫**：相邻对 jaccard<0.10） | 0.626866 | 0.626866 | 67 | 只作「不恶化」，不加分 |
| 4b | jaccard 均值 / 中位数（全相邻对） | 0.0874 / 0.0698 | 0.0850 / 0.0851 | 67 | 无方向性差异 |
| 4c | jaccard（仅 `switched` 子集） | n=0（无切换） | 【见 `summary.json`，n 极小】 | — | **只报数，不比率** |

**读法（三列对照，缺一不可）**：① 切换次数是**计数**（10 条追加 / 67 相邻对）；② 切换后相邻对 jaccard 分布**两臂均值几乎相同**（0.0874 vs 0.0850，p50 0.0698 vs 0.0851）⇒ **内容层没有变"碎"也没有变"粘"**，这正支持「多线索是叠加而非替换」；③ 唯一能撑因果的是 **off-arm 同 seed 同配置对照**（`D=0` vs `D=47`）。

### 4.2 `tag_replaced = 0` 的意义（反证，不是缺陷）

两臂皆 0 证明实现**没有替换**原话题 ⇒ 「话题展开」与「换话题」在本轮被清晰区分开；这也是 §1 命名不许写「岔题」的实证依据。

### 4.3 人工 precision（主判据）

- 判定对象：`landed=true` 的 **10 条**（全量判，n=10）
- **precision = 8/10 = 0.80**，Wilson95 **[0.490, 0.943]**（下界 0.49 > 门槛 0.40，**距门槛仅 0.09**）
- 两条被判「假展开」的类型：动作不一致 / 话题词落在次要位置（**都不是「复述提示词」**）⇒ 假阳性来源是"话题降级为修饰语"，不是词表泄漏
- 原件：`v2/evidence/r19_topicbreadth_n8r24_seed42/precision_sample.md`（含逐条原文与同线程上一句）

### 4.4 排除性（门控是否真的在排除）

| 量 | 值 |
|---|---|
| `T` = 10/47 = 0.2128，Wilson 下界 | **0.1199** |
| off 臂门控假阳性 FP = 1/47 = 0.0213，Wilson 上界 | **0.1111** |
| 判定 | `Wilson_lo(T) > Wilson_hi(FP)` **成立，但余量仅 0.9pp** ⇒ **本批余量很小，原因是 n=47 的下发样本窄**（属本批限制）。放量到 n16（下发约 343 条）后区间收窄：`T=15%` 时下界约 **0.115** 仍 > FP 上界约 **0.025**（3/342），余量约 **9pp** ⇒ **真正会卡住放量的是 precision（见 §10 条件 1/5），不是排除性** |

### 4.5 证据文件与 sha256（照抄可核）

| 文件 | sha256 |
|---|---|
| `run_on/run.jsonl` | `6e08b25f4b68ad8fb2a919445df52f31a74eeb6c2773483dce6d2cb4c8449111` |
| `run_off/run.jsonl` | `4dfc26e12dba102422c0306a6d53efb806bdb9f5efc87528fc56a42fe5e46ca8` |
| `code/frontend/sample/dialogue_r19_topicbreadth_on/threads.json` | `5120df824bcf720210b955624f9884534b7f04902ac1f0c2710b19c6b42de399` |

**复算命令（全部只读 / 幂等）**：

```bash
cd /root/jiuwenswarm/agent/workspace/work/尝试/social-experiment   # 实际路径见上方命令
E=v2/evidence/r19_topicbreadth_n8r24_seed42
# ① 双臂读数（D / through / landed / 指标 / 守卫，单一真源 = tools/d5/dialogue_metrics.py）
python3 $E/summarize_arms.py            # 输出对照 $E/summary.json 与 $E/readings.md
# ② 四子树指纹（证明两臂同一份运行代码）
python3 $E/fingerprint_4trees.py        # 期望 f1645dcfa9cb06cd，110 文件
# ③ 真跑验真
cd code && python3 -m obs llm-cost --log ../$E/run_on/run.jsonl --require-provider openai_compat | head -c 400
# ④ 门控假阳性（off 基线回归）
python3 ../$E/off_gate_fp.py
```

---

## 5. 方法学（本轮重点）：F-2 / F-2b 曾是「死尺子」

### 5.1 死在哪

| 位置 | 事实 |
|---|---|
| `tools/d5/dialogue_metrics.py:672` | F-2 分子 = `(tags 无交集) AND (jaccard<0.10)`——**第一个条件是一票否决项** |
| `tools/d5/dialogue_metrics.py:666` | F-2b 分子 = 线程内 `union(tags) ≥ 2`——同样依赖 tag 变化 |
| `code/life/agent.py:1126`（发起） | `tag_hints:[tid]`，`tid` = 日程 slot 的 `template_id` |
| `code/life/agent.py:1065`（回复） | 回复**原样继承**被回复者的 `tag_hints` |

⇒ 线程内 tag **恒为常量** ⇒ F-2 的「tag 无交集」恒 False、F-2b 的 `union≥2` 恒 False ⇒ **两指标在新结构下结构性恒 0**，与对话写得好不好无关。这就是「死尺子」。

**注意区分**：0 不是「字段缺失」（4 批数据 `tag_hints` 100% 存在），也不是「内容真的不漂移」——内容层实测相邻对低重叠比例本来就有 66%–73%，**人本来就在跳话题，是尺子看不见**。

### 5.2 构造正例 PASS（不是写死 0）

同线程两条消息、tag 分别 `gift` / `combat_training`、正文零重叠 ⇒ F-2 / F-2b 均报 `1.0`。⇒ 指标**能**报 >0，只是在真实数据上不可触发（前者改常量、后者改信号源，修法完全不同）。

### 5.3 因此：「F-2 0 → >0」只能算「尺子恢复可动」

- 本轮改造让线程内 tag 可**追加** ⇒ F-2/F-2b **必然**上升，这是**改造的定义本身**，不是效果证据（R16 的 L-7 `BELOW_BAND` 同型）。
- 故本报告把 F-2/F-2b 只放**机制侧存在性**位置；效果侧一律用 §4 的「追加事件计数 + jaccard 分布 + off-arm 对照」。
- `content_drift` **只作不恶化守卫**：它两臂完全相同（0.626866 vs 0.626866）⇒ 改造**没有把对话写碎**，仅此而已，**不能当提升**。

### 5.4 顺带纠正的历史引用

1. **R4:57 的 v0 `F-2 = 33.3%` 不是「改造前会岔话题」**：v0 批无 `thread_id`，`mixed_key` 退化为「(day, channel, 无序对)」，把**不同模板**的多段对话并进同一"线程" ⇒ 14/136 线程 tag 多变是 **legacy 分组假象**；v0 与新结构 **跨口径不可比**。
2. **R13:409 / R12:312「`ctx.topic` 原样插提示词」仍成立，但 F-2 读的不是它**：F-2 读 `tag_hints`，`ctx.topic` 只被 K-1 与 L-13 使用 ⇒ 只修 `ctx.topic` 人话化**不会让 F-2/F-2b 动一个数**。⚠️ 这是本轮最容易误导读者的地方。

---

## 6. 守卫与不符项

| 守卫 | off | on | 判定 | 说明 |
|---|---|---|---|---|
| `L-6` 精确重复率 | 0.0 | 0.0 | **未恶化** | per-message，97 |
| `L-5` 模板命中率 | 0.0 | 0.0 | **未恶化** | per-message，97 |
| `L-7` 8-gram 近重复率 | 0.2577（25/97） | **0.1856（18/97）** | **未击穿（且下降）** | ⚠️ **n=97 未估噪声带** ⇒ 只写「未恶化」，不写「改善」 |
| `F-1` 非功能性闲聊率 | 0.628866 | 0.628866 | **未恶化** | per-message，97；防「用旁白换线索」 |
| `meta.json` | 存在（events 9282） | 存在（events 9286） | **满足** | 缺则全批封顶 probe |
| `L-13` 内部 token 泄漏 | 0/97 | 0/97 | **未见恶化** | ⚠️ 分母 97 ≠ R17 的 686，**不可混比、不可求差** |

**不符项**：`F-2b` 为 **per-thread** 单位且**噪声带上界未估计** ⇒ 按纪律**不得借用消息级 B2 带**，本报告只报 `0/30 → 7/30` 的计数与比率，不据此判效果。

---

## 7. 截图（5 张真渲染，全部取自本轮 on 臂）

**数据来源（唯一）**：`run_on/run.jsonl`（sha256 `6e08b25f…`）→ `gen_threads.py` → `threads.json`（sha256 `5120df82…`）。

```bash
cd <repo>/code
# ① 由 on 臂真源派生页面数据（不写世界；只搬运 thread_id / tag_hints / ctx）
python3 frontend/tools/gen_threads.py \
  --log  ../v2/evidence/r19_topicbreadth_n8r24_seed42/run_on/run.jsonl \
  --meta ../v2/evidence/r19_topicbreadth_n8r24_seed42/run_on/meta.json \
  --out  frontend/sample/dialogue_r19_topicbreadth_on/threads.json --label r19tb_on
# ② 复用已在跑的静态服务（**未起新进程**：PID 477109 监听 0.0.0.0:8848，服务本仓库 code/frontend）
# ③ 四视图 → 直接写入本报告的真实截图目录（第 5 个参数 = 输出目录；脚本内部 mkdir -p）
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
  sample/dialogue_r19_topicbreadth_on/threads.json r19tb_on 6e08b25f \
  ../v2/evidence/r19_topicbreadth_shots
# ④ 「真展开线程」定向图（页面用 q= 正文搜索过滤到该线程；页面没有 thread= 入参，见下注）
python3 frontend/tools/shot.py \
  --url "http://127.0.0.1:8848/dialogue.html?still=1&multi=0&min=0&q=%E4%B8%A4%E5%8C%B9%E5%B8%83%E5%85%88%E5%88%AB%E6%80%A5%E7%9D%80%E5%8E%8B&sort=turns&data=sample/dialogue_r19_topicbreadth_on/threads.json" \
  --out ../v2/evidence/r19_topicbreadth_shots/r19tb_on-thread-TH-P007-P001-3-6e08b25f.png \
  --width 1400 --height 900
```

> **实际取证序列（如实登记，避免"照抄后对不上"）**：本轮执行时 ③ 我漏传了第 5 个参数，`dialogue_shots.sh` 于是用了它自己的默认输出目录 `../v2/evidence/d7_shots`（旧报告目录），四张图生成后由我用 `mv` 移入 `v2/evidence/r19_topicbreadth_shots/`。**上面 ③ 写的是修正后的正确命令**（第 5 参数已补上，2026-10-22 20:44 用 `/tmp/r19_shots_verify` 空跑验证过：`OK: ...{chat,rhythm,spread,600}...`，4 张全部 `SHOT OK`、`blank_retries=0/2`）。⚠️ **重渲染会得到同一视图但字节不保证逐位相同**（本次复验 chat 图 301,824 B vs 存档 301,802 B）⇒ 表中的 5 个 sha256 是**存档件**的指纹，复跑请以表为准、不要把新图的 sha 当成"对不上"。

| 图 | 文件 | 尺寸 | sha256 | 视图 |
|---|---|---|---|---|
| ①「真展开线程」主图 | `v2/evidence/r19_topicbreadth_shots/r19tb_on-thread-TH-P007-P001-3-6e08b25f.png` | 1400×900 | `682b7101eac0892ed001b95ce051bf28c6928866c07978ba9dd8994c2e19162e` | 对话流（`q=两匹布先别急着压` 过滤到 `TH-P007-P001-3`） |
| ② 整体观看台 | `.../r19tb_on-chat-6e08b25f.png` | 1400×900 | `d9106ffaff6f520f2909e29e783236c091be53903224c691d788d8183439cb8e` | 全量对话流 |
| ③ 节律·串门 | `.../r19tb_on-rhythm-6e08b25f.png` | 1300×1050 | `0ec86af9e264f24cf3742d3b61cc1cc3954c734ead9a9729f837b948d9b5b032` | `view=rhythm` |
| ④ 闲话传播 | `.../r19tb_on-spread-6e08b25f.png` | 1300×900 | `21e15a5375900aecc2ea7d40cc59ba8c98b6ce39be6c103b0885105960ccb1be` | `view=spread` |
| ⑤ 600px 判读 | `.../r19tb_on-600-6e08b25f.png` | 600×900 | `b58e60891c1507fc42be096a1d659ce0c9d74819a9f45cbc510399c023c6416b` | 全量口径 |

**图① 展示了什么（人工核对原文）**：线程 `TH-P007-P001-3`（阿林 ↔ 老周，6 轮），第 4 轮「老周：你那两匹布先别急着压，我这儿还欠着王木匠家半袋谷子…」→ 第 5 轮「阿林：…王木匠家那半袋谷子你慢慢攒，我这儿还有一小包…陈皮，回头给你送两片…」→ 第 6 轮「老周：陈皮你留着自个儿泡吧，我这儿正给西头老刘家修那半截篱笆呢…」。该线程的 `tag_hints` 依次累积为 `scarce_buy` → `scarce_buy,savings` → `scarce_buy,savings,rel_maintain`，是 §4 中 `landed=true` 且 **三标签**的代表样本。

**如实登记的取证细节**：

- **复用既有静态服务（PID 477109），未起新进程**。
- 每张图 `blank_retries = 0/2`，`blank_cumulative = 7/215`（`shot.py` 的 T282 观察哨：已知低概率首帧空白竞态，本次**未发生空白、未掩盖**）。
- **页面不支持 `thread=` 入参**（`src/dialogue.js` 只读取 `data/person/place/min/multi/q/sort/leak/world`，`thread` 仅在点击时被**写出**到 URL）⇒ 定向到具体线程只能用正文搜索 `q=` 过滤。本图用的就是该方法，**未修改任何数据**。
- 若某条被抽样的 `landed` 事件在页面上定位不到（消息被折叠/需滚动），本报告选择**同线程内页面上可见的相邻轮次**作展示，并在图注说明；本轮图①的定位成功，未发生"覆盖不到"的情形。

---

## 8. 未采用方案：`feat/r19-life-anchor`（`7825d66`，"生活锚点"）

- **内容**：把「我现在在哪儿 / 什么时辰 / 手上正做着什么事」在**生成前**塞进提示词（`LIFE_PROMPT_LIFE_ANCHOR`，默认 OFF）；改动 `code/life/agent.py`(+37)、新增 `code/life/life_anchor.py`(186)、`code/life/tests/test_r19_life_anchor.py`(177)，**21 项单测通过**。
- **未跑批**：该分支只到单测；本轮未进入 on/off 跑批。
- **本轮不选的原因**：① 一轮只能有一个变量——话题展开臂已经要动提示词装配，再叠一条"锚点句"就无法归因；② 它缺独立判据：锚点句是否让台词更像"手上正有事"需要新尺子或新词表（旧词表无 sha、不可复算），成本高于本轮预算；③ 它的风险面更大（每轮都改提示词 ⇒ 直接冲击 L-7/L-5 守卫）。
- **后续最小验证形态（给下一轮）**：单独分支 + 两臂（OFF/ON）同 seed n16×60；指标 = 「地点/时辰/手上的事」三类**具体性锚点命中率**（词表先冻结 sha）＋`L-7`/`L-5` 守卫＋`dialogue.tokens_in` 的 DiD（该行 ≈ 多少 token/条，做法同 C-1 的 §5.5）；只有命中率与守卫同时成立才谈效果。

---

## 9. 遗留与口径说明（附录）

1. **L-13**：本批两臂 **0/97**，只能写「**未见恶化**」——且**分母 97 与 R17 的 686 不同，不可混比、不可求差**。历史读数（R17 a1 全批 9/686 = 1.312%，曾被引用为「≤7 条」）的守卫出处待 D8 预注册原文落定；**本轮不改判、不写成突破阈值**。另：`ctx.topic` 仍是内部 token（本轮的 `_topic_label()` 只作用于提示词呈现，未改字段语义）⇒ **不得出现「L-13 归零」表述**。
2. **R15 截图**：`reports/README.md` 已改口径为「**未入库** + 原因 + 修订日期 2026-10-22」，渲染命令与 8 个原 sha 留在 R15 §5.4。
3. **R17 §5.9**：a1 臂已收批并回填读数，但两臂**均无 `meta.json`** ⇒ d5 准入 `REJECTED / probe`，读数标注「**过程记录、不入结论**」。
4. **不可跨词表求差值**：旧词表（board-scout 2026-10-22 20:11 复核所用版本）未留 sha、已不可复算 ⇒ 与现词表数字**只能并列**，禁止写「9.6% → X%」「解决 N 倍」。
5. **本批 `assertions.code_unchanged_during_run`**：两臂 `meta.json` 存在且 assertions 通过；但 `code_sha` 差异已由 §3.1 的「空 diff + 四子树指纹逐位相同」证明不影响运行代码。

---

## 10. 结论档位

### 最终档位：**部分有效（方向为正，强度＝弱证据）**

**一句话**：话题展开机制**确实生效、且被判为「真展开」的占 8/10**，但这是 **pilot 规模、单 seed、非盲判、擦线通过** 的弱证据，**不外推**，也不等于「居民对话更有生活气息了」。

**必须并列的限定条件（缺一条即视为夸大）**：

| # | 限定条件 |
|---|---|
| 1 | precision = **8/10 = 0.80**，Wilson95 **[0.490, 0.943]**——下界 0.49 > 门槛 0.4，但**距门槛仅 0.09** |
| 2 | 本批排除性余量仅 **0.9pp**（`T` Wilson 下界 **0.1199** vs off 门控假阳性上界 **0.1111**）——这是 **n=47 下发样本窄**所致，**属本批限制**，不是「稳健通过」。放量到 n16（下发约 343 条）后区间收窄：`T=15%` 时下界 **0.115** 仍 > FP 上界 **0.025**（3/342），余量约 **9pp** ⇒ **真正会卡住放量的是 precision，不是排除性**（不得把「排除性擦线」写成放量的主要风险，否则下一轮会防错方向） |
| 3 | 样本：**n8r24 / 97 条消息 / 67 相邻对 / 10 条判定事件 / 单 seed / 单批 / 2 个 night 窗** ⇒ **不外推** |
| 4 | **非盲判**：`tag 追加` 按构造只可能来自 on 臂，臂标签无法隐去；判定者**先跑指标后判读**，未满足预注册 B.3「先判后算」的顺序 ⇒ 口径与判据未变，但**挑样空间不能宣称已排除** |
| 5 | **下一轮判定线（侦察员已冻结，B.4-v2）**：precision 判定线 = **≥20/30**（19/30 的 0.633 与 Wilson 下界 0.455 仍属擦线）；且**不回溯**——R19 的 8/10 按 B.4（`8≤N<15` 全量判）成立，**不得用 v2 重判本轮** |
| 6 | 结论**只覆盖「话题展开」一维**：线程内可承载 **≥2 条线索**的比例 **0 → 23.3%**（机制侧 7/30）；**不是**"居民对话更有生活气息了"；`tag_replaced` 两臂皆 **0**（只追加不替换） |

| # | 结论 | 档位 | 依据 / 分母 |
|---|---|---|---|
| 1 | 开关生效、门控在排除（机制侧存在性事实） | **已验证（机制侧）** | `D 0→47`、`landed 10`、`T 21.28%`、off 门控假阳性 1/47 |
| 2 | 被判定为「真展开」的比例 8/10 | **部分有效（弱）** | Wilson [0.490,0.943]，n=10 |
| 3 | 线程内可承载 ≥2 线索的线程占比 0→23.3% | **部分有效（机制侧）** | 7/30，per-thread，无可用带 |
| 4 | 对话内容未被写碎（不恶化守卫） | **未恶化** | content_drift 0.626866 vs 0.626866 |
| 5 | 「居民对话更有生活气息」 | **无结论（不得宣称）** | 单维、单臂对读、pilot 规模、非盲判 |
| 6 | 本轮「无效果 / 无效」 | **不得写** | 「无结论」≠「无效」 |

---

## 11. 复现清单（全部只读，除截图外不起进程）

```bash
REPO=<仓库根>
E=$REPO/v2/evidence/r19_topicbreadth_n8r24_seed42
cd $REPO
python3 $E/summarize_arms.py                 # 双臂读数 → 对照 $E/readings.md / summary.json
python3 $E/fingerprint_4trees.py             # 四子树指纹（期望 f1645dcfa9cb06cd，110 文件）
python3 $E/off_gate_fp.py                    # off 基线门控假阳性
cd code && python3 -m obs llm-cost --log ../$E/run_off/run.jsonl --require-provider openai_compat | head -c 300
cd code && python3 -m obs llm-cost --log ../$E/run_on/run.jsonl  --require-provider openai_compat | head -c 300
# 截图（需要静态服务在跑）
cd code && python3 frontend/tools/gen_threads.py --log ../$E/run_on/run.jsonl --meta ../$E/run_on/meta.json \
  --out frontend/sample/dialogue_r19_topicbreadth_on/threads.json --label r19tb_on
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 sample/dialogue_r19_topicbreadth_on/threads.json r19tb_on 6e08b25f ../v2/evidence/r19_topicbreadth_shots
```

> **本报告引用的证据 commit**：`c523fd7`（`feat/r19-topic-breadth` tip，含 §3.2 的 precision 抽样修正）；代码 commit：`dd0c2bc`；报告自身 commit 待提交后回填。
