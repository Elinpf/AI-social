# R11 图片证据 · 引用片段与校验回执（可直接粘贴到报告）

> 生成器：`tools/r11/make_r11_evidence_shots.py`（只读真实产物，零 mock / 零手绘）
> 图源批：OFF = `v2/evidence/run_f6_off_n16r60_seed42`（run.jsonl sha256 `c73bead6…`）｜
> ON = `v2/evidence/run_f6_on_n16r60_seed42`（run.jsonl sha256 `7de6a7be…`）｜两臂 code_sha `895b9a3`（同树，唯一差异 env）
> 生成时刻：2026-10-21 16:1x（渲染时间，非跑批时间）

## 1. 可直接粘贴的 Markdown 引用片段

### 1.1 F-6 ON vs OFF（带分子/分母 + Wilson95）

```markdown
![R11 F-6 ON vs OFF](v2/evidence/r11_shots/f6_on_vs_off_n16r60_seed42-f6-memory-rate.png)

**图 1 · F-6「跨天记忆进对话」ON vs OFF**（图源批 `run_f6_off_n16r60_seed42` / `run_f6_on_n16r60_seed42`，
run.jsonl sha256 `c73bead6…` / `7de6a7be…`，code_sha `895b9a3`，n16×60 seed42）
OFF `19/510 = 3.73%`（Wilson95 [2.40%, 5.75%]）｜ON `57/510 = 11.18%`（Wilson95 [8.73%, 14.21%]）｜Δ `+7.45pp`。
两臂区间不重叠 ⇒ 按 R11 §3.3 判据「显著」。数据来源 `tools/d5/dialogue_metrics.py` 的 `F-6_crossday_memory.timeref_rate`
（OFF `0.037255` / ON `0.111765`），图内数值由正文 11 词表直数复核一致。F-6 只测「提到过去」，不测「引用是否正确」。
⚠ **必须与图 4 并列陈述**：同一干预在 L-7 上从 `181/510` 升到 `332/510`（`+29.61pp`），越过预注册闸门
⇒ 本轮的完整结论是「**F-6 能力提升（+7.45pp）的代价是套路化（L-7 +29.61pp）**」，不得只报正向一侧。
```

### 1.2 ON 臂「注入的记忆 → 生成的正文」真实样本（正例 + 反例）

```markdown
![R11 ON 臂注入记忆样本](v2/evidence/r11_shots/f6_on_n16r60_seed42-memory-injected-dialogue-samples.png)

**图 2 · ON 臂注入记忆与生成正文的真实样本**（图源批 `run_f6_on_n16r60_seed42`，run.jsonl sha256 `7de6a7be…`）
4 行样本按 `seq` 定位：`seq 27449`（L27450，正文逐字吸收注入的「少放半勺盐/多搁一把干贝」，共享 7 个 4-gram）、
`seq 21821`（L21822，命中时间回指词「上回」但与注入的两条汤类记忆 **0 个 4-gram 重合**）、
`seq 29481`（L29482，共享 26 个）、`seq 34341`（L34342，共享 14 个）。
⇒ **「F-6 命中」≠「用上了注入的记忆」**；图只能证「注入发生了 + 正文与记忆原文有字面重合」，不证「引用语义正确」。
注入面：510 条 MSG 中 412 条带 `ctx.memory_refs`（OFF 0 条），共引用 824 次、仅 128 个不同 `mem_id`（记忆池很窄）。
```

### 1.3 跑批健康度

```markdown
![R11 跑批健康度](v2/evidence/r11_shots/f6_on_vs_off_n16r60_seed42-run-health.png)

**图 3 · 两臂跑批健康度**（数据取自 `meta.json` + `obs llm-cost`，`provider_guard.ok=true`、`problems=[]`）
LLM 调用 2878 / 2878（两臂相同）｜degraded 0 / 0｜events 116,294 / 116,261｜时长 5,201s / 6,436s（+23.75%）｜
`tokens_in` 228,749 / 271,717（+18.78%）｜`tokens_total` 484,835 / 540,840（+11.55%）。
```

### 1.4 恶化项证据：L-7 套路化 + L-13 token 泄漏（与 F-6 增益并列呈现）

```markdown
![R11 L-7 / L-13 恶化项](v2/evidence/r11_shots/f6_on_vs_off_n16r60_seed42-l7-l13-degradation.png)

**图 4 · 恶化项：F-6 增益的代价是套路化**（图源批 `run_f6_on_n16r60_seed42` / `run_f6_off_n16r60_seed42`，
run.jsonl sha256 `7de6a7be…` / `c73bead6…`，code_sha `895b9a3`，两臂 n=510）
- **L-7（8-gram 近重复/口头禅）**：OFF `181/510 = 35.49%`（Wilson95 [31.46%, 39.74%]）→ ON `332/510 = 65.10%`
  （Wilson95 [60.86%, 69.11%]），Δ `+29.61pp`，两区间不重叠；**越过预注册闸门「≤ OFF + 5pp（40.49%）视为未恶化」⇒ 判定：恶化**。
- **L-13（内部 token 泄漏）**：OFF `2/510` → ON `14/510`（**×7.0**，按主题 `whisper` 11 / `scarce_buy` 2 / `combat_training` 1）。
- 结论措辞按预案锁定为「**能力提升的代价是套路化**」：F-6 的 `+7.45pp` 增益与 L-7 的 `+29.61pp` 恶化必须同时陈述，
  不得只报正向一侧、不得写成「改善生活气息」。两项分母均为 510（≥68 达标），与 F-6 同级可判。
```

**机制证据（可定位到日志行）**：ON 臂 332 条近重复消息中 **315 条带 `ctx.memory_refs`**（OFF 臂该数为 0）
⇒ 重复不是随机重复，而是「注入记忆行被逐字吸进正文、并在不同线程间被反复复用」。

- ON 臂最强重复簇：8-gram `先把动作做稳别急` 出现 **25 条**消息，seq =
  `20725, 34416, 56313, 56399, 56556, 56635, 56924, 57001, 57724, 57804, 57862, 58000, 58076, 58378, 60137, 60287, 60330, 60920, 61299, 62319, 69266, 80374, 84301, 86589, 88886`
- OFF 臂最强重复簇：8-gram `账要平肚子也得平` 出现 **5 条**消息，seq = `8456, 21914, 22941, 37147, 38031`
  （对照：两臂最强簇的规模 25 vs 5，量级差 5 倍）
- L-13 命中 seq：OFF = `6049, 99056`（均为 `whisper`）；ON 共 14 条 =
  `whisper` 11 条 `8350, 13356, 62319, 62422, 71011, 74613, 79833, 80012, 82482, 84033, 99021`、
  `scarce_buy` 2 条 `60137, 60920`、`combat_training` 1 条 `21903`

**复算命令（仓库根目录，逐条可粘贴）**：

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
cd $REPO

# ① 官方 L-7 / L-13（唯一来源：tools/d5/dialogue_metrics.py）
python3 -c "
import json
for a in ('off','on'):
    d=json.load(open(f'v2/evidence/r1_f6_{a}_metrics.json'))
    L=d['L_wording']; T=d['L-13_token_leak']
    print(a,'L-7',L['L-7_dup_ngram8_rate'],'L-6',L['L-6_dup_exact_rate'],'L-13',T['n'],'/',510,T['by_topic'])
"
# 期望：off L-7 0.354902 ... L-13 2 / 510 {'whisper': 2}
#       on  L-7 0.65098  ... L-13 14 / 510 {'whisper': 11, 'scarce_buy': 2, 'combat_training': 1}

# ② 独立复算 L-7 计数 + 最强重复簇 seq 列表（与官方同口径：去标点后 8-gram 交集）
python3 -c "
import json,re
from collections import defaultdict
def norm(b): return re.sub(r'[\s，。！？、；：「」（）,.!?;:()\"\'“”‘’…—-]','',b or '')
for a in ('off','on'):
    ms=[]
    for l in open(f'v2/evidence/run_f6_{a}_n16r60_seed42/run.jsonl'):
        d=json.loads(l)
        if d.get('type') in ('MSG_DM','MSG_GROUP','MSG_PUBLIC'):
            p=d.get('payload') or {}
            ms.append((d.get('seq'), norm(p.get('body') or ''), bool(((p.get('ctx') or {}).get('memory_refs') or []))))
    idx=defaultdict(list)
    for i,(s,n,r) in enumerate(ms):
        for j in range(max(0,len(n)-7)): idx[n[j:j+8]].append(i)
    dup=set()
    for g,ids in idx.items():
        if len(ids)>1: dup.update(ids)
    top=max(idx.items(), key=lambda kv: len(kv[1]))
    print(a,'dup',len(dup),'/',len(ms),round(len(dup)/len(ms),6),
          'with_memrefs',sum(1 for i in dup if ms[i][2]),
          '| top8gram',top[0],len(top[1]),[ms[i][0] for i in top[1]])
"
# 期望：off dup 181 / 510 0.354902 with_memrefs 0 | top8gram 账要平肚子也得平 5 [...]
#       on  dup 332 / 510 0.65098  with_memrefs 315 | top8gram 先把动作做稳别急 25 [...]

# ③ L-13 命中行逐条定位（示例：取 ON 的 whisper 泄漏）
python3 -c "
import json
for l in open('v2/evidence/run_f6_on_n16r60_seed42/run.jsonl'):
    d=json.loads(l)
    if d.get('type') not in ('MSG_DM','MSG_GROUP','MSG_PUBLIC'): continue
    p=d.get('payload') or {}; t=(p.get('ctx') or {}).get('topic') or ''
    if t and t in (p.get('body') or ''): print(d.get('seq'), t, (p.get('body') or '')[:60])
"
```

### 1.5 四视图 ON 臂真拍（渲染层证据，非 F-6 证据）

```markdown
![R11 ON chat](v2/evidence/f6_shots/run_f6_on_n16r60_seed42-chat-7de6a7be.png)
![R11 ON rhythm](v2/evidence/f6_shots/run_f6_on_n16r60_seed42-rhythm-7de6a7be.png)
![R11 ON spread](v2/evidence/f6_shots/run_f6_on_n16r60_seed42-spread-7de6a7be.png)
![R11 ON 600](v2/evidence/f6_shots/run_f6_on_n16r60_seed42-600-7de6a7be.png)

**图 4–7 · ON 臂四视图真拍**（图源批 `run_f6_on_n16r60_seed42`，run.jsonl sha256 `7de6a7be…`，code_sha `895b9a3`）。
四视图**看不到 `ctx.memory_refs` 注入**，**不能**用来证明 F-6 生效；它们只证「这批 16 居民 × 60 回合的小镇在正常说话、
正常串门、非黑屏」。图源为既有批产物，生成时刻为渲染时间而非跑批时间。
```

## 2. 复算命令（第二人照做，仓库根目录执行）

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
cd $REPO

# ① 重出四张图表（OFF/ON 官方指标与 cost 件均已入仓）
python3 tools/r11/make_r11_evidence_shots.py --repo . --out v2/evidence/r11_shots \
  --off-metrics v2/evidence/r1_f6_off_metrics.json --on-metrics v2/evidence/r1_f6_on_metrics.json \
  --off-cost v2/evidence/f6_cost_off.json --on-cost v2/evidence/f6_cost_on.json

# ② 图内数值独立复算（正文 11 词表直数，期望 OFF 19/510、ON 57/510）
python3 -c "
import json
T=['昨天','前天','上次','上回','那天','前几天','昨儿','昨晚上','以前','早就','那次']
for a in ('off','on'):
    k=n=0
    for l in open(f'v2/evidence/run_f6_{a}_n16r60_seed42/run.jsonl'):
        d=json.loads(l)
        if d.get('type') in ('MSG_DM','MSG_GROUP','MSG_PUBLIC'):
            n+=1; k+=any(w in ((d.get('payload') or {}).get('body') or '') for w in T)
    print(a,k,n,round(k/n,6))
"

# ③ 样本行定位（图 2 的 4 行）
sed -n '27450p;21822p;29482p;34342p' v2/evidence/run_f6_on_n16r60_seed42/run.jsonl | cut -c1-160

# ④ 图片真实性校验（尺寸/亮度/非全白非全黑/色数/sha256）
python3 -c "
import hashlib,os,sys
from PIL import Image
fs=['v2/evidence/r11_shots/f6_on_vs_off_n16r60_seed42-f6-memory-rate.png',
    'v2/evidence/r11_shots/f6_on_n16r60_seed42-memory-injected-dialogue-samples.png',
    'v2/evidence/r11_shots/f6_on_vs_off_n16r60_seed42-run-health.png']
for f in fs:
    im=Image.open(f); im.load(); px=list(im.convert('RGB').getdata()); n=len(px)
    print(f, os.path.getsize(f), im.size, 'mean=%.1f'%(sum(sum(p) for p in px)/(3*n)),
          'dark%%=%.4f'%(sum(1 for p in px if max(p)<8)/n*100),
          'white%%=%.2f'%(sum(1 for p in px if min(p)>247)/n*100), len(set(px)),
          hashlib.sha256(open(f,'rb').read()).hexdigest()[:16])
"
```

## 3. 校验回执（本次实测输出，2026-10-21）

| 文件 | bytes | 尺寸 | mean_brightness | dark_frac | near_white_frac | distinct_colors | sha256（前 16） |
|---|---|---|---|---|---|---|---|
| `r11_shots/f6_on_vs_off_n16r60_seed42-f6-memory-rate.png` | 162,195 | 1472×960 | 225.5 | 1.9378% | 79.89% | 919 | `0938b9659c3e5eae` |
| `r11_shots/f6_on_n16r60_seed42-memory-injected-dialogue-samples.png` | 525,912 | 2700×1395 | 246.0 | 0.2621% | 93.78% | 1,169 | `355781115665b01c` |
| `r11_shots/f6_on_vs_off_n16r60_seed42-run-health.png` | 191,066 | 2160×1110 | 225.8 | 0.8260% | 77.75% | 1,036 | `cb119b7be929a38f` |
| `r11_shots/f6_on_vs_off_n16r60_seed42-l7-l13-degradation.png` | 250,078 | 2190×990 | 226.0 | 0.8560% | 78.69% | 1,188 | `aedeef024b742528` |
| `f6_shots/run_f6_on_n16r60_seed42-chat-7de6a7be.png` | 262,261 | 1400×900 | 35.6 | 0.0019% | 0.10% | 22,208 | `2cf622ebfd025f71` |
| `f6_shots/run_f6_on_n16r60_seed42-rhythm-7de6a7be.png` | 283,776 | 1300×1050 | 34.3 | 0.0018% | 0.10% | 22,410 | `fc11501c1a421d8f` |
| `f6_shots/run_f6_on_n16r60_seed42-spread-7de6a7be.png` | 192,519 | 1300×900 | 25.4 | 0.0021% | 0.03% | 16,253 | `308844ded88073fd` |
| `f6_shots/run_f6_on_n16r60_seed42-600-7de6a7be.png` | 180,705 | 600×900 | 40.4 | 0.0044% | 0.20% | 18,162 | `54e36930ad154258` |

非退化判据（全部通过）：无空白图（near_white_frac 均 < 94%，图表为白底排版属正常，四视图均 < 0.2%）；
无全黑图（dark_frac ≤ 1.94%）；色数 ≥ 919（不是单色块）；尺寸均为标准输出尺寸且内容目视可读（图 2 已 1:1 裁剪复核字形）。

四视图由 `code/frontend/tools/dialogue_shots.sh` 自身输出 `SHOT OK`（`blank_retries=0/2`），8848 静态服务 `http=200`。
