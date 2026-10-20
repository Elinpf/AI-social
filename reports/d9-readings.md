# D9 轮读数汇总（两臂：A0 vs D9）· 读数与 caveat 登记

> **两臂**：A0（基线，`reply_window_rounds=2`，`884f4541`）vs **D9**（本轮变量臂，`reply_window_rounds=4`，`05636bc`）。同 `n=16` / `rounds=84` / `seed=42` / `provider=openai_compat` / `model=DeepSeek-Flash`。
> **独立复核**：`d9-verify`（project-recon，全程只读）裁定 **PASS-WITH-CAVEATS**，6 条 caveat 见 §6（其中 C-3 / C-5 / C-6 直接决定结论怎么写）。复核报告全文在团队共享工作区 `d9-verify-独立复核.md`（不在本仓库发布）。
> **本文件放读数与 caveat，不放判定**：判定与措辞边界在 `R8-dialogue-density.md` §2 / §7。
> **口径纪律**（`reports/README.md` 三条通用纪律）：每个数值带**来源文件 + sha + 复算命令**；分母 <30 只报事件数不报比率；分母 <68 标 `probe`。

---

## 0. 臂身份与来源对账

### 0.1 两臂身份表

| 臂 | 含义 | `code_sha`（取自该臂 `meta.json`） | `run.jsonl` sha256 / 字节 | `meta.json` sha256 | 规模 |
|---|---|---|---|---|---|
| **A0** | 基线（`reply_window_rounds=2`） | `884f4541b80e5343119b51bf94054b2f54dd4559` | `643f13a528c288d3e9677cb8ac100139224afbd0b46c0f7da0c3a5ed85b13141` / 91,336,366 B | `5fe058f38fa8239854d91db7126f4acb019f0b8692a2dca08610a07c887d4a20` | 16 × 84 / seed 42 / 194,108 事件 |
| **D9** | 本轮变量臂（`reply_window_rounds=4`） | `05636bcde2f1759b1bbc8d9eb74f43ec241be6a9`（= `code_sha_end`） | `abefdf73ca239cda6b4b11ebf1081949f9f278586989d392113b5c57e1c9f427` / 91,343,119 B | `f9ba950acbcc653d91ec2e5d8b2237895916e96d5385c17daf0b558ce539c3d4` | 16 × 84 / seed 42 / 194,126 事件 |

- 文件大小差 **6,753 B**、sha 完全不同、事件数差 **18** ⇒ 非同一文件（§7）。
- **MSG 条数两臂同为 686**：事件差来自记忆/叙事写入类，不影响结构指标（§6 非阻断观察②）。

### 0.2 变量确实改了（可复算）

```bash
git show 884f4541:code/life/dialogue_threads.py | grep -n "reply_window_rounds"   # 2
grep -n "reply_window_rounds" code/life/dialogue_threads.py                      # 4（分支 05636bc）
python3 -c "import json;print(list(json.load(open('code/config/life_v2.json')).keys()))"  # 无 dialogue 段 ⇒ 代码常量即生效值
```

> **C-6 限定（必读）**：两臂 `code_sha` 相隔 **11 个 commit**（`884f4541` → `05636bc`）。因此「唯一变量」只成立于 **「相对 master 的 diff 只动一个文件」** 这一层，**不等于**「两臂 `code_sha` 之间只差一个文件」。本轮实测的零漂移只在配置/指纹层：`engine_version = sha256:a871e36c…` 两臂相同、12 项 `config_components` 逐项 sha256 相同（整体 digest `b4421cfc053d6fb6`）；那 11 个 commit 的逐条 diff **未由 d9-verify 复核**（超出其任务范围）。R8 §3.0 的「漂移仅限 `code/frontend/`」属**引用**，不是本轮新证。

### 0.3 D9 批来源对账（原件 → 仓库复制件）

- 原件 `/tmp/d9_a1_run/`（**只有 `meta.json` + `run.jsonl`**）；复制时点 **2026-10-21 04:09–04:10（+08:00）**，执行者 prompt-writer。
- 复制件 `v2/evidence/run_d9_a1_n16r84_seed42/`：`run.jsonl` **不入库**（`.gitignore:8 **/*.jsonl`），`meta.json` / `llmcost.json` / `host.log` 入库。

| 文件 | 原件 sha256 | 复制件 sha256 | 判定 |
|---|---|---|---|
| `run.jsonl` | `abefdf73ca239cda6b4b11ebf1081949f9f278586989d392113b5c57e1c9f427` | 同 | ✅ 逐位一致 |
| `meta.json` | `f9ba950acbcc653d91ec2e5d8b2237895916e96d5385c17daf0b558ce539c3d4` | 同 | ✅ 逐位一致 |
| `host.log` | **原件不存在** | `c66a735c36f831da…`（2,027 B） | ⚠️ **C-1：作者保存的 stdout 摘录，无法对拍** |
| `llmcost.json` / `llmcost.err` | 原件不存在 | `ecfe861dc5a5a2a2…` / 空（`e3b0c442…`） | 复制件新增，与独立复跑一致（§4.1） |

```bash
sha256sum /tmp/d9_a1_run/run.jsonl /tmp/d9_a1_run/meta.json
sha256sum v2/evidence/run_d9_a1_n16r84_seed42/{run.jsonl,meta.json}
wc -c v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl     # 91343119
```

- **未入库原因（如实登记）**：该批输出直接写 `/tmp`，跑完无人搬入 `v2/evidence/`，因此在本轮之前仓库内确实不存在 `run_d9*` 目录。经 `d9-verify` 复核（真跑成立、非拷贝、读数可复算）后作为 D9 正式对照臂入库。

---

## 1. 口径与复算命令

| 读数 | 源文件（入库） | 复算命令（仓库根执行） |
|---|---|---|
| 密度/线程 | `v2/evidence/d9_density_d9a0.{json,md}`（A0）／`d9_density_d9a1.{json,md}`（D9） | `python3 v2/evidence/d9_density.py --log <run.jsonl> --out-json /tmp/x.json --out-md /tmp/x.md` |
| 回复延迟 | `v2/evidence/d9_reply_latency_a0.{json,md}`（A0）／`d9_reply_latency_d9a1.{json,md}`（D9） | `python3 v2/evidence/d9_reply_latency.py --log <run.jsonl> --out-json /tmp/y.json --out-md /tmp/y.md` |
| d5 全指标 + 准入 | `v2/evidence/d5_metrics_d9a0.{json,md}`（A0）／`d5_metrics_d9a1.{json,md}`（D9） | `python3 tools/d5/dialogue_metrics.py --log <run.jsonl> --meta <meta.json> --out-json /tmp/z.json --out-md /tmp/z.md` |
| 线程字段断言 | `v2/evidence/d9_threads_d9a0.json`（**A0 口径**） | `python3 -c "import json;print(json.load(open('v2/evidence/d9_threads_d9a0.json'))['assertions'])"` |
| LLM 目的层审计 | `v2/evidence/d5_llm_purpose_audit_d9a0.{json,md}`（**A0 口径**） | 头部 `n_llm_calls=3403`、`bad_lines=0` |
| LLM 真实性与成本 | A0 `run_d2_after_n16_seed42/meta.json`；D9 `run_d9_a1_n16r84_seed42/llmcost.json` | `cd code && python3 -m obs llm-cost --log ../<run.jsonl> --require-provider openai_compat` |
| 干净树判定 | `v2/evidence/d5_s0a_d9a0.json`（A0 起跑前核对，`head=05636bc…`、`verdict=PASS`、`blocking=[]`） | 见文件内 `rule` / `nonblocking` 字段 |

> **口径归属（不与新 D9 读数混引）**：`*_d9a0.*`、`d9_threads_d9a0.json`、`d5_llm_purpose_audit_d9a0.*`、`d5_s0a_d9a0.json`、`samples_d9a0/` 全部是**对 A0 日志 `643f13a5` 的复算/采信件**——文件名里的 `d9` 指「D9 轮做的分析」，**不是** D9 臂数据。D9 臂（`abefdf73`）读数在 `*_d9a1.*` 与 `run_d9_a1_n16r84_seed42/` 下。

> ### ⚠️ 口径修正（易踩坑；复核方也踩过一次）
> **d5 命令必须带 `--meta`。** 只给 `--log` 时 `admission.verdict = REJECTED`、`evidence_level = probe`（`B-7_files` / `B-9_event_count` / `B-2b_manifest_effective` / `B-10_provider` 因缺 meta 判 False），**指标数值完全不变**。
> ```bash
> python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_d2_after_n16_seed42/run.jsonl \
>     --meta v2/evidence/run_d2_after_n16_seed42/meta.json --out-json /tmp/d5.json
> sha256sum /tmp/d5.json v2/evidence/d5_metrics_d9a0.json   # 两行相同：a2b55e21831a65ae…
> ```

---

## 2. 定稿抽查：3 个数值亲自重算（不照抄草案）

| # | 抽查项 | 命令 | 本次实际输出 | 对账 |
|---|---|---|---|---|
| 1 | 线程/消息密度 | `python3 v2/evidence/d9_density.py --log v2/evidence/run_d2_after_n16_seed42/run.jsonl --out-json /tmp/d9_density_recheck.json` | `n_messages=686`、`n_threads=206`、`slot_units=381`、`slot_at_cap2=305`、`slot_ge3=0`、`ge3_rounds=89`、`ge6_rounds=68`、`ge3_speakers=9`、`mean_roundtrip=3.0049` | 与入库 `d9_density_d9a0.json` **逐键全等**（sort_keys 后 `diff` 空） |
| 2 | 回复延迟（分母 480） | `python3 v2/evidence/d9_reply_latency.py --log v2/evidence/run_d2_after_n16_seed42/run.jsonl --out-json /tmp/d9_lat_recheck.json` | `denominator=480`、`latency_rounds={1:327,2:153}`、`latency_ge3=0`、`by_channel={dm:{1:231,2:136},group:{1:96,2:17}}`、`unresolved_reply_to=0`、`cross_thread_pointers=0` | 与入库 `d9_reply_latency_a0.json` **15 键逐项相同** |
| 3 | d5 措辞层 L-2/L-3/L-6/L-7 | §1 的 `--meta` 命令 | `L-2=0.819242`、`L-3=0.860058`、`L-6=0.099125`、`L-7=0.488338` | 产物 sha256 **与入库件相同**（`a2b55e21831a65ae…`） |

- 与 `d9-verify` 的一致性：复核方独立复算的五项措辞指标（A0/D9 = 0.819242/0.810496、0.860058/0.846939、0.018950/0.021866、0.099125/0.090379、0.488338/0.488338）与本文件**逐位相同**，无需修正。
- 另按 purpose 分组复算了提示词对拍（§7.3）：`judge 717`、`importance 1747`、`negotiation 81`、`plan 16`，合计 **2561 / 3403 = 75.26%**，与复核报告一致。

---

## 3. A0 臂读数（`run_d2_after_n16_seed42`，sha8 `643f13a5`）

### 3.1 线程密度（`d9_density_d9a0.md`，`tid_mode`）

- 消息 **686** / 线程 **206** / schema=`explicit`；渠道 `dm 497 / group 126 / public 63`
- 轮数分布 `{'1':102,'2':15,'3':6,'4':14,'5':1,'6':68}`；条数分布 `{'1':102,'2':14,'3':6,'4':14,'6':62,'11':1,'12':1,'13':3,'15':2,'18':1}`
- 平均往返 **3.0049**、平均条数 **3.3301**
- **≥3 轮 89/206 = 43.2039%**；**≥6 轮 68/206 = 33.0097%**；**≥3 发言者 9/206 = 4.3689%**
- 最长线程（条数）`TH-P009-Gplace-hall-67`：18 条 / 6 轮 / 8 发言者 / reply 17；最长（轮数）`TH-P001-P005-39`：6 条 / 6 轮 / DM
- `reply_coverage = 0.699708`

### 3.2 单 slot 上限的实际约束

- 单位 `(agent, day, slot)` **381**；分布 `{'1':76,'2':305}` ⇒ 顶格 `max_messages_per_slot=2` **305/381 = 80.05%**，**≥3 条 0 个**

### 3.3 回复延迟（`d9_reply_latency_a0.md`）

- 分母 **480**：`t+1 = 327`、`t+2 = 153`、0 回合 0、**≥3 回合 0**；DM `231/136`、GROUP `96/17`

### 3.4 d5 全指标（`ADMITTED / evidence`）

- **F**：F-1 **0.760933**（功能性 164）；F-2 0.0；F-2b 0.0；F-3 **0.242991**（分母 107）；F-4 **0.076923**（张力 39 / 修好 3）；F-5 1.0；F-6 0.06414；F-7a 0.155977（**旧口径，R4 §2 已声明不可引用**）
- **L（n=686）**：L-1 p50/p90 = 54.0/97.5（去括号 p50 41.0）；**L-2 0.819242**；**L-3 0.860058**；L-4 0.069971；L-5 0.01895；L-6 0.099125；**L-7 0.488338**；L-8/8b/8c/9/10 = 0；L-11 0.727127（n=577）；L-12 0.656501、L-12b 0.510433（n=623）；L-13 0.039359（27/686）
- **S/K/E**：S-1C p50/p90/max = 2.0/6.0/6.0；`single_msg_thread_ratio 0.495146`；`multi_turn_thread_ratio 0.436893`；S-4 指针完整率 **1.0**（480）；K-1（480 对）`1.0 / 0.547917 / 0.685417`；K-1b（670 对）`0.491045 / 0.197015`；E-1 0.529321、E-2 42.833819、`dialogue_calls 714`、`degraded_ratio 0.0`

### 3.5 LLM 真实性（`d5_llm_purpose_audit_d9a0` + `meta.json`）

- `LLM_CALL` **3403**（无法解析 0）；`tokens_in 265,579 / tokens_out 332,426`；`provider={openai_compat:3403}`、`degraded_calls=0`、`fallback_detected=false`
- 分目的：`dialogue 714`（cached 68）、`judge 717`（全 thinking）、`importance 1747`（cached 1597）、`reflect 112`、`negotiation 81`、`describe 16`、`plan 16`、**`narrate 0`**
- 成本结构：`judge` 占 tokens_out **75.81%**（252,020 / 332,426）

---

## 4. D9 臂读数（`run_d9_a1_n16r84_seed42`，sha8 `abefdf73`）

### 4.1 批身份与验真

- `code_sha = code_sha_end = 05636bcde2f1759b1bbc8d9eb74f43ec241be6a9`；`n=16`、`rounds=84`、`rounds_effective=84`、`rounds_contiguous=true`、`seed=42`、`n_in_log=16`、`seed_in_log=42`
- `provider={openai_compat:3403}`、`model={DeepSeek-Flash:3403}`、`llm_calls=3403`、`llm_cached=1729`（0.5081）、**`degraded_calls=0`**、**`fallback_detected=false`**、`mock_precalib_msg_count=0`、`git_dirty_code_files=[]`
- `events=194126`（= `wc -l`）；`run_bytes=91,343,119`；`02:05:04 → 03:32:23`、`duration_sec=5239`（复核按时间戳复算 5239.0 s，自洽）
- **obs 验真原件**（`llmcost.json`，sha8 `ecfe861d`）：
  ```bash
  cd code && python3 -m obs llm-cost --log ../v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl --require-provider openai_compat
  # RC=0；provider_guard: {"ok": true, "by_provider": {"openai_compat": 3403}, "problems": []}
  # total: {"calls": 3403, "cached": 1729, "degraded": 0, "thinking": 733,
  #         "tokens_in": 265486, "tokens_out": 317162, "tokens_total": 582648}
  ```
- **"真跑"判据以字段组合为准，不单引 host.log 那句**（C-1）：`code_sha==code_sha_end` + provider 全 `openai_compat` + `llm_calls>0 且 cached 自洽` + `degraded_calls=0` + `fallback_detected=false` + `seed_in_log==seed_declared` + `n_in_log==n_declared` + `rounds_effective==rounds_declared` + `wc_l==events`，九条逐条成立。
- **配置零漂移的运行侧证据**：`WORLD_INIT.config_components` 两臂 **12 项逐项 sha256 相同**（含 `life_v2.json = sha256:ff230d69…`；整体 digest `b4421cfc053d6fb6`）
  ```bash
  python3 - <<'PY'
  import json
  def wi(p):
      for ln in open(p,encoding="utf-8"):
          r=json.loads(ln)
          if r.get("type")=="WORLD_INIT": return (r.get("payload") or {}).get("config_components") or {}
  a=wi("v2/evidence/run_d2_after_n16_seed42/run.jsonl"); b=wi("v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl")
  print("identical:", a==b, "n:", len(a))    # identical: True  n: 12
  PY
  ```

### 4.2 d5 准入与关键指标（`d5_metrics_d9a1.md`）

- **准入：`ADMITTED` / `evidence`**（`B-15_msg_volume` 686≥150 PASS、`B-10_provider openai_compat`、`B-20_model_no_mock DeepSeek-Flash`、`B-12_degraded_ratio 0.0`）
- **L**：**L-2 0.810496**、**L-3 0.846939**、L-5 0.021866、L-6 0.090379、**L-7 0.488338**、L-4 0.062682、L-13 0.021866（15/686）
- **F**：F-1 0.753644（功能性 169）、F-3 0.190476（分母 105）、F-4 0.03125（张力 32 / 修好 1）、F-6 0.05102、F-7a 0.158892

### 4.3 密度 / 延迟（`d9_density_d9a1.md` / `d9_reply_latency_d9a1.md`）

- 消息 **686** / 线程 **206** / 渠道 `dm 497 / group 126 / public 63`；平均往返 **3.0049**、平均条数 **3.3301**
- `slot_units=381`、`units_at_cap2=305`、`units_ge3=0`；`threads_ge3_rounds=89`、`threads_ge6_rounds=68`、`threads_ge3_speakers=9`；`reply_coverage=0.699708`
- 延迟：分母 **480**、`{1:327,2:153}`、`≥3 = 0`、分渠道与 A0 同

---

## 5. 两臂对账

### 5.1 结构层：**零差异**（可独立复算的存在性事实）

`n_messages` / `n_threads` / 渠道计数 / `per_slot` 全分布 / `per_agent_day` 全分布 / `threads`（条数·轮数·发言者直方图、`top10_by_msgs`、最长线程两条）/ `reply_coverage` / `mean_roundtrip` / `mean_msgs_per_thread`，以及延迟的 `denominator` / `latency_rounds` / `by_channel` / `latency_ge3` —— **逐项相同**。

```bash
python3 tools/d5/dialogue_metrics.py --log <A0> --meta <A0 meta> --out-json /tmp/a0.json
python3 tools/d5/dialogue_metrics.py --log <D9> --meta <D9 meta> --out-json /tmp/d9.json
python3 - <<'PY'
import json
a=json.load(open('/tmp/a0.json')); b=json.load(open('/tmp/d9.json'))
def walk(x,y,p=""):
    if isinstance(x,dict) and isinstance(y,dict):
        for k in sorted(set(x)&set(y)): yield from walk(x[k],y[k],p+"/"+k)
    elif x!=y: yield (p,x,y)
for p,x,y in walk(a,b): print(p,"A0=",x,"D9=",y)
PY
```

### 5.2 措辞 / 语义层：有差异（同分母 686、同口径，只列差项）

| 指标 | A0 | D9 | Δ | 分子/分母 |
|---|---|---|---|---|
| L-2 旁白代理率 | 0.819242 | 0.810496 | **−0.008746（−0.87 pp）** | 562/686 → 556/686 |
| L-3 括号块率 | 0.860058 | 0.846939 | **−0.013119（−1.31 pp）** | 590/686 → 581/686 |
| L-6 精确重复率 | 0.099125 | 0.090379 | **−0.008746** | 68/686 → 62/686 |
| L-5 模板命中率 | 0.018950 | 0.021866 | **+0.002916（反向）** | 13/686 → 15/686 |
| L-4 第三人称自指 | 0.069971 | 0.062682 | −0.007289 | 48/686 → 43/686 |
| L-13 token 泄漏 | 0.039359 | 0.021866 | −0.017493 | 27/686 → 15/686 |
| **L-7 8-gram 重复率** | **0.488338** | **0.488338** | 0.000000（**计数巧合，见 C-3**） | **335/686 → 335/686；触发集合不同（jaccard 0.5581）** |
| F-1 非功能性闲聊 | 0.760933 | 0.753644 | −0.007289 | 522/686 → 517/686（功能性 164→169） |
| F-3 情绪呼应 | 0.242991 | 0.190476 | −0.052515 | 26/107 → 20/105 |
| F-4 修复闭环 | 0.076923（3/39） | 0.03125（1/32） | — | 事件级、分母 <68 ⇒ `probe` |
| F-6 跨天记忆引用 | 0.064140 | 0.051020 | −0.013120 | — |
| F-7a 越界提及（旧口径，不可引用） | 0.155977 | 0.158892 | — | 见 C-5：judge 侧指标不吃正文 |
| K-1 backref / lexical | 0.547917 / 0.685417 | 0.531250 / 0.687500 | −0.016667 / +0.002083 | 480 对 |
| K-1b backref / lexical | 0.491045 / 0.197015 | 0.468657 / 0.185075 | −0.022388 / −0.011940 | 670 对 |
| E-2 tokens/msg | 42.833819 | 42.775510 | −0.058309 | — |

> **L-7 读法（C-3，禁止误写）**：两臂计数相同（335/686）**不是**「措辞没变」，也**不是**「疑似复用」。作者与复核方各自复算触发集合：`|A0|=335`、`|D9|=335`、`交集=240`、`并集=430`、**jaccard = 0.5581**（同位同时命中 240 条，两侧各有 95 条命中位置不同）。⇒ 正确写法：「**L-7 计数相同属巧合，触发消息集合不同**」。
> **幅度读法**：每项差异在 686 条分母上只对应个位数条消息（ΔL-2 ≈ 6 条、ΔL-3 ≈ 9 条）；**只能写方向性**，不得写「明显改善」，也不得隐去 L-5 反向 +0.29 pp。

### 5.3 提示词级对拍（按 purpose 分组，作者独立复算）

| purpose | A0 调用 | D9 调用 | 逐位相同 `prompt_hash` | 比例 | 交集 | unique A0 / D9 |
|---|---|---|---|---|---|---|
| `judge` | 717 | 717 | **717** | **100%** | 717 | 717 / 717 |
| `importance` | 1747 | 1747 | **1747** | **100%** | 150 | 150 / 150 |
| `negotiation` | 81 | 81 | **81** | **100%** | 16 | 16 / 16 |
| `plan` | 16 | 16 | **16** | **100%** | 16 | 16 / 16 |
| `dialogue` | 714 | 714 | 248 | 34.7% | 218 | 646 / 651 |
| `reflect` | 112 | 112 | 26 | 23.2% | 22 | 108 / 108 |
| `describe` | 16 | 16 | 0 | 0% | 0 | 16 / 16 |

- **四类 `judge` / `importance` / `negotiation` / `plan` 合计 2561 / 3403 = 75.26%**，两臂提示词**逐位相同** ⇒ 这四类**不吃正文措辞** ⇒ 两臂世界态一致，差异只可能来自正文措辞层。
- `describe`（0%）/ `reflect`（23.2%）/ `dialogue`（34.7%）**存在差异**，**不得**并入上面那句断言；这三类的派生指标理论上**可受措辞影响**。
- **措辞注意**：不得写成「提示词复用」（会被误读为串味）。逐位相同是**不含正文的确定性输入**所致，反向印证两批是独立生成。

```bash
python3 - <<'PY'
import json
from collections import defaultdict
def calls(p):
    out=defaultdict(list)
    for ln in open(p,encoding="utf-8"):
        r=json.loads(ln)
        if r.get("type")!="LLM_CALL": continue
        pl=r.get("payload") or {}
        out[pl.get("purpose")].append(pl.get("prompt_hash"))
    return out
A=calls("v2/evidence/run_d2_after_n16_seed42/run.jsonl"); B=calls("v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl")
for p in sorted(set(A)|set(B)):
    a,b=A.get(p,[]),B.get(p,[])
    same=sum(1 for x,y in zip(a,b) if x==y)
    print(f"{p:12} {len(a):5} {len(b):5} same={same:5} ratio={same/max(1,len(a)):.3f} inter={len(set(a)&set(b))}")
PY
```

---

## 6. Caveat 清单（来自 `d9-verify`，引用本文件时必须连带）

| 编号 | 内容 | 写作影响 |
|---|---|---|
| **C-1** | `/tmp/d9_a1_run/` 只有 `meta.json` + `run.jsonl`，**无 host.log**；仓库里的 `host.log`（2,027 B）是**作者保存的 stdout 摘录**，无法与原件对拍。其字段（events=194126、llm_calls=3403、cached_ratio=0.5081、`final_state_hash=sha256:4f4bc8c5…`、`replay_parity=True`、`conservation_ok=True`）与 meta 自洽，但属旁证。 | 引用必须标「作者保存的 stdout 摘录（未能对拍原件）」；真跑判据引 §4.1 字段组合 |
| **C-2** | `meta.side_root = null`，而命令行有 `--side-root /tmp/d9_a1_side` ⇒ meta 未记录声明值。目录仍在：`/tmp/d9_a1_side/freeze_cache/responses` 共 **1674** 个文件 = 本批唯一 `prompt_hash` 数 **1674** | 引「缓存隔离」只能引**目录 + 条数**，不能引 `meta.side_root` |
| **C-3** | L-7 两臂同为 0.488338 是**计数巧合**；触发集合 jaccard **0.5581**、交集 240/335 | **禁止**写「L-7 完全不变 ⇒ 措辞无实质变化」，也禁止写「L-7 相同 ⇒ 疑似复用」 |
| **C-4** | 措辞幅度小：ΔL-2 −0.87 pp、ΔL-3 −1.31 pp、ΔL-6 −0.87 pp，**L-5 反向 +0.29 pp**；分母均 686 | 只能写「方向性变化」；能否称"改善"需 B2/精确二项带支持，复核方不代判 |
| **C-5** | **只有** `judge` / `importance` / `negotiation` / `plan` 四类（合计 2561/3403 = 75.26%）提示词两臂**逐位相同**，即这四类不吃正文 ⇒ **由这四类派生的指标**（含 F-7 越界提及、关系变动判定等 judge 侧指标）不能用来衡量措辞变化。**排除面只到这四类**：`describe` / `reflect` / `dialogue` 派生指标理论上可受措辞影响，**不得**一并排除 | 写结论时把排除面钉死在这四类，别写大 |
| **C-6** | 两臂 `code_sha` 隔 11 个 commit，但 `engine_version`（`a871e36c…`）与 12 项 `config_components`（digest `b4421cfc053d6fb6`）完全相同 | 「唯一变量」只能限定为**相对 master 的 diff**；R8 §3.0 的「漂移仅限 `code/frontend/`」属引用，未由复核方验证 |

非阻断观察两条：① 耗时两口径——`meta.duration_sec=5239`（整进程墙钟）vs `host.log` `[life] … seconds=5216.8343`（内核自报，差 22.2 s 进程外开销），引用须说明哪一层；② 两臂事件数差 18 而 MSG 条数完全相同 ⇒ 措辞差异波及记忆/叙事写入类事件，不影响结构指标。

---

## 7. 反串味核查（证明 D9 不是 A0 的拷贝或改写）

| 证据 | A0 | D9 | 读法 |
|---|---|---|---|
| `run.jsonl` sha256 / 字节 | `643f13a5…` / 91,336,366 | `abefdf73…` / 91,343,119（+6,753） | 不同 |
| 事件行数 | 194,108 | 194,126（+18） | 不同 |
| **正文同位相同** | — | **35 / 686** | 几乎全不同 |
| 唯一正文数 / 交集 | 618 | 624 | **交集仅 34 条** |
| `msg_uid` 前 3 条 | `P-0-0:42:53` 等 | **相同** | **不是串味**：构造式 `seed:seq`，同 seed 必然相同，判重用正文 |
| `dialogue` 提示词 | 714 次 / unique 646 | 714 次 / unique 651 | 逐位相同 248（34.7%），交集 218 |
| 缓存目录 | `/tmp/d2_after16b_side` | `/tmp/d9_a1_side`（独立） | 物理隔离（见 C-2：不引 meta 字段） |
| 缓存条目 | cached 1734 | `responses` 1674 = 唯一 prompt 1674；cached 1729 | 无外来复用 |
| token | out 332,426 | out 317,162 | 不同批 |

```bash
python3 - <<'PY'
import sys; sys.path.insert(0,'tools/d5'); import dialogue_metrics as dm
from collections import defaultdict
def dupidx(p):
    recs,_=dm.read_run(p); msgs=dm.extract_messages(recs)
    norm=[dm.normalize_body(m["body"]) for m in msgs]; idx=defaultdict(list)
    for i,t in enumerate(norm):
        for g in {t[k:k+8] for k in range(max(0,len(t)-7))}: idx[g].append(i)
    dup=set()
    for g,l in idx.items():
        if len(l)>1: dup.update(l)
    return dup, msgs
A,ma=dupidx("v2/evidence/run_d2_after_n16_seed42/run.jsonl")
B,mb=dupidx("v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl")
print("|A|",len(A),"|B|",len(B),"|∩|",len(A&B),"|∪|",len(A|B),"jaccard",round(len(A&B)/len(A|B),4))
ba=[m["body"] for m in ma]; bb=[m["body"] for m in mb]
print("positionwise identical:",sum(1 for x,y in zip(ba,bb) if x==y),"/",len(ba))
print("unique bodies",len(set(ba)),len(set(bb)),"inter",len(set(ba)&set(bb)))
PY
# |A| 335 |B| 335 |∩| 240 |∪| 430 jaccard 0.5581
# positionwise identical: 35 / 686
# unique bodies 618 624 inter 34
```

---

## 8. 线程字段断言（`d9_threads_d9a0.json`，**A0 口径**）

| 断言 | 值 | 读法 |
|---|---|---|
| `msg_uid_unique` | **True** | 消息级 uid 唯一（准入用它） |
| `msg_id_unique` | **False** | `msg_id` 在 `(day,slot)` 内重复（`dup_msg_ids_legacy_known_defect`，如 `D-31-0:16`）——**既知 legacy 缺陷**（R7 §7.1(1)） |
| `participants_consistent` | True / 0 违规 | 参与者集合一致 |
| `ptr_cross_thread` / `ptr_dangling` / `reply_to_same_thread` | 0 / 0 / True | 指针干净 |
| `turn_index_dense` | True / 0 违规 | `tid_mode` 口径；`temporal_mode` 另有 113 处违规，**两口径不可混用** |
| `chain_by_alternation` max / `chain_by_pointer` max | 18 / 6 | 群聊多人回同一条 ⇒ 指针链天然浅；DM 上两者相等（6/6） |
| `temporal_mode` vs `tid_mode` 线程数 | 244 vs **206** | **只许用 `tid_mode`=206** |

---

## 9. 原文样本（`v2/evidence/samples_d9a0/`，samples.md sha8 `972c2087`）

- **A0 口径**：686 消息 / 206 线程 / `explicit`；结构分档 good=78 / mid=54 / bad=74（**结构分档 ≠ 自然度**）
- 最长线程可读样本 3 组（18 / 15 / 15 条），`turns_A` 与指针数匹配
- 【观察，非结论】样本文本里 `（……）` 括号旁白近乎每句都有，与 L-3=0.860 一致；**不得**用它替代读数

---

## 10. 两处"预期内红"（必须复述，否则会被误读为事故）

1. `d5_metrics_d9a0` 的 `B-15_msg_volume` 在本批 **PASS**（686≥150）；D8 两臂（`n4r60`，124 条）当时 `REJECTED`（<150）——**规模不同，不是缺陷**（`60ecd51`）。
2. `d5_s0a_d9a0.json`：`verdict=PASS`、`blocking=[]`、`nonblocking` 2 条（当时未跟踪的 `reports/R8-dialogue-density.md`、`v2/evidence/d9_density.py`）——与"树不干净"无关。

---

## 11. 截图（转交 batch-runner，`d9-shots-push` 回填）

- **D9 需真拍**：来源 run 目录 `v2/evidence/run_d9_a1_n16r84_seed42/`，日志 sha256 `abefdf73…`，渲染命令沿用 `code/frontend/tools/shot.py`；A0 既有四图（`v2/evidence/d7_shots/run_d2_after_n16_seed42-{600,chat,rhythm,spread}-643f13a5.png`）**只作对照**，两批不同源、不得互相替换。

---

## 12. 不可写清单（红线）

- ❌「D9 臂从未跑批」——已复核入库（§0.3）。
- ❌「对话密度提升了 X%」「生活气息变好了」——结构层两臂零差异。
- ❌「L-7 完全不变 / 无变化」——是计数巧合，见 C-3。
- ❌ 用 `judge` / `importance` / `negotiation` / `plan` 四类派生指标（含 F-7）衡量措辞效果；也**不得**把排除面扩大到 `describe` / `reflect` / `dialogue`，见 C-5。
- ❌ 把「唯一变量」写成两臂 `code_sha` 之间只差一个文件，见 C-6。
- ❌ 隐去 L-5 反向 +0.29 pp。
- ❌ 混用 `temporal_mode`(244) 与 `tid_mode`(206) 分母；混引 `*_d9a0`（A0 复算件）与 `*_d9a1`（D9 臂读数）。
