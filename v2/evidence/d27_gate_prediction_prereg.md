# D2.7 验收侧 · 运行期接线验真的**事前预测**（prereg by evidence-gate）

> 落笔时刻：**2026-10-24T16:12:20+08:00**（机器时戳）
> 落笔条件：**B 臂 `run_d27_B_n16r60_seed42` 仍在跑（round 45/60，run.jsonl 38,353,800 B），本文件写于任何 B 臂指标出数之前**。
> 作者：evidence-gate（验收方）。用途：给「改动是否真的生效到运行期」一个**事前**可判定的量化判据，避免事后凑数。

## 1. 为什么需要它（上一个方案为何不通）

原设想「用 `LLM_CALL.prompt_hash` 跨臂比对」**不成立**，两条实证：
1. `prompt_hash` 是**每次调用整段 prompt 的内容 hash**，prompt 内含当次上下文（场景/对象/情绪/需求/最近对话）⇒ C 臂 510 次 `purpose=dialogue` 调用得到 **510 个互异 hash**（实测 distinct=510），两臂集合不可能有交集；
2. `run.jsonl` **不含 prompt 正文**：`LLM_CALL` 字段仅 `cache_key / prompt_hash / meta_digest / model / purpose / tokens_in / tokens_out / provider / cached / degraded / engine_version / tier / thinking / cost_units`；`WORLD_INIT` 仅含 `config_components / config_digest / engine_version / fingerprint / seed / time_U / time_model`，**不含 `prompt_fn_sha256`**（该值只存在于静态渲染件 `v2/evidence/d27_prompt_wiring.json`）。

⇒ 必须换一个**能从日志直接取到、且对 prompt 长度敏感**的量：`purpose=dialogue` 的 `tokens_in` 逐次均值。

## 2. 判据来源（三个数，别人拿这三个数就能自己验）

**① 渲染差 = +35 字符（两处都是）**，取自 `v2/evidence/d27_prompt_wiring.json`：
- `dialogue_prompt_len`：C=258 → B=293（+35）
- `reply_prompt_len`：C=271 → B=306（+35）
- `dialogue_len_delta = reply_len_delta = 35`；`only_narration_half_changed = true`

**② C 臂基线（本批 C 现算，master 主树脚本，run 目录 `v2/evidence/run_d27_C_n16r60_seed42/`）**

| 项 | 值 |
|---|---|
| `purpose=dialogue` calls | **510** |
| 其中 `cached` | **0** |
| `tokens_in` 合计 | **148,940** |
| `tokens_in` 均值 | **292.04** |
| `tokens_out` 合计 | **19,298** |
| `tokens_out` 均值 | **37.84** |

**③ 预测带 = 320~335（用 C 自身数据自校准，不靠"1 字符≈1 token"的粗估）**

不用拍的比值，直接从 C 自己的数据反推 token/字符：
- C 的 dialogue prompt 长度：initiate **258**、reply **271** ⇒ 均值 **264.5 字符**
- C 的 dialogue `tokens_in` 均值 **292.04**
  ⚠ 注意 `tokens_in` 含系统/前缀等固定部分，故该比值是**上界估计**；但两臂固定部分逐字相同，**差值**才是我们用的量，故用"边际比值"更稳：
- ⇒ 边际估计 `token/字符 ≈ 292.04 / 264.5 = 1.104`（若固定部分占比较大，边际比值会更低，最低可到 ~0.6）

由此给出两条边界：
- 上界预测（边际 1.10）：`292.04 + 35×1.104 ≈ 330.7`
- 下界预测（边际 0.6，中文双字词被合并的情况）：`292.04 + 35×0.6 ≈ 313.0`

⇒ **预测区间 ≈ 313 ~ 331**；本文件仍把 `320~335` 记为"强证据带"（偏保守，宁窄不宽），
并把 `302~320` 显式定义为**灰区**（见 §3），因为下界 313 正落在灰区内。

## 3. 判定表（事前写死，事后不得追加档位；区间为**左闭右开**，无重叠无空白）

| B 的 dialogue `tokens_in` 均值（**uncached**） | 判定 |
|---|---|
| `< 302` | **未生效（≈C 或更低）** ⇒ 接线作废，即使 M1 达标也须重查 |
| `[302, 320)` | **灰区：既不得判强证据，也不得判失败** ⇒ 必须补两项再裁：① 用**实际分词器或 provider 返回的 usage** 核 35 字符究竟折多少 token（不按 1:1 估）；② 核 B 与 C 的 dialogue 历史长度分布是否显著不同。两项都排除后仍落灰区 ⇒ 老实写「运行期证据不足，结论降级」，**不许硬凑到某一侧** |
| `[320, 335)` | 新 prompt 确已进入运行时 = **强证据** |
| `[335, 360]` | **仍判生效**；偏上归因于历史更长（旁白使回复变长 ⇒ 后续轮次拼接更长），**不得判失败** |
| `> 360` | 判生效，但须单独说明为何远超预测（多半是历史膨胀），并记一笔 |

> 区间边界说明（避免重叠/空白）：以 302 / 320 / 335 / 360 为切点，`<302`、`[302,320)`、`[320,335)`、`[335,360]`、`>360` 五段互斥且覆盖全数轴。

## 4. 已知假阴性陷阱（处理方式事前写明）

C 臂 dialogue `cached=0`。若 B 出现 `cached>0`，缓存命中调用的 `tokens_in` 会偏低，把均值向下拽、**看起来像 prompt 没生效**。
处理：
- **判定一律取 uncached 均值**；全量均值只作诊断参照，两者并列报；
- 若 B 的 dialogue `cached>0`，另核其 `cache_key` 是否与 C 有交集（有交集说明存在完全相同 prompt，需单独解释）。

## 5. 并列证据（不单独定罪）

M1 `paren_rate`：C = **0.00%**（实测）。B 若起来（预登记要求 ≥30%），则**旁白机制在运行期显然生效**。
两条并列：`tokens_in` 均值异常而 M1 达标 ⇒ 不下「未生效」结论，先查 tokens 记账口径；两条同时异常才判接线失败。

## 6. 复算命令

```bash
# 取 C 臂 dialogue 的 calls/cached/tokens（主树，勿在 worktree 里跑）
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 - <<'PY'
import json
from collections import Counter
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
n=tin=tout=0; c=Counter()
for line in open(p,encoding='utf-8'):
    try: e=json.loads(line)
    except Exception: continue
    if e.get('type')=='LLM_CALL' and (e.get('payload') or {}).get('purpose')=='dialogue':
        pl=e['payload']; n+=1; tin+=pl.get('tokens_in') or 0; tout+=pl.get('tokens_out') or 0
        c['cached' if pl.get('cached') else 'uncached']+=1
print(n, c['cached'], tin, round(tin/n,2), tout, round(tout/n,2))
PY
# 期望输出：510 0 148940 292.04 19298 37.84
```
