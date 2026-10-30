# D9n GOLDEN 与仪器身份（impl-2 交付）

> 本轮编号：**D9n**（原 D9m，因与并行线 `D9m-prereg-narration-action-diversity` 冲突而改名，内容未改）。
> 预登记冻结件：`v2/refs/D9n-prereg-narration-example-rotation.md`
> sha256 = `0d10450232b04327fe7980ddbaa68b694fba9b1b827b433b5b54b5d7c1b06643`

## 1. 四个 GOLDEN（`narration_tail` 整段文本的 sha256）

| # | 组合 | kind | sha256 | seed |
|---|---|---|---|---|
| G1 | 默认关（`LIFE_PROMPT_NARRATION` 未设/0） | initiate | `3646f04995a961b12573157ccd7dc70fa4fef1828c1415209f197aab0972a77c` | 不适用 |
| G2 | 默认关 | reply | `ce2cfb8757b1a053b1a9e811e070c7ef91aa3a90cac2c5b6161dff6543ad324d` | 不适用 |
| G3 | 旁白开 + 旋转关（`LIFE_PROMPT_NARRATION=1`，**不设** `LIFE_PROMPT_NARRATION_ROTATION`） | initiate | `d8382f82eb5285eb78110f40b204e6c99e61645d9a233e1a347f98cff101168d` | 不适用（固定示例） |
| G4 | 旁白开 + 旋转关 | reply | `5e45e318030098824bc32b9d429d8fddb8c55167fb9b35728c5e325525f02d2b` | 不适用（固定示例） |

补充：旋转开（`NARRATION=1 + ROTATION=1`）的整段文本**随选句变化**，故不给单一 sha256；
其正确性由「模板只换示例句」锁死：`_NARRATION_TAIL_ON_TPL[k].format(<D9i 原示例>) == _NARRATION_TAIL_ON[k]`
（单测 `tests/test_life_narration_rotation.py::test_template_differs_from_d9i_on_only_in_example`）。

### 1.1 现场导出命令（不切分支、不动工作树 ⇒ 基线不被污染）

```bash
R=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
cd "$R"
git archive d2a6fa9 | tar -x -C /tmp/d2a6fa9        # d2a6fa9 = feat/prompt-narration-toggle 尖端
cd /tmp/d2a6fa9
# G1/G2 默认关
env -u LIFE_PROMPT_NARRATION -u LIFE_PROMPT_NARRATION_ROTATION PYTHONPATH=/tmp/d2a6fa9/code \
  python3 -c "import hashlib;from life.agent import narration_tail;print({k: hashlib.sha256(narration_tail(k).encode()).hexdigest() for k in ('initiate','reply')})"
# G3/G4 旁白开 + 旋转关
env -u LIFE_PROMPT_NARRATION_ROTATION LIFE_PROMPT_NARRATION=1 PYTHONPATH=/tmp/d2a6fa9/code \
  python3 -c "import hashlib;from life.agent import narration_tail;print({k: hashlib.sha256(narration_tail(k).encode()).hexdigest() for k in ('initiate','reply')})"
```

同源关系：四值与 `code/tests/test_life_narration_rotation.py` 的断言**同源**
（`GOLDEN_OFF_*` / `GOLDEN_ON_*` 常量即上表四值）。

## 2. `HITT_WORLD_SEED` 未设 ⇒ 回落 `"0"`（显式一条）

- 跑批链路**从不设** `HITT_WORLD_SEED`（`run_batch.sh` 只 export `HITT_LLM_PROVIDER`）；
  基线 `meta.switch_declared.HITT_WORLD_SEED = {raw: null, parsed_int: 0}`。
- 因此旋转选句的实际输入是 `sha256("narration-rotate|0|<agent_id>|<round>|<kind>")`。
- **本轮裁决：保持不设**（设 42 会连带改变 `weather.py::world_seed`，破坏单变量）。
- 契约：未设 / 空串 / `"0"` 三者**逐字节等价**（单测 `test_seed_default_fallback_is_zero` 锁定）；
  换 seed ⇒ 序列随 seed 变但仍确定（不得据此认为「序列失稳」）。

## 3. 仪器身份（sha256）

| 文件 | sha256 |
|---|---|
| `tools/d9n/narration_family_lexicon.json`（exp-designer 冻结，权威副本） | `9a87ebb5ee80bb8d991d2c54e1562e312810ed23f1081141e30b98b3f9933edd` |
| `tools/d9n/narration_family.py` | `3dbca76f1f387cd7df6bd1810cb1a0dcd1e347fb17c26d9f23ea9654628ee636` |
| `tools/d9n/narration_example_seq.py` | `e55a97bf254820648d2c85fa48557ca7263b47bf7006060afa6cd146b28fadbc` |
| `tools/d9n/test_narration_family.py`（仪器自测，13 项） | `68b7ec740d443942bf4133a52623152da0969c2f22ba43e94d61a8b524ab7ffd` |
| `tools/d9n/GOLDEN.md`（本文件，填 sha 前的版本） | `f4976a689d5e5878b382685263132d5abb789a3bdfdcccd382adefb53ae36def` |

词表身份：`V_judge` = 闭表 8（蹭/搓/抹/擦/拂/拍/抿/揉）+ 旋转 13（别/挽/拢/让/靠/挪/望/扇/撤/抬/低/伸/侧）= **21 词，顺序即口径**；
`parts_6` = 手背/指腹/指头/手指/手/肩；`objs_13` = 围裙/锉刀/木屑/木花/袖口/袖子/衣襟/竹篮/碗/壶/锅/凳/门槛。

## 4. 复算入口（六条判据）

```bash
R=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
cd "$R"
python3 tools/d9n/narration_family.py \
   --log <arm_out_dir>/run.jsonl \
   --lexicon tools/d9n/narration_family_lexicon.json \
   --out <arm_out_dir>/d9n_judgement.json
# 片段级交叉校验（第三方口径，blocks_total 必须相等）
python3 tools/d9i/narration_stats.py --log <arm_out_dir>/run.jsonl --out <arm_out_dir>/narration_stats.json
# S-DET（两次独立进程应逐字节一致）
PYTHONPATH=code python3 tools/d9n/narration_example_seq.py --agent P003 --rounds 0-23 --kind initiate --out /tmp/s1.json
PYTHONPATH=code python3 tools/d9n/narration_example_seq.py --agent P003 --rounds 0-23 --kind initiate --out /tmp/s2.json
diff /tmp/s1.json /tmp/s2.json && echo "S-DET PASS"
```

## 5. 历史 ON 日志复现结果（`v2/evidence/narr-on-20261030/run.jsonl`，sha256 `fdb31c7e…63ee`）

| 项 | lexicon `baseline_reference` | 本仪器实测 | 一致 |
|---|---|---|---|
| blocks_total | 205 | 205 | ✅ |
| msgs_total | 191 | 191 | ✅ |
| density | — | 1.073298 | ✅（=205/191） |
| 闭表 8 动词计数 | 蹭31/搓5/抹3/擦0/拂0/拍0/抿0/揉1 | 同 | ✅ |
| `蹭\|手` | total 8, P004 5, share 0.625 | total 8, P004 5, share 0.625 | ✅ |
| `蹭\|锉刀` | total 9, n_ge2 3 | total 9, n_ge2 3 | ✅ |
| `蹭\|指腹` / `蹭\|手背` / `蹭\|指头` | 4 / 2 / 1 | 4 / 2 / 1 | ✅ |
| max_exact_dup | 3 | 3 | ✅ |
| max_v | 31（蹭） | 31（蹭） | ✅ |
| max_k / e_dist | 2；0:12 / 1:153 / 2:26 | 同 | ✅ |
| **coverage** | **40/205 = 0.19512** | **66/205 = 0.321951** | ❌ 见 §6 |
| **unassigned_verb_rate** | **0.80488** | **0.678049** | ❌ 见 §6 |

## 6. 已上报的口径缺陷（未擅自改阈值）

`baseline_reference.coverage = 40/205` 是**闭表 8 动词**口径的遗留值；而 `assignment_rules R2` 规定
`V_judge` = 21 词。按 R2 实测：`assigned = 66`（闭表 40 + 旋转动词命中 26），`coverage = 0.321951`，
`unassigned_verb_rate = 0.678049`。⇒ 冻结件里「基线 coverage / unassigned」与「R2 的 V_judge」**不同源**。

按 R2 重算后的自洽取值（**待 exp-designer 以 amendment 确认，本工具不改 lexicon**）：

| 守卫 | 同口径基线 | 门限（沿用冻结件规则式） |
|---|---|---|
| coverage ≥ 0.60 × baseline | 0.321951（66/205） | **0.193171（≥ 40 片段）** |
| unassigned ≤ baseline + 0.10 | 0.678049 | **0.778049** |

注：两套门限下**基线本身两条守卫都通过**（0.321951 ≥ 0.11707；0.678049 ≤ 0.90488），
故该缺陷**不改变基线判定的三态结论**，只改变报告的守卫读数与「门槛是否需要重算」的可复算性。
